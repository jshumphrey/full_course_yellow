"""This contains functionality to represent the servers monitored by Full Course Yellow."""
# pylint: disable = too-few-public-methods, invalid-name, too-many-arguments

from __future__ import annotations

import discord
import logging
import typing
from typing import Callable, Optional

from fcy_types import *  # pylint: disable = wildcard-import, unused-wildcard-import

logging.basicConfig(level=logging.INFO)
fcy_logger = logging.getLogger("full_course_yellow")
pycord_logger = logging.getLogger("discord")


class InstalledGuild:
    """An InstalledGuild represents a Guild on which the bot is installed.
    This might be a Guild that is monitored for new bans (a MonitoredGuild),
    or a Guild that receives alert messages about new bans (an AlertGuild)."""

    id: GuildID
    name: str
    enabled: bool
    guild: discord.Guild  # This will get set during bot.on_ready

    def __init__(
        self,
        id: GuildID,  # pylint: disable = redefined-builtin
        name: str,
        enabled: bool = True,
    ) -> None:
        self.id = id
        self.name = name
        self.enabled = enabled

    def __str__(self) -> str:
        return self.name

    @property
    def roles_dict(self) -> dict[RoleID, discord.Role]:
        """A dict of {Role ID: Role} for all roles in the guild, making it O(1) to look up a Role by ID."""
        return {role.id: role for role in self.guild.roles}


class AlertGuild(InstalledGuild):
    """An AlertGuild is a type of InstalledGuild that has a channel that
    posts new alert messages from this bot."""

    id: GuildID
    name: str
    enabled: bool
    guild: discord.Guild

    alert_channel_id: ChannelID
    general_notification_role_id: Optional[RoleID]
    guild_notification_roles: dict[GuildID, RoleID]

    def __init__(
        self,
        id: GuildID, # pylint: disable = redefined-builtin
        name: str,
        alert_channel_id: ChannelID,
        general_notification_role_id: Optional[RoleID] = None,
        guild_notification_roles: Optional[dict[GuildID, RoleID]] = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(id, name, enabled)
        self.alert_channel_id = alert_channel_id
        self.general_notification_role_id = general_notification_role_id
        self.guild_notification_roles = guild_notification_roles or {}

    def decorate_message_body(self, message_body: Optional[str]) -> str:
        """"Decorates" the provided message body by prepending this AlertGuild's
        general-notification Role, if one has been defined for this AlertGuild."""
        return (
            (message_body or "") if self.general_notification_role_id is None
            else f"<@&{self.general_notification_role_id}> {message_body or ''}"
        )

    def decorate_mutual_guilds(self, mutual_guilds: list[MonitoredGuild]) -> str:
        """"Decorates" the provided list of mutual guilds by transforming the guilds in it into
        role pings for this AlertGuild's role for that guild, based on guild_notification_roles."""

        if not mutual_guilds:
            return "[Not found in any monitored server]"

        return ", ".join(
            guild.name if guild.id not in self.guild_notification_roles
            else f"<@&{self.guild_notification_roles[guild.id]}>"
            for guild in mutual_guilds
        )


class MonitoredGuild(InstalledGuild):
    """A MonitoredGuild is a type of InstalledGuild that is monitored for new bans.

    The audit_log_handler callable is run when a new audit log entry is created"""

    id: GuildID
    name: str
    enabled: bool
    guild: discord.Guild

    audit_log_handler: Callable[[discord.AuditLogEntry], bool]

    def __init__(
        self,
        id: int, # pylint: disable = redefined-builtin
        name: str,
        audit_log_handler: Callable[[discord.AuditLogEntry], bool],
        enabled: bool = True,
    ) -> None:
        super().__init__(id, name, enabled)
        self.audit_log_handler = audit_log_handler

        if self.enabled and self.audit_log_handler is self.placeholder_ale_handler:
            fcy_logger.warning(f"MonitoredGuild {self.name} is enabled, but its audit log handler is a placeholder!")

    @staticmethod
    def true_ale_handler(_: discord.AuditLogEntry) -> bool:
        """Handle AuditLogEntries for servers for which bans are
        always permanent (i.e. we should always create an alert."""
        return True

    @staticmethod
    def false_ale_handler(_: discord.AuditLogEntry) -> bool:
        """An ALE handler that always returns False.
        This can be used for MonitoredGuilds that do not wish to automatically raise alerts."""
        return False

    @staticmethod
    def placeholder_ale_handler(_: discord.AuditLogEntry) -> bool:
        """An ALE handler that always returns False.
        This can be used to set up placeholder MonitoredGuilds."""
        return False


def rf1_ale_handler(entry: discord.AuditLogEntry) -> bool:
    """Handle AuditLogEntries for the /r/formula1 server."""

    # Cast attributes of the ALE based on what we know about the ALE.
    banning_moderator = typing.cast(discord.Member, entry.user)

    # If the user was banned outside of the normal moderation system, raise an alert.
    if banning_moderator.id not in {
        424900962449358848,  # Formula One
        886984180800577636,  # Formula One Dev
    }:
        return True

    # If the ban is temporary, don't raise an alert.
    if entry.reason and any(x in entry.reason for x in ["10 day ban", "30 day ban"]):
        return False

    # Otherwise, this is a permanent ban - raise an alert.
    return True
