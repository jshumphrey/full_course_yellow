"""This file defines a number of constants and globals used by other components of the Full Course Yellow bot."""

from fcy_guilds import MonitoredGuild, AlertGuild
from fcy_types import *  # pylint: disable = wildcard-import, unused-wildcard-import

FULL_COURSE_YELLOW_USER_ID = "1105933971264647168"
LUX_USER_ID = "145582654857805825"
LUX_TESTING_USER_ID = "1086293154304634910"

TESTING_USER_IDS = {LUX_TESTING_USER_ID}

#LUX_DEV_MG = MonitoredGuild(1079109375647555695, "Lux's Dev/Testing Server", MonitoredGuild.true_ale_handler)

R_F1_MG = MonitoredGuild(177387572505346048, "/r/formula1", MonitoredGuild.placeholder_ale_handler, enabled = False)
OF1D_MG = MonitoredGuild(142082511902605313, "Formula One", MonitoredGuild.placeholder_ale_handler, enabled = False)
NASCAR_MG = MonitoredGuild(877239953174691910, "NASCAR", MonitoredGuild.placeholder_ale_handler, enabled = False)
LTL_MG = MonitoredGuild(271077595913781248, "Left Turn Lounge", MonitoredGuild.placeholder_ale_handler, enabled = False)
RED_BULL_MG = MonitoredGuild(1014269980960899173, "Oracle Red Bull Racing", MonitoredGuild.placeholder_ale_handler, enabled = False)
MCLAREN_MG = MonitoredGuild(897158147511316522, "McLaren", MonitoredGuild.placeholder_ale_handler, enabled = False)
R_WEC_MG = MonitoredGuild(193548511126487040, "/r/WEC", MonitoredGuild.placeholder_ale_handler, enabled = False)
IMSA_MG = MonitoredGuild(878844647173132359, "IMSA", MonitoredGuild.placeholder_ale_handler, enabled = False)
EXTREME_E_MG = MonitoredGuild(830080368089890887, "Extreme E", MonitoredGuild.placeholder_ale_handler, enabled = False)
R_INDYCAR_MG = MonitoredGuild(360079258980319232, "/r/INDYCAR", MonitoredGuild.placeholder_ale_handler, enabled = False)

# Publish a dict that maps each MonitoredGuild ID to its MonitoredGuild.
MONITORED_GUILDS: dict[GuildID, MonitoredGuild] = {
    mg_object.id: mg_object
    for mg_object in locals().values()
    if isinstance(mg_object, MonitoredGuild)
    and mg_object.enabled is True
}

LUX_DEV_AG = AlertGuild(
    id = 1079109375647555695,
    name = "Lux's Dev/Testing Server",
    alert_channel_id = 1105555454605672448,
    general_notification_role_id = 1136730925481340968,
    guild_notification_roles = {
        1079109375647555695: 1136731212828901397, # Lux's Dev / Testing Server
        177387572505346048: 1143326383955783783, # /r/formula1
    },
)
SMS_AG = AlertGuild(
    id = 959541053915037697,
    name = "Staff of MS Discords",
    alert_channel_id = 960480902331383809,
    guild_notification_roles = {
        177387572505346048: 959862354663850086, # /r/formula1
        142082511902605313: 959542104302944327, # OF1D
        877239953174691910: 959542131251380274, # NASCAR
        271077595913781248: 959543894704537630, # Left Turn Lounge
        1014269980960899173: 1041018881214525561, # Red Bull
        897158147511316522: 953661058118197338, # McLaren
        193548511126487040: 1118919138321104906, # WEC
        878844647173132359: 1129338140390346873, # IMSA
        830080368089890887: 1133781212251553883, # Extreme E
        360079258980319232: 1112467709045788692, # /r/IndyCar
    },
    enabled = False,
)

# Publish a dict that maps each AlertGuild ID to its AlertGuild.
ALERT_GUILDS: dict[GuildID, AlertGuild] = {
    ag_object.id: ag_object
    for ag_object in locals().values()
    if isinstance(ag_object, AlertGuild)
    and ag_object.enabled is True
}

if __name__ == "__main__":
    breakpoint() # pylint: disable = forgotten-debug-statement
    pass # pylint: disable = unnecessary-pass
