import os
import discord
from discord.ext import commands
from flask import Flask

# --- Configurazione Flask ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Il bot di Madison Unban è online!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Configurazione Discord Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# ID delle categorie o dei ruoli (Modifica con i tuoi dati)
SUPPORT_ROLE_ID = 1352284377698144336  # ID del ruolo Staff
CATEGORY_TICKET_ID = 1352281057273188354 # ID della categoria dove creare i ticket


# --- Modal per la richiesta di unban ---
class UnbanModal(discord.ui.Modal, title="Richiesta di Unban - Modulo"):
    when_banned = discord.ui.TextInput(
        label="Quando sei stato bannato?",
        placeholder="Es. Circa 2 mesi fa / 15 Gennaio...",
        style=discord.TextStyle.short,
        required=True
    )
    
    ban_reason = discord.ui.TextInput(
        label="Qual è il motivo del ban?",
        placeholder="Spiega la motivazione per cui hai ricevuto la sanzione...",
        style=discord.TextStyle.long,
        required=True
    )
    
    why_deserve = discord.ui.TextInput(
        label="Perché meriti una seconda possibilità?",
        placeholder="Argomenta perché dovremmo rivalutare il tuo ban...",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        
        # Controlla se l'utente ha già un ticket aperto
        existing_channel = discord.utils.get(guild.text_channels, name=f"unban-{interaction.user.name.lower()}")
        if existing_channel:
            await interaction.followup.send(f"❌ Hai già un ticket aperto: {existing_channel.mention}", ephemeral=True)
            return

        # Crea i permessi per il canale privato
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        
        if SUPPORT_ROLE_ID:
            support_role = guild.get_role(SUPPORT_ROLE_ID)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Crea il canale del ticket
        channel_name = f"unban-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        # Messaggio di benvenuto nel ticket
        embed = discord.Embed(
            title="🔓 Richiesta di Unban - Madison",
            description=(
                f"👋 Benvenuto {interaction.user.mention} nel tuo ticket di Unban!\n\n"
                f"📝 **Spiega la tua situazione:**\n"
                f"• **Quando sei stato bannato?:** {self.when_banned.value}\n"
                f"• **Qual è il motivo del ban?:** {self.ban_reason.value}\n"
                f"• **Perché meriti una seconda possibilità?:** {self.why_deserve.value}\n\n"
                f"⏳ Lo staff risponderà il prima possibile.\n"
                f"📌 Mantieni sempre un comportamento rispettoso."
            ),
            color=discord.Color.blue()
        )
        
        close_view = TicketCloseView()
        
        support_ping = f"<@&{SUPPORT_ROLE_ID}>" if SUPPORT_ROLE_ID else ""
        await ticket_channel.send(content=f"{interaction.user.mention} {support_ping}", embed=embed, view=close_view)
        
        await interaction.followup.send(f"✅ Il tuo ticket è stato creato con successo: {ticket_channel.mention}", ephemeral=True)


class UnbanSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Richiesta Unban",
                description="Apri un ticket per richiedere la revoca del ban",
                emoji="🔓",
                value="open_unban_ticket"
            )
        ]
        # Assegniamo un custom_id fisso fondamentale per la persistenza
        super().__init__(placeholder="Seleziona dal menù per aprire una richiesta...", min_values=1, max_values=1, options=options, custom_id="unban_persistent_select")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "open_unban_ticket":
            await interaction.response.send_modal(UnbanModal())

class UnbanDropView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout None rende la view persistente
        self.add_item(UnbanSelect())

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Chiudi Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Chiusura del ticket in corso...", ephemeral=True)
        await interaction.channel.delete()


# --- Sottoclasse del Bot per gestire correttamente la persistenza tramite setup_hook ---
class PersistentBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Registriamo le viste in modo persistente prima che il bot sia pronto
        self.add_view(UnbanDropView())
        self.add_view(TicketCloseView())
        print("✅ Viste persistenti caricate correttamente.")

    async def on_ready(self):
        print(f'Bot loggato come {self.user} (ID: {self.user.id})')

bot = PersistentBot()


@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="Madison Unban",
        description=(
            "👋 **Benvenuto nel pannello dedicato alle richieste di Unban, ricorda:** ⚠️\n\n"
            "• **Niente ticket troll.**\n"
            "• **Solo richieste di Unban.**\n"
            "• **Non aprire più ticket per la stessa sanzione.**\n"
            "• **Mantieni sempre rispetto verso lo Staff.**\n"
            "• **Fornisci informazioni veritiere.**\n\n"
            "📌 **Una seconda possibilità non viene regalata, si conquista.**\n"
            "📌 **Ogni errore può diventare un'opportunità per migliorare.**\n\n"
            "🔓 **Se ritieni che il ban debba essere rivalutato, spiega la situazione con sincerità e attenzione.**\n"
            "📩 **Seleziona dal menù qui sotto per aprire una richiesta.**\n\n"
            "ServerUnban: *Dimostra chi sei oggi, non chi eri ieri.*"
        ),
        color=discord.Color.from_rgb(43, 45, 49)
    )
    
    # Inserisci qui il tuo link Imgur
    embed.set_image(url="https://imgur.com/a/G6c7Lwg")
    
    view = UnbanDropView()
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()


if __name__ == "__main__":
    import threading
    t = threading.Thread(target=run_flask)
    t.start()
    
    TOKEN = os.getenv("DISCORD_TOKEN") or "IL_TUO_TOKEN_BOT"
    bot.run(TOKEN)
