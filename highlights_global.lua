-- SPDX-License-Identifier: MIT
--
-- If someone hilights you on any giving iRCD server you are on, it will display it in the current window/channel you are currently viewing
-- AUTHOR : piratpalle
--
hexchat.register('Highlights', '1', 'Prints highlights to currently focused tab')

local current_focused_context = hexchat.get_context()

-- Track the currently focused context
hexchat.hook_print('Focus Window', function()
    current_focused_context = hexchat.get_context()
    return hexchat.EAT_NONE
end)

hexchat.hook_print('Focus Tab', function()
    current_focused_context = hexchat.get_context()
    return hexchat.EAT_NONE
end)

local function print_to_current_buffer(server, channel, nick, message, is_action, is_private)
    -- Don't show notification if we're already in the same server and channel
    local current_server = current_focused_context:get_info('server')
    local current_channel = current_focused_context:get_info('channel')
    
    if current_server == server and current_channel == channel then
        return  -- We're already viewing this channel, no need for notification
    end
    
    local format
    if is_private then
        if is_action then
            format = '\00304,00*** [%s] (private) * %s %s'
        else
            format = '\00304,00*** [%s] (private) <%s> %s'
        end
    else
        if is_action then
            format = '\00304,00*** [%s] (%s) * %s %s'
        else
            format = '\00304,00*** [%s] (%s) <%s> %s'
        end
    end
    
    -- Print to the last known focused context
    if current_focused_context then
        current_focused_context:print(string.format(format, server, channel, nick, message))
    else
        -- Fallback to current context if no focused context tracked
        hexchat.print(string.format(format, server, channel, nick, message))
    end
end

-- Hook the highlight events
hexchat.hook_print('Channel Msg Hilight', function(args)
    local server = hexchat.get_info('server') or 'Unknown'
    local channel = hexchat.get_info('channel') or 'Unknown'
    -- For Channel Msg Hilight, args[1] is the nick
    local nick = args[1] or 'Unknown'
    
    print_to_current_buffer(server, channel, nick, args[2] or '', false, false)
    return hexchat.EAT_NONE
end)

hexchat.hook_print('Channel Action Hilight', function(args)
    local server = hexchat.get_info('server') or 'Unknown'
    local channel = hexchat.get_info('channel') or 'Unknown'
    -- For Channel Action Hilight, args[1] is the nick
    local nick = args[1] or 'Unknown'
    
    print_to_current_buffer(server, channel, nick, args[2] or '', true, false)
    return hexchat.EAT_NONE
end)

-- Also handle private messages
hexchat.hook_print('Private Message', function(args)
    local server = hexchat.get_info('server') or 'Unknown'
    local nick = args[1] or 'Unknown'
    
    print_to_current_buffer(server, 'private', nick, args[2] or '', false, true)
    return hexchat.EAT_NONE
end)

hexchat.hook_print('Private Action', function(args)
    local server = hexchat.get_info('server') or 'Unknown'
    local nick = args[1] or 'Unknown'
    
    print_to_current_buffer(server, 'private', nick, args[2] or '', true, true)
    return hexchat.EAT_NONE
end)

