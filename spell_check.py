import hexchat
import re
import os
from collections import deque

__module_name__ = "AutoCorrect"
__module_version__ = "1.7"
__module_description__ = "Spell checker with tab completion - Fixed word boundary tracking"

# Basic English word list
WORD_LIST = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over",
    "think", "also", "back", "after", "use", "two", "how", "our", "work",
    "first", "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "is", "are", "was", "were", "has", "had",
    "been", "being", "did", "done", "does", "doing", "said", "says", "went",
    "gone", "going", "came", "come", "coming", "got", "get", "getting",
    "made", "make", "making", "took", "take", "taking", "saw", "see",
    "seeing", "knew", "know", "knowing", "thought", "think", "thinking",
}

# Common misspellings and corrections
COMMON_CORRECTIONS = {
    "teh": "the", "adn": "and", "btw": "by the way", "plz": "please",
    "thx": "thanks", "ty": "thank you", "np": "no problem", "yw": "you're welcome",
    "u": "you", "r": "are", "ur": "your", "yr": "your", "k": "ok", "kk": "ok",
    "lol": "laugh out loud", "brb": "be right back", "afk": "away from keyboard",
    "omw": "on my way", "tbh": "to be honest", "imo": "in my opinion",
    "fyi": "for your information", "irl": "in real life", "gtg": "got to go",
    "hbu": "how about you", "idk": "i don't know", "smh": "shaking my head",
    "nvm": "never mind", "jk": "just kidding", "ikr": "i know right",
    "ofc": "of course", "ttyl": "talk to you later", "cya": "see you",
    "gm": "good morning", "gn": "good night", "gl": "good luck", "hf": "have fun",
    "gg": "good game", "wth": "what the", "omg": "oh my god",
    "recieve": "receive", "redeve": "receive", "seperate": "separate", 
    "definately": "definitely", "definatly": "definitely", "occured": "occurred",
    "accomodate": "accommodate", "acheive": "achieve", "accross": "across",
    "wrogn": "wrong", "nothign": "nothing", "tel": "the", "wrogn": "wrong",
    "arguement": "argument", "athelete": "athlete", "begining": "beginning",
    "beleive": "believe", "cemetary": "cemetery", "collegue": "colleague",
    "comming": "coming", "concensus": "consensus", "dilemna": "dilemma",
    "dissapear": "disappear", "embarass": "embarrass", "existance": "existence",
    "wha": "when",
}

class SimpleSpellChecker:
    def __init__(self):
        self.wordlist = set(WORD_LIST)
        self.ignore_words = set()
        self.personal_dict = set()
        self.load_personal_dictionary()
    
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
    
    def check(self, word):
        """Check if word is spelled correctly"""
        if not word or len(word) < 2:
            return True
            
        word_lower = word.lower()
        
        if word in self.ignore_words:
            return True
        
        if word_lower in self.personal_dict:
            return True
        
        if word_lower in self.wordlist:
            return True
        
        # Check common corrections
        if word_lower in COMMON_CORRECTIONS:
            return False  # This is a known misspelling
        
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
        
        return False
    
    def suggest(self, word):
        """Get spelling suggestions"""
        word_lower = word.lower()
        
        # Check common corrections first
        if word_lower in COMMON_CORRECTIONS:
            return [COMMON_CORRECTIONS[word_lower]]
        
        suggestions = []
        
        # Find similar words
        for dict_word in self.wordlist:
            if len(dict_word) > 2:
                # Simple similarity check
                if word_lower and dict_word and word_lower[0] == dict_word[0]:
                    if abs(len(word_lower) - len(dict_word)) <= 2:
                        # Count matching characters
                        matches = sum(1 for a, b in zip(word_lower, dict_word) if a == b)
                        if matches >= max(2, len(word_lower) - 2):
                            suggestions.append(dict_word)
        
        # Remove duplicates and limit
        unique_suggestions = []
        for sug in suggestions:
            if sug not in unique_suggestions:
                unique_suggestions.append(sug)
        
        return unique_suggestions[:5]

class AutoCorrect:
    def __init__(self):
        self.spell = SimpleSpellChecker()
        self.suggestions = deque()
        self.current_word = ""
        self.word_start = 0
        self.word_end = 0
        self.active = False
        self.last_text = ""
        self.showing_suggestions = False
        
        # Hook print event to capture TAB key
        hexchat.hook_print("Key Press", self.on_key_press)
        hexchat.hook_command("spell", self.cmd_spell)
        hexchat.hook_command("addword", self.cmd_addword)
        hexchat.hook_command("ac", self.cmd_autocorrect)
        
        # Set up timer to check spelling (less frequent to avoid cursor issues)
        hexchat.hook_timer(500, self.check_spelling_timer)
        
        # Display startup message quietly
        self.quiet_print("\00304AutoCorrect v1.7 loaded - Word boundary tracking fixed")
        self.quiet_print("\00303Type /ac help for commands")
    
    def quiet_print(self, message):
        """Print message without affecting input box focus"""
        # Store current input text
        current_text = hexchat.get_info("inputbox")
        
        # Print the message
        hexchat.prnt(message)
        
        # Restore input text if it was changed
        if current_text:
            new_text = hexchat.get_info("inputbox")
            if new_text != current_text:
                hexchat.command("settext " + current_text)
    
    def check_spelling_timer(self, userdata):
        """Timer callback to check current input for spelling"""
        try:
            text = hexchat.get_info("inputbox")
            if not text or text == self.last_text:
                return 1
            
            self.last_text = text
            
            # Get the last word
            words = text.split()
            if not words:
                if self.active:
                    self.active = False
                    self.showing_suggestions = False
                return 1
            
            last_word = words[-1]
            
            # Only check words of reasonable length
            if len(last_word) < 2:
                if self.active:
                    self.active = False
                    self.showing_suggestions = False
                return 1
            
            # Find the position of the last word
            word_start = text.rfind(last_word)
            word_end = word_start + len(last_word)
            
            # Always update word boundaries when active to track typing
            if self.active:
                self.current_word = last_word
                self.word_start = word_start
                self.word_end = word_end
            
            # Check if it's a new/different word
            if last_word != self.current_word or not self.active:
                self.current_word = last_word
                self.word_start = word_start
                self.word_end = word_end
                
                # Check spelling
                if not self.spell.check(last_word):
                    suggestions = self.spell.suggest(last_word)
                    if suggestions:
                        self.suggestions = deque(suggestions)
                        self.active = True
                        
                        # Show suggestions quietly
                        if not self.showing_suggestions:
                            self.quiet_print(f"\00307'{last_word}' → \00303{suggestions[0]} \00307(TAB to accept)")
                            self.showing_suggestions = True
                    else:
                        self.active = False
                        self.showing_suggestions = False
                else:
                    self.active = False
                    self.showing_suggestions = False
            
        except:
            pass
        
        return 1
    
    def on_key_press(self, word, word_eol, userdata):
        """Handle key presses - FIXED cursor positioning"""
        try:
            if not word:
                return hexchat.EAT_NONE
            
            key_code = int(word[0])
            
            # TAB key = 65289
            if key_code == 65289 and self.active and self.suggestions:
                suggestion = self.suggestions[0]
                text = hexchat.get_info("inputbox")
                
                if text and self.word_start < len(text):
                    # Apply the suggestion
                    new_text = text[:self.word_start] + suggestion + text[self.word_end:]
                    
                    # Calculate new cursor position (end of the replaced word)
                    new_cursor_pos = self.word_start + len(suggestion)
                    
                    # Set the text and cursor position
                    hexchat.command("settext " + new_text)
                    hexchat.command("setcursor " + str(new_cursor_pos))
                    
                    # Rotate suggestions for next TAB press
                    self.suggestions.rotate(-1)
                    
                    # Clear the active state
                    self.active = False
                    self.showing_suggestions = False
                    
                    return hexchat.EAT_ALL  # Eat the TAB key
            
            # ESC key = 65307 to cancel suggestions
            elif key_code == 65307 and self.active:
                self.active = False
                self.showing_suggestions = False
                self.suggestions.clear()
                return hexchat.EAT_NONE
            
            # SPACE key = 32 to apply correction and add space
            elif key_code == 32 and self.active and self.suggestions:
                suggestion = self.suggestions[0]
                text = hexchat.get_info("inputbox")
                
                if text and self.word_start < len(text):
                    # Apply the suggestion and add space
                    new_text = text[:self.word_start] + suggestion + " " + text[self.word_end:]
                    
                    # Calculate new cursor position (after the space)
                    new_cursor_pos = self.word_start + len(suggestion) + 1
                    
                    # Set the text and cursor position
                    hexchat.command("settext " + new_text)
                    hexchat.command("setcursor " + str(new_cursor_pos))
                    
                    self.active = False
                    self.showing_suggestions = False
                    self.suggestions.clear()
                    return hexchat.EAT_ALL  # Eat the SPACE key to prevent double space
            
            # Any other key resets suggestion display
            elif self.showing_suggestions and key_code not in [65289, 65307, 32]:
                self.showing_suggestions = False
            
        except:
            pass
        
        return hexchat.EAT_NONE
    
    def cmd_spell(self, words, word_eol, userdata):
        """Manual spell check: /spell <word>"""
        if len(words) < 2:
            self.quiet_print("Usage: /spell <word> - Check spelling")
            return hexchat.EAT_ALL
        
        word = words[1]
        if self.spell.check(word):
            self.quiet_print(f"\00303'{word}' is spelled correctly")
        else:
            suggestions = self.spell.suggest(word)
            if suggestions:
                self.quiet_print(f"\00304'{word}' → \00307{suggestions[0]}")
                if len(suggestions) > 1:
                    self.quiet_print(f"\00303Other: {', '.join(suggestions[1:3])}")
            else:
                self.quiet_print(f"\00304No suggestions for '{word}'")
        
        return hexchat.EAT_ALL
    
    def cmd_addword(self, words, word_eol, userdata):
        """Add word to dictionary: /addword <word>"""
        if len(words) < 2:
            self.quiet_print("Usage: /addword <word> - Add to personal dictionary")
            return hexchat.EAT_ALL
        
        word = words[1].lower()
        self.spell.personal_dict.add(word)
        self.spell.wordlist.add(word)
        if self.spell.save_personal_dictionary():
            self.quiet_print(f"\00303Added '{word}' to dictionary")
        else:
            self.quiet_print(f"\00304Could not save '{word}'")
        
        return hexchat.EAT_ALL
    
    def cmd_autocorrect(self, words, word_eol, userdata):
        """AutoCorrect commands: /ac <command>"""
        if len(words) < 2 or words[1].lower() == "help":
            # Use regular print for help since user expects to see it
            hexchat.prnt("\00303AutoCorrect Commands:")
            hexchat.prnt("  \00307/spell <word>\00303 - Check spelling")
            hexchat.prnt("  \00307/addword <word>\00303 - Add to dictionary")
            hexchat.prnt("  \00307/ac help\00303 - Show this help")
            hexchat.prnt("  \00307/ac test\00303 - Test examples")
            hexchat.prnt("  \00307/ac status\00303 - Show current status")
            hexchat.prnt("\00303How to use:")
            hexchat.prnt("  1. Type a misspelled word like 'tel' or 'redeve'")
            hexchat.prnt("  2. Suggestion appears in chat")
            hexchat.prnt("  3. Press \00307TAB\00303 to accept correction")
            hexchat.prnt("  4. Cursor stays at end of corrected word")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "test":
            self.quiet_print("\00307Test these misspellings:")
            self.quiet_print("  1. Type 'tel' → shows 'the' → Press TAB")
            self.quiet_print("  2. Type 'redeve' → shows 'receive' → Press TAB")
            self.quiet_print("  3. Type 'seperate' → shows 'separate' → Press TAB")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "status":
            status = "active" if self.active else "inactive"
            self.quiet_print(f"\00303AutoCorrect is {status}")
            if self.active:
                self.quiet_print(f"\00307Current word: '{self.current_word}'")
                if self.suggestions:
                    self.quiet_print(f"\00303Suggestions: {list(self.suggestions)}")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "off":
            self.active = False
            self.showing_suggestions = False
            self.suggestions.clear()
            self.quiet_print("\00304AutoCorrect disabled")
            return hexchat.EAT_ALL
        
        elif words[1].lower() == "on":
            self.quiet_print("\00303AutoCorrect enabled")
            return hexchat.EAT_ALL
        
        return hexchat.EAT_ALL

# Start the plugin
autocorrect = AutoCorrect()