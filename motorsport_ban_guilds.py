"""This contains functionality to represent the servers monitored by motorsport_ban_alerts."""
# pylint: disable = too-few-public-methods


import discord
import typing
from typing import Callable


class MonitoredGuild:
    """A MonitoredGuild is a Guild on which the bot is installed,
    and which will be monitored for new bans.

    This class is generally a simple container to organize various
    attributes for eacn MonitoredGuild."""

    guild_id: int
    name: str

    audit_log_handler: Callable[[discord.AuditLogEntry], bool]

    def __init__(
        self,
        guild_id: int,
        name: str,
        audit_log_handler: Callable[[discord.AuditLogEntry], bool],
    ) -> None:
        self.guild_id = guild_id
        self.name = name
        self.audit_log_handler = audit_log_handler

    def __str__(self) -> str:
        return self.name


def true_ale_handler(_: discord.AuditLogEntry) -> bool:
    """Handle AuditLogEntries for servers for which bans are
    always permanent (i.e. we should always create an alert."""
    return True


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


# With the class structure set up, define some MonitoredGuild objects for public use.
lux_dev_mg = MonitoredGuild(1079109375647555695, "Lux's Dev Server", true_ale_handler)
rf1_mg = MonitoredGuild(177387572505346048, "/r/formula1", rf1_ale_handler)

MONITORED_GUILDS = {  # Publish a dict that maps each guild ID to its MonitoredGuild.
    mg_object.guild_id: mg_object
    for object_name, mg_object in locals().items()
    if object_name[:3] == "_mg"
}
