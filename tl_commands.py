import hexchat

__module_name__ = "TL Commands"
__module_version__ = "2.0"
__module_description__ = "FLS commonly used commands"
__author__ = 'Piratpalle'

#----------
# Speedtest
#----------
def speedtest_cmd(word, word_eol, userdata):
    if len(word) < 2:
        hexchat.command("say Usage: /speedtest <username>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    response = f"I need the following from you {username}, speedtest from https://speedtest.net/run/ and paste the result URL here"

    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register both commands
hexchat.hook_command("speedtest", speedtest_cmd, help="/speedtest <username> - Request speedtest results")

#--------
# Welcome
#--------
def hi_cmd(word, word_eol, userdata):
    if len(word) < 2:
        hexchat.command("say Usage: /hi <username>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    
    # Send the formatted welcome message
    response = f"Welcome {username}, can you confirm your \x02site username\x02 and tell me how I can help you today?"
    
    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register both commands
hexchat.hook_command("hi", hi_cmd, help="/hi <username> - Welcome message")

#---------
# New User
#---------
def newuser_cmd(word, word_eol, userdata):
    if len(word) < 2:
        print("Usage: /newuser <username>")
        return hexchat.EAT_ALL
    
    #username = word[1]
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    response = (
        f"{username}, \x0314You have been enabled. Here are a few links to help you get started. "
        "\002Wiki\002: http://wiki.torrentleech.org/doku.php | "
        "\002New User Guide\002: https://wiki.torrentleech.org/doku.php/newly_invited_users | "
        "\002How long do I need to seed\002: http://wiki.torrentleech.org/doku.php/user_classes | "
        "\002How to maintain a good ratio\002: https://forums.torrentleech.org/t/how-to-maintain-your-ratio/78082 | "
        "\002HnR\002: https://wiki.torrentleech.org/doku.php/hnr | "
        "\002Our Forum\002: https://forums.torrentleech.org/ | "
        "\002Freeleech - (bookmark this)\002: https://www.torrentleech.org/torrents/browse/index/facets/tags%3AFREELEECH_added%3A%255BNOW%252FMINUTE-10MINUTES%2520TO%2520NOW%252FMINUTE%252B1MINUTE%255D - "
        "Please ensure you give them all a good read!\x03"
    )
    
    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register the command
hexchat.hook_command("newuser", newuser_cmd, help="/newuser <username> - welcome message to user")

#--------
# Enabled
#--------
def enabled_cmd(word, word_eol, userdata):
    if len(word) < 3:
        hexchat.command("say Usage: /enabled <username> <days>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()
    days = word[2]
    
    # Send the message in parts to avoid line wrapping issues with bold formatting
    line1 = (
        f"{username}, Your account is now enabled. You have {days} days to fix your ratio! "
        "Here are a few links to help you get started. "
        "\002The wiki\002: https://wiki.torrentleech.org/doku.php | "
        "\002New User Guide\002: https://wiki.torrentleech.org/doku.php/newly_invited_users | "
        "\002Common mistakes\002: https://wiki.torrentleech.org/doku.php/common_mistakes | "
        "\002How to maintain a good ratio\002: https://forums.torrentleech.org/t/how-to-maintain-your-ratio/78082 - "
        "Please ensure you give them all"
    )
    
    line2 = (
        "a good read! | "
        "\002Client Related\002: https://seedit4.me/kb/articles/qbittorrent-autobrr-setup/152 | "
        "https://wiki.torrentleech.org/doku.php/autobrr | "
        "https://seedit4.me/kb/articles/optimizing-seedbox-upload-speeds-and-building-ratio/146 | "
        "\002If you have torrents in your client -> Your passkey was reset, so any torrents you still have open in your client will not be able to connect.\002"
    )
    
    line3 = (
        "\002You can redownload the .torrent files from your profile or update them in your client manually.\002"
    )
    
    hexchat.command(f"say {line1}")
    hexchat.command(f"say {line2}")
    hexchat.command(f"say {line3}")
    return hexchat.EAT_ALL

# Register the command
hexchat.hook_command("enabled", enabled_cmd, help="/enabled <username> <days> - enabled notification")

#----------
# Freeleech
#----------
def fl_cmd(word, word_eol, userdata):
    if len(word) < 2:
        hexchat.command("say Usage: /fl <username>")
        return hexchat.EAT_ALL
    
    # Use word[1] instead of word_eol[1] to get just the first argument
    # word_eol[1] includes everything after the command, which adds spaces
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces  

    response = f"{username}, You need to download our FREELEECH torrents you can find here: https://www.torrentleech.org/torrents/browse/index/facets/tags%3AFREELEECH_added%3A%255BNOW%252FMINUTE-10MINUTES%2520TO%2520NOW%252FMINUTE%252B1MINUTE%255D | keep in mind that these torrents also needs to be seeded as long as your user class tells you to! | Read more here: http://wiki.torrentleech.org/doku.php/user_classes"
    
    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register the command
hexchat.hook_command("fl", fl_cmd, help="/fl <message> - Freeleech Link")

#------
# Promo
#------
def promo_cmd(word, word_eol, userdata):
    if len(word) < 2:
        hexchat.command("say Usage: /promo <username>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    response = f"{username}, You can use this promoreg: https://www.torrentleech.org/user/account/promoreg"

    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

hexchat.hook_command("promo", promo_cmd, help="/promo <username> - promo registration link")

#--------------------
# Change Mail Address
#--------------------
def chgmail_cmd(word, word_eol, userdata):
    if len(word) < 2:
        hexchat.command("say Usage: /chgmail <username>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    response = f"{username}, Email change: Send me an PM with the current mail and new mail address: https://www.torrentleech.org/user/messages/index/new/piratpalle"

    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register the command
hexchat.hook_command("chgmail", chgmail_cmd, help="/chgmail <username> - email change instructions")

#---------
# TL Links
#---------
def link_cmd(word, word_eol, userdata):
    # Check if we have at least one argument
    if len(word) < 2:
        hexchat.command("say Usage: /link <username>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    response = f"{username}, Here are some usefull links: \002Wiki\002: http://wiki.torrentleech.org/doku.php | \002New User Guide\002: https://wiki.torrentleech.org/doku.php/newly_invited_users | \002How long do I need to seed\002: http://wiki.torrentleech.org/doku.php/user_classes | \002Common Mistakes\002: https://wiki.torrentleech.org/doku.php/common_mistakes | \002How to maintain a good ratio\002: https://forums.torrentleech.org/t/how-to-maintain-your-ratio/78082 | \002Our Forum\002: https://forums.torrentleech.org/ | \002Freeleech - (bookmark this)\002: https://www.torrentleech.org/torrents/browse/index/facets/tags%3AFREELEECH_added%3A%255BNOW%252FMINUTE-10MINUTES%2520TO%2520NOW%252FMINUTE%252B1MINUTE%255D"
    
    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register the command
hexchat.hook_command("link", link_cmd, help="/link <username> - Shows TL links")

#----------
# IRC Guide
#----------
def irc_cmd(word, word_eol, userdata):
    # Check if we have at least one argument
    if len(word) < 2:
        hexchat.command("say Usage: /irc <username>")
        return hexchat.EAT_ALL
    
    username = word[1].strip()  # Use word[1] and remove any leading/trailing spaces
    response = f"{username}, howto join #torrentleech. Follow these guides. 1: https://wiki.torrentleech.org/doku.php/joining_irc 2: https://wiki.torrentleech.org/doku.php/how_to_join_tl_irc"

    hexchat.command(f"say {response}")
    return hexchat.EAT_ALL

# Register the command
hexchat.hook_command("irc", irc_cmd, help="/irc <username> - Shows TL iRC Guides")    


