"""This file defines cogs for the Motorsport Ban Alerts bot, providing functionality
that can be imported into the scope of a pycord Bot."""
# pylint: disable = logging-not-lazy

import datetime
import discord  # This uses pycord, not discord.py
from discord.ext import commands
import logging
from typing import Optional

import motorsport_ban_alerts as mba
import motorsport_ban_guilds as mba_guilds


Snowflake = int
ChannelID = Snowflake
GuildID = Snowflake
RoleID = Snowflake
ActorID = Snowflake
Actor = discord.User | discord.Member


logging.basicConfig(level=logging.INFO)
mba_logger = logging.getLogger("motorsport_ban_alerts")
pycord_logger = logging.getLogger("discord")

class ServerSelectView(discord.ui.View):
    pass

class NewAlertModal(discord.ui.Modal):
    """This Modal captures information for a new ban."""

    def __init__(
        self,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.InputText(
            label = "Banned User's ID",
            placeholder = "The Discord User ID of the user to create the alert for.",
            style = discord.InputTextStyle.short,
            required = True,
        ))
        self.add_item(discord.ui.InputText(
            label = "Reason for the Alert",
            placeholder = "The reason for raising an Alert for this user.",
            style = discord.InputTextStyle.long,
            required = False,
        ))

    async def callback(self, interaction: discord.Interaction):
        pass


class MBAFunctionality(commands.Cog):
    """This cog implements the majority of the functionality for the Motorsport Ban Alerts bot."""

    alert_guild_members: set[str]

    def __init__(self, bot: mba.MBABot):
        self.bot = bot
        self.alert_guild_members = set()

    @staticmethod
    def get_mutual_monitored_guilds(actor: Actor) -> list[mba_guilds.MonitoredGuild]:
        """This wraps the process of retrieving the list of MonitoredGuilds that contain the provided Actor."""
        return [mg for mg in mba_guilds.MONITORED_GUILDS.values() if mg.id in {g.id for g in actor.mutual_guilds}]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """When a new member joins, if the joined guild is an AlertGuild, update alert_guild_members."""
        if member.guild.id in mba_guilds.ALERT_GUILDS:
            self.alert_guild_members.add(str(member.id))

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        """When a member leaves, if the left guild is an AlertGuild, update alert_guild_members.
        This needs to be the RAW member remove event because the normal member remove event
        depends on the member cache, which we're not using."""

        if payload.guild_id in mba_guilds.ALERT_GUILDS:
            self.alert_guild_members.remove(payload.user.id) # type: ignore - why isn't this working?

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Execute a number of tasks that need to happen at the bot's startup."""
        self.check_populate_installed_guilds()
        await self.populate_alert_guild_members()
        mba_logger.info("MBAFunctionality.on_ready has completed successfully.")

    @commands.Cog.listener()
    async def on_audit_log_entry(self, entry: discord.AuditLogEntry) -> None:
        """When an audit log entry is created in an installed guild, if the ALE is for a user ban, we dispatch
        the ALE to the respective guild's ALE handler for further processing.

        Some guilds have more complex moderation systems that allow for the issuance of temporary bans;
        we only want to create alerts for permanent bans, so the handling function for that server
        will need to determine whether the ban was permanent before issuing the alert."""

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

    def check_populate_installed_guilds(self) -> None:
        """This executes a number of checks on the bot's InstalledGuilds, and attempts to populate
        InstalledGuild.guild. This is run as part of the on_ready process."""

        for installed_guild in list(mba_guilds.MONITORED_GUILDS.values()) + list(mba_guilds.ALERT_GUILDS.values()):
            if installed_guild.id not in {guild.id for guild in self.bot.guilds}:
                mba_logger.error(
                    f"The bot is configured for Guild ID {installed_guild.id}, "
                    "but the bot is not installed in that Guild!"
                )
                raise commands.GuildNotFound(str(installed_guild.id))

            if (guild := self.bot.get_guild(installed_guild.id)) is None:
                mba_logger.error(
                    f"Tried to set InstalledGuild.guild for Guild ID {installed_guild.id}, "
                    "but was unable to retrieve the Guild object from Discord!"
                )
                raise commands.GuildNotFound(str(installed_guild.id))

            installed_guild.guild = guild

        mba_logger.info("All InstalledGuilds detected successfully. Populated self.guild for all Installed Guilds.")

    async def populate_alert_guild_members(self) -> None:
        """This process runs during startup (in on_ready) to populate self.alert_guild_members, a type of
        "limited member cache" that only tracks the members present in the configured AlertGuilds."""

        for alert_guild in mba_guilds.ALERT_GUILDS.values():
            async for member in alert_guild.guild.fetch_members():
                self.alert_guild_members.add(str(member.id))

        mba_logger.info("Populated MBAFunctionality.alert_guild_members.")

    async def fetch_most_recent_bans(
        self,
        guild: discord.Guild,
        max_bans: int = 5,
    ) -> list[discord.AuditLogEntry]:
        """This wraps the process of retrieving the most recent Audit Log events for bans in the server."""
        return await guild.audit_logs(action = discord.AuditLogAction.ban, limit = max_bans).flatten()

    async def decorate_ban(self, ban_ale: discord.AuditLogEntry) -> str:
        """This "decorates" an AuditLogEntry pertaining to a user ban, to provide a pretty-printed
        representation of the AuditLogEntry that helps a human recognize the banned user."""

        banned_actor = await self.bot.solidify_actor_abstract(ban_ale._target_id) # pylint: disable = protected-access
        return (
            f"{self.bot.pprint_actor_name(banned_actor)} "
            f"({ban_ale.reason or '[No reason provided]'})"
        )[:100]  # These values can only be up to 100 characters long

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
            .add_field(name = "Ban reason", value = ban_reason or "[No reason provided]", inline = False)
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
    async def slash_alert(
        self,
        ctx: discord.ApplicationContext,
        user_id: int,
        server: str,
        reason: Optional[str],
    ) -> None:
        """Executes the flow to create and send an alert from a slash command.
        Responds to the user via an ephemeral message."""

        # Check to make sure the user isn't a moderator.
        # We can effectively do this by checking to see if the user is in any of the ALERT_GUILDS.
        if str(user_id) in self.alert_guild_members:
            await ctx.send_response(
                content = (
                    "The provided user ID belongs to a motorsport-server moderator.\n"
                    "Please don't ping a bunch of roles just to make a joke."
                ),
                ephemeral = True,
            )
            mba_logger.info(f"Declining to create alert against User ID {user_id} because they are a moderator.")

        else:
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
