import discord
from discord.ext import commands
import time
from config import CHAT_XP

RANK_LEVELS = {
    0: "E",
    10: "D",
    20: "C",
    35: "B",
    50: "A",
    70: "S",
    100: "National"
}

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    def get_rank(self, level):
        rank = "E"
        for lvl, r in sorted(RANK_LEVELS.items()):
            if level >= lvl:
                rank = r
        return rank

    async def update_rank_role(self, member, new_rank):
        guild = member.guild
        role_name = f"{new_rank} Rank Hunter"

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name)

        # remove old rank roles
        for r in guild.roles:
            if "Rank Hunter" in r.name and r in member.roles:
                await member.remove_roles(r)

        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if len(message.content) < 5:
            return

        now = time.time()
        last = self.cooldowns.get(message.author.id, 0)

        if now - last < 20:
            return

        self.cooldowns[message.author.id] = now

        async with self.bot.pool.acquire() as conn:
            hunter = await conn.fetchrow(
                "SELECT * FROM hunters WHERE user_id=$1",
                message.author.id
            )

            if not hunter:
                return

            new_xp = hunter["xp"] + CHAT_XP
            level = hunter["level"]

            xp_needed = 100 + (level * 50)

            if new_xp >= xp_needed:
                level += 1
                new_xp -= xp_needed

                new_rank = self.get_rank(level)

                await conn.execute("""
                    UPDATE hunters
                    SET level=$1, xp=$2, rank=$3
                    WHERE user_id=$4
                """, level, new_xp, new_rank, message.author.id)

                await self.update_rank_role(message.author, new_rank)

                await message.channel.send(
                    f"⚡ {message.author.mention} leveled up to {level}! Rank: {new_rank}"
                )
            else:
                await conn.execute(
                    "UPDATE hunters SET xp=$1 WHERE user_id=$2",
                    new_xp, message.author.id
                )

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
