import discord
from discord import app_commands
from discord.ext import commands
import os

TOKEN = os.getenv('DISCORD_TOKEN')

# --- CONFIGURAZIONE RUOLI AUTORIZZATI ---
AUTHORIZED_ROLE_IDS = [1497868039234781316, 1455297931799298191]

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f'✅ Bot online come {bot.user}')

@bot.tree.command(name="partnership", description="Crea un annuncio di partnership")
@app_commands.describe(
    descrizione="La descrizione del server partner",
    manager="Seleziona il manager partner",
    ping="Inserisci il tag (es. @everyone)"
)
async def partnership(
    interaction: discord.Interaction, 
    descrizione: str, 
    manager: discord.Member, 
    ping: str
):
    # Controllo ruoli
    user_role_ids = [role.id for role in interaction.user.roles]
    authorized = any(role_id in AUTHORIZED_ROLE_IDS for role_id in user_role_ids)

    if not authorized:
        await interaction.response.send_message("❌ Non hai un ruolo autorizzato per usare questo comando.", ephemeral=True)
        return

    # Messaggio finale senza automatismi sul ping
    testo_partnership = (
        f"{ping}\n\n"
        f"🇮🇹 **NUOVA PARTNERSHIP** 🇮🇹\n\n"
        f"{descrizione}\n\n"
        f"**---------------------------------**\n"
        f"👤 **Author:** {interaction.user.mention}\n"
        f"🚀 **Server:** 🇮🇹 **{interaction.guild.name}** 🇮🇹\n"
        f"🥰 **Manager:** {manager.mention}\n"
        f" @ **Ping:** {ping}\n"
        f"**---------------------------------**"
    )

    # Invio nel canale
    await interaction.channel.send(testo_partnership)
    
    # Risposta silenziosa di conferma
    await interaction.response.send_message("✅ Partnership inviata!", ephemeral=True)

if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRORE: Variabile DISCORD_TOKEN non trovata!")
