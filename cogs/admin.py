import discord
from discord.ext import commands
from discord import app_commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setspawnchannel")
    async def setspawnchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.pool.execute("""
            INSERT INTO guild_settings (guild_id, spawn_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET spawn_channel_id=$2
        """, interaction.guild.id, channel.id)

        await interaction.response.send_message("Spawn channel set.")

    @app_commands.command(name="setrole")
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.pool.execute("""
            INSERT INTO guild_settings (guild_id, ping_role_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET ping_role_id=$2
        """, interaction.guild.id, role.id)

        await interaction.response.send_message("Ping role set.")

    @app_commands.command(name="addshadow")
    async def addshadow(self, interaction: discord.Interaction,
                        name: str,
                        droprate: int,
                        catchrate: int,
                        health: int,
                        damage: int,
                        rarity: str,
                        imageurl: str):

        await self.bot.pool.execute("""
            INSERT INTO shadows (name, drop_rate, catch_rate, health, damage, rarity, image_url)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        """, name, droprate, catchrate, health, damage, rarity, imageurl)

        await interaction.response.send_message(f"{name} added.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
