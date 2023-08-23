# Full Course Yellow

This is a Discord bot designed to help moderators of affiliated Discord servers alert one another about problematic users that might be present in several of the affiliated servers.

The bot's goal is to simplify the process of broadcasting an informative alert about the user, including automating the process of checking a number of servers to see whether the user is a member of any of them.

## Slash Commands

### `/alert`

![Screenshot of the /alert command in use](/images/screenshot_1.png?raw=true)

This command asks you for some information about a problematic user, then generates an alert message that gets broadcast to one or more servers that are configured to receive these alerts.

When `/alert` is used, it will scan all of the servers it's monitoring, checking to see if the user is in any of them. The alert message it creates will include a list of any servers where it detected the user, and will ping the respective roles for those servers in the alert message. (If it doesn't detect the user in any of the servers, it'll mention that, too.)

`/alert` also allows a server that receives alert broadcasts to set up a role for users to opt into; if configured, this role will be pinged every time a new alert is broadcast, regardless of which server(s) the offending user was detected in. (Users might want to do this so that even if the offending user isn't in their server yet, they'll still get pinged about the alert so that they know to preemptively ban them from joining.)

#### Options for `/alert`

- `user_id`: The Discord User ID for the user you're raising an alert about. Note that this needs to be the User **ID** (a long number that looks something like `1086293154304634910`), not the Discord username (`@snowcultscuffle`) or the Discord display name (`Lux's Dev/Testing Account`).
- `reason`: The reason you're raising an alert for this user. Add as much text as you want.

Once you use `/alert`, the bot will try to automatically determine which server you're raising the alert for, based on the roles you have in the server. If it can't figure that out (either because you don't have any of the roles it's looking for, or because you have more than one of them), it'll bring up a dropdown asking you to choose one. 

Right now, the `/alert` command is only available in Alert servers, not Monitored servers. (See [How the Bot Works](#how-the-bot-works) below for more details on the different kinds of servers.)

## Inviting the Bot

### ⚠️ Get in touch with me before you try to invite the bot! ⚠️

Because this bot is intended for use in a private, niche use-case, the bot is set to Private, meaning that **none of the below invite links will work!** 

This prevents people from inviting the bot to random servers, but it makes it so that only I can invite the bot to new servers - which isn't ideal, since server admins would have to give an untrusted user (me) the Manage Server permission in order to complete the install.

To get around this, message me on Discord so that we can coordinate a time when you want to invite the bot. I'll un-private the bot for a short while, which will make the invite links below work, you can go through the invite process, and when you're done, I can make the bot private again. 

_I recognize that this is all a bit silly, but considering that the bot is being hosted on my personal computer at the moment, I'd really prefer to not have a bunch of random servers invite the bot and generate traffic._

### When the bot's ready to invite...

Once you get the green light that the bot's been made public, you can go ahead and click through on one of the links below. These invite links are pre-populated with the bare minimum permissions required for the bot to do its job - see below for more details.

- If you're intending for the server to be a Monitored server, use [this link](https://discord.com/api/oauth2/authorize?client_id=1105933971264647168&permissions=0&scope=bot)
- If you're intending for the server to be an Alert server, use [this link](https://discord.com/api/oauth2/authorize?client_id=1105933971264647168&permissions=166912&scope=bot)

(If you don't know what type of server you're inviting it to, you should probably read [the section below on how the bot works](#how-the-bot-works) 😉)

Also, to be clear, regardless of which type of server you're inviting it to, there's nothing you need to do on your end to configure that! That's all handled by [some configuration parameters in the bot's code](fcy_constants.py), so as part of the installation, I'll extend the configuration to add in some information about your server.

## How the Bot Works

In general, there are two different types of servers that invite this bot - "Monitored" servers and "Alert" servers.

### Monitored Servers

"Monitored" servers are servers where the bot is invited simply to be able to look through the server's members. 

When a user has an alert raised against them, the bot will sweep through all of its Monitored servers, checking to see if that user is present in any of the servers. The alert that gets broadcast will include a list of any Monitored servers that the user is currently a member of, and it'll ping the respective role(s) for that server's admins.

#### Required Permissions for Monitored Servers

For a Monitored server, the bot needs ***literally no permissions*** to do its job; all that's required is that the bot exist in the server, as if it were a normal user. It doesn't need to be able to send messages, mention any roles, or even view any channels.

_If you're on the fence about whether you're comfortable inviting this thing into your server - which is an attitude I very much sympathize with, for the record - yes, I am trying to make the point that the bot can function perfectly fine even if you strip it of every single permission it could use to harm your server in any way._

_I get extremely frustrated with bot developers that suggest that you should just grant their bot Administrator permissions so that "you'll never have to deal with permissions issues", and I've tried hard to keep the list of necessary permissions to the absolute bare minimum._

### Alert Servers

"Alert" servers are servers where the bot listens for slash commands and broadcasts new alerts.

#### Required Permissions for Alert Servers

Alert servers do need a few permissions for the bot to function properly, since in Alert servers, the bot is actually "doing things."

The bot will need to have the following permissions:
- **Read Messages / View Channels**: Required so that the bot can access the channel it'll be sending alerts in.
- **Send Messages**: Required so that the bot can actually send its alert messages.
- **Mention Everyone**: Required so that the bot can ping the "all notifications" role, plus the roles that correspond to various servers, if it finds that an alert's user is present in those servers.
- **Attach Files**: Required so that the bot can post images submitted by users of the slash command as evidence for an alert.

If you're concerned about granting these permissions globally, you can choose to instead just grant the permissions for the bot's role only in the channel where the bot will post new alerts, and the bot will still work correctly. 

_Note that if you do this, the names of the permissions in Discord's "Edit Channel -> Permissions" screen are different from the names given above; "Read Messages / View Channels" will appear as "View Channel", and "Mention Everyone" will appear as "Mention @everyone, @here, and All Roles"._

## Current List of To-Dos

### New features

#### Allow the bot to automatically raise alerts for any new bans in a Monitored server. 

This functionality is essentially already mostly set up, but I haven't turned it on yet because of the potential for (a), spamming the alert channels with information about bans that didn't actually need alerts raised, or (b), the bot automatically broadcasting sensitive/private moderation-log material to everyone.

If/when we go ahead with this, the use-case will involve providing a slash command to the Monitored servers that they can use to _selectively_ raise an alert about a recent ban, rather than automatically publishing information for any new bans.

#### Allow users to optionally upload files instead of / alongside an alert reason.

This shouldn't be too difficult to set up; I just haven't done it yet.

### Things that need fixing or improvement

#### Add more custom error messages when something goes wrong with the slash command.

I've already implemented as many of these as I can currently think of, but if you run into any issues with the bot where it gives you an unhelpful error message (or no error message at all), please let me know about it, and I'll try to add in a more helpful one.