# -*- coding: utf-8 -*-
"""
HexChat Spell Correction Script - Auto-correction with cycling

Workflow:
1. Type a word and press SPACE - suggestions appear if misspelled
2. Type /n to cycle through suggestions (don't → font → dint → don't)
3. Press SPACE SPACE (double-space) - uses the selected suggestion
4. Or use /fix to correct all errors at once

Optional: Bind TAB key to /n in Settings → Keyboard Shortcuts

Simple and effective!
"""

__module_name__ = "spell_correction"
__module_version__ = "3.2"
__module_description__ = "Auto spell correction with /n cycling (TAB bindable)"

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
detected_errors = {}  # {context_key: [{'word': str, 'suggestions': list, 'position': int}]}

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
    
    # Common contractions without apostrophes should be flagged as misspelled
    contractions_to_fix = [
        'dont', 'doesnt', 'didnt', 'wont', 'cant', 'couldnt', 'wouldnt', 
        'shouldnt', 'isnt', 'arent', 'wasnt', 'werent', 'hasnt', 'havent',
        'hadnt', 'shant', 'ive', 'youve', 'weve', 'theyve', 'youre', 
        'theyre', 'im', 'hes', 'shes', 'thats', 'whats', 'wheres',
        'whos', 'hows', 'theres', 'heres', 'id', 'hed', 'shed', 'wed',
        'theyd', 'youd', 'ill', 'youll', 'hell', 'shell', 'theyll'
    ]
    
    if word.lower() in contractions_to_fix:
        return False  # Flag as misspelled so we can suggest the contraction
    
    return spell_checker.check(word)


def get_suggestions(word, max_suggestions=None):
    """Get spelling suggestions for a word"""
    if spell_checker is None:
        return []
    
    if max_suggestions is None:
        max_suggestions = config['max_suggestions']
    
    # Check for common contractions first
    contractions = {
        'dont': "don't",
        'doesnt': "doesn't",
        'didnt': "didn't",
        'wont': "won't",
        'cant': "can't",
        'couldnt': "couldn't",
        'wouldnt': "wouldn't",
        'shouldnt': "shouldn't",
        'isnt': "isn't",
        'arent': "aren't",
        'wasnt': "wasn't",
        'werent': "weren't",
        'hasnt': "hasn't",
        'havent': "haven't",
        'hadnt': "hadn't",
        'wont': "won't",
        'shant': "shan't",
        'ive': "I've",
        'youve': "you've",
        'weve': "we've",
        'theyve': "they've",
        'youre': "you're",
        'theyre': "they're",
        'were': "we're",
        'im': "I'm",
        'hes': "he's",
        'shes': "she's",
        'its': "it's",
        'thats': "that's",
        'whats': "what's",
        'wheres': "where's",
        'whos': "who's",
        'hows': "how's",
        'theres': "there's",
        'heres': "here's",
        'id': "I'd",
        'hed': "he'd",
        'shed': "she'd",
        'wed': "we'd",
        'theyd': "they'd",
        'youd': "you'd",
        'ill': "I'll",
        'youll': "you'll",
        'hell': "he'll",
        'shell': "she'll",
        'well': "we'll",
        'theyll': "they'll",
    }
    
    word_lower = word.lower()
    
    # If it's a known contraction without apostrophe, return the correct form first
    if word_lower in contractions:
        correct_form = contractions[word_lower]
        # Preserve original capitalization pattern
        if word[0].isupper():
            correct_form = correct_form[0].upper() + correct_form[1:]
        suggestions = [correct_form]
        # Add other suggestions after
        other_suggestions = spell_checker.suggest(word)
        for sugg in other_suggestions:
            if sugg not in suggestions:
                suggestions.append(sugg)
        return suggestions[:max_suggestions]
    
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
        
        # Auto-fix: Only trigger on double-space when there are detected errors
        if context_key in detected_errors and len(detected_errors[context_key]) > 0:
            # Double-space means user wants to fix all errors
            if input_text.endswith('  ') and not prev_input.endswith('  '):
                # Get current words from input (strip trailing spaces)
                current_text = input_text.rstrip()
                words = current_text.split()
                
                if len(words) > 0:
                    # Build a map of positions to corrections
                    corrections_map = {}
                    for error in detected_errors[context_key]:
                        # Check if this error has a selected suggestion (via /n command)
                        if (context_key in pending_correction and 
                            pending_correction[context_key]['word'] == error['word']):
                            # Use the selected suggestion
                            new_word = pending_correction[context_key]['suggestion']
                        else:
                            # Use first suggestion
                            new_word = error['suggestions'][0] if error['suggestions'] else error['word']
                        
                        corrections_map[error['position']] = {
                            'old': error['word'],
                            'new': new_word
                        }
                    
                    # Apply all corrections
                    new_words = []
                    corrections_made = []
                    
                    for i, word in enumerate(words):
                        if i in corrections_map:
                            old_word = corrections_map[i]['old']
                            new_word = corrections_map[i]['new']
                            
                            # Check if word still matches (strip punctuation for comparison)
                            clean_word = word.strip('.,!?;:\'"')
                            if clean_word == old_word:
                                # Replace while keeping punctuation
                                corrected_word = word.replace(old_word, new_word)
                                new_words.append(corrected_word)
                                corrections_made.append((old_word, new_word))
                            else:
                                new_words.append(word)
                        else:
                            new_words.append(word)
                    
                    if corrections_made:
                        new_text = ' '.join(new_words) + ' '
                        cursor_pos = len(new_text)
                        
                        hexchat.command(f"settext {new_text}")
                        hexchat.command(f"setcursor {cursor_pos}")
                        
                        # Show what was corrected
                        for old, new in corrections_made:
                            hexchat.prnt(f"\00303✓ '{old}' → '{new}'\003")
                        
                        # Clear detected errors
                        del detected_errors[context_key]
                        if context_key in pending_correction:
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
                                    'suggestions': suggestions,
                                    'suggestion': suggestions[0],
                                    'position': word_position,
                                    'index': 0  # Track which suggestion is selected
                                }
                                
                                # Also store in detected_errors for later correction
                                if context_key not in detected_errors:
                                    detected_errors[context_key] = []
                                detected_errors[context_key].append({
                                    'word': last_word,
                                    'suggestions': suggestions,
                                    'position': word_position
                                })
                                
                                # Display: red word -> green suggestion + other suggestions
                                first_sugg = f"\00303{suggestions[0]}\003"  # Green
                                other_suggs = ", ".join(suggestions[1:]) if len(suggestions) > 1 else ""
                                
                                if other_suggs:
                                    hexchat.prnt(f"\00304{last_word}\003 → {first_sugg}, {other_suggs}")
                                    hexchat.prnt("Type /n to cycle, SPACE SPACE to accept")
                                else:
                                    hexchat.prnt(f"\00304{last_word}\003 → {first_sugg}")
                                    hexchat.prnt("Press SPACE SPACE to accept")
            
            # User is typing after seeing suggestions - clear pending
            elif context_key in pending_correction and not input_text.endswith(' '):
                del pending_correction[context_key]
        
        previous_input[context_key] = input_text
        
    except Exception as e:
        hexchat.prnt(f"Spell check error: {e}")
    
    return 1


def cmd_next_suggestion(word, word_eol, userdata):
    """Cycle to next suggestion for last misspelled word"""
    context_key = get_context_key()
    
    if context_key not in pending_correction:
        hexchat.prnt("No pending correction")
        return hexchat.EAT_ALL
    
    pending = pending_correction[context_key]
    suggestions = pending['suggestions']
    
    if not suggestions:
        hexchat.prnt("No suggestions available")
        return hexchat.EAT_ALL
    
    # Cycle to next suggestion
    pending['index'] = (pending['index'] + 1) % len(suggestions)
    pending['suggestion'] = suggestions[pending['index']]
    
    # Display all suggestions with current one highlighted
    sugg_display = []
    for i, sugg in enumerate(suggestions):
        if i == pending['index']:
            sugg_display.append(f"\00303[{sugg}]\003")  # Green with brackets for selected
        else:
            sugg_display.append(sugg)
    
    hexchat.prnt(f"\00304{pending['word']}\003 → {', '.join(sugg_display)}")
    hexchat.prnt("Press TAB or /n to cycle, SPACE SPACE to accept")
    
    return hexchat.EAT_ALL


def cmd_spellfix(word, word_eol, userdata):
    """Fix all misspelled words in current input"""
    if spell_checker is None:
        hexchat.prnt("Spell checker not initialized")
        return hexchat.EAT_ALL
    
    context_key = get_context_key()
    input_text = hexchat.get_info("inputbox") or ""
    
    if not input_text.strip():
        hexchat.prnt("Input is empty")
        return hexchat.EAT_ALL
    
    # Get all words and check them
    words = input_text.split()
    replacements = []
    
    for i, w in enumerate(words):
        clean_word = w.strip('.,!?;:\'"')
        if len(clean_word) >= config['min_word_length'] and clean_word.isalpha():
            if not check_word(clean_word):
                suggestions = get_suggestions(clean_word, 1)
                if suggestions:
                    replacements.append({
                        'position': i,
                        'old': clean_word,
                        'new': suggestions[0],
                        'original': w  # Keep punctuation
                    })
    
    if not replacements:
        hexchat.prnt("\00303No misspelled words found!\003")
        return hexchat.EAT_ALL
    
    # Apply replacements
    new_words = words[:]
    for rep in replacements:
        # Replace while keeping punctuation
        old_word = rep['original']
        new_word = old_word.replace(rep['old'], rep['new'])
        new_words[rep['position']] = new_word
        hexchat.prnt(f"\00303✓ '{rep['old']}' → '{rep['new']}'\003")
    
    new_text = ' '.join(new_words)
    
    # Preserve trailing space if it existed
    if input_text.endswith(' '):
        new_text += ' '
    
    # Calculate cursor position (end of text)
    cursor_pos = len(new_text)
    
    hexchat.command(f"settext {new_text}")
    hexchat.command(f"setcursor {cursor_pos}")
    
    # Clear detected errors for this context
    if context_key in detected_errors:
        del detected_errors[context_key]
    
    return hexchat.EAT_ALL


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
    global check_timer, pending_correction, previous_input, detected_errors
    
    check_timer = None
    pending_correction.clear()
    previous_input.clear()
    detected_errors.clear()
    
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
        hexchat.prnt("\00303         How to use:\003")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("")
        hexchat.prnt("  1. Type your sentence normally")
        hexchat.prnt("  2. Misspelled words show in \00304RED\003")
        hexchat.prnt("     Suggestions show (\00303GREEN\003 = first)")
        hexchat.prnt("")
        hexchat.prnt("  3. Type \00302/n\003 to cycle through suggestions")
        hexchat.prnt("     (or bind TAB key - see below)")
        hexchat.prnt("")
        hexchat.prnt("  4. Press \00302SPACE SPACE\003 to accept")
        hexchat.prnt("")
        hexchat.prnt("\00303 Optional: Bind TAB key to /n:\003")
        hexchat.prnt("  • Settings → Keyboard Shortcuts")
        hexchat.prnt("  • Add: TAB → /n")
        hexchat.prnt("")
        hexchat.prnt("  Example:")
        hexchat.prnt("    Type: I dont know")
        hexchat.prnt("    See:  dont → don't, font, dint")
        hexchat.prnt("    Type: /n  (or press TAB if bound)")
        hexchat.prnt("    See:  dont → don't, [font], dint")
        hexchat.prnt("    Type: /n")
        hexchat.prnt("    See:  dont → [don't], font, dint")
        hexchat.prnt("    Press: SPACE SPACE")
        hexchat.prnt("    Result: I don't know")
        hexchat.prnt("")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("")
        hexchat.prnt("Commands: \00302/n\003 (cycle) \00302/fix\003 (all) /spellcheck")
        hexchat.prnt("")
    else:
        hexchat.prnt(f"{__module_name__} loaded but failed to initialize")
        hexchat.prnt("Use /spelldict to select a dictionary")

# Register commands
hexchat.hook_command("n", cmd_next_suggestion, help="Cycle to next spelling suggestion")
hexchat.hook_command("fix", cmd_spellfix, help="Fix all misspelled words in current input")
hexchat.hook_command("spellcheck", cmd_spellcheck, help="Check spelling of current input")
hexchat.hook_command("spelldict", cmd_spelldict, help="Change dictionary: /spelldict <language>")
hexchat.hook_command("spelltoggle", cmd_spelltoggle, help="Toggle spell checking on/off")
hexchat.hook_command("spellcancel", cmd_spellcancel, help="Cancel pending correction")

hexchat.hook_unload(unload_cb)
