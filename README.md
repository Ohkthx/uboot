# UBOOT

------------
A Discord Bot written in Python3 for UO servers. This is the primary source code for the current iteration of the Gatekeeper Bot. Default prefix for commands is `?` but can be changed in the `config.ini` file in the root directory.

#### Some Features
- Create and Manage Support Tickets in private threads.
- Bug Reports and Suggestions are automatically applied the **open** label if it exists.
- Bug Report Thread Panel for labeling in-progress and closing.
- Suggestion Thread Panel for approving, denying, and closing out new suggestions.
- Embed Manager for creating and editing embeds.
- Gambling points earned by participating in conversation.
- Private Guilds, these are sub-guilds for privatized invite-only conversations.
- Lotto! A system for rewarding members with specialized roles.
- Auto-creation of `config.ini` file.

## General
No prefix assigned. General commands that have no real category.
- **embed** - (Admin Only) Create or Edit embeds created by the Discord Bot.
- **ping** - Responds with "Pong" and the current one-way latency.
- **s2s** - Sucks to suck.
- **8ball** - Shake the magic 8-ball! Results may vary.

## Admin / Server Commands
Prefixed with **server** (ie. `?server`). These commands are reserved for only admins to utilize. Help can be viewed with `?help server`
- **settings** group (aliases: `setting`) (called: `?server setting`)
	Allows you to manage server specific settings for the Discord Bot.
	Additional help can be viewed with `?help server settings`
	- **show** - Shows all currently set settings.


- **react-role** group (called: `?server react-role`)
	React Roles are bound pairs of Emojis to Roles. Reacting on specified message with the bound reaction grants the role assigned to it.
	Additional help can be viewed with `?help server react-role`
	- **show** - Shows all currently bound Reactions to Roles.
	- **bind**- Binds a Reaction (emoji) to a Role.
	- **unbind** - Unbinds a Reaction (emoji) from a Role.


- **add-role-all** - Adds are a role to all users on a server.
- **remove** - Removes n amount of messages from the channel executed in.
- **support** - Creates the support ticket button if it is missing.

## Gamble
No prefix assigned, Gamble utilizes the gold mechanic. Gold is generate by participating in channel discussions. There is a small cooldown to prevent spamming messages from generation gold. Help can be viewed with: `?help Gamble`
- **stats** - Shows the players stats including gambling statistics and current gold amount.
- **bet** - Bet your gold. Three choices: low, seven, and high.
- **give** - Give gold from your balance to another player.
- **leaderboard** - Shows the current leaderboard for accumulated gold.
- **lotto** - (Admin Only) Performs a lotto rewarding selected members with a role.
- **spawn** - (Admin Only) Gives ore removes gold from a user.

## Guild (Private / Sub Guilds)
Prefixed with **guild** (ie. `?guild`).
Private (Sub) Guilds are individual threads that are invite only with an assigned "Guild Leader" that can manage the thread without having Admin access to the whole server. Upon Private Guild creation, a promotional text is created with buttons to request to join.
- **kick** - (Private Guild Leader Only) Removes a user from the private guild.
- **ban** - (Private Guild Leader Only) Bans a user from private guild.
- **unban** - (Private Guild Leader Only) Unbands a user from a private guild.
- **description** -(Private Guild Leader Only) Edits the promotional description for the guild.
- **signup-panel** - (Admin Only) Recreates the signup panel for creating new private guilds.
- **manage-panel** - (Admin Only) Adds the **Close** and **Reopen** panel to manage created private guilds.

## Threads
Few commands to manage threads (open / close) and add panels to the threads that are missing.
- **close** - (Admin Only) Closes and cleanup the thread, labeling it if it can.
- **open** - (Admin Only) Opens a thread, labeling it if it can.
- **isdone** - (Admin Only) Prompts the thread if it is complete and should be closed.
- **leave** - (Admin Only) Leave a thread, dramatically.
- **panel** - (Admin Only) Creates the management panel if it is missing.
