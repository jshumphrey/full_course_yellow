"""This bot monitors various motorsport Discord servers for new instances
where a user is banned from the server, or other critera as specified
for that server.

When a new ban is detected, a message is sent to the "Staff of Motorsport
Discords" server, alerting all mod staff of the new ban, and providing
information about whether the newly-banned user is present in any of the
other servers."""

import discord  # This uses pycord, not discord.py
import logging

import motorsport_ban_cogs as mba_cogs


TOKEN_FILENAME = "token.txt"
INTENTS = discord.Intents.default()
INTENTS.members = True
ALLOWED_MENTIONS = discord.AllowedMentions(
    everyone = False,
    roles = True,
    users = False,
    replied_user = True,
)

logging.basicConfig(level=logging.INFO)
mba_logger = logging.getLogger("motorsport_ban_alerts")
pycord_logger = logging.getLogger("discord")


class MBABot(discord.Bot):
    """This subclass of Bot defines the Motorsport Ban Alerts bot."""


def read_token(token_filename: str) -> str:
    """Load the bot's token from the file."""
    with open(token_filename, "r", encoding="utf-8") as infile:
        return infile.read().strip()


def main():
    """Execute top-level functionality - load the token and start the bot."""
    bot = MBABot(
        intents = INTENTS,
        allowed_mentions = ALLOWED_MENTIONS,
    )
    bot.add_cog(mba_cogs.MBAFunctionality(bot))
    bot.run(token = read_token(TOKEN_FILENAME))


if __name__ == "__main__":
    main()
