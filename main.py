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
tree = bot.tree

message_count = 0
active_shadow = None

RANK_ROLES = ["E", "D", "C", "B", "A", "S", "SS"]


# ================= RANK SYSTEM =================

def get_rank(level):
    if level >= 75:
        return "SS"
    elif level >= 50:
        return "S"
    elif level >= 35:
        return "A"
    elif level >= 20:
        return "B"
    elif level >= 10:
        return "C"
    elif level >= 5:
        return "D"
    return "E"


def xp_for_next_level(level):
    return 100 + (level * 50)


async def update_rank_role(member, level):
    rank = get_rank(level)

    # Remove old rank roles
    for role_name in RANK_ROLES:
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role and role in member.roles:
            await member.remove_roles(role)

    # Add new rank role
    new_role = discord.utils.get(member.guild.roles, name=rank)
    if new_role:
        await member.add_roles(new_role)


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
        image TEXT,
        rarity TEXT
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

    await bot.db.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        guild_id INTEGER PRIMARY KEY,
        spawn_channel INTEGER
    )
    """)

    await bot.db.commit()


# ================= XP SYSTEM =================

async def add_xp(member):
    cursor = await bot.db.execute(
        "SELECT xp, level FROM users WHERE user_id = ?",
        (member.id,)
    )
    data = await cursor.fetchone()

    if not data:
        await bot.db.execute(
            "INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)",
            (member.id, CHAT_XP, 0)
        )
        await bot.db.commit()
        return

    xp, level = data
    xp += CHAT_XP

    leveled_up = False

    if xp >= xp_for_next_level(level):
        xp = 0
        level += 1
        leveled_up = True

    await bot.db.execute(
        "UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
        (xp, level, member.id)
    )
    await bot.db.commit()

    if leveled_up:
        await update_rank_role(member, level)


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

    embed = discord.Embed(
        title="A Shadow Has Appeared...",
        color=discord.Color.dark_red()
    )
    embed.set_image(url=image)

    msg = await channel.send(embed=embed)

    await asyncio.sleep(DESPAWN_TIME)

    if active_shadow and not active_shadow["claimed"]:
        active_shadow = None
        await msg.edit(content="The shadow vanished...", embed=None)


# ================= EVENTS =================

@bot.event
async def on_ready():
    await setup_database()
    await tree.sync()
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    global message_count

    if message.author.bot:
        return

    await add_xp(message.author)

    message_count += 1

    if message_count >= SPAWN_MESSAGE_COUNT:
        message_count = 0

        if random.random() <= SPAWN_CHANCE and not active_shadow:

            cursor = await bot.db.execute(
                "SELECT spawn_channel FROM settings WHERE guild_id = ?",
                (message.guild.id,)
            )
            data = await cursor.fetchone()

            channel = bot.get_channel(data[0]) if data else message.channel

            if channel:
                await spawn_shadow(channel)

    await bot.process_commands(message)


# ================= SLASH COMMANDS =================

@tree.command(name="profile", description="View your hunter profile")
async def profile(interaction: discord.Interaction):

    cursor = await bot.db.execute(
        "SELECT xp, level FROM users WHERE user_id = ?",
        (interaction.user.id,)
    )
    data = await cursor.fetchone()

    xp, level = data if data else (0, 0)
    rank = get_rank(level)

    cursor = await bot.db.execute(
        "SELECT SUM(count) FROM inventory WHERE user_id = ?",
        (interaction.user.id,)
    )
    total = (await cursor.fetchone())[0] or 0

    embed = discord.Embed(
        title=f"{interaction.user.name}'s Hunter Card",
        color=discord.Color.dark_purple()
    )

    embed.add_field(name="Level", value=level)
    embed.add_field(name="Rank", value=rank)
    embed.add_field(name="XP", value=xp)
    embed.add_field(name="Total Shadows", value=total)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@tree.command(name="inventory", description="View your shadow inventory")
async def inventory(interaction: discord.Interaction):

    cursor = await bot.db.execute(
        "SELECT shadow_name, count FROM inventory WHERE user_id = ?",
        (interaction.user.id,)
    )
    rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message("You have no shadows.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"{interaction.user.name}'s Shadows",
        color=discord.Color.dark_blue()
    )

    for name, count in rows:
        embed.add_field(name=name, value=f"x{count}", inline=True)

    await interaction.response.send_message(embed=embed)


@tree.command(name="leaderboard", description="Top hunters by level")
async def leaderboard(interaction: discord.Interaction):

    cursor = await bot.db.execute(
        "SELECT user_id, level FROM users ORDER BY level DESC LIMIT 10"
    )
    rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message("No data yet.")
        return

    embed = discord.Embed(title="Top Hunters", color=discord.Color.gold())

    for i, (user_id, level) in enumerate(rows, start=1):
        user = bot.get_user(user_id)
        name = user.name if user else f"User {user_id}"
        embed.add_field(name=f"#{i} {name}", value=f"Level {level}", inline=False)

    await interaction.response.send_message(embed=embed)


@tree.command(name="shadows", description="List all available shadows")
async def shadows(interaction: discord.Interaction):

    cursor = await bot.db.execute("SELECT name, rarity FROM shadows")
    rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message("No shadows added yet.")
        return

    embed = discord.Embed(title="Available Shadows", color=discord.Color.dark_purple())

    for name, rarity in rows:
        embed.add_field(name=name, value=f"Rarity: {rarity}", inline=True)

    await interaction.response.send_message(embed=embed)


@tree.command(name="addshadow", description="Add a shadow (Admin only)")
async def addshadow(interaction: discord.Interaction, name: str, image: str, rarity: str):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return

    await bot.db.execute(
        "INSERT INTO shadows (name, image, rarity) VALUES (?, ?, ?)",
        (name, image, rarity)
    )
    await bot.db.commit()

    await interaction.response.send_message("Shadow added.")


@tree.command(name="spawn", description="Force spawn shadow (Admin only)")
async def spawn(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return

    if active_shadow:
        await interaction.response.send_message("Shadow already active.")
        return

    await interaction.response.send_message("Spawning shadow...")
    await spawn_shadow(interaction.channel)


@tree.command(name="setspawnchannel", description="Set spawn channel (Admin only)")
async def setspawnchannel(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only.", ephemeral=True)
        return

    await bot.db.execute(
        "INSERT OR REPLACE INTO settings (guild_id, spawn_channel) VALUES (?, ?)",
        (interaction.guild.id, interaction.channel.id)
    )
    await bot.db.commit()

    await interaction.response.send_message("Spawn channel set.")


@tree.command(name="arise", description="Attempt to extract the active shadow")
async def arise(interaction: discord.Interaction, name: str):
    global active_shadow

    if not active_shadow:
        await interaction.response.send_message("No shadow active.", ephemeral=True)
        return

    if active_shadow["claimed"]:
        await interaction.response.send_message("Already claimed.", ephemeral=True)
        return

    if name.lower() != active_shadow["name"].lower():
        await interaction.response.send_message("Wrong name.", ephemeral=True)
        return

    active_shadow["claimed"] = True

    if random.random() <= ARISE_SUCCESS_RATE:

        cursor = await bot.db.execute(
            "SELECT SUM(count) FROM inventory WHERE user_id = ?",
            (interaction.user.id,)
        )
        total = (await cursor.fetchone())[0] or 0

        if total >= MAX_TOTAL_SHADOWS:
            await interaction.response.send_message("Inventory full (16 max).")
            active_shadow = None
            return

        cursor = await bot.db.execute(
            "SELECT count FROM inventory WHERE user_id = ? AND shadow_name = ?",
            (interaction.user.id, active_shadow["name"])
        )
        data = await cursor.fetchone()

        if data and data[0] >= MAX_DUPLICATE_SHADOW:
            await interaction.response.send_message("Max duplicate reached (3).")
            active_shadow = None
            return

        if data:
            await bot.db.execute(
                "UPDATE inventory SET count = count + 1 WHERE user_id = ? AND shadow_name = ?",
                (interaction.user.id, active_shadow["name"])
            )
        else:
            await bot.db.execute(
                "INSERT INTO inventory (user_id, shadow_name, count) VALUES (?, ?, 1)",
                (interaction.user.id, active_shadow["name"])
            )

        await bot.db.commit()

        await interaction.response.send_message(
            f"{interaction.user.mention} successfully extracted **{active_shadow['name']}**!"
        )

    else:
        await interaction.response.send_message(
            f"{interaction.user.mention} extraction failed!"
        )

    active_shadow = None


bot.run(TOKEN)
