"""This file implements type hints used throughout the Full Course Yellow bot."""

import discord  # This uses pycord, not discord.py

Snowflake = int
ChannelID = Snowflake
GuildID = Snowflake
RoleID = Snowflake
ActorID = Snowflake
Actor = discord.User | discord.Member
