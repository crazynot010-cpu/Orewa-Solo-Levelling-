import discord
from discord.ext import commands
import asyncio
import asyncpg
import os

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=ints)

async def create_pool():
    bot.pool = await asyncpg.create_pool(DATABASE_URL)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

async def load_cogs():
    await bot.load_extension("cogs.profile")
    await bot.load_extension("cogs.xp_system")
    await bot.load_extension("cogs.shadow_spawn")
    await bot.load_extension("cogs.admin")

async def main():
    async with bot:
        await create_pool()
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())
