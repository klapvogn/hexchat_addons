# -*- coding: utf-8 -*-
"""
HexChat Spell Correction Script - Auto-correction with Space
Shows suggestions after you type a word, press space again to accept

Workflow:
1. Type a word and press SPACE - suggestions appear if misspelled
2. Press SPACE again - automatically replaces with the green suggestion
3. Continue typing normally

No commands needed!
"""

__module_name__ = "spell_correction"
__module_version__ = "3.0"
__module_description__ = "Auto spell correction with space key"

try:
    import hexchat
    import re
except ImportError:
    print("This script must be run under HexChat.")
    raise

try:
    import enchant
    SPELL_ENGINE = "enchant"
except ImportError:
    enchant = None
    SPELL_ENGINE = None
    print("Warning: pyenchant not found. Install with: pip install pyenchant")

# Global variables
spell_checker = None
current_dict = "en_US"
enabled = True
previous_input = {}
check_timer = None
pending_correction = {}  # {context_key: {'word': str, 'suggestion': str, 'position': int}}

# Configuration
config = {
    'max_suggestions': 5,
    'min_word_length': 3,
    'check_delay': 150,  # Check every 150ms
}


def get_context_key():
    """Get a unique key for the current context"""
    channel = hexchat.get_info("channel") or "unknown"
    network = hexchat.get_info("network") or "unknown"
    return f"{network}:{channel}"


def init_spell_checker(dict_lang=None):
    """Initialize the spell checker with specified dictionary"""
    global spell_checker, current_dict
    
    if SPELL_ENGINE is None:
        return False
    
    if dict_lang is None:
        dict_lang = current_dict
    
    try:
        spell_checker = enchant.Dict(dict_lang)
        current_dict = dict_lang
        hexchat.prnt(f"Spell checker initialized with dictionary: {dict_lang}")
        return True
    except enchant.errors.DictNotFoundError:
        hexchat.prnt(f"Dictionary '{dict_lang}' not found. Available dictionaries:")
        for d in enchant.list_dicts():
            hexchat.prnt(f"  - {d.tag}")
        return False


def check_word(word):
    """Check if a word is spelled correctly"""
    if spell_checker is None or not enabled:
        return True
    
    if len(word) < config['min_word_length']:
        return True
    
    if not word.isalpha():
        return True
    
    return spell_checker.check(word)


def get_suggestions(word, max_suggestions=None):
    """Get spelling suggestions for a word"""
    if spell_checker is None:
        return []
    
    if max_suggestions is None:
        max_suggestions = config['max_suggestions']
    
    suggestions = spell_checker.suggest(word)
    return suggestions[:max_suggestions]


def find_word_position(text, word):
    """Find the position of the last occurrence of a word in text"""
    words = text.split()
    for i in range(len(words) - 1, -1, -1):
        if words[i].strip('.,!?;:\'"') == word:
            return i
    return -1


def replace_word_at_position(text, position, new_word):
    """Replace a word at a specific position in the text"""
    words = text.split()
    if 0 <= position < len(words):
        words[position] = new_word
    return ' '.join(words)


def check_input_timer(userdata):
    """Timer to monitor input and detect word completion / double-space"""
    global check_timer
    
    if not enabled or spell_checker is None or check_timer is None:
        return 0
    
    try:
        context_key = get_context_key()
        input_text = hexchat.get_info("inputbox") or ""
        prev_input = previous_input.get(context_key, "")
        
        # Detect double-space for auto-correction
        if context_key in pending_correction:
            # Check if user pressed space again (double space pattern)
            if input_text.endswith('  '):  # Double space detected
                pending = pending_correction[context_key]
                
                # Replace the misspelled word with the suggestion
                text_without_trailing_spaces = input_text.rstrip()
                position = pending['position']
                
                # Get words and replace at position
                words = text_without_trailing_spaces.split()
                if position < len(words) and words[position] == pending['word']:
                    old_word = pending['word']
                    new_word = pending['suggestion']
                    words[position] = new_word
                    new_text = ' '.join(words) + ' '
                    
                    # Calculate cursor position adjustment
                    # Find where the old word was in the original text
                    word_start = 0
                    for i in range(position):
                        word_start += len(words[i]) + 1  # +1 for space
                    
                    # New cursor position should be after the replaced word
                    word_length_diff = len(new_word) - len(old_word)
                    new_cursor_pos = word_start + len(new_word) + 1  # +1 for the space after
                    
                    # Set text and cursor position
                    hexchat.command(f"settext {new_text}")
                    hexchat.command(f"setcursor {new_cursor_pos}")
                    
                    hexchat.prnt(f"\00303✓ '{old_word}' → '{new_word}'\003")
                    
                    # Clear pending correction
                    del pending_correction[context_key]
                    previous_input[context_key] = new_text
                    return 1
        
        # Detect single space (word completion)
        if len(input_text) > len(prev_input):
            # Check if space was just added (not double space)
            if input_text.endswith(' ') and not input_text.endswith('  ') and not prev_input.endswith(' '):
                # Word was just completed
                words = input_text.strip().split()
                if words:
                    last_word = words[-1].strip('.,!?;:\'"')
                    
                    if len(last_word) >= config['min_word_length'] and last_word.isalpha():
                        if not check_word(last_word):
                            suggestions = get_suggestions(last_word, config['max_suggestions'])
                            
                            if suggestions:
                                # Store first suggestion as pending correction
                                word_position = len(words) - 1
                                pending_correction[context_key] = {
                                    'word': last_word,
                                    'suggestion': suggestions[0],
                                    'position': word_position
                                }
                                
                                # Display: red word -> green suggestion + other suggestions
                                first_sugg = f"\00303{suggestions[0]}\003"  # Green
                                other_suggs = ", ".join(suggestions[1:]) if len(suggestions) > 1 else ""
                                
                                if other_suggs:
                                    hexchat.prnt(f"\00304{last_word}\003 → {first_sugg}, {other_suggs}")
                                else:
                                    hexchat.prnt(f"\00304{last_word}\003 → {first_sugg}")
                                
                                hexchat.prnt("\00302Press SPACE again to use the green suggestion\003")
            
            # User is typing after seeing suggestions - clear pending
            elif context_key in pending_correction and not input_text.endswith(' '):
                del pending_correction[context_key]
        
        previous_input[context_key] = input_text
        
    except Exception as e:
        hexchat.prnt(f"Spell check error: {e}")
    
    return 1


def cmd_spellcheck(word, word_eol, userdata):
    """Check current input text"""
    if spell_checker is None:
        hexchat.prnt("Spell checker not initialized")
        return hexchat.EAT_ALL
    
    input_text = hexchat.get_info("inputbox") or ""
    
    if not input_text:
        hexchat.prnt("Input is empty")
        return hexchat.EAT_ALL
    
    words = re.findall(r'\b[a-zA-Z]+\b', input_text)
    errors = []
    
    for w in words:
        if not check_word(w):
            suggestions = get_suggestions(w, 3)
            errors.append((w, suggestions))
    
    if not errors:
        hexchat.prnt("\00303✓ All words spelled correctly!\003")
    else:
        hexchat.prnt(f"\00304Found {len(errors)} misspelled word(s):\003")
        for w, suggs in errors:
            sugg_text = ", ".join([f"\00303{s}\003" for s in suggs]) if suggs else "no suggestions"
            hexchat.prnt(f"  \00304{w}\003 → {sugg_text}")
    
    return hexchat.EAT_ALL


def cmd_spelldict(word, word_eol, userdata):
    """Change spell checking dictionary"""
    if len(word) < 2:
        hexchat.prnt(f"Current dictionary: {current_dict}")
        hexchat.prnt("Available dictionaries:")
        if enchant:
            for d in enchant.list_dicts():
                hexchat.prnt(f"  - {d.tag}")
        hexchat.prnt("Usage: /spelldict <language>")
        return hexchat.EAT_ALL
    
    new_dict = word[1]
    if init_spell_checker(new_dict):
        hexchat.prnt(f"Dictionary changed to: {new_dict}")
    
    return hexchat.EAT_ALL


def cmd_spelltoggle(word, word_eol, userdata):
    """Toggle spell checking on/off"""
    global enabled, check_timer
    enabled = not enabled
    status = "enabled" if enabled else "disabled"
    
    if enabled and spell_checker is not None:
        if check_timer is None:
            check_timer = hexchat.hook_timer(config['check_delay'], check_input_timer)
    elif not enabled:
        check_timer = None
    
    hexchat.prnt(f"Spell checking {status}")
    return hexchat.EAT_ALL


def cmd_spellcancel(word, word_eol, userdata):
    """Cancel pending correction"""
    context_key = get_context_key()
    
    if context_key in pending_correction:
        word_name = pending_correction[context_key]['word']
        del pending_correction[context_key]
        hexchat.prnt(f"Cancelled correction for '{word_name}'")
    else:
        hexchat.prnt("No pending correction")
    
    return hexchat.EAT_ALL


def unload_cb(userdata):
    """Cleanup when script is unloaded"""
    global check_timer, pending_correction, previous_input
    
    check_timer = None
    pending_correction.clear()
    previous_input.clear()
    
    hexchat.prnt(f"{__module_name__} version {__module_version__} unloaded")
    return hexchat.EAT_NONE


# Main initialization
if SPELL_ENGINE is None:
    hexchat.prnt(f"{__module_name__} loaded but spell checking disabled")
    hexchat.prnt("Install pyenchant: pip install pyenchant")
else:
    if init_spell_checker():
        hexchat.prnt(f"{__module_name__} version {__module_version__} loaded")
        check_timer = hexchat.hook_timer(config['check_delay'], check_input_timer)
        hexchat.prnt("")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("\00303         How to use (SIMPLE!):\003")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("")
        hexchat.prnt("  1. Type a word and press \00302SPACE\003")
        hexchat.prnt("  2. If misspelled → suggestions appear")
        hexchat.prnt("     • \00304Red word\003 = wrong")
        hexchat.prnt("     • \00303Green word\003 = correct suggestion")
        hexchat.prnt("")
        hexchat.prnt("  3. Press \00302SPACE AGAIN\003 to use green word")
        hexchat.prnt("  4. Or just keep typing to ignore it")
        hexchat.prnt("")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("")
        hexchat.prnt("Commands: /spellcheck /spelldict /spelltoggle")
        hexchat.prnt("")
    else:
        hexchat.prnt(f"{__module_name__} loaded but failed to initialize")
        hexchat.prnt("Use /spelldict to select a dictionary")

# Register commands
hexchat.hook_command("spellcheck", cmd_spellcheck, help="Check spelling of current input")
hexchat.hook_command("spelldict", cmd_spelldict, help="Change dictionary: /spelldict <language>")
hexchat.hook_command("spelltoggle", cmd_spelltoggle, help="Toggle spell checking on/off")
hexchat.hook_command("spellcancel", cmd_spellcancel, help="Cancel pending correction")

hexchat.hook_unload(unload_cb)