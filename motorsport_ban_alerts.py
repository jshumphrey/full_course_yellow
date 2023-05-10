"""This bot monitors various motorsport Discord servers for new instances
where a user is banned from the server, or other critera as specified
for that server.

When a new ban is detected, a message is sent to the "Staff of Motorsport
Discords" server, alerting all mod staff of the new ban, and providing
information about whether the newly-banned user is present in any of the
other servers."""

import discord  # This uses pycord, not discord.py
import typing

import motorsport_ban_guilds as mba_guilds


TOKEN_FILENAME = "token.txt"

# List of (guild_id, channel_id) tuples to send alerts to
ALERT_TARGET_CHANNELS: list[tuple[int, int]] = [
    (1079109375647555695, 1105555454605672448),  # #ban-alerts in Lux's Dev/Testing
    # (959541053915037697, 960480902331383809),  # alerts in Staff of MS Discords
]


class MBABot(discord.Bot):
    """This subclass of Bot defines the Motorsport Ban Alerts bot."""

    async def on_ready(self) -> None:
        """When the bot has logged in and begun running, we need to ensure
        that it has the appropriate access and permissions to do its job.

        For each guild and channel that are set up as places to raise an
        alert (i.e. the entries in ALERT_TARGET_CHANNELS), we check that
        the bot has access to the guild, and we check that the bot has
        Send Messages permissions in the channel.

        If any of these conditions are not fulfilled, we crash out."""

        for guild_id, channel_id in ALERT_TARGET_CHANNELS:
            pass

    async def on_audit_log_entry(self, entry: discord.AuditLogEntry) -> None:
        """When an audit log entry is created in an installed guild,
        if the ALE is for a user ban, we dispatch the ALE to the
        respective guild's ALE handler for further processing.

        Some guilds have more complex moderation systems that allow
        for the issuance of temporary bans; we only want to create
        alerts for permanent bans, so the handling function for that
        server will need to determine whether the ban was permanent
        before issuing the alert."""

        if entry.action != discord.AuditLogAction.ban:
            return

        try:
            ale_handler = mba_guilds.MONITORED_GUILDS[entry.guild.id].audit_log_handler

        except KeyError as ex:
            raise KeyError(
                f"Tried to process audit log entry for guild {entry.guild.name} "
                f"(guild ID {entry.guild.id}), but guild ID not present in MONITORED_GUILDS!"
            ) from ex

        if ale_handler(entry) is True:
            entry.user = typing.cast(discord.User, entry.user)
            await self.create_alert(entry.user)

    async def create_alert(self, user: discord.User) -> None:
        """This handles the process of creating an alert from a provided User."""


def read_token(token_filename: str) -> str:
    """Load the bot's token from the file."""
    with open(token_filename, "r", encoding="utf-8") as infile:
        return infile.read().strip()


def main():
    """Execute top-level functionality - load the token and start the bot."""
    bot = MBABot(
        intents=discord.Intents(
            moderation=True,  # Needed to get audit log events
            members=True,  # Needed to get / examine guild members
        ),
        allowed_mentions=discord.AllowedMentions.none(),
    )
    bot.run(token=read_token(TOKEN_FILENAME))


if __name__ == "__main__":
    main()
