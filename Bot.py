import discord
from discord import app_commands
from discord.ext import commands
import os

# Legge il token dal Secret Environment di Render
TOKEN = os.getenv('DISCORD_TOKEN')

# Inserisci qui i due ID autorizzati
AUTHORIZED_IDS = [1497868039234781316, 1455297931799298191] 

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Bot online come {bot.user}')

@bot.tree.command(name="partnership", description="Crea un annuncio di partnership")
@app_commands.describe(
    descrizione="La descrizione del server partner",
    manager="Seleziona il manager partner",
    ping="Inserisci il ping (es. everyone o here)"
)
async def partnership(
    interaction: discord.Interaction, 
    descrizione: str, 
    manager: discord.Member, 
    ping: str
):
    # Controllo se l'utente è tra i due autorizzati
    if interaction.user.id not in AUTHORIZED_IDS:
        await interaction.response.send_message("❌ Non hai il permesso di usare questo bot.", ephemeral=True)
        return

    # Formattazione automatica del ping
    final_ping = ping if ping.startswith('@') else f"@{ping}"
    
    emoji_ds = "🇮🇹" 
    
    # Costruzione del messaggio stile immagine (senza limoni)
    testo_partnership = (
        f"{final_ping}\n\n"
        f"{emoji_ds} **NUOVA PARTNERSHIP** {emoji_ds}\n\n"
        f"{descrizione}\n\n"
        f"**---------------------------------**\n"
        f"👤 **Author:** {interaction.user.mention}\n"
        f"🚀 **Server:** 🇮🇹 **{interaction.guild.name}** 🇮🇹\n"
        f"🥰 **Manager:** {manager.mention}\n"
        f" @ **Ping:** {final_ping}\n"
        f"**---------------------------------**"
    )

    # Invia il messaggio nel canale
    await interaction.channel.send(testo_partnership)
    
    # Risposta di conferma (solo tu la vedi)
    await interaction.response.send_message("✅ Messaggio inviato!", ephemeral=True)

bot.run(TOKEN)
