"""This file defines a number of constants and globals used by other components of the Full Course Yellow bot."""

from fcy_guilds import MonitoredGuild, AlertGuild
from fcy_types import *  # pylint: disable = wildcard-import, unused-wildcard-import

FULL_COURSE_YELLOW_USER_ID = "1105933971264647168"
LUX_USER_ID = "145582654857805825"
LUX_TESTING_USER_ID = "1086293154304634910"

TESTING_USER_IDS = {LUX_TESTING_USER_ID}

LUX_DEV_MG = MonitoredGuild(
    1079109375647555695,
    "Lux's Dev/Testing Server",
    MonitoredGuild.true_ale_handler,
    testing = True,
)
R_F1_MG = MonitoredGuild(177387572505346048, "/r/formula1", MonitoredGuild.placeholder_ale_handler)
OF1D_MG = MonitoredGuild(142082511902605313, "Formula One", MonitoredGuild.placeholder_ale_handler)
WILLIAMS_MG = MonitoredGuild(1135611684560572466, "Williams Gaming Club", MonitoredGuild.placeholder_ale_handler)
YES2_MG = MonitoredGuild(765047002156367873, "Yes2 Motorsports", MonitoredGuild.placeholder_ale_handler)
MCLAREN_MG = MonitoredGuild(897158147511316522, "McLaren", MonitoredGuild.placeholder_ale_handler)
R_WEC_MG = MonitoredGuild(193548511126487040, "/r/WEC", MonitoredGuild.placeholder_ale_handler)
LTL_MG = MonitoredGuild(271077595913781248, "Left Turn Lounge", MonitoredGuild.placeholder_ale_handler)
ORBR_MG = MonitoredGuild(1014269980960899173, "Oracle Red Bull Racing", MonitoredGuild.placeholder_ale_handler)

NASCAR_MG = MonitoredGuild(877239953174691910, "NASCAR", MonitoredGuild.placeholder_ale_handler, enabled = False)
IMSA_MG = MonitoredGuild(878844647173132359, "IMSA", MonitoredGuild.placeholder_ale_handler, enabled = False)
EXTREME_E_MG = MonitoredGuild(830080368089890887, "Extreme E", MonitoredGuild.placeholder_ale_handler, enabled = False)
R_INDYCAR_MG = MonitoredGuild(360079258980319232, "/r/INDYCAR", MonitoredGuild.placeholder_ale_handler, enabled = False)
ALPINE_MG = MonitoredGuild(824991244706512897, "Alpine", MonitoredGuild.placeholder_ale_handler, enabled = False)

LUX_DEV_AG = AlertGuild(
    id = 1079109375647555695,
    name = "Lux's Dev/Testing Server",
    alert_channel_id = 1105555454605672448,
    general_notification_role_id = 1136730925481340968,
    guild_notification_roles = {
        1079109375647555695: 1136731212828901397, # Lux's Dev / Testing Server
        177387572505346048: 1143326383955783783, # /r/formula1
    },
    testing = True,
)
SMS_AG = AlertGuild(
    id = 959541053915037697,
    name = "Staff of MS Discords",
    alert_channel_id = 960480902331383809,
    general_notification_role_id = 1144006270454599720,
    guild_notification_roles = {
        177387572505346048: 959862354663850086, # /r/formula1
        142082511902605313: 959542104302944327, # OF1D
        877239953174691910: 959542131251380274, # NASCAR
        271077595913781248: 959543894704537630, # Left Turn Lounge
        1014269980960899173: 1041018881214525561, # Red Bull
        897158147511316522: 1067767300935131216, # McLaren
        193548511126487040: 1118919138321104906, # WEC
        878844647173132359: 1129338140390346873, # IMSA
        830080368089890887: 1133781212251553883, # Extreme E
        360079258980319232: 1112467709045788692, # /r/IndyCar
        1135611684560572466: 1194260632174874754, # Williams Gaming Club
        824991244706512897: 1283392453721980969, # Alpine
    },
)

# Expose some dicts as public collections of MonitoredGuilds and AlertGuilds.
ALL_MONITORED_GUILDS: dict[GuildID, MonitoredGuild] = {
    mg_object.id: mg_object
    for mg_object in sorted(
        [obj for obj in locals().values() if isinstance(obj, MonitoredGuild)],
        key = lambda mg_object: mg_object.name.casefold()
    )
}
ENABLED_MONITORED_GUILDS = {mg_id: mg for mg_id, mg in ALL_MONITORED_GUILDS.items() if mg.enabled is True}

ALL_ALERT_GUILDS: dict[GuildID, AlertGuild] = {
    ag_object.id: ag_object
    for ag_object in sorted(
        [obj for obj in locals().values() if isinstance(obj, AlertGuild)],
        key = lambda ag_object: ag_object.name.casefold()
    )
}
ENABLED_ALERT_GUILDS = {ag_id: ag for ag_id, ag in ALL_ALERT_GUILDS.items() if ag.enabled is True}

ALL_GUILDS = ALL_MONITORED_GUILDS | ALL_ALERT_GUILDS
ALL_GUILD_OBJECTS = set(ALL_MONITORED_GUILDS.values()) | set(ALL_ALERT_GUILDS.values())
ALL_ENABLED_GUILDS = ENABLED_MONITORED_GUILDS | ENABLED_ALERT_GUILDS
ALL_ENABLED_GUILD_OBJECTS = set(ENABLED_MONITORED_GUILDS.values()) | set(ENABLED_ALERT_GUILDS.values())

ALL_TESTING_GUILDS = {ig_id: ig for ig_id, ig in ALL_GUILDS.items() if ig.testing is True}
ENABLED_TESTING_GUILDS = {ig_id: ig for ig_id, ig in ALL_TESTING_GUILDS.items() if ig.enabled is True}

if __name__ == "__main__":
    breakpoint() # pylint: disable = forgotten-debug-statement
    pass # pylint: disable = unnecessary-pass
