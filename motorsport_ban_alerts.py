"""This bot monitors various motorsport Discord servers for new instances
where a user is banned from the server, or other critera as specified
for that server.

When a new ban is detected, a message is sent to the "Staff of Motorsport
Discords" server, alerting all mod staff of the new ban, and providing
information about whether the newly-banned user is present in any of the
other servers."""

# pylint: disable = protected-access

import discord  # This uses pycord, not discord.py
import logging
import typing

import motorsport_ban_guilds as mba_guilds


TOKEN_FILENAME = "token.txt"
INTENTS = discord.Intents.default()
INTENTS.members = True

logging.basicConfig(level=logging.DEBUG)
mba_logger = logging.getLogger("motorsport_ban_alerts")
pycord_logger = logging.getLogger("discord")


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

        for alert_guild in mba_guilds.ALERT_GUILDS.values():
            if await alert_guild.is_bot_installed(self) is False:
                raise RuntimeError(
                    f"The bot is configured to send alerts to {alert_guild.name}, "
                    "but the bot is not installed in the server!"
                )

            if await alert_guild.can_bot_send_alerts(self) is False:
                raise RuntimeError(
                    f"The bot is configured to send alerts to {alert_guild.name}, "
                    "but it does not have the appropriate permissions "
                    "in that server's configured alert channel!"
                )

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

        mba_logger.debug(f"{entry.__dict__}")

        try:
            ale_handler = mba_guilds.MONITORED_GUILDS[entry.guild.id].audit_log_handler

        except KeyError as ex:
            raise KeyError(
                f"Tried to process audit log entry for guild {entry.guild.name} "
                f"(guild ID {entry.guild.id}), but guild ID not present in MONITORED_GUILDS!"
            ) from ex

        if ale_handler(entry) is True:
            alert_embed = await self.create_alert_embed(entry)
            await self.send_alert(alert_embed)

    async def create_alert_embed(self, entry: discord.AuditLogEntry) -> discord.Embed:
        """This handles the process of creating an alert from a provided ALE."""

        banned_user_id = typing.cast(int, entry._target_id)
        banned_user = await self.get_or_fetch_user(banned_user_id)
        if not banned_user:
            raise RuntimeError(f"Could not find any Discord user with user ID {banned_user_id}!")

        mutual_guild_names = (
            "None" if not (mutual_guilds := banned_user.mutual_guilds)
            else ", ".join(g.name for g in mutual_guilds)
        )

        description = (
            f"**Banning server:** {entry.guild.name}\n\n"
            f"**Ban reason:** {entry.reason or ''}\n\n"
            f"**Motorsport servers with user:** {mutual_guild_names}"
        )

        embed = (
            discord.Embed(type = "rich", description = description, timestamp = entry.created_at)
            .set_author(
                name = f"{banned_user.global_name} ({banned_user.name}#{banned_user.discriminator})",
                icon_url = banned_user.display_avatar.url,
            )
            .set_footer(text = f"Banned user's ID: {banned_user.id}")
        )

        return embed

    async def send_alert(self, alert_embed: discord.Embed) -> None:
        """This handles the process of sending a prepared alert out to the AlertGuilds."""

        for alert_guild in mba_guilds.ALERT_GUILDS.values():
            if (guild := self.get_guild(alert_guild.guild_id)) is None:
                continue
            if (channel := guild.get_channel(alert_guild.alert_target_channel_id)) is None:
                continue
            if not isinstance(channel, discord.TextChannel):
                continue

            embed = alert_embed.copy()
            # embed.description = description
            await channel.send(
                content = "A new permanent ban has been detected!",
                embed = embed,
            )


def read_token(token_filename: str) -> str:
    """Load the bot's token from the file."""
    with open(token_filename, "r", encoding="utf-8") as infile:
        return infile.read().strip()


def main():
    """Execute top-level functionality - load the token and start the bot."""
    bot = MBABot(
        intents=INTENTS,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    bot.run(token=read_token(TOKEN_FILENAME))


if __name__ == "__main__":
    main()
