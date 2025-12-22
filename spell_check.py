import hexchat
import re
import os
from collections import deque

__module_name__ = "AutoCorrect"
__module_version__ = "3.0"
__module_description__ = "Spell checker using system dictionaries"
__author__ = 'Klapvogn'

# Common misspellings and corrections
COMMON_CORRECTIONS = {
    "teh": "the", "adn": "and", "btw": "by the way", "plz": "please",
    "thx": "thanks", "ty": "thank you", "np": "no problem", "yw": "you're welcome",
    "u": "you", "r": "are", "ur": "your", "yr": "your", "k": "ok", "kk": "ok",
    "recieve": "receive", "redeve": "receive", "seperate": "separate", 
    "definately": "definitely", "definatly": "definitely", "occured": "occurred",
    "accomodate": "accommodate", "acheive": "achieve", "accross": "across",
    "wrogn": "wrong", "nothign": "nothing", "tel": "the",
    "arguement": "argument", "athelete": "athlete", "begining": "beginning",
    "beleive": "believe", "cemetary": "cemetery", "collegue": "colleague",
    "comming": "coming", "concensus": "consensus", "dilemna": "dilemma",
    "dissapear": "disappear", "embarass": "embarrass", "existance": "existence",
    "wha": "when",
}

class SystemSpellChecker:
    def __init__(self):
        self.wordlist = set()
        self.ignore_words = set()
        self.personal_dict = set()
        self.use_aspell = False
        self.aspell_available = False
        self.aspell_cmd = 'aspell'  # Default command
        
        # Try to use aspell/hunspell first
        if self.try_init_aspell():
            hexchat.prnt("\00303Using aspell for spell checking")
        else:
            # Fall back to loading system dictionary
            self.load_system_dictionary()
        
        # Always load personal dictionary
        self.load_personal_dictionary()
    
    def try_init_aspell(self):
        """Try to use aspell if available"""
        try:
            import subprocess
            
            # Try aspell command (works on Windows if aspell.exe is in PATH)
            aspell_cmd = 'aspell'
            
            # On Windows, also try common installation paths
            if os.name == 'nt':  # Windows
                possible_paths = [
                    'aspell',
                    r'C:\Program Files\Aspell\bin\aspell.exe',
                    r'C:\Program Files (x86)\Aspell\bin\aspell.exe',
                ]
                
                for path in possible_paths:
                    try:
                        result = subprocess.run([path, '--version'], 
                                              capture_output=True, 
                                              text=True, 
                                              timeout=2)
                        if result.returncode == 0:
                            self.aspell_cmd = path
                            self.use_aspell = True
                            self.aspell_available = True
                            return True
                    except:
                        continue
            else:
                # Linux/Unix
                result = subprocess.run(['aspell', '--version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=2)
                if result.returncode == 0:
                    self.aspell_cmd = 'aspell'
                    self.use_aspell = True
                    self.aspell_available = True
                    return True
        except:
            pass
        
        return False
    
    def load_system_dictionary(self):
        """Load words from system dictionary files"""
        
        # Get HexChat config directory for storing dictionary
        config_dir = hexchat.get_info("configdir")
        local_dict = os.path.join(config_dir, "english_words.txt")
        
        # Check if we have a local dictionary file
        if os.path.exists(local_dict):
            try:
                word_count = 0
                with open(local_dict, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        word = line.strip().lower()
                        if word and len(word) > 1 and word.isalpha():
                            self.wordlist.add(word)
                            word_count += 1
                
                hexchat.prnt(f"\00303Loaded {word_count} words from local dictionary")
                return True
            except Exception as e:
                hexchat.prnt(f"\00304Error loading local dictionary: {e}")
        
        # Try Windows paths (for Hunspell/LibreOffice dictionaries)
        dictionary_paths = [
            # Windows LibreOffice paths
            os.path.expandvars(r'%ProgramFiles%\LibreOffice\share\extensions\dict-en\en_US.dic'),
            os.path.expandvars(r'%ProgramFiles(x86)%\LibreOffice\share\extensions\dict-en\en_US.dic'),
            # Windows Hunspell paths
            os.path.expandvars(r'%APPDATA%\hunspell\en_US.dic'),
            # Linux paths (if running on WSL or similar)
            '/usr/share/dict/words',
            '/usr/share/dict/american-english',
            '/usr/share/dict/british-english',
            '/usr/share/hunspell/en_US.dic',
            '/usr/share/myspell/en_US.dic',
        ]
        
        # Try to load from system paths
        for dict_path in dictionary_paths:
            if os.path.exists(dict_path):
                try:
                    word_count = 0
                    with open(dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            word = line.strip().lower()
                            # Skip empty lines, comments, and lines with special characters
                            if word and len(word) > 1 and not word.startswith('#'):
                                # Remove affixes (like /SM in hunspell dictionaries)
                                word = word.split('/')[0]
                                if word.isalpha():
                                    self.wordlist.add(word)
                                    word_count += 1
                    
                    hexchat.prnt(f"\00303Loaded {word_count} words from {os.path.basename(dict_path)}")
                    
                    # Save to local cache for faster loading next time
                    try:
                        with open(local_dict, 'w', encoding='utf-8') as f:
                            for word in sorted(self.wordlist):
                                f.write(word + "\n")
                        hexchat.prnt(f"\00303Cached dictionary to {os.path.basename(local_dict)}")
                    except:
                        pass
                    
                    return True
                except Exception as e:
                    continue
        
        # If no dictionary found, offer to download one
        hexchat.prnt("\00304No system dictionary found!")
        hexchat.prnt("\00307Attempting to download English word list...")
        
        if self.download_dictionary(local_dict):
            return self.load_system_dictionary()  # Try loading again
        
        hexchat.prnt("\00304Could not load or download dictionary")
        hexchat.prnt("\00307You can manually download a word list and save it as:")
        hexchat.prnt(f"\00307{local_dict}")
        hexchat.prnt("\00307Or install LibreOffice which includes dictionaries")
        return False
    
    def download_dictionary(self, save_path):
        """Download a dictionary file from the internet"""
        try:
            import urllib.request
            
            # Use a reliable word list source
            urls = [
                # SCOWL word list (commonly used)
                'https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt',
                # Alternative: Hunspell English dictionary
                'https://cgit.freedesktop.org/libreoffice/dictionaries/plain/en/en_US.dic',
            ]
            
            for url in urls:
                try:
                    hexchat.prnt(f"\00307Downloading from {url[:50]}...")
                    
                    # Download with timeout
                    with urllib.request.urlopen(url, timeout=10) as response:
                        content = response.read().decode('utf-8', errors='ignore')
                    
                    # Save to file
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    hexchat.prnt("\00303Dictionary downloaded successfully!")
                    return True
                    
                except Exception as e:
                    hexchat.prnt(f"\00304Failed to download from {url[:30]}: {str(e)[:50]}")
                    continue
            
            return False
            
        except ImportError:
            hexchat.prnt("\00304urllib not available for downloading")
            return False
        except Exception as e:
            hexchat.prnt(f"\00304Download error: {e}")
            return False
    
    def load_personal_dictionary(self):
        """Load personal dictionary from file"""
        try:
            config_dir = hexchat.get_info("configdir")
            dict_file = os.path.join(config_dir, "autocorrect_dict.txt")
            
            if os.path.exists(dict_file):
                with open(dict_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().lower()
                        if word and len(word) > 1:
                            self.personal_dict.add(word)
                            self.wordlist.add(word)
        except:
            pass
    
    def save_personal_dictionary(self):
        """Save personal dictionary to file"""
        try:
            config_dir = hexchat.get_info("configdir")
            dict_file = os.path.join(config_dir, "autocorrect_dict.txt")
            
            with open(dict_file, 'w', encoding='utf-8') as f:
                for word in sorted(self.personal_dict):
                    f.write(word + "\n")
            return True
        except:
            return False
    
    def check_with_aspell(self, word):
        """Check word using aspell"""
        try:
            import subprocess
            result = subprocess.run(
                [self.aspell_cmd, '-a'],
                input=word + "\n",
                capture_output=True,
                text=True,
                timeout=1
            )
            
            # aspell output format:
            # First line: version info
            # Second line: "*" (correct) or "& word count offset: suggestions" (incorrect)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                if lines[1].startswith('*'):
                    return True
                else:
                    return False
        except:
            return None
    
    def suggest_with_aspell(self, word):
        """Get suggestions using aspell"""
        try:
            import subprocess
            result = subprocess.run(
                [self.aspell_cmd, '-a'],
                input=word + "\n",
                capture_output=True,
                text=True,
                timeout=1
            )
            
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                line = lines[1]
                # Format: "& word count offset: suggestion1, suggestion2, ..."
                if line.startswith('&'):
                    parts = line.split(':')
                    if len(parts) > 1:
                        suggestions = [s.strip() for s in parts[1].split(',')]
                        return suggestions[:5]
        except:
            pass
        return []
    
    def check(self, word):
        """Check if word is spelled correctly"""
        if not word or len(word) < 2:
            return True
            
        word_lower = word.lower()
        
        # Check ignore list
        if word in self.ignore_words:
            return True
        
        # Check personal dictionary
        if word_lower in self.personal_dict:
            return True
        
        # Check common corrections (these are known misspellings)
        if word_lower in COMMON_CORRECTIONS:
            return False
        
        # Ignore URLs, mentions, etc.
        if re.match(r'^(https?://|www\.|@|#|\d)', word):
            return True
        
        # Ignore all-caps words (acronyms)
        if len(word) > 1 and word.isupper():
            return True
        
        # Check contractions
        contractions = {
            "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
            "haven't", "hasn't", "hadn't", "won't", "wouldn't", "shouldn't",
            "can't", "couldn't", "mustn't", "i'm", "you're", "he's", "she's",
            "it's", "we're", "they're", "i've", "you've", "we've", "they've",
            "i'll", "you'll", "he'll", "she'll", "it'll", "we'll", "they'll",
            "i'd", "you'd", "he'd", "she'd", "it'd", "we'd", "they'd"
        }
        if word_lower in contractions:
            return True
        
        # Use aspell if available
        if self.use_aspell:
            result = self.check_with_aspell(word)
            if result is not None:
                return result
        
        # Fall back to wordlist
        return word_lower in self.wordlist
    
    def suggest(self, word):
        """Get spelling suggestions"""
        word_lower = word.lower()
        
        # Check common corrections first
        if word_lower in COMMON_CORRECTIONS:
            return [COMMON_CORRECTIONS[word_lower]]
        
        # Use aspell if available
        if self.use_aspell:
            suggestions = self.suggest_with_aspell(word)
            if suggestions:
                return suggestions
        
        # Fall back to basic algorithm
        suggestions = []
        
        if not self.wordlist:
            return []
        
        # Find similar words
        for dict_word in self.wordlist:
            if len(dict_word) < 2:
                continue
                
            # Must start with same letter
            if word_lower[0] != dict_word[0]:
                continue
            
            # Length difference shouldn't be too large
            len_diff = abs(len(word_lower) - len(dict_word))
            if len_diff > 3:
                continue
            
            # Calculate similarity score
            matches = 0
            min_len = min(len(word_lower), len(dict_word))
            
            for i in range(min_len):
                if word_lower[i] == dict_word[i]:
                    matches += 1
            
            # Require high similarity
            similarity = matches / max(len(word_lower), len(dict_word))
            
            if similarity >= 0.7:
                suggestions.append((dict_word, similarity))
            
            # Limit search to avoid slowdown
            if len(suggestions) >= 20:
                break
        
        # Sort by similarity and return top 5
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [word for word, score in suggestions[:5]]

class AutoCorrect:
    def __init__(self):
        self.spell = SystemSpellChecker()
        self.enabled = True
        self.suggestions = deque()
        self.current_word = ""
        self.word_start = 0
        self.word_end = 0
        self.suggestion_active = False
        self.last_text = ""
        self.last_check_word = ""
        
        # Hook events
        hexchat.hook_print("Key Press", self.on_key_press)
        hexchat.hook_command("spell", self.cmd_spell)
        hexchat.hook_command("addword", self.cmd_addword)
        hexchat.hook_command("aspell", self.cmd_aspell)
        
        # Check spelling periodically
        hexchat.hook_timer(200, self.check_spelling_timer)
        
        hexchat.prnt("\00303System dictionary spell checker loaded")
        hexchat.prnt("\00307Suggestions auto-appear - TAB to cycle, SPACE to accept")
        hexchat.prnt("\00307Type /aspell help for commands")
    
    def check_spelling_timer(self, userdata):
        """Check spelling as you type and show suggestions automatically"""
        if not self.enabled:
            return 1
        
        try:
            text = hexchat.get_info("inputbox")
            if not text:
                if self.suggestion_active:
                    self.suggestion_active = False
                    self.last_check_word = ""
                return 1
            
            # Get the last word being typed
            words = text.split()
            if not words:
                if self.suggestion_active:
                    self.suggestion_active = False
                    self.last_check_word = ""
                return 1
            
            last_word = words[-1]
            
            # Only check words of reasonable length
            if len(last_word) < 2:
                if self.suggestion_active:
                    self.suggestion_active = False
                    self.last_check_word = ""
                return 1
            
            # Find position of last word
            word_start = text.rfind(last_word)
            word_end = word_start + len(last_word)
            
            # Check if this is a new word or word changed
            if last_word != self.last_check_word:
                self.last_check_word = last_word
                self.current_word = last_word
                self.word_start = word_start
                self.word_end = word_end
                
                # Check spelling
                if not self.spell.check(last_word):
                    suggestions = self.spell.suggest(last_word)
                    if suggestions:
                        self.suggestions = deque(suggestions)
                        self.suggestion_active = True
                        
                        # Show suggestion automatically
                        hexchat.prnt(f"\00304'{last_word}'\00307 → \00303{suggestions[0]}\00307 (TAB=cycle, SPACE=accept)")
                    else:
                        self.suggestion_active = False
                else:
                    self.suggestion_active = False
            elif self.suggestion_active:
                # Update word boundaries as user types
                self.current_word = last_word
                self.word_start = word_start
                self.word_end = word_end
            
        except:
            pass
        
        return 1
    
    def on_key_press(self, word, word_eol, userdata):
        """Handle TAB and SPACE keys for suggestion cycling and accepting"""
        try:
            if not word:
                return hexchat.EAT_NONE
            
            key_code = int(word[0])
            
            # TAB key = 65289 - cycle through suggestions
            if key_code == 65289 and self.suggestion_active and self.suggestions:
                # Rotate to next suggestion
                self.suggestions.rotate(-1)
                next_suggestion = self.suggestions[0]
                
                # Show the next suggestion
                hexchat.prnt(f"\00307→ \00303{next_suggestion}\00307 (TAB=cycle, SPACE=accept)")
                
                return hexchat.EAT_ALL  # Eat the TAB key
            
            # SPACE key = 32 - accept current suggestion
            elif key_code == 32 and self.suggestion_active and self.suggestions:
                suggestion = self.suggestions[0]
                text = hexchat.get_info("inputbox")
                
                if text and self.word_start >= 0 and self.word_end <= len(text):
                    # Replace the misspelled word with suggestion and add space
                    new_text = text[:self.word_start] + suggestion + " " + text[self.word_end:]
                    
                    # Calculate cursor position (after the space)
                    new_cursor_pos = self.word_start + len(suggestion) + 1
                    
                    # Apply changes
                    hexchat.command("settext " + new_text)
                    hexchat.command("setcursor " + str(new_cursor_pos))
                    
                    # Clear suggestion state
                    self.suggestion_active = False
                    self.suggestions.clear()
                    self.last_check_word = ""
                    
                    return hexchat.EAT_ALL  # Eat the SPACE key
            
            # ESC key = 65307 - cancel suggestions
            elif key_code == 65307 and self.suggestion_active:
                self.suggestion_active = False
                self.suggestions.clear()
                self.last_check_word = ""
                hexchat.prnt("\00307Suggestion cancelled")
                return hexchat.EAT_NONE
            
        except:
            pass
        
        return hexchat.EAT_NONE
    
    def cmd_spell(self, words, word_eol, userdata):
        """Manual spell check: /spell <word>"""
        if len(words) < 2:
            hexchat.prnt("Usage: /spell <word> - Check spelling")
            return hexchat.EAT_ALL
        
        word = words[1]
        if self.spell.check(word):
            hexchat.prnt(f"\00303'{word}' is spelled correctly")
        else:
            suggestions = self.spell.suggest(word)
            if suggestions:
                hexchat.prnt(f"\00304'{word}' is misspelled")
                hexchat.prnt(f"\00307Suggestions: {', '.join(suggestions)}")
            else:
                hexchat.prnt(f"\00304No suggestions for '{word}'")
        
        return hexchat.EAT_ALL
    
    def cmd_addword(self, words, word_eol, userdata):
        """Add word to dictionary: /addword <word>"""
        if len(words) < 2:
            hexchat.prnt("Usage: /addword <word> - Add to personal dictionary")
            return hexchat.EAT_ALL
        
        word = words[1].lower()
        self.spell.personal_dict.add(word)
        self.spell.wordlist.add(word)
        if self.spell.save_personal_dictionary():
            hexchat.prnt(f"\00303Added '{word}' to dictionary")
        else:
            hexchat.prnt(f"\00304Could not save '{word}'")
        
        return hexchat.EAT_ALL
    
    def cmd_aspell(self, words, word_eol, userdata):
        """aspell-style commands: /aspell <command>"""
        if len(words) < 2 or words[1].lower() == "help":
            hexchat.prnt("\00303System Dictionary Spell Checker Commands:")
            hexchat.prnt("  \00307/spell <word>\00303 - Check spelling of a word")
            hexchat.prnt("  \00307/addword <word>\00303 - Add word to personal dictionary")
            hexchat.prnt("  \00307/aspell enable|disable\00303 - Toggle spell checking")
            hexchat.prnt("  \00307/aspell status\00303 - Show current status")
            hexchat.prnt("  \00307/aspell path\00303 - Show dictionary file location")
            hexchat.prnt("  \00307/aspell reload\00303 - Reload dictionary from disk")
            hexchat.prnt("  \00307/aspell help\00303 - Show this help")
            hexchat.prnt("\00303How to use:")
            hexchat.prnt("  1. Type normally - suggestions appear automatically")
            hexchat.prnt("  2. When you see a suggestion:")
            hexchat.prnt("     \00307TAB\00303 - Cycle through different suggestions")
            hexchat.prnt("     \00307SPACE\00303 - Accept current suggestion and add space")
            hexchat.prnt("     \00307ESC\00303 - Cancel and keep your spelling")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "path":
            config_dir = hexchat.get_info("configdir")
            local_dict = os.path.join(config_dir, "english_words.txt")
            personal_dict = os.path.join(config_dir, "autocorrect_dict.txt")
            
            hexchat.prnt("\00303Dictionary file locations:")
            hexchat.prnt(f"\00307Main dictionary: {local_dict}")
            hexchat.prnt(f"\00307Personal dictionary: {personal_dict}")
            
            if os.path.exists(local_dict):
                size = os.path.getsize(local_dict) / 1024  # KB
                hexchat.prnt(f"\00303Main dictionary exists ({size:.1f} KB)")
            else:
                hexchat.prnt("\00304Main dictionary not found")
            
            if os.path.exists(personal_dict):
                hexchat.prnt(f"\00303Personal dictionary exists")
            else:
                hexchat.prnt("\00307Personal dictionary not created yet")
            
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "reload":
            hexchat.prnt("\00307Reloading dictionary...")
            
            # Clear current wordlist
            old_count = len(self.spell.wordlist)
            self.spell.wordlist.clear()
            
            # Reload system dictionary
            if self.spell.use_aspell:
                hexchat.prnt("\00303Using aspell (no reload needed)")
            else:
                self.spell.load_system_dictionary()
            
            # Reload personal dictionary
            self.spell.load_personal_dictionary()
            
            new_count = len(self.spell.wordlist)
            hexchat.prnt(f"\00303Dictionary reloaded: {old_count} → {new_count} words")
            
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "enable":
            self.enabled = True
            hexchat.prnt("\00303Spell checking enabled")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "disable":
            self.enabled = False
            self.suggestion_active = False
            hexchat.prnt("\00304Spell checking disabled")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "status":
            status = "enabled" if self.enabled else "disabled"
            hexchat.prnt(f"\00303Spell checking is {status}")
            
            if self.spell.use_aspell:
                hexchat.prnt("\00303Using: aspell")
            else:
                hexchat.prnt(f"\00303Using: system dictionary ({len(self.spell.wordlist)} words)")
            
            if self.suggestion_active:
                hexchat.prnt(f"\00307Current word: '{self.current_word}'")
                if self.suggestions:
                    hexchat.prnt(f"\00303Current suggestion: {self.suggestions[0]}")
                    hexchat.prnt(f"\00307All suggestions: {list(self.suggestions)}")
            return hexchat.EAT_ALL
        
        return hexchat.EAT_ALL

# Start the plugin
autocorrect = AutoCorrect()
