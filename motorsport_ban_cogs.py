"""This file defines cogs for the Motorsport Ban Alerts bot, providing functionality
that can be imported into the scope of a pycord Bot."""

import datetime
import discord  # This uses pycord, not discord.py
from discord.ext import commands
import logging
from typing import Optional

import motorsport_ban_alerts as mba
import motorsport_ban_guilds as mba_guilds


Actor = discord.User | discord.Member

logging.basicConfig(level=logging.INFO)
mba_logger = logging.getLogger("motorsport_ban_alerts")
pycord_logger = logging.getLogger("discord")

class MBAFunctionality(commands.Cog):
    """This cog implements the majority of the functionality for the Motorsport Ban Alerts bot."""

    def __init__(self, bot: mba.MBABot):
        self.bot = bot

    @staticmethod
    def get_mutual_monitored_guilds(actor: Actor) -> list[mba_guilds.MonitoredGuild]:
        """This wraps the process of retrieving the list of MonitoredGuilds that contain the provided Actor."""
        return [mg for mg in mba_guilds.MONITORED_GUILDS.values() if mg.id in {g.id for g in actor.mutual_guilds}]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """When the bot has logged in and begun running, we need to ensure
        that it has the appropriate access and permissions to do its job.

        For each guild and channel that are set up as places to raise an
        alert (i.e. the entries in ALERT_TARGET_CHANNELS), we check that
        the bot has access to the guild, and we check that the bot has
        Send Messages permissions in the channel.

        If any of these conditions are not fulfilled, we crash out."""

        for alert_guild in mba_guilds.ALERT_GUILDS.values():
            if await alert_guild.is_bot_installed(self.bot) is False:
                mba_logger.error(
                    f"The bot is configured to send alerts to {alert_guild.id}, "
                    "but the bot is not installed in the server!"
                )
                raise commands.GuildNotFound(str(alert_guild.id))

        mba_logger.info("Startup checks passed and the bot is configured correctly.")

    @commands.Cog.listener()
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

        except KeyError as ex: # BUG: We need to not raise this blindly - it could be an AlertGuild!
            raise KeyError(
                f"Tried to process audit log entry for guild {entry.guild.name} "
                f"(guild ID {entry.guild.id}), but guild ID not present in MONITORED_GUILDS!"
            ) from ex

        if ale_handler(entry) is True:
            await self.send_alerts(
                banned_actor = await self.bot.solidify_actor_abstract(entry._target_id), # pylint: disable = protected-access
                banning_server_name = entry.guild.name,
                ban_reason = entry.reason,
                message_body = "A new permanent ban has been detected!",
            )

    async def fetch_most_recent_bans(
        self,
        guild: discord.Guild,
        max_bans: int = 5,
    ) -> list[discord.AuditLogEntry]:
        """This wraps the process of retrieving the most recent Audit Log events for bans in the server."""
        return await guild.audit_logs(action = discord.AuditLogAction.ban, limit = max_bans).flatten()

    def generate_base_alert_embed(
        self,
        banned_actor: Actor,
        banning_server_name: str,
        ban_reason: Optional[str],
        timestamp: datetime.datetime = datetime.datetime.now(),
    ):
        """This handles the process of creating the embed for a "New Alert" message.

        The embed generated is the "base embed" - i.e., it will not contain any references to roles
        for a particular server, since we don't yet know which server this alert is being sent to."""

        base_embed = (
            discord.Embed(
                type = "rich",
                timestamp = timestamp,
            )
            .set_author(
                name = self.bot.pprint_actor_name(banned_actor),
                icon_url = banned_actor.display_avatar.url,
            )
            .set_footer(text = f"Banned user's ID: {banned_actor.id}")
            .add_field(name = "Relevant server", value = banning_server_name, inline = False)
            .add_field(name = "Ban reason", value = ban_reason or "", inline = False)
        )

        return base_embed

    async def send_alerts(
        self,
        banned_actor: Actor,
        banning_server_name: str,
        ban_reason: Optional[str],
        message_body: Optional[str],
    ) -> None:
        """This handles the process of sending a prepared alert out to ALL configured AlertGuilds."""

        base_embed = self.generate_base_alert_embed(banned_actor, banning_server_name, ban_reason)
        mutual_mgs = self.get_mutual_monitored_guilds(banned_actor)

        for alert_guild in mba_guilds.ALERT_GUILDS.values():
            if (guild := self.bot.get_guild(alert_guild.id)) is None:
                raise commands.GuildNotFound(str(alert_guild.id))
            if (channel := guild.get_channel(alert_guild.alert_channel_id)) is None:
                raise commands.ChannelNotFound(str(alert_guild.alert_channel_id))
            if not isinstance(channel, discord.TextChannel):
                raise TypeError(f"{alert_guild.alert_channel_id} is not a text channel")

            decorated_body = alert_guild.decorate_message_body(message_body)
            decorated_embed = (
                base_embed.copy()
                .add_field(
                    name = "Motorsport servers with user",
                    value = alert_guild.decorate_mutual_guilds(mutual_mgs),
                    inline = False,
                )
            )

            await channel.send(content = decorated_body, embed = decorated_embed)

    @commands.slash_command(
        name = "alert",
        description = "Send an alert about a problematic user.",
        options = [
            discord.Option( # pylint: disable = no-member
                name = "user_id",
                description = "The Discord User ID of the user you're raising an alert for",
                input_type = int,
                required = True,
            ),
            discord.Option( # pylint: disable = no-member
                name = "server",
                description = "The Discord server raising the alert",
                input_type = str,
                required = True,
                choices = [mg.name for mg in mba_guilds.MONITORED_GUILDS.values()],
            ),
            discord.Option( # pylint: disable = no-member
                name = "reason",
                description = "The reason for the alert",
                input_type = str,
                required = False,
            ),
        ],
        ids = list(mba_guilds.ALERT_GUILDS.keys()),
        guild_only = True,
        cooldown = None,
    )
    async def slash_send_alerts(
        self,
        ctx: discord.ApplicationContext,
        user_id: int,
        server: str,
        reason: Optional[str],
    ) -> None:
        """Executes the flow to create and send an alert from a slash command.
        Responds to the user via an ephemeral message."""

        await self.send_alerts(
            banned_actor = await self.bot.solidify_actor_abstract(user_id),
            banning_server_name = server,
            ban_reason = reason,
            message_body = f"New alert raised by {self.bot.pprint_actor_name(ctx.author)}!",
        )

        await ctx.send_response(
            content = "Successfully raised an alert.",
            ephemeral = True,
            delete_after = 10,
        )
