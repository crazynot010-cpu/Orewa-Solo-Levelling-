import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import time
from config import SPAWN_MESSAGE_COUNT, SPAWN_CHANCE, DESPAWN_TIME

class ShadowSpawn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spawn_cleanup.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        async with self.bot.pool.acquire() as conn:
            settings = await conn.fetchrow(
                "SELECT * FROM guild_settings WHERE guild_id=$1",
                message.guild.id
            )

            if not settings or not settings["spawn_channel_id"]:
                return

            counter = settings["message_counter"] + 1

            await conn.execute("""
                UPDATE guild_settings
                SET message_counter=$1
                WHERE guild_id=$2
            """, counter, message.guild.id)

            if counter % SPAWN_MESSAGE_COUNT != 0:
                return

            active = await conn.fetchrow(
                "SELECT * FROM active_spawns WHERE guild_id=$1",
                message.guild.id
            )

            if active:
                return

            if random.random() <= SPAWN_CHANCE:
                shadow = await conn.fetchrow(
                    "SELECT * FROM shadows ORDER BY RANDOM() LIMIT 1"
                )

                if not shadow:
                    return

                await conn.execute("""
                    INSERT INTO active_spawns (guild_id, shadow_id, claimed_by)
                    VALUES ($1, $2, NULL)
                """, message.guild.id, shadow["id"])

                channel = message.guild.get_channel(settings["spawn_channel_id"])
                role = message.guild.get_role(settings["ping_role_id"])

                if channel:
                    ping = role.mention if role else ""
                    await channel.send(f"{ping}\n??? Error")

                    embed = discord.Embed()
                    embed.set_image(url=shadow["image_url"])
                    await channel.send(embed=embed)

    @app_commands.command(name="arise")
    async def arise(self, interaction: discord.Interaction, name: str):
        async with self.bot.pool.acquire() as conn:
            active = await conn.fetchrow(
                "SELECT * FROM active_spawns WHERE guild_id=$1",
                interaction.guild.id
            )

            if not active:
                return await interaction.response.send_message("No active shadow.", ephemeral=True)

            if active["claimed_by"]:
                return await interaction.response.send_message("Already claimed.", ephemeral=True)

            shadow = await conn.fetchrow(
                "SELECT * FROM shadows WHERE id=$1",
                active["shadow_id"]
            )

            if shadow["name"].lower() != name.lower():
                return await interaction.response.send_message("Incorrect.", ephemeral=True)

            # lock spawn
            await conn.execute("""
                UPDATE active_spawns
                SET claimed_by=$1
                WHERE guild_id=$2
            """, interaction.user.id, interaction.guild.id)

            success = random.random() <= 0.55

            if success:
                count_total = await conn.fetchval(
                    "SELECT COUNT(*) FROM hunter_shadows WHERE user_id=$1",
                    interaction.user.id
                )

                count_dup = await conn.fetchval("""
                    SELECT COUNT(*) FROM hunter_shadows
                    WHERE user_id=$1 AND shadow_id=$2
                """, interaction.user.id, shadow["id"])

                if count_total >= 16 or count_dup >= 3:
                    await interaction.response.send_message(
                        "Shadow limit reached.", ephemeral=True
                    )
                else:
                    await conn.execute("""
                        INSERT INTO hunter_shadows (user_id, shadow_id)
                        VALUES ($1, $2)
                    """, interaction.user.id, shadow["id"])

                    await interaction.response.send_message(
                        f"🔥 {interaction.user.mention} successfully extracted {shadow['name']}!"
                    )
            else:
                await interaction.response.send_message(
                    f"❌ Extraction failed. The shadow vanished."
                )

            await conn.execute(
                "DELETE FROM active_spawns WHERE guild_id=$1",
                interaction.guild.id
            )

    @tasks.loop(seconds=60)
    async def spawn_cleanup(self):
        async with self.bot.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM active_spawns
                WHERE NOW() - spawned_at > INTERVAL '5 minutes'
            """)

async def setup(bot):
    await bot.add_cog(ShadowSpawn(bot))
