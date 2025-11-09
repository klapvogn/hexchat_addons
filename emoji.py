#!/usr/bin/env python
"""
HexChat Emoji Translator - Send Only Version
Only translates when pressing Enter - no cursor issues during typing

INSTALLATION:
1: pip install emoji
2: load the script
3: enjoy!
"""

import hexchat
import emoji

__module_name__ = "Send Emoji Translator"
__module_version__ = "1.0"
__module_description__ = "Translates emojis only when sending messages"
__author__ = 'Klapvogn'

def on_message_send(word, word_eol, userdata):
    """Translate emojis when sending message"""
    original_message = word_eol[0]
    
    # Check if message contains emoji codes
    if ":" in original_message:
        translated_message = emoji.emojize(original_message, language='alias')
        
        if translated_message != original_message:
            # Send the translated message directly instead of using SETTEXT
            hexchat.command("MSG {} {}".format(hexchat.get_info("channel"), translated_message))
            # Clear the input box
            hexchat.command("SETTEXT ")
            return hexchat.EAT_ALL  # Prevent the original message from being sent
    
    return hexchat.EAT_NONE

def unload_callback(userdata):
    """Cleanup"""
    print("Send Emoji Translator unloaded")

# Hook for sending messages
hook_command = hexchat.hook_command("", on_message_send)

# Hook for unload
hook_unload = hexchat.hook_unload(unload_callback)

print("Send Emoji Translator loaded!")
print("Type :heart: and press Enter - it will send as ❤️")