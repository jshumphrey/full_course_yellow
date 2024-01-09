"""This file defines cogs for the Full Course Yellow bot, providing functionality
that can be imported into the scope of a pycord Bot."""
# pylint: disable = logging-not-lazy

import datetime
import discord  # This uses pycord, not discord.py
from discord.ext import commands
import logging
import typing
from typing import Any, Optional

import full_course_yellow as fcy
import fcy_guilds
import fcy_constants
from fcy_types import *  # pylint: disable = wildcard-import, unused-wildcard-import

fcy_logger = logging.getLogger("full_course_yellow")


class FCYFunctionality(commands.Cog):
    """This cog implements the majority of the functionality for the Full Course Yellow bot."""

    alert_guild_members: set[str]

    def __init__(self, bot: fcy.FCYBot) -> None:
        self.bot = bot
        self.alert_guild_members = set()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """When a new member joins, if the joined guild is an AlertGuild, update alert_guild_members."""
        if member.guild.id in fcy_constants.ENABLED_ALERT_GUILDS:
            self.alert_guild_members.add(str(member.id))

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent) -> None:
        """When a member leaves, if the left guild is an AlertGuild, update alert_guild_members.
        This needs to be the RAW member remove event because the normal member remove event
        depends on the member cache, which we're not using."""

        if payload.guild_id in fcy_constants.ENABLED_ALERT_GUILDS:
            self.alert_guild_members.remove(payload.user.id) # type: ignore - why isn't this working?

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Execute a number of tasks that need to happen at the bot's startup."""
        self.check_populate_installed_guilds()
        await self.populate_alert_guild_members()
        fcy_logger.debug(f"Enabled MonitoredGuilds: {[g.name for g in fcy_constants.ENABLED_MONITORED_GUILDS.values()]}")
        fcy_logger.debug(f"Enabled AlertGuilds: {[g.name for g in fcy_constants.ENABLED_ALERT_GUILDS.values()]}")
        fcy_logger.info("FCYFunctionality.on_ready has completed successfully.")

    @commands.Cog.listener()
    async def on_audit_log_entry(self, entry: discord.AuditLogEntry) -> None:
        """When an audit log entry is created in an installed guild, if the ALE is for a user ban, we dispatch
        the ALE to the respective guild's ALE handler for further processing.

        Some guilds have more complex moderation systems that allow for the issuance of temporary bans;
        we only want to create alerts for permanent bans, so the handling function for that server
        will need to determine whether the ban was permanent before issuing the alert."""
        # pylint: disable = unreachable
        # This listener is disabled for right now - we're still figuring out how we want to handle automatic
        # processing of audit log entries. The return statement below stops the function from doing anything.
        return

        if entry.action != discord.AuditLogAction.ban:
            return

        if entry.guild.id not in fcy_constants.ALL_ENABLED_GUILDS:
            raise commands.GuildNotFound(
                f"Could not process audit log entry for guild {entry.guild.id} / {entry.guild.name}: "
                f"guild is not an InstalledGuild, or guild is not enabled"
            )

        if entry.guild.id not in fcy_constants.ENABLED_MONITORED_GUILDS:
            # We know that it's an enabled InstalledGuild, so if the lookup in MONITORED_GUILDS
            # fails, that just means it's an AlertGuild. In that case, we don't want to process this ALE.
            return

        ale_handler = fcy_constants.ENABLED_MONITORED_GUILDS[entry.guild.id].audit_log_handler
        if ale_handler(entry) is True:
            await self.send_alerts(
                offending_actor = await self.bot.solidify_actor_abstract(entry._target_id), # pylint: disable = protected-access
                alerting_server_name = entry.guild.name,
                alert_reason = entry.reason,
                message_body = "A new permanent ban has been detected!",
                testing_guilds_only = fcy_constants.ENABLED_MONITORED_GUILDS[entry.guild.id].testing,
            )

    @staticmethod
    async def get_mutual_monitored_guilds(actor: Actor) -> list[fcy_guilds.MonitoredGuild]:
        """This wraps the process of retrieving the list of MonitoredGuilds that contain the provided Actor.

        This is done by attempting to fetch the member from each of the MonitoredGuilds, instead of simply
        caching members and using a get, because that would require that we cache and track offline members
        (because it's critical that we detect whether the user is present in the MonitoredGuild, even if
        they're offline), and the servers that this particular bot will be installed in are HUMONGOUS;
        as a result, caching members is both extremely slow and extremely expensive.

        Ultimately, a single fetch for each guild is going to be a lot less work."""

        mutual_mgs = []
        for monitored_guild in fcy_constants.ENABLED_MONITORED_GUILDS.values():
            try:
                _ = await monitored_guild.guild.fetch_member(actor.id)
                mutual_mgs.append(monitored_guild)
            except discord.Forbidden:
                fcy_logger.error(
                    f"Attempted to fetch a member from MonitoredGuild {monitored_guild.name}, "
                    "but permission was denied to perform this action!"
                )
            except discord.HTTPException:  # This is thrown by discord in the event that the user is not found
                pass  # If we don't find them, that's fine; just move on

        fcy_logger.debug(f"Mutual guilds for actor ID {actor.id}: {mutual_mgs}")
        return mutual_mgs

    def check_populate_installed_guilds(self) -> None:
        """This executes a number of checks on the bot's InstalledGuilds, and attempts to populate
        InstalledGuild.guild. This is run as part of the on_ready process."""

        for installed_guild in fcy_constants.ALL_ENABLED_GUILD_OBJECTS:
            if installed_guild.id not in {guild.id for guild in self.bot.guilds}:
                fcy_logger.error(
                    f"The bot is configured for Guild ID {installed_guild.id}, "
                    "but the bot is not installed in that Guild!"
                )
                raise commands.GuildNotFound(str(installed_guild.id))

            if (guild := self.bot.get_guild(installed_guild.id)) is None:
                fcy_logger.error(
                    f"Tried to set InstalledGuild.guild for Guild ID {installed_guild.id}, "
                    "but was unable to retrieve the Guild object from Discord!"
                )
                raise commands.GuildNotFound(str(installed_guild.id))

            installed_guild.guild = guild

        fcy_logger.info("All InstalledGuilds detected successfully. Populated self.guild for all Installed Guilds.")

    async def populate_alert_guild_members(self) -> None:
        """This process runs during startup (in on_ready) to populate self.alert_guild_members, a type of
        "limited member cache" that only tracks the members present in the configured AlertGuilds."""

        for alert_guild in fcy_constants.ENABLED_ALERT_GUILDS.values():
            async for member in alert_guild.guild.fetch_members():
                self.alert_guild_members.add(str(member.id))

        fcy_logger.info("Populated FCYFunctionality.alert_guild_members.")

    async def send_non_id_user_id_error_message(
        self,
        ctx: discord.ApplicationContext,
        option_name: str = "user_id",
    ) -> None:
        """Send an error message to the user that the Discord User ID they provided isn't actually a User ID."""
        await ctx.respond(
            content = (
                f"Sorry, it looks like the `{option_name}` you gave me isn't an actual Discord User ID.\n"
                "Remember that this needs to be a user ***ID*** - a big number, not text."
            ),
            ephemeral = True,
            delete_after = 30,
        )
        fcy_logger.info(
            f"Sent non-ID User ID error to {self.bot.pprint_actor_name(ctx.author)} as a result of their invocation "
            f"of {ctx.command.name} at {self.bot.get_current_utc_iso_time_str()}, with options: {ctx.selected_options}"
        )

    async def send_moderator_error_message(self, ctx: discord.ApplicationContext) -> None:
        """Send an error message to the user that the Discord User ID they provided belongs to a moderator."""
        await ctx.respond(
            content = (
                "The provided user ID belongs to a server moderator.\n"
                "Please don't ping a bunch of roles just to make a joke.\n\n"
                "If you just want to test out the bot, send an alert against **your own User ID**.\n"
                "The bot will detect that it's a \"self-alert\" and send an alert that only you can see."
            ),
            ephemeral = True,
            delete_after = 60,
        )
        fcy_logger.info(
            f"Sent moderator User ID error to {self.bot.pprint_actor_name(ctx.author)} as a result of their invocation "
            f"of {ctx.command.name} at {self.bot.get_current_utc_iso_time_str()}, with options: {ctx.selected_options}"
        )

    async def send_user_id_not_found_error_message(self, ctx: discord.ApplicationContext) -> None:
        """Send an error message to the user that the Discord User ID they provided could not be found."""
        user_id = self.bot.get_option_value(ctx, "user_id")
        await ctx.respond(
            content = (
                f"Sorry, I looked, but I couldn't find any Discord user with the User ID `{user_id}`.\n"
                "Please double-check that you typed or pasted it correctly."
            ),
            ephemeral = True,
            delete_after = 30,
        )
        fcy_logger.info(
            f"Sent User ID not found error to {self.bot.pprint_actor_name(ctx.author)} as a result of their invocation "
            f"of {ctx.command.name} at {self.bot.get_current_utc_iso_time_str()}, with options: {ctx.selected_options}"
        )

    async def fetch_most_recent_bans(self, guild: discord.Guild, max_bans: int = 5) -> list[discord.AuditLogEntry]:
        """This wraps the process of retrieving the most recent Audit Log events for bans in the server."""
        return await guild.audit_logs(action = discord.AuditLogAction.ban, limit = max_bans).flatten()

    async def decorate_ban(self, ban_ale: discord.AuditLogEntry) -> str:
        """This "decorates" an AuditLogEntry pertaining to a user ban, to provide a pretty-printed
        representation of the AuditLogEntry that helps a human recognize the banned user."""

        offending_actor = await self.bot.solidify_actor_abstract(ban_ale._target_id) # pylint: disable = protected-access
        return (
            f"{self.bot.pprint_actor_name(offending_actor)} "
            f"({ban_ale.reason or '[No reason provided]'})"
        )[:100]  # These values can only be up to 100 characters long

    async def determine_alert_server(self, ctx: discord.ApplicationContext) -> str:
        """Attempt to determine the name of the server for the use of the `alert` slash command, from
        the application context alone. In many use-cases, this can be determined without ever having
        to ask the user for more information, but if we do need to, we can dispatch a View to do so.

        - If the command was invoked from a MonitoredGuild, we can return the MonitoredGuild's name.

        - If not, then it must have been invoked from an AlertGuild. Cross-reference the invoking user's
        list of roles with the AlertGuild's guild_notification_roles; if we find exactly one match,
        we can return the name of that role.

        - If we find no matches, or more than one match, dispatch a View to ask the user which server to use."""

        invoking_member = typing.cast(discord.Member, ctx.interaction.user)
        invoking_guild = ctx.interaction.guild
        if invoking_guild is None or invoking_guild.id not in fcy_constants.ALL_ENABLED_GUILDS:
            raise commands.GuildNotFound(str(invoking_guild.id) if invoking_guild else "[None]")

        if invoking_guild.id in fcy_constants.ENABLED_MONITORED_GUILDS:
            return fcy_constants.ENABLED_MONITORED_GUILDS[invoking_guild.id].name

        # At this point, the invoking guild must be an AlertGuild
        invoking_alert_guild = fcy_constants.ENABLED_ALERT_GUILDS[invoking_guild.id]
        member_notification_roles = [
            role.name for role in invoking_member.roles
            if role.id in invoking_alert_guild.guild_notification_roles.values()
        ]

        if len(member_notification_roles) == 1: # The user had exactly one notification role
            return member_notification_roles[0]

        options = member_notification_roles if member_notification_roles else [
            role.name for role in invoking_alert_guild.guild.roles
            if role.id in invoking_alert_guild.guild_notification_roles.values()
        ]

        prompt = (
            "I wasn't able to automatically determine which server is raising this alert.\n"
            "Please use the dropdown below to tell me which server this alert is coming from."
        )
        selection_view = ServerSelectView(options)

        await ctx.send_response(prompt, view = selection_view, ephemeral = True)
        await selection_view.wait()
        return selection_view.selection

    def generate_base_alert_embed(
        self,
        offending_actor: Actor,
        alerting_server_name: str,
        alert_reason: Optional[str],
        timestamp: Optional[datetime.datetime] = None,
    ) -> discord.Embed:
        """This handles the process of creating the embed for a "New Alert" message.

        The embed generated is the "base embed" - i.e., it will not contain any references to roles
        for a particular server, since we don't yet know which server this alert is being sent to."""

        emg_names = ", ".join([g.name for g in fcy_constants.ENABLED_MONITORED_GUILDS.values() if g.testing is False])
        emg_string = f"{emg_names}\n\nTo include your server in this list, message Lux in #bot."

        base_embed = (
            discord.Embed(type = "rich", timestamp = timestamp or datetime.datetime.now())
            .set_author(
                name = self.bot.pprint_actor_name(offending_actor),
                icon_url = offending_actor.display_avatar.url,
            )
            .set_footer(text = f"Offending user's ID: {offending_actor.id}")
            .add_field(name = "Relevant server", value = alerting_server_name, inline = False)
            .add_field(name = "Reason for alert", value = alert_reason or "[No reason provided]", inline = False)
            .add_field(name = "Servers scanned for offending user", value = emg_string, inline = False)
        )

        return base_embed

    async def send_self_alert(
        self,
        ctx: discord.ApplicationContext,
        reason: Optional[str] = None,
        **kwargs,  # Can include any additional kwargs to Interaction.send/send_message
    ) -> None:
        """Users may want to raise an alert against themselves to test the alert functionality.
        This use-case is supported, but with a few caveats: the alert is sent ephemerally, and
        it doesn't ping anyone."""

        offending_actor = ctx.author
        mutual_mgs = await self.get_mutual_monitored_guilds(offending_actor)
        message_body = f"New alert raised by {self.bot.pprint_actor_name(ctx.author)}!"
        base_embed = self.generate_base_alert_embed(
            offending_actor,
            alerting_server_name = await self.determine_alert_server(ctx),
            alert_reason = reason,
        )

        if (alert_guild := fcy_constants.ENABLED_ALERT_GUILDS.get(ctx.guild.id)) is None:  # type: ignore - we know that the Guild won't be None
            decorated_body = message_body
            decorated_mgs = ", ".join([guild.name for guild in mutual_mgs])
        else:
            decorated_body = alert_guild.decorate_message_body(message_body)
            decorated_mgs = alert_guild.decorate_mutual_guilds(mutual_mgs)

        await ctx.respond(
            content = "Since this alert is against yourself, it's visible only to you.",
            ephemeral = True,
            delete_after = 30,
        )

        await ctx.respond(
            content = decorated_body,
            embed = (base_embed.add_field(name = "Scanned servers with user", value = decorated_mgs, inline = False)),
            ephemeral = True,
            delete_after = None,
            **kwargs,
        )

    async def send_alerts(
        self,
        offending_actor: Actor,
        alerting_server_name: str,
        alert_reason: Optional[str] = None,
        message_body: Optional[str] = None,
        testing_guilds_only: bool = False,
        **kwargs,  # Can include any additional kwargs to Interaction.send/send_message
    ) -> None:
        """This handles the process of sending a prepared alert out to ALL configured AlertGuilds."""

        base_embed = self.generate_base_alert_embed(offending_actor, alerting_server_name, alert_reason)
        mutual_mgs = await self.get_mutual_monitored_guilds(offending_actor)

        for alert_guild in fcy_constants.ENABLED_ALERT_GUILDS.values():
            if testing_guilds_only is True and alert_guild.testing is False:
                continue

            await alert_guild.get_alert_channel().send(
                content = alert_guild.decorate_message_body(message_body),
                embed = (
                    base_embed.copy()
                    .add_field(
                        name = "Scanned servers with user",
                        value = alert_guild.decorate_mutual_guilds(mutual_mgs),
                        inline = False,
                    )
                ),
                **kwargs,
            )

    @commands.slash_command(
        name = "alert",
        description = "Raise an alert about a problematic user.",
        ids = list(fcy_constants.ENABLED_ALERT_GUILDS.keys()),
        guild_only = True,
        cooldown = None,
    )
    @discord.commands.option(
        "user_id",
        type = str,
        description = "The Discord User ID of the user you're raising an alert for"
    )
    @discord.commands.option(
        "reason",
        type = str,
        description = "The reason for the alert",
        required = False,
    )
    @discord.commands.option(
        "attachment",
        type = discord.Attachment,
        description = "A screenshot or other attachment you might want to include with the alert",
        required = False,
    )
    async def slash_alert(
        self,
        ctx: discord.ApplicationContext,
        user_id: str,
        reason: Optional[str],
        attachment: Optional[discord.Attachment],
    ) -> None:
        """Executes the flow to create and send an alert from a slash command. Responds to the user ephemerally."""

        message_kwargs: dict[str, Any] = {}

        if attachment:
            message_kwargs["file"] = await attachment.to_file(spoiler = attachment.is_spoiler())

        # Make sure `user_id` is an actual Discord User ID, and not a username or display name.
        if not user_id.isdigit():
            await self.send_non_id_user_id_error_message(ctx)
            return

        # If the user is creating an alert against themself, that's valid, but we have a separate
        # execution flow for that, which sends it ephemerally and doesn't ping anyone.
        if user_id == str(ctx.author.id):
            await self.send_self_alert(ctx, reason, **message_kwargs)
            return

        # If the offending user is a server moderator, tell off the user about it.
        # We can effectively do this by checking to see if the user is in any of the ALERT_GUILDS.
        if user_id not in fcy_constants.TESTING_USER_IDS and user_id in self.alert_guild_members:
            await self.send_moderator_error_message(ctx)
            return

        try:
            solidified_actor = await self.bot.solidify_actor_abstract(user_id)
        except commands.UserNotFound:
            await self.send_user_id_not_found_error_message(ctx)
            return

        # Once all checks have passed, we can proceed to create and send the alerts.
        await self.send_alerts(
            offending_actor = solidified_actor,
            alerting_server_name = await self.determine_alert_server(ctx),
            alert_reason = reason,
            message_body = f"New alert raised by {self.bot.pprint_actor_name(ctx.author)}!",
            testing_guilds_only = fcy_constants.ALL_GUILDS[ctx.guild.id].testing, # type: ignore - we know that the Guild won't be None
            **message_kwargs,
        )

        # When we go to respond, we don't know whether we had to ask the user for more information about the server.
        # As a result, we need to try to respond normally first, then if that fails, edit the interaction response.
        response_message = "Successfully raised an alert."
        try:
            await ctx.send_response(content = response_message, delete_after = 10, ephemeral = True)
        except RuntimeError:
            await ctx.interaction.edit_original_response(content = response_message, delete_after = 10, view = None)


class ServerSelectView(discord.ui.View):
    """This view provides a way to ask the user for more information about which server a new alert should be
    raised for. In many use-cases, we can deduce the server from  the context of the interaction, but if more
    information is needed, this View can be dispatched to collect it."""

    options: list[str]
    select_menu: discord.ui.Select

    selection: str

    def __init__(self, options: list[str]) -> None:
        super().__init__()
        self.options = options

        self.select_menu = discord.ui.Select(
            select_type = discord.ComponentType.string_select,
            placeholder = "Which server should this alert come from?",
            min_values = 1,
            max_values = 1,
            options = [discord.SelectOption(label = option) for option in self.options],
        )
        self.select_menu.callback = self.select_callback

        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction) -> None: # pylint: disable = unused-argument
        """Set this View's attributes based on the selections made in the menu,
        and pass the signal that this View has stopped accepting input."""
        self.selection = str(self.select_menu.values[0])
        self.stop()
