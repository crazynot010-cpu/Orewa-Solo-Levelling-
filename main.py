import discord
from discord.ext import commands
import random
import asyncio
import aiosqlite
from config import *

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

message_count = 0
active_shadow = None


# ================= DATABASE =================

async def setup_database():
    bot.db = await aiosqlite.connect("database.db")

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0
    )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS shadows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        image TEXT
    )
    """)

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        shadow_name TEXT,
        count INTEGER,
        PRIMARY KEY(user_id, shadow_name)
    )
    """)

    await bot.db.commit()


# ================= LEVEL SYSTEM =================

def xp_for_next_level(level):
    return 100 + (level * 50)


async def add_xp(user_id):
    cursor = await bot.db.execute(
        "SELECT xp, level FROM users WHERE user_id = ?",
        (user_id,)
    )
    data = await cursor.fetchone()

    if not data:
        await bot.db.execute(
            "INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)",
            (user_id, CHAT_XP, 0)
        )
        await bot.db.commit()
        return

    xp, level = data
    xp += CHAT_XP

    if xp >= xp_for_next_level(level):
        xp = 0
        level += 1

    await bot.db.execute(
        "UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
        (xp, level, user_id)
    )
    await bot.db.commit()


# ================= SHADOW SPAWN =================

async def spawn_shadow(channel):
    global active_shadow

    cursor = await bot.db.execute(
        "SELECT name, image FROM shadows ORDER BY RANDOM() LIMIT 1"
    )
    shadow = await cursor.fetchone()

    if not shadow:
        return

    name, image = shadow

    active_shadow = {
        "name": name,
        "claimed": False
    }

    embed = discord.Embed(title="??? Error")
    embed.set_image(url=image)

    msg = await channel.send(embed=embed)

    await asyncio.sleep(DESPAWN_TIME)

    if not active_shadow["claimed"]:
        active_shadow = None
        await msg.edit(content="Shadow disappeared...", embed=None)


# ================= EVENTS =================

@bot.event
async def on_ready():
    await setup_database()
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    global message_count

    if message.author.bot:
        return

    await add_xp(message.author.id)

    message_count += 1

    if message_count >= SPAWN_MESSAGE_COUNT:
        message_count = 0
        if random.random() <= SPAWN_CHANCE and not active_shadow:
            await spawn_shadow(message.channel)

    await bot.process_commands(message)


# ================= ARISE =================

@bot.command()
async def arise(ctx, *, guess):
    global active_shadow

    if not active_shadow:
        return

    if active_shadow["claimed"]:
        return

    if guess.lower() != active_shadow["name"].lower():
        return

    active_shadow["claimed"] = True

    if random.random() <= ARISE_SUCCESS_RATE:

        cursor = await bot.db.execute(
            "SELECT COUNT(*) FROM inventory WHERE user_id = ?",
            (ctx.author.id,)
        )
        total = (await cursor.fetchone())[0]

        if total >= MAX_TOTAL_SHADOWS:
            await ctx.send("Inventory full (16 max).")
            return

        cursor = await bot.db.execute(
            "SELECT count FROM inventory WHERE user_id = ? AND shadow_name = ?",
            (ctx.author.id, active_shadow["name"])
        )
        data = await cursor.fetchone()

        if data and data[0] >= MAX_DUPLICATE_SHADOW:
            await ctx.send("Max duplicate reached (3).")
            return

        if data:
            await bot.db.execute(
                "UPDATE inventory SET count = count + 1 WHERE user_id = ? AND shadow_name = ?",
                (ctx.author.id, active_shadow["name"])
            )
        else:
            await bot.db.execute(
                "INSERT INTO inventory (user_id, shadow_name, count) VALUES (?, ?, 1)",
                (ctx.author.id, active_shadow["name"])
            )

        await bot.db.commit()

        await ctx.send(f"{ctx.author.mention} successfully extracted **{active_shadow['name']}**!")

    else:
        await ctx.send(f"{ctx.author.mention} extraction failed!")

    active_shadow = None


# ================= ADD SHADOW =================

@bot.command()
@commands.has_permissions(administrator=True)
async def addshadow(ctx, name, image):
    await bot.db.execute(
        "INSERT INTO shadows (name, image) VALUES (?, ?)",
        (name, image)
    )
    await bot.db.commit()
    await ctx.send("Shadow added.")


bot.run(TOKEN)
