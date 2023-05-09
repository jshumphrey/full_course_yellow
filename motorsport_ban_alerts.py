"""This bot monitors various motorsport Discord servers for new instances
where a user is banned from the server, or other critera as specified
for that server.

When a new ban is detected, a message is sent to the "Staff of Motorsport
Discords" server, alerting all mod staff of the new ban, and providing
information about whether the newly-banned user is present in any of the
other servers."""

import discord  # This uses pycord, not discord.py


TOKEN_FILENAME = "token.txt"


MESSAGE_TARGETS = [  # List of (guild_id, channel_id) tuples
    ("1079109375647555695", "1105555454605672448")
]


bot = discord.Bot(
    intents = discord.Intents(
        moderation = True,
        messages = True,
        message_content = True,
    ),
    allowed_mentions = discord.AllowedMentions.none(),
)


@bot.event
async def on_member_ban(
    guild: discord.Guild,
    user: discord.User | discord.Member
):
    pass


def read_token(token_filename: str) -> str:
    """Load the bot's token from the file."""
    with open(token_filename, "r", encoding = "utf-8") as infile:
        return infile.read().strip()


def main():
    """Execute top-level functionality - load the token and start the bot."""
    bot.run(token = read_token(TOKEN_FILENAME))


if __name__ == "__main__":
    main()
