"""This contains functionality to represent the servers monitored by motorsport_ban_alerts."""
# pylint: disable = too-few-public-methods, invalid-name

import discord
import typing
from typing import Callable, Optional

Snowflake = int
ChannelID = Snowflake
GuildID = Snowflake
RoleID = Snowflake


class InstalledGuild:
    """An InstalledGuild represents a Guild on which the bot is installed.
    This might be a Guild that is monitored for new bans (a MonitoredGuild),
    or a Guild that receives alert messages about new bans (an AlertGuild)."""

    id: GuildID
    name: str

    def __init__(
        self,
        id: GuildID,  # pylint: disable = redefined-builtin
        name: str
    ) -> None:
        self.id = id
        self.name = name

    def __str__(self) -> str:
        return self.name

    async def is_bot_installed(self, bot: discord.Bot) -> bool:
        """Assesses whether the provided bot is installed on the guild."""
        return self.id in {guild.id for guild in bot.guilds}


class AlertGuild(InstalledGuild):
    """An AlertGuild is a type of InstalledGuild that has a channel that
    posts new alert messages from this bot."""

    id: GuildID
    name: str

    alert_channel_id: ChannelID
    guild_notification_roles: Optional[dict[GuildID, RoleID]]

    def __init__(
        self,
        id: GuildID, # pylint: disable = redefined-builtin
        name: str,
        alert_channel_id: ChannelID,
        guild_notification_roles: Optional[dict[GuildID, RoleID]] = None,
    ) -> None:
        super().__init__(id, name)
        self.alert_channel_id = alert_channel_id
        self.guild_notification_roles = guild_notification_roles

    async def can_bot_send_alerts(self, bot: discord.Bot) -> bool:
        """Assesses whether the provided bot has the permissions
        to send messages to this AlertGuild's alert channel."""
        return (
            bot
            .get_partial_messageable(self.alert_channel_id)
            .can_send(discord.Message)
        )


class MonitoredGuild(InstalledGuild):
    """A MonitoredGuild is a type of InstalledGuild that is monitored for new bans."""

    id: GuildID
    name: str

    audit_log_handler: Callable[[discord.AuditLogEntry], bool]

    def __init__(
        self,
        id: int, # pylint: disable = redefined-builtin
        name: str,
        audit_log_handler: Callable[[discord.AuditLogEntry], bool],
    ) -> None:
        super().__init__(id, name)
        self.audit_log_handler = audit_log_handler


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
lux_dev_mg = MonitoredGuild(1079109375647555695, "Lux's Dev/Testing Server", true_ale_handler)
r_f1_mg = MonitoredGuild(177387572505346048, "/r/formula1", rf1_ale_handler)
# of1d_mg = MonitoredGuild(142082511902605313, "Formula One", None)
# nascar_mg = MonitoredGuild(877239953174691910, "Nascar", None)

# Publish a dict that maps each MonitoredGuild ID to its MonitoredGuild.
MONITORED_GUILDS: dict[GuildID, MonitoredGuild] = {
    mg_object.id: mg_object
    for object_name, mg_object in locals().items()
    if object_name[-3:] == "_mg"
}

lux_dev_ag = AlertGuild(1079109375647555695, "Lux's Dev/Testing Server", 1105555454605672448)
# sms_ag = AlertGuild(959541053915037697, "Staff of MS Discords, 960480902331383809)

# Publish a dict that maps each AlertGuild ID to its AlertGuild.
ALERT_GUILDS: dict[GuildID, AlertGuild] = {
    ag_object.id: ag_object
    for object_name, ag_object in locals().items()
    if object_name[-3:] == "_ag"
}

if __name__ == "__main__":
    breakpoint() # pylint: disable = forgotten-debug-statement
    pass # pylint: disable = unnecessary-pass
