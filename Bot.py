import os
import io
import discord
from discord.ext import commands
from flask import Flask

# --- Configurazione Flask (per tenere il bot attivo su hosting tipo Replit/Render) ---
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
intents.members = True # Necessario per rilevare gli ingressi e le uscite dei membri

# ID delle categorie, ruoli e canali inseriti
SUPPORT_ROLE_ID = 1352284377698144336        # ID del ruolo Staff
CATEGORY_TICKET_ID = 1352281057273188354     # ID della categoria dove creare i ticket
TICKET_LOG_CHANNEL_ID = 1494425912727572611  # ID del canale in cui inviare i log e i transcript
WELCOME_CHANNEL_ID = 1352287128532418632     # ID del canale Benvenuto
GOODBYE_CHANNEL_ID = 1494373723199901887     # ID del canale Arrivederci (Leave)


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
        
        # Invia il log di apertura nel canale log dedicato
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="📂 Ticket Aperto",
                description=(
                    f"• **Utente:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"• **Canale:** {ticket_channel.mention}\n"
                    f"• **Quando bannato:** {self.when_banned.value}\n"
                    f"• **Motivo ban:** {self.ban_reason.value}\n"
                    f"• **Perché merita unban:** {self.why_deserve.value}"
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await log_channel.send(embed=log_embed)

        await interaction.followup.send(f"✅ Il tuo ticket è stato creato con successo: {ticket_channel.mention}", ephemeral=True)


class UnbanSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Richiesta Unban",
                description="Apri un ticket per richiedere la revoca del ban",
                emoji="<:MadisonStateUnban:1494380677389488237>",
                value="open_unban_ticket"
            )
        ]
        super().__init__(placeholder="Seleziona dal menù per aprire una richiesta...", min_values=1, max_values=1, options=options, custom_id="unban_persistent_select")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "open_unban_ticket":
            await interaction.response.send_modal(UnbanModal())

class UnbanDropView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(UnbanSelect())

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Chiudi Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Chiusura del ticket in corso e generazione del transcript...", ephemeral=True)
        
        guild = interaction.guild
        channel = interaction.channel
        closed_by = interaction.user

        # Genera il transcript della chat
        messages = [message async for message in channel.history(limit=None, oldest_first=True)]
        transcript_content = f"--- TRANSCRIPT DEL TICKET: {channel.name} ---\nChiuso da: {closed_by} ({closed_by.id})\n\n"
        
        for msg in messages:
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            transcript_content += f"[{timestamp}] {msg.author}: {msg.content}\n"
            if msg.embeds:
                for embed in msg.embeds:
                    transcript_content += f"  [EMBED] Titolo: {embed.title} | Descrizione: {embed.description}\n"

        # Converte la stringa in un file binario leggibile da Discord
        file_bytes = io.BytesIO(transcript_content.encode('utf-8'))
        transcript_file = discord.File(file_bytes, filename=f"transcript-{channel.name}.txt")

        # Invia il log e il transcript nel canale log
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            close_embed = discord.Embed(
                title="🔒 Ticket Chiuso",
                description=f"• **Canale:** #{channel.name}\n• **Chiuso da:** {closed_by.mention} (`{closed_by.id}`)",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            await log_channel.send(embed=close_embed, file=transcript_file)

        # Elimina il canale del ticket
        await channel.delete()


# --- Configurazione del Bot con Viste Persistenti ---
class PersistentBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(UnbanDropView())
        self.add_view(TicketCloseView())
        print("✅ Viste persistenti caricate correttamente.")

    async def on_ready(self):
        print(f'Bot loggato come {self.user} (ID: {self.user.id})')
        try:
            synced = await self.tree.sync()
            print(f"Sincronizzati {len(synced)} comandi slash.")
        except Exception as e:
            print(f"Errore nella sincronizzazione dei comandi: {e}")

bot = PersistentBot()


# --- Eventi di Benvenuto e Arrivederci (Con Debug Completo) ---
@bot.event
async def on_member_join(member):
    print(f"\n[DEBUG JOIN] ----------------------------------------")
    print(f"[DEBUG JOIN] Rilevato ingresso utente: {member.name} (ID: {member.id})")
    print(f"[DEBUG JOIN] L'utente è un bot? -> {member.bot}")
    
    if member.bot:
        print("[DEBUG JOIN] Ignorato perché è un bot.")
        return
        
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    print(f"[DEBUG JOIN] ID Canale Benvenuto configurato: {WELCOME_CHANNEL_ID}")
    print(f"[DEBUG JOIN] Canale trovato nel server? -> {channel}")

    if channel:
        try:
            file_path = "file_00000000125c720a85fa9d73a34549c7.png"
            file_esiste = os.path.exists(file_path)
            print(f"[DEBUG JOIN] Il file '{file_path}' esiste nella cartella? -> {file_esiste}")

            if file_esiste:
                file = discord.File(file_path, filename="file_00000000125c720a85fa9d73a34549c7.png")
            else:
                print(f"[DEBUG JOIN] ERRORE: Il file immagine '{file_path}' NON è stato trovato nella repository!")
                file = None

            embed = discord.Embed(
                title="🎉 • ʙᴇɴᴠᴇɴᴜᴛᴏ",
                description=(
                    f"👋 Benvenuto {member.mention} nella zona Unban di Madison State Full RP!\n"
                    f"➢ 📍 Qui potrai richiedere assistenza riguardo ban, blacklist e controlli staff.\n"
                    f"➢ 📍 Leggi attentamente la guida sban nel canale <#1352295921999937686>.\n"
                    f"➢ 📍 Compila correttamente tutti i moduli richiesti.\n"
                    f"➢ 📍 Mantieni sempre un comportamento rispettoso verso lo staff.\n\n"
                    f"📌 Una richiesta ben compilata velocizzerà la revisione del tuo caso.\n"
                    f"💬 Per qualsiasi dubbio apri un ticket assistenza."
                ),
                color=discord.Color.green()
            )
            
            if file:
                embed.set_image(url="attachment://file_00000000125c720a85fa9d73a34549c7.png")
                await channel.send(file=file, embed=embed)
            else:
                await channel.send(embed=embed)
                
            print("[DEBUG JOIN] SUCCESS: Messaggio di benvenuto inviato con successo!")
        except Exception as e:
            print(f"[DEBUG JOIN] ERRORE CRITICO durante l'invio del benvenuto: {e}")
    else:
        print("[DEBUG JOIN] ERRORE: Impossibile inviare il messaggio, canale non valido o non trovato.")
    print(f"[DEBUG JOIN] ----------------------------------------\n")


@bot.event
async def on_member_remove(member):
    print(f"\n[DEBUG REMOVE] ----------------------------------------")
    print(f"[DEBUG REMOVE] Rilevata uscita utente: {member.name} (ID: {member.id})")
    print(f"[DEBUG REMOVE] L'utente era un bot? -> {member.bot}")
    
    if member.bot:
        print("[DEBUG REMOVE] Ignorato perché è un bot.")
        return
        
    channel = member.guild.get_channel(GOODBYE_CHANNEL_ID)
    print(f"[DEBUG REMOVE] ID Canale Arrivederci configurato: {GOODBYE_CHANNEL_ID}")
    print(f"[DEBUG REMOVE] Canale trovato nel server? -> {channel}")

    if channel:
        try:
            file_path = "partenza.jpeg"
            file_esiste = os.path.exists(file_path)
            print(f"[DEBUG REMOVE] Il file '{file_path}' esiste nella cartella? -> {file_esiste}")

            if file_esiste:
                file = discord.File(file_path, filename="partenza.jpeg")
            else:
                print(f"[DEBUG REMOVE] ERRORE: Il file immagine '{file_path}' NON è stato trovato nella repository!")
                file = None

            embed = discord.Embed(
                title="✈️ • ᴘᴀʀᴛᴇɴᴢᴀ",
                description=(
                    f"👋 Il volo di {member.mention} è ufficialmente partito da Madison State Full RP!\n"
                    f"➢ 📍 Grazie per aver giocato con noi.\n"
                    f"➢ 📍 Speriamo di rivederti presto nella città di Madison.\n"
                    f"➢ 📍 Ogni storia lascia il segno… la tua continuerà altrove.\n\n"
                    f"📌 Ti auguriamo buona fortuna per il tuo prossimo percorso RP!\n"
                    f"💬 Arrivederci da tutta la community di Madison State FRP."
                ),
                color=discord.Color.red()
            )
            
            if file:
                embed.set_image(url="attachment://partenza.jpeg")
                await channel.send(file=file, embed=embed)
            else:
                await channel.send(embed=embed)
                
            print("[DEBUG REMOVE] SUCCESS: Messaggio di arrivederci inviato con successo!")
        except Exception as e:
            print(f"[DEBUG REMOVE] ERRORE CRITICO durante l'invio dell'addio: {e}")
    else:
        print("[DEBUG REMOVE] ERRORE: Impossibile inviare il messaggio, canale non valido o non trovato.")
    print(f"[DEBUG REMOVE] ----------------------------------------\n")

# --- Comando per inviare il pannello dei ticket ---
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    file = discord.File("pannello.png", filename="pannello.png")
    
    embed = discord.Embed(
        title="<:MadisonStateUnban:1494380677389488237> • MADISON PANELLO SBAN",
        description=(
            "👋 **Benvenuto nel pannello dedicato alle richieste di Unban, ricorda:** ⚠️\n"
            "• **Niente ticket troll.**\n"
            "• **Solo richieste di Unban.**\n"
            "• **Non aprire più ticket per la stessa sanzione.**\n"
            "• **Mantieni sempre rispetto verso lo Staff.**\n"
            "• **Fornisci informazioni veritiere.**\n\n"
            "📌 *Una seconda possibilità non viene regalata, si conquista.*\n"
            "📌 *Ogni errore può diventare un'opportunità per migliorare.*\n"
            "🔓 *Se ritieni che il ban debba essere rivalutato, spiega la situazione con sincerità e attenzione.*\n"
            "📩 *Seleziona dal menù qui sotto per aprire una richiesta.*\n\n"
            "🔎 *Dimostra chi sei oggi, non chi eri ieri.*"
        ),
        color=discord.Color.from_rgb(43, 45, 49)
    )
    
    embed.set_image(url="attachment://pannello.png")
    
    view = UnbanDropView()
    await ctx.send(file=file, embed=embed, view=view)
    await ctx.message.delete()

if __name__ == "__main__":
    import threading
    t = threading.Thread(target=run_flask)
    t.start()
    
    TOKEN = os.getenv("DISCORD_TOKEN") or "IL_TUO_TOKEN_BOT"
    bot.run(TOKEN)
