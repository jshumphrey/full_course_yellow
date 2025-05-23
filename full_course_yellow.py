"""This bot monitors various motorsport Discord servers for new instances where a user is banned from the server,
or other critera as specified for that server.

When a new ban is detected, a message is sent to the "Staff of Motorsport Discords" server, alerting all mod staff
of the new ban, and providing information about whether the newly-banned user is present in any of the other servers."""

import datetime
import discord  # This uses pycord, not discord.py
from discord.ext import commands
import logging
import sys
from typing import Any

import fcy_cogs
from fcy_types import *  # pylint: disable = wildcard-import, unused-wildcard-import

logging.basicConfig(level=logging.INFO)
(fcy_logger := logging.getLogger("full_course_yellow")).setLevel(logging.DEBUG)
pycord_logger = logging.getLogger("discord")

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


class FCYBot(discord.Bot):
    """This subclass of Bot defines the Full Course Yellow bot."""

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
        discord_username = actor.name
        if actor.global_name is None or actor.global_name == discord_username:
            return discord_username
        return f"{actor.global_name} ({actor.name})"

    @staticmethod
    def get_option_value(ctx: discord.ApplicationContext, option_name: str) -> Any | None:
        """Given an ApplicationContext in which options were provided, return the value of the option
        whose name is the provided `option_name`. If the option was not provided at all, return None."""

        if option_name in {option.name for option in ctx.unselected_options or []}:
            return None

        if ctx.selected_options is None:
            return None

        for option_dict in ctx.selected_options:
            if option_name in option_dict:
                return option_dict[option_name]

        return None

    async def solidify_actor_abstract(self, actor_abstract: Actor | int | str | None) -> Actor:
        """This takes a "Actor abstract" - a nebulous parameter that might be a fully-fledged Actor,
        or their user ID in integer form, their user ID in string form, or None. The actor abstract is then
        "solidified" into a real Actor, if possible. If not possible, commands.UserNotFound is raised."""

        if actor_abstract is None:
            raise commands.UserNotFound("Attempted to solidify the provided Actor abstract, but it is None!")

        if isinstance(actor_abstract, Actor):
            return actor_abstract

        user_id = int(actor_abstract)
        try:
            actor = await self.fetch_user(user_id)
        except discord.errors.HTTPException as ex:
            raise commands.UserNotFound(
                "Attempted to solidify the provided Actor abstract, "
                "but the user ID provided was out of range of what a valid User ID should be!"
            ) from ex

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
        This function will be called from inside an exception handler, thus the call to sys.exception."""

        if (ex := sys.exception()) is None:
            fcy_logger.error(
                f"on_error was called during the execution of {event} "
                f"at {self.get_current_utc_iso_time_str()}, "
                "but no exception was raised."
            )
            return

        try:  # We need to intentially re-raise the exception so that the logger can pick up the traceback
            raise ex
        except Exception:  # pylint: disable = broad-exception-caught
            fcy_logger.exception( # This only works inside an exception handler
                f"Exception raised during the handling of {event} "
                f"at {self.get_current_utc_iso_time_str()}: "
            )

    async def on_application_command_error(
        self,
        context: discord.ApplicationContext,
        exception: commands.CommandError, # pylint: disable = unused-argument
    ) -> None:
        """This listener implements custom error handling for exceptions raised during the invocation
        of a Command. The primary goal is to clean up the exceptions that are printed out to the log."""

        # In case the context had its response deferred, respond to it ephemerally so that it doesn't spin forever.
        await context.respond(
            content = "Your slash command was received, but an unknown error occurred while working on it.",
            delete_after = 30,
            ephemeral = True,
        )

        try: # We need to intentially re-raise the exception so that the logger can pick up the traceback
            raise exception
        except commands.CommandError:
            fcy_logger.exception( # This only works inside an exception handler
                f"Exception raised during the invocation of {context.command.name} "
                f"by {self.pprint_actor_name(context.author)} ({context.author.id}) "
                f"at {self.get_current_utc_iso_time_str()}"
            )

    async def on_application_command(self, ctx: discord.ApplicationContext) -> None:
        """This listener implements custom logging for whenever a Command is invoked."""
        fcy_logger.info(
            f"{ctx.command.name} invoked by {self.pprint_actor_name(ctx.author)} ({ctx.author.id}) "
            f"in {ctx.guild.name if ctx.guild else 'DMs'} "
            f"at {self.get_current_utc_iso_time_str()}, with options: {ctx.selected_options}"
        )


def read_token(token_filename: str) -> str:
    """Load the bot's token from the file."""
    try:
        with open(token_filename, "r", encoding = "utf-8") as infile:
            return infile.read().strip()
    except FileNotFoundError:
        fcy_logger.exception(f"Could not find the token filename on disk: {TOKEN_FILENAME}")
        sys.exit(1)


def main():
    """Execute top-level functionality - load the token and start the bot."""
    bot = FCYBot(
        intents = INTENTS,
        member_cache_flags = MEMBER_CACHE_FLAGS,
        allowed_mentions = ALLOWED_MENTIONS,
    )
    bot.add_cog(fcy_cogs.FCYFunctionality(bot))
    bot.run(token = read_token(TOKEN_FILENAME))


if __name__ == "__main__":
    main()
