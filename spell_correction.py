# -*- coding: utf-8 -*-
"""
HexChat Spell Correction Script - Auto-correction with bidirectional cycling

Workflow:
1. Type a word and press SPACE - suggestions appear if misspelled
2. Press Ctrl+Right Arrow (forward) or Ctrl+Left Arrow (backward) to cycle
   Or use /next and /prev commands
3. Press SPACE SPACE (double-space) - uses the selected suggestion
4. Or use /fix to correct all errors at once

Simple and effective!
"""

__module_name__ = "spell_correction"
__module_version__ = "3.8"
__module_description__ = "Auto spell correction with common typo detection (si→is, fo→of, etc.)"

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
pending_correction = {}
detected_errors = {}

# Configuration
config = {
    'max_suggestions': 5,
    'min_word_length': 2,  # Check words with 2+ letters (was 3)
    'check_delay': 150,
}

# Common typos with their corrections
COMMON_TYPOS = {
    'si': 'is',
    'fo': 'of',
    'ti': 'it',
    'od': 'do',
    'ot': 'to',
    'teh': 'the',
    'hte': 'the',
    'adn': 'and',
    'nad': 'and',
}

# Contractions without apostrophes mapped to correct forms
CONTRACTIONS = {
    'dont': "don't", 'doesnt': "doesn't", 'didnt': "didn't",
    'wont': "won't", 'cant': "can't", 'couldnt': "couldn't",
    'wouldnt': "wouldn't", 'shouldnt': "shouldn't",
    'isnt': "isn't", 'arent': "aren't", 'wasnt': "wasn't",
    'werent': "weren't", 'hasnt': "hasn't", 'havent': "haven't",
    'hadnt': "hadn't", 'shant': "shan't",
    'ive': "I've", 'youve': "you've", 'weve': "we've",
    'theyve': "they've", 'youre': "you're", 'theyre': "they're",
    'were': "we're", 'im': "I'm", 'hes': "he's", 'shes': "she's",
    'its': "it's", 'thats': "that's", 'whats': "what's",
    'wheres': "where's", 'whos': "who's", 'hows': "how's",
    'theres': "there's", 'heres': "here's",
    'id': "I'd", 'hed': "he'd", 'shed': "she'd", 'wed': "we'd",
    'theyd': "they'd", 'youd': "you'd",
    'ill': "I'll", 'youll': "you'll", 'hell': "he'll",
    'shell': "she'll", 'well': "we'll", 'theyll': "they'll",
}

# List of contractions to check (for check_word function)
CONTRACTIONS_TO_FIX = list(CONTRACTIONS.keys())


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
            # enchant.list_dicts() returns tuples: (tag, provider)
            tag = d[0] if isinstance(d, tuple) else d.tag
            hexchat.prnt(f"  - {tag}")
        return False


def check_word(word):
    """Check if a word is spelled correctly"""
    if spell_checker is None or not enabled:
        return True
    
    if len(word) < config['min_word_length']:
        return True
    
    if not word.isalpha():
        return True
    
    # Check if it's a contraction without apostrophe
    if word.lower() in CONTRACTIONS_TO_FIX:
        return False
    
    # Check if it's a common typo that should be flagged
    # (e.g., "si" is a musical note but usually a typo for "is")
    if word.lower() in COMMON_TYPOS:
        return False
    
    return spell_checker.check(word)


def get_suggestions(word, max_suggestions=None):
    """Get spelling suggestions for a word"""
    if spell_checker is None:
        return []
    
    if max_suggestions is None:
        max_suggestions = config['max_suggestions']
    
    word_lower = word.lower()
    
    # Check if it's a common typo first
    if word_lower in COMMON_TYPOS:
        correct_form = COMMON_TYPOS[word_lower]
        # Preserve original capitalization
        if word[0].isupper():
            correct_form = correct_form[0].upper() + correct_form[1:]
        suggestions = [correct_form]
        # Add other suggestions from spell checker
        other_suggestions = spell_checker.suggest(word)
        for sugg in other_suggestions:
            if sugg not in suggestions:
                suggestions.append(sugg)
        return suggestions[:max_suggestions]
    
    # Check for contractions
    # If it's a known contraction without apostrophe, return the correct form first
    if word_lower in CONTRACTIONS:
        correct_form = CONTRACTIONS[word_lower]
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


def cycle_next_suggestion():
    """Cycle to next suggestion - called by key press"""
    context_key = get_context_key()
    
    if context_key not in pending_correction:
        hexchat.prnt("\00304No suggestion to cycle\003 - Type a misspelled word + SPACE first")
        return
    
    pending = pending_correction[context_key]
    suggestions = pending['suggestions']
    
    if not suggestions or len(suggestions) <= 1:
        hexchat.prnt("\00304No other suggestions available\003")
        return
    
    # Cycle to next suggestion
    pending['index'] = (pending['index'] + 1) % len(suggestions)
    pending['suggestion'] = suggestions[pending['index']]
    
    # Display all suggestions with current one highlighted in brackets
    sugg_display = []
    for i, sugg in enumerate(suggestions):
        if i == pending['index']:
            sugg_display.append(f"\00303[{sugg}]\003")  # Green with brackets for selected
        else:
            sugg_display.append(sugg)
    
    hexchat.prnt(f"\00304{pending['word']}\003 → {', '.join(sugg_display)}")
    hexchat.prnt("↳ \00302SPACE SPACE\003 = accept | \00302Ctrl+Arrow\003 = cycle")


def cycle_previous_suggestion():
    """Cycle to previous suggestion - called by key press"""
    context_key = get_context_key()
    
    if context_key not in pending_correction:
        hexchat.prnt("\00304No suggestion to cycle\003 - Type a misspelled word + SPACE first")
        return
    
    pending = pending_correction[context_key]
    suggestions = pending['suggestions']
    
    if not suggestions or len(suggestions) <= 1:
        hexchat.prnt("\00304No other suggestions available\003")
        return
    
    # Cycle to previous suggestion (backwards)
    pending['index'] = (pending['index'] - 1) % len(suggestions)
    pending['suggestion'] = suggestions[pending['index']]
    
    # Display all suggestions with current one highlighted in brackets
    sugg_display = []
    for i, sugg in enumerate(suggestions):
        if i == pending['index']:
            sugg_display.append(f"\00303[{sugg}]\003")  # Green with brackets for selected
        else:
            sugg_display.append(sugg)
    
    hexchat.prnt(f"\00304{pending['word']}\003 → {', '.join(sugg_display)}")
    hexchat.prnt("↳ \00302SPACE SPACE\003 = accept | \00302Ctrl+Arrow\003 = cycle")


def key_press_cb(word, word_eol, userdata):
    """Handle key press events"""
    # word[0] contains the key value
    # word[1] contains the state (modifier keys)
    
    # Try to detect Ctrl+Arrow keys
    # This might need adjustment based on your system
    try:
        key = int(word[0]) if len(word) > 0 else 0
        state = int(word[1]) if len(word) > 1 else 0
        
        # Arrow key codes (may vary by system):
        # Right arrow: 65363
        # Left arrow: 65361
        # Ctrl modifier: 4
        
        if state & 4:  # Ctrl is pressed
            if key == 65363:  # Right arrow
                cycle_next_suggestion()
                return hexchat.EAT_ALL
            elif key == 65361:  # Left arrow
                cycle_previous_suggestion()
                return hexchat.EAT_ALL
    except:
        pass
    
    return hexchat.EAT_NONE


def check_input_timer(userdata):
    """Timer to monitor input and detect word completion / double-space"""
    global check_timer
    
    if not enabled or spell_checker is None or check_timer is None:
        return 0
    
    try:
        context_key = get_context_key()
        input_text = hexchat.get_info("inputbox") or ""
        prev_input = previous_input.get(context_key, "")
        
        # Detect /fix command in input (before Enter is pressed)
        # Process corrections and remove /fix from input
        if input_text.strip().endswith('/fix') and not prev_input.strip().endswith('/fix'):
            # Remove /fix from the text
            text_without_fix = re.sub(r'\s*/fix\s*$', '', input_text).strip()
            
            if text_without_fix:
                words = text_without_fix.split()
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
                                    'original': w
                                })
                
                if replacements:
                    new_words = words[:]
                    for rep in replacements:
                        old_word = rep['original']
                        new_word = old_word.replace(rep['old'], rep['new'])
                        new_words[rep['position']] = new_word
                        hexchat.prnt(f"\00303✓ '{rep['old']}' → '{rep['new']}'\003")
                    
                    new_text = ' '.join(new_words)
                    cursor_pos = len(new_text)
                    
                    hexchat.command(f"settext {new_text}")
                    hexchat.command(f"setcursor {cursor_pos}")
                    
                    if context_key in detected_errors:
                        del detected_errors[context_key]
                    if context_key in pending_correction:
                        del pending_correction[context_key]
                    
                    previous_input[context_key] = new_text
                    return 1
                else:
                    hexchat.prnt("\00303No misspelled words found!\003")
                    # Remove /fix from input anyway
                    hexchat.command(f"settext {text_without_fix}")
                    hexchat.command(f"setcursor {len(text_without_fix)}")
                    previous_input[context_key] = text_without_fix
                    return 1
        
        # Auto-fix on double-space - simple version that works with pending correction
        if input_text.endswith('  ') and not prev_input.endswith('  '):
            # Check if there's a pending correction to apply
            if context_key in pending_correction:
                pending = pending_correction[context_key]
                word_to_replace = pending['word']
                replacement = pending['suggestion']
                
                # Get current input without trailing spaces
                current_text = input_text.rstrip()
                words = current_text.split()
                
                # Find and replace the misspelled word
                new_words = []
                word_replaced = False
                
                for i, word in enumerate(words):
                    clean_word = word.strip('.,!?;:\'"')
                    if clean_word == word_to_replace and not word_replaced:
                        # Replace while preserving punctuation
                        new_word = word.replace(word_to_replace, replacement)
                        new_words.append(new_word)
                        word_replaced = True
                        hexchat.prnt(f"\00303✓ '{word_to_replace}' → '{replacement}'\003")
                    else:
                        new_words.append(word)
                
                if word_replaced:
                    new_text = ' '.join(new_words) + ' '
                    cursor_pos = len(new_text)
                    
                    hexchat.command(f"settext {new_text}")
                    hexchat.command(f"setcursor {cursor_pos}")
                    
                    # Clear the pending correction
                    del pending_correction[context_key]
                    if context_key in detected_errors:
                        detected_errors[context_key] = [e for e in detected_errors[context_key] 
                                                        if e['word'] != word_to_replace]
                        if not detected_errors[context_key]:
                            del detected_errors[context_key]
                    
                    previous_input[context_key] = new_text
                    return 1
            
            # If no pending correction, try to fix all detected errors
            elif context_key in detected_errors and len(detected_errors[context_key]) > 0:
                current_text = input_text.rstrip()
                words = current_text.split()
                
                if len(words) > 0:
                    corrections_map = {}
                    for error in detected_errors[context_key]:
                        new_word = error['suggestions'][0] if error['suggestions'] else error['word']
                        corrections_map[error['position']] = {
                            'old': error['word'],
                            'new': new_word
                        }
                    
                    new_words = []
                    corrections_made = []
                    
                    for i, word in enumerate(words):
                        if i in corrections_map:
                            old_word = corrections_map[i]['old']
                            new_word = corrections_map[i]['new']
                            clean_word = word.strip('.,!?;:\'"')
                            if clean_word == old_word:
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
                        
                        for old, new in corrections_made:
                            hexchat.prnt(f"\00303✓ '{old}' → '{new}'\003")
                        
                        del detected_errors[context_key]
                        previous_input[context_key] = new_text
                        return 1
        
        # Detect single space (word completion)
        if len(input_text) > len(prev_input):
            if input_text.endswith(' ') and not input_text.endswith('  ') and not prev_input.endswith(' '):
                words = input_text.strip().split()
                if words:
                    last_word = words[-1].strip('.,!?;:\'"')
                    
                    if len(last_word) >= config['min_word_length'] and last_word.isalpha():
                        if not check_word(last_word):
                            suggestions = get_suggestions(last_word, config['max_suggestions'])
                            
                            if suggestions:
                                word_position = len(words) - 1
                                pending_correction[context_key] = {
                                    'word': last_word,
                                    'suggestions': suggestions,
                                    'suggestion': suggestions[0],
                                    'position': word_position,
                                    'index': 0
                                }
                                
                                if context_key not in detected_errors:
                                    detected_errors[context_key] = []
                                detected_errors[context_key].append({
                                    'word': last_word,
                                    'suggestions': suggestions,
                                    'position': word_position
                                })
                                
                                # Display suggestions based on how many there are
                                if len(suggestions) == 0:
                                    # No suggestions available
                                    hexchat.prnt(f"\00304{last_word}\003 - No suggestions found")
                                    hexchat.prnt("↳ Try adding to dictionary or use /fix to skip")
                                elif len(suggestions) == 1:
                                    # Only one suggestion
                                    first_sugg = f"\00303{suggestions[0]}\003"
                                    hexchat.prnt(f"\00304{last_word}\003 → {first_sugg}")
                                    hexchat.prnt("↳ \00302SPACE SPACE\003 = accept correction")
                                else:
                                    # Multiple suggestions - show with cycling options
                                    first_sugg = f"\00303[{suggestions[0]}]\003"  # Brackets around first
                                    other_suggs = ", ".join(suggestions[1:])
                                    hexchat.prnt(f"\00304{last_word}\003 → {first_sugg}, {other_suggs}")
                                    hexchat.prnt("↳ \00302SPACE SPACE\003 = accept | \00302Ctrl+Arrow\003 or \00302/next\003/\00302/prev\003 = cycle")
            
            elif context_key in pending_correction and not input_text.endswith(' '):
                del pending_correction[context_key]
        
        previous_input[context_key] = input_text
        
    except Exception as e:
        hexchat.prnt(f"Spell check error: {e}")
    
    return 1


def cmd_next_suggestion(word, word_eol, userdata):
    """Cycle to next suggestion"""
    cycle_next_suggestion()
    return hexchat.EAT_ALL


def cmd_prev_suggestion(word, word_eol, userdata):
    """Cycle to previous suggestion"""
    cycle_previous_suggestion()
    return hexchat.EAT_ALL


def cmd_spellfix(word, word_eol, userdata):
    """Fix all misspelled words in current input"""
    if spell_checker is None:
        hexchat.prnt("Spell checker not initialized")
        return hexchat.EAT_ALL
    
    context_key = get_context_key()
    input_text = hexchat.get_info("inputbox") or ""
    
    # Remove the /fix command itself if it's in the input
    # This handles cases where user types "text /fix" and presses Enter
    input_text = re.sub(r'\s*/fix\s*$', '', input_text)
    
    if not input_text.strip():
        hexchat.prnt("Input is empty - nothing to fix")
        return hexchat.EAT_ALL
    
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
                        'original': w
                    })
    
    if not replacements:
        hexchat.prnt("\00303No misspelled words found!\003")
        return hexchat.EAT_ALL
    
    new_words = words[:]
    for rep in replacements:
        old_word = rep['original']
        new_word = old_word.replace(rep['old'], rep['new'])
        new_words[rep['position']] = new_word
        hexchat.prnt(f"\00303✓ '{rep['old']}' → '{rep['new']}'\003")
    
    new_text = ' '.join(new_words)
    
    cursor_pos = len(new_text)
    hexchat.command(f"settext {new_text}")
    hexchat.command(f"setcursor {cursor_pos}")
    
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
        # List available dictionaries
        hexchat.prnt(f"\00303Current dictionary: {current_dict}\003")
        hexchat.prnt("Available dictionaries:")
        if enchant:
            for d in enchant.list_dicts():
                # enchant.list_dicts() returns tuples: (tag, provider)
                tag = d[0] if isinstance(d, tuple) else d.tag
                provider = d[1] if isinstance(d, tuple) else str(d.provider)
                hexchat.prnt(f"  \00302{tag}\003 ({provider})")
        hexchat.prnt("Usage: \00302/spelldict <language>\003")
        hexchat.prnt("Example: \00302/spelldict en_US\003")
        return hexchat.EAT_ALL
    
    # Change to specified dictionary
    new_dict = word[1]
    if init_spell_checker(new_dict):
        hexchat.prnt(f"\00303Dictionary changed to: {new_dict}\003")
    
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
        hexchat.prnt("\00303      SPELL CHECKER - EASY VERSION\003")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("")
        hexchat.prnt("  \002Simple workflow:\002")
        hexchat.prnt("  1. Type: I dont know")
        hexchat.prnt("  2. See: \00304dont\003 → \00303[don't]\003, font, dint")
        hexchat.prnt("  3. Cycle: \00302Ctrl+→\003 (next) or \00302Ctrl+←\003 (prev)")
        hexchat.prnt("     Or type: \00302/next\003 or \00302/prev\003")
        hexchat.prnt("  4. Accept: \00302SPACE SPACE\003")
        hexchat.prnt("")
        hexchat.prnt("  \002Quick fix (no cycling):\002")
        hexchat.prnt("  • Type: I dont know si teh thing \00302/fix\003")
        hexchat.prnt("  • Press Enter - all errors fixed instantly!")
        hexchat.prnt("  • (The \00302/fix\003 gets removed automatically)")
        hexchat.prnt("")
        hexchat.prnt("  \002Controls:\002")
        hexchat.prnt("  • \00302Ctrl+→\003 or \00302/next\003 = cycle forward through suggestions")
        hexchat.prnt("  • \00302Ctrl+←\003 or \00302/prev\003 = cycle backward through suggestions")
        hexchat.prnt("  • \00302SPACE SPACE\003 = accept the [bracketed] suggestion")
        hexchat.prnt("  • \00302/fix\003 at end of line = fix all errors at once")
        hexchat.prnt("")
        hexchat.prnt("\00303═══════════════════════════════════════════\003")
        hexchat.prnt("")
    else:
        hexchat.prnt(f"{__module_name__} loaded but failed to initialize")
        hexchat.prnt("Use /spelldict to select a dictionary")

# Register commands
hexchat.hook_command("next", cmd_next_suggestion, help="Cycle to next spelling suggestion")
hexchat.hook_command("prev", cmd_prev_suggestion, help="Cycle to previous spelling suggestion")
hexchat.hook_command("previous", cmd_prev_suggestion, help="Cycle to previous spelling suggestion")
hexchat.hook_command("fix", cmd_spellfix, help="Fix all misspelled words")
hexchat.hook_command("spellcheck", cmd_spellcheck, help="Check spelling")
hexchat.hook_command("spelldict", cmd_spelldict, help="Change dictionary")
hexchat.hook_command("spelltoggle", cmd_spelltoggle, help="Toggle spell checking")

# Try to hook key press events (may not work in all HexChat versions)
try:
    hexchat.hook_print("Key Press", key_press_cb)
except:
    pass

hexchat.hook_unload(unload_cb)
