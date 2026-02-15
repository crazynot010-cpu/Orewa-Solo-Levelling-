import discord
from discord import app_commands
from discord.ext import commands

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start")
    async def start(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with self.bot.pool.acquire() as conn:
            exists = await conn.fetchrow("SELECT * FROM hunters WHERE user_id=$1", user_id)
            if exists:
                return await interaction.response.send_message("You already have a hunter.", ephemeral=True)

            await conn.execute(
                "INSERT INTO hunters (user_id) VALUES ($1)",
                user_id
            )

        await interaction.response.send_message("Hunter created. You are now E Rank Level 0.")

    @app_commands.command(name="profile")
    async def profile(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with self.bot.pool.acquire() as conn:
            hunter = await conn.fetchrow("SELECT * FROM hunters WHERE user_id=$1", user_id)

        if not hunter:
            return await interaction.response.send_message("Use /start first.", ephemeral=True)

        xp_needed = 100 + (hunter["level"] * 50)

        embed = discord.Embed(title=f"{interaction.user.name}'s Hunter Profile")
        embed.add_field(name="Rank", value=hunter["rank"])
        embed.add_field(name="Level", value=hunter["level"])
        embed.add_field(name="XP", value=f"{hunter['xp']} / {xp_needed}", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))
