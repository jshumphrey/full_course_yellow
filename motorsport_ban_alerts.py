"""This bot monitors various motorsport Discord servers for new instances
where a user is banned from the server, or other critera as specified
for that server.

When a new ban is detected, a message is sent to the "Staff of Motorsport
Discords" server, alerting all mod staff of the new ban, and providing
information about whether the newly-banned user is present in any of the
other servers."""

import datetime
import discord  # This uses pycord, not discord.py
from discord.ext import commands
import logging
import sys

import motorsport_ban_cogs as mba_cogs


Actor = discord.User | discord.Member


TOKEN_FILENAME = "token.txt"
INTENTS = discord.Intents.default()
INTENTS.members = True
MEMBER_CACHE_FLAGS = discord.MemberCacheFlags.none()
ALLOWED_MENTIONS = discord.AllowedMentions(
    everyone = False,
    roles = True,
    users = False,
    replied_user = True,
)

logging.basicConfig(level=logging.INFO)
mba_logger = logging.getLogger("motorsport_ban_alerts")
pycord_logger = logging.getLogger("discord")


class MBABot(discord.Bot):
    """This subclass of Bot defines the Motorsport Ban Alerts bot."""

    @staticmethod
    def get_current_utc_iso_time_str() -> str:
        """This is a shortcut to get a simple datetime string in the form
        `YYYY-MM-DD HH:MM:SS UTC` for the current UTC date and time."""
        return datetime.datetime.now(datetime.timezone.utc).strftime(r"%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def pprint_timedelta_from_timestamp(timestamp: datetime.datetime) -> str:
        """This is a shortcut to take in a datetime that represents a time in the past,
        and quickly print out "H hours, M minutes ago". An attempt is made to ensure
        timezone awareness."""

        current_datetime = datetime.datetime.now(datetime.timezone.utc)

        if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
            # The timestamp is timezone-naive
            timedelta = current_datetime - timestamp.replace(tzinfo = datetime.timezone.utc)
        else:
            # The timestamp is timezone-aware
            timedelta = current_datetime - timestamp

        days = timedelta.days
        hours = timedelta.seconds // 3600
        minutes = (timedelta.seconds % 3600) // 60

        return ", ".join([
            f"{days} days" if days > 0 else "",
            f"{hours} hours" if hours > 0 else "",
            f"{minutes} minutes" if minutes > 0 else "",
        ]) + " ago"

    @staticmethod
    def pprint_actor_name(actor: Actor) -> str:
        """This is a quick shortcut to generate a pretty-printed Actor name.
        This requires an actual Actor; await solidify_actor_abstract if necessary."""
        discord_username = actor.name if actor.discriminator == "0" else f"{actor.name}#{actor.discriminator}"
        if actor.global_name is None or actor.global_name == discord_username:
            return discord_username
        return f"{actor.global_name} ({actor.name}#{actor.discriminator})"

    async def solidify_actor_abstract(self, actor_abstract: Actor | int | str | None) -> Actor:
        """This takes a "Actor abstract" - a nebulous parameter that might be a fully-fledged Actor,
        or their user ID in integer form, their user ID in string form, or None. The actor abstract is then
        "solidified" into a real Actor, if possible. If not possible, commands.UserNotFound is raised."""

        if actor_abstract is None:
            raise commands.UserNotFound("Attempted to solidify the provided Actor abstract, but it is None!")

        if isinstance(actor_abstract, Actor):
            return actor_abstract

        user_id = int(actor_abstract)
        actor = await self.fetch_user(user_id)
        if actor is None:
            raise commands.UserNotFound(
                "Attempted to solidify the provided Actor abstract, "
                f"but could not find any Discord user with user ID {user_id}!"
            )

        return actor

    async def on_error(  # pylint: disable = arguments-differ
        self,
        event: str,
        *args,  # pylint: disable = unused-argument
        **kwargs  # pylint: disable = unused-argument
    ) -> None:
        """This listener implements custom error handling for exceptions raised during other listeners.
        The primary goal is to clean up the exceptions that are printed out to the log.

        This function will be called from inside an exception handler, so the bare `raise` statement
        will successfully pick up the exception. (We hope.)"""

        if (ex := sys.exception()) is None:
            mba_logger.error(
                f"on_error was called during the execution of {event} at time, "
                "but no exception was raised."
            )
            return

        try:  # We need to intentially re-raise the exception so that the logger can pick up the traceback
            raise ex
        except Exception:  # pylint: disable = broad-exception-caught
            mba_logger.exception( # This only works inside an exception handler
                f"Exception raised during the handling of {event} "
                f"at time"
            )

    async def on_application_command_error(
        self,
        context: discord.ApplicationContext,
        exception: commands.CommandError, # pylint: disable = unused-argument
    ) -> None:
        """This listener implements custom error handling for exceptions raised during the invocation
        of a Command. The primary goal is to clean up the exceptions that are printed out to the log."""

        try: # We need to intentially re-raise the exception so that the logger can pick up the traceback
            raise exception
        except commands.CommandError:
            mba_logger.exception( # This only works inside an exception handler
                f"Exception raised during the invocation of {context.command.name} "
                f"by {self.pprint_actor_name(context.author)} "
                f"at {self.get_current_utc_iso_time_str()}"
            )

    async def on_application_command(self, ctx: discord.ApplicationContext) -> None:
        """This listener implements custom logging for whenever a Command is invoked."""
        mba_logger.info(
            f"{ctx.command.name} invoked by {self.pprint_actor_name(ctx.author)} "
            f"at {self.get_current_utc_iso_time_str()}"
        )


def read_token(token_filename: str) -> str:
    """Load the bot's token from the file."""
    with open(token_filename, "r", encoding="utf-8") as infile:
        return infile.read().strip()


def main():
    """Execute top-level functionality - load the token and start the bot."""
    bot = MBABot(
        intents = INTENTS,
        member_cache_flags = MEMBER_CACHE_FLAGS,
        allowed_mentions = ALLOWED_MENTIONS,
    )
    bot.add_cog(mba_cogs.MBAFunctionality(bot))
    bot.run(token = read_token(TOKEN_FILENAME))


if __name__ == "__main__":
    main()
