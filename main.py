import os
import io
import json
import asyncio
import aiohttp
import discord
from discord.ext import commands
from flask import Flask

# --- Configurazione Flask (per tenere il bot attivo su Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Il bot di Backup Cloud Totale è online!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Configurazione Discord Bot ---
intents = discord.Intents.all()

# --- ID DEI SERVER E DEI CANALI ---
SOURCE_SERVER_ID = 1446478097494048783        # ID del server PRINCIPALE da cui fare il backup
BACKUP_SERVER_ID = 1531305565496672266        # ID del server SECONDARIO (di sicurezza/destinazione)
CLOUD_JSON_CHANNEL_ID = 1531308877943935178   # ID del canale privato nel server di backup dove salvare il JSON Cloud

# --- I 2 UTENTI AMMINISTRATORI SEPARATI ---
ADMIN_1_ID = 1487792322392363008  # ID del primo amministratore
ADMIN_2_ID = 1191824316376043580  # ID del secondo amministratore

# --- PASSWORD SEGRETA LETTA DA VARIABILE D'AMBIENTE (ENV) ---
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")


# --- Funzione di supporto per allegati permanenti ---
async def permanent_upload_attachment(bot, attachment_url, filename):
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        return attachment_url
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment_url) as resp:
                if resp.status == 200:
                    file_bytes = await resp.read()
                    discord_file = discord.File(io.BytesIO(file_bytes), filename=filename)
                    sent_msg = await channel.send(f"📎 **Allegato permanente archiviato ({filename}):**", file=discord_file)
                    if sent_msg.attachments:
                        return sent_msg.attachments[0].url
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO ALLEGATO PERMANENTE]: {e}")
    
    return attachment_url


# --- Gestione del Database Cloud su Discord ---
async def get_cloud_json_message(bot):
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        return None, None
    
    async for message in channel.history(limit=10):
        if message.author == bot.user and message.attachments:
            for att in message.attachments:
                if att.filename == "backup_database_cloud.json":
                    file_bytes = await att.read()
                    try:
                        data = json.loads(file_bytes.decode("utf-8"))
                        return data, message
                    except Exception:
                        pass
    return None, None


async def load_backup_data(bot):
    data, _ = await get_cloud_json_message(bot)
    if data:
        return data
    return {
        "messages": {},
        "channels": {},
        "roles": {},
        "threads": {}
    }


async def save_backup_data(bot, data):
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        print("[ERRORE CLOUD]: Canale JSON Cloud non trovato!")
        return

    json_str = json.dumps(data, indent=4, ensure_ascii=False)
    file_bytes = io.BytesIO(json_str.encode("utf-8"))
    discord_file = discord.File(file_bytes, filename="backup_database_cloud.json")

    _, old_message = await get_cloud_json_message(bot)
    
    try:
        if old_message:
            await old_message.delete()
        await channel.send("🔄 **Database JSON Cloud aggiornato:**", file=discord_file)
    except Exception as e:
        print(f"[ERRORE SINCRONIZZAZIONE CLOUD]: {e}")


# --- Modulo Password per il Ripristino Sicuro ---
class PasswordModal(discord.ui.Modal, title="Verifica di Sicurezza - Password"):
    password_input = discord.ui.TextInput(
        label="Inserisci la Password di Sicurezza",
        placeholder="Digita la password per confermare...",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if not BACKUP_PASSWORD or self.password_input.value != BACKUP_PASSWORD:
            await interaction.response.send_message("❌ **Password Errata o non configurata nelle ENV!** Operazione interrotta.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
        
        data = await load_backup_data(self.bot)
        target_guild = interaction.guild

        if target_guild.id != SOURCE_SERVER_ID:
            await interaction.followup.send("❌ **Errore:** Questo comando può essere eseguito solo sul server sorgente.", ephemeral=True)
            return

        # 1. RIPRISTINO CATEGORIE E CANALI
        channels_dict = data.get("channels", {})
        created_categories = {}
        
        for chan_id, info in channels_dict.items():
            if info["type"] == "category":
                try:
                    new_cat = await target_guild.create_category(name=info["name"], position=info["position"])
                    created_categories[info["name"]] = new_cat
                except Exception as e:
                    print(f"[ERRORE CREAZIONE CATEGORIA]: {e}")

        for chan_id, info in channels_dict.items():
            if info["type"] != "category":
                try:
                    cat = created_categories.get(info["category_name"]) if info["category_name"] else None
                    if info["type"] == "text":
                        await target_guild.create_text_channel(name=info["name"], category=cat, position=info["position"])
                    elif info["type"] == "voice":
                        await target_guild.create_voice_channel(name=info["name"], category=cat, position=info["position"])
                except Exception as e:
                    print(f"[ERRORE CREAZIONE CANALE]: {e}")

        # 2. RIPRISTINO TOTALE DI TUTTI I MESSAGGI
        messages_dict = data.get("messages", {})
        restored_messages = 0
        
        for msg_id, info in messages_dict.items():
            channel_name = info["channel_name"]
            target_channel = discord.utils.get(target_guild.text_channels, name=channel_name)
            
            if not target_channel:
                try:
                    target_channel = await target_guild.create_text_channel(name=channel_name)
                except Exception:
                    continue

            try:
                webhooks = await target_channel.webhooks()
                webhook = webhooks[0] if webhooks else await target_channel.create_webhook(name="Madison Secure Restorer")

                content_to_send = info["content"] or ""
                attachments = info.get("attachments", [])
                if attachments:
                    content_to_send += "\n" + "\n".join(attachments)

                await webhook.send(
                    content=content_to_send or "[Contenuto multimediale]",
                    username=f"{info['author']} (Ripristinato)",
                    avatar_url=info["avatar_url"]
                )
                restored_messages += 1
            except Exception as e:
                print(f"[ERRORE RIPRISTINO MESSAGGIO]: {e}")

        await interaction.followup.send(f"✅ **Ripristino Totale Completato!** Ricreati canali e ripristinati con successo **{restored_messages}** messaggi storici.", ephemeral=True)


class SecureRestoreView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🚀 Avvia Ripristino Totale", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="secure_password_restore_btn")
    async def open_password_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [ADMIN_1_ID, ADMIN_2_ID]:
            await interaction.response.send_message("❌ **Accesso Negato:** Non sei autorizzato.", ephemeral=True)
            return

        await interaction.response.send_modal(PasswordModal(self.bot))


class BackupBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(SecureRestoreView(self))
        try:
            synced = await self.tree.sync()
            print(f"Sincronizzati {len(synced)} comandi Slash.")
        except Exception as e:
            print(f"Errore sincronizzazione comandi Slash: {e}")

    async def on_ready(self):
        print(f'Bot loggato come {self.user} (ID: {self.user.id})')

bot = BackupBot()


# --- SISTEMA ANTI-INFILTRAZIONE ---
@bot.event
async def on_member_join(member):
    if member.guild.id == BACKUP_SERVER_ID:
        if member.id not in [ADMIN_1_ID, ADMIN_2_ID] and not member.bot:
            try:
                await member.ban(reason="[Anti-Infiltrazione] Accesso non autorizzato.")
            except Exception as e:
                print(f"[ERRORE BAN AUTOMATICO]: {e}")


# --- COMANDO SLASH: /manualbackup ---
@bot.tree.command(name="manualbackup", description="Esegue un backup COMPLETO e ILLIMITATO di tutto il server storico")
async def manualbackup(interaction: discord.Interaction):
    if interaction.user.id not in [ADMIN_1_ID, ADMIN_2_ID]:
        await interaction.response.send_message("❌ **Accesso Negato:** Non sei autorizzato.", ephemeral=True)
        return

    if interaction.guild.id != SOURCE_SERVER_ID:
        await interaction.response.send_message("❌ **Errore:** Questo comando può essere eseguito solo nel server sorgente.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    
    guild = interaction.guild
    data = await load_backup_data(bot)

    for role in guild.roles:
        if role.is_default():
            continue
        data["roles"][str(role.id)] = {
            "name": role.name,
            "color": str(role.color),
            "position": role.position,
            "permissions": str(role.permissions.value),
            "hoist": role.hoist,
            "mentionable": role.mentionable
        }

    for channel in guild.channels:
        chan_type = "category" if isinstance(channel, discord.CategoryChannel) else ("text" if isinstance(channel, discord.TextChannel) else "voice")
        data["channels"][str(channel.id)] = {
            "name": channel.name,
            "type": chan_type,
            "category_id": channel.category.id if channel.category else None,
            "category_name": channel.category.name if channel.category else None,
            "position": channel.position
        }

    total_messages_saved = 0
    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=None, oldest_first=True):
                if message.author.bot:
                    continue
                
                msg_id_str = str(message.id)
                if msg_id_str in data["messages"]:
                    continue

                permanent_attachments = []
                for att in message.attachments:
                    perm_url = await permanent_upload_attachment(bot, att.url, att.filename)
                    permanent_attachments.append(perm_url)

                data["messages"][msg_id_str] = {
                    "message_id": message.id,
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "author_id": message.author.id,
                    "author": message.author.name,
                    "avatar_url": str(message.author.display_avatar.url),
                    "content": message.content,
                    "attachments": permanent_attachments,
                    "timestamp": str(message.created_at)
                }
                total_messages_saved += 1
        except Exception as e:
            print(f"[ERRORE STORICO CANALE {channel.name}]: {e}")

    await save_backup_data(bot, data)
    await interaction.followup.send(f"✅ **Backup Totale Completato!** Archiviati **{total_messages_saved}** nuovi messaggi storici nel Cloud JSON.", ephemeral=True)


# --- COMANDO SLASH: /securepanel ---
@bot.tree.command(name="securepanel", description="Invia il pannello di controllo protetto per il ripristino")
async def securepanel(interaction: discord.Interaction):
    if interaction.user.id not in [ADMIN_1_ID, ADMIN_2_ID]:
        await interaction.response.send_message("❌ **Accesso Negato:** Non sei autorizzato.", ephemeral=True)
        return

    if interaction.guild.id != SOURCE_SERVER_ID:
        await interaction.response.send_message("❌ **Errore:** Questo pannello può essere inviato solo nel server sorgente.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🔒 • MADISON SECURE CLOUD BACKUP & RESTORE (TOTAL)",
        description=(
            f"Pannello di controllo ufficiale (Server ID: `{SOURCE_SERVER_ID}`).\n\n"
            "• **Backup Illimitato:** `/manualbackup` scarica TUTTO lo storico passato senza limiti.\n"
            "• **Tempo Reale:** Ogni modifica viene registrata all'istante.\n"
            "• **Ripristino Sicuro:** Richiede la password configurata tramite variabile d'ambiente (`BACKUP_PASSWORD`).\n\n"
            "🔐 *Riservato esclusivamente ai 2 admin.*"
        ),
        color=discord.Color.dark_red()
    )
    view = SecureRestoreView(bot)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


# --- MONITORAGGIO LIVE ---
@bot.event
async def on_guild_role_create(role):
    if role.guild.id != SOURCE_SERVER_ID:
        return
    data = await load_backup_data(bot)
    data["roles"][str(role.id)] = {"name": role.name, "color": str(role.color), "position": role.position, "permissions": str(role.permissions.value)}
    await save_backup_data(bot, data)

@bot.event
async def on_guild_channel_create(channel):
    if channel.guild.id != SOURCE_SERVER_ID:
        return
    data = await load_backup_data(bot)
    chan_type = "category" if isinstance(channel, discord.CategoryChannel) else ("text" if isinstance(channel, discord.TextChannel) else "voice")
    data["channels"][str(channel.id)] = {"name": channel.name, "type": chan_type, "category_name": channel.category.name if channel.category else None, "position": channel.position}
    await save_backup_data(bot, data)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild.id != SOURCE_SERVER_ID:
        return

    permanent_attachments = []
    for att in message.attachments:
        perm_url = await permanent_upload_attachment(bot, att.url, att.filename)
        permanent_attachments.append(perm_url)

    data = await load_backup_data(bot)
    data["messages"][str(message.id)] = {
        "message_id": message.id,
        "channel_id": message.channel.id,
        "channel_name": message.channel.name,
        "author_id": message.author.id,
        "author": message.author.name,
        "avatar_url": str(message.author.display_avatar.url),
        "content": message.content,
        "attachments": permanent_attachments,
        "timestamp": str(message.created_at)
    }
    await save_backup_data(bot, data)

    backup_guild = bot.get_guild(BACKUP_SERVER_ID)
    if backup_guild:
        target_channel = discord.utils.get(backup_guild.text_channels, name=message.channel.name)
        if not target_channel:
            target_channel = await backup_guild.create_text_channel(name=message.channel.name)
        try:
            webhooks = await target_channel.webhooks()
            webhook = webhooks[0] if webhooks else await target_channel.create_webhook(name="Madison Cloud Archiver")
            
            content_to_send = message.content or ""
            if permanent_attachments:
                content_to_send += "\n" + "\n".join(permanent_attachments)

            await webhook.send(content=content_to_send or "[Allegato]", username=f"{message.author.name} (Backup)", avatar_url=message.author.display_avatar.url)
        except Exception:
            pass

    await bot.process_commands(message)


if __name__ == "__main__":
    import threading
    t = threading.Thread(target=run_flask)
    t.start()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)
