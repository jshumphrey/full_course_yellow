"""This file defines cogs for the Motorsport Ban Alerts bot, providing functionality
that can be imported into the scope of a pycord Bot."""

import datetime
import discord  # This uses pycord, not discord.py
from discord.ext import commands
import logging
from typing import Optional

import motorsport_ban_guilds as mba_guilds


Actor = discord.User | discord.Member

logging.basicConfig(level=logging.INFO)
mba_logger = logging.getLogger("motorsport_ban_alerts")
pycord_logger = logging.getLogger("discord")

class MBAFunctionality(commands.Cog):
    """This cog implements the majority of the functionality for the Motorsport Ban Alerts bot."""

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @staticmethod
    def get_current_utc_iso_time_str() -> str:
        """This is a shortcut to get a simple datetime string in the form
        `YYYY-MM-DD HH:MM:SS UTC` for the current UTC date and time."""
        return datetime.datetime.now(datetime.timezone.utc).strftime(r"%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def pprint_actor_name(actor: Actor) -> str:
        """This is a quick shortcut to generate a pretty-printed Actor name.
        This requires an actual Actor; await solidify_actor_abstract if necessary."""
        return f"{actor.global_name} ({actor.name}#{actor.discriminator})"

    @staticmethod
    def get_mutual_monitored_guilds(actor: Actor) -> list[mba_guilds.MonitoredGuild]:
        """This wraps the process of retrieving the list of MonitoredGuilds that contain the provided Actor."""
        return [mg for mg in mba_guilds.MONITORED_GUILDS.values() if mg.guild_id in {g.id for g in actor.mutual_guilds}]

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
                raise RuntimeError(
                    f"The bot is configured to send alerts to {alert_guild.name}, "
                    "but the bot is not installed in the server!"
                )

            if await alert_guild.can_bot_send_alerts(self.bot) is False:
                raise RuntimeError(
                    f"The bot is configured to send alerts to {alert_guild.name}, "
                    "but it does not have the appropriate permissions "
                    "in that server's configured alert channel!"
                )

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

        except KeyError as ex:
            raise KeyError(
                f"Tried to process audit log entry for guild {entry.guild.name} "
                f"(guild ID {entry.guild.id}), but guild ID not present in MONITORED_GUILDS!"
            ) from ex

        if ale_handler(entry) is True:
            alert_embed = await self.create_alert_embed(
                banned_actor = await self.solidify_actor_abstract(entry._target_id), # pylint: disable = protected-access
                banning_server_name = entry.guild.name,
                ban_reason = entry.reason,
            )
            await self.send_alert(
                message_body = "A new permanent ban has been detected!",
                alert_embed = alert_embed,
            )

    async def solidify_actor_abstract(self, actor_abstract: Actor | int | str | None) -> Actor:
        """This takes a "Actor abstract" - a nebulous parameter that might be a fully-fledged Actor,
        or their user ID in integer form, their user ID in string form, or None. The actor abstract is then
        "solidified" into a real Actor, if possible. If not possible, commands.UserNotFound is raised."""

        if actor_abstract is None:
            raise commands.UserNotFound("Attempted to solidify the provided Actor abstract, but it is None!")

        if isinstance(actor_abstract, Actor):
            return actor_abstract

        user_id = int(actor_abstract)
        actor = await self.bot.fetch_user(user_id)
        if actor is None:
            raise commands.UserNotFound(
                "Attempted to solidify the provided Actor abstract, "
                f"but could not find any Discord user with user ID {user_id}!"
            )

        return actor

    async def create_alert_embed(
        self,
        banned_actor: Actor,
        banning_server_name: str,
        ban_reason: Optional[str],
        timestamp: datetime.datetime = datetime.datetime.now(),
    ):
        """This handles the process of creating an alert from a provided ALE."""

        mutual_mgs = self.get_mutual_monitored_guilds(banned_actor)
        mutual_mg_names = "None" if not mutual_mgs else ", ".join(mg.name for mg in mutual_mgs)

        embed = (
            discord.Embed(
                type = "rich",
                timestamp = timestamp,
            )
            .set_author(
                name = self.pprint_actor_name(banned_actor),
                icon_url = banned_actor.display_avatar.url,
            )
            .set_footer(text = f"Banned user's ID: {banned_actor.id}")
            .add_field(name = "Relevant server", value = banning_server_name, inline = False)
            .add_field(name = "Ban reason", value = ban_reason or "", inline = False)
            .add_field(name = "Motorsport servers with user", value = mutual_mg_names, inline = False)
        )

        return embed

    async def old_create_alert_embed(self, entry: discord.AuditLogEntry) -> discord.Embed:
        """This handles the process of creating an alert from a provided ALE."""

        banned_actor = await self.solidify_actor_abstract(entry._target_id) # pylint: disable = protected-access

        mutual_guild_names = (
            "None" if not (mutual_guilds := banned_actor.mutual_guilds)
            else ", ".join(g.name for g in mutual_guilds)
        )

        description = (
            f"**Banning server:** {entry.guild.name}\n\n"
            f"**Ban reason:** {entry.reason or ''}\n\n"
            f"**Motorsport servers with user:** {mutual_guild_names}"
        )

        embed = (
            discord.Embed(
                type = "rich",
                description = description,
                timestamp = entry.created_at
            )
            .set_author(
                name = self.pprint_actor_name(banned_actor),
                icon_url = banned_actor.display_avatar.url,
            )
            .set_footer(text = f"Banned user's ID: {banned_actor.id}")
            .add_field(name = "Banning server", value = entry.guild.name)
        )

        return embed

    async def send_alert(self, message_body: Optional[str], alert_embed: discord.Embed) -> None:
        """This handles the process of sending a prepared alert out to the AlertGuilds."""

        for alert_guild in mba_guilds.ALERT_GUILDS.values():
            if (guild := self.bot.get_guild(alert_guild.guild_id)) is None:
                mba_logger.error(
                    f"send_alert: Unable to retrieve Guild for {alert_guild.name}! "
                    f"(Guild ID: {alert_guild.guild_id})"
                )
                return

            if (channel := guild.get_channel(alert_guild.alert_target_channel_id)) is None:
                mba_logger.error(
                    f"send_alert: Unable to retreive alert Channel for {alert_guild.name}! "
                    f"(Guild ID: {alert_guild.guild_id}; Channel ID: {alert_guild.alert_target_channel_id})"
                )
                return

            if not isinstance(channel, discord.TextChannel):
                mba_logger.error(
                    f"send_alert: Designated alert Channel for {alert_guild.name} is not a text channel! "
                    f"(Guild ID: {alert_guild.guild_id}; Channel ID: {alert_guild.alert_target_channel_id})"
                )
                return

            await channel.send(content = message_body, embed = alert_embed)

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
        guild_ids = list(mba_guilds.ALERT_GUILDS.keys()),
        guild_only = True,
        cooldown = None,
    )
    async def slash_create_and_send_alert(
        self,
        ctx: discord.ApplicationContext,
        user_id: int,
        server: str,
        reason: Optional[str],
    ) -> None:
        """Executes the flow to create and send an alert from a slash command.
        Responds to the user via an ephemeral message."""

        embed = await self.create_alert_embed(
            banned_actor = await self.solidify_actor_abstract(user_id),
            banning_server_name = server,
            ban_reason = reason
        )
        await self.send_alert(
            message_body = f"New alert raised by {self.pprint_actor_name(ctx.user)}!",
            alert_embed = embed
        )

        await ctx.send_response(
            content = "Successfully raised an alert.",
            ephemeral = True,
            delete_after = 10,
        )

        mba_logger.info(
            f"slash_create_and_send_alert invoked by {self.pprint_actor_name(ctx.user)} "
            f"at {self.get_current_utc_iso_time_str()}"
        )
