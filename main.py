import os
import asyncio
import threading
from flask import Flask
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import requests
from supabase import create_client, Client

# Carica le variabili d'ambiente
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", 5000))
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD", "password_default")

if not DISCORD_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano una o più variabili d'ambiente nel file .env!")

# Inizializza Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configurazione Flask per Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Il bot di backup Discord con Supabase è attivo e operativo!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# Configurazione Bot Discord con Intents e Cache forzata all'avvio
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True
intents.presences = True

class BackupBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, chunk_guilds_at_startup=True)

    async def setup_hook(self):
        await self.tree.sync()
        print("Comandi slash (/) sincronizzati con successo.")

bot = BackupBot()

@bot.event
async def on_ready():
    print(f"Bot online come {bot.user}!")
    for guild in bot.guilds:
        await sync_guild_structure(guild)

async def sync_guild_structure(guild: discord.Guild):
    """Sincronizzazione completa della struttura (ruoli e canali)"""
    try:
        for role in guild.roles:
            if role.is_default(): 
                continue
            supabase.table("roles").upsert({
                "id": role.id,
                "name": role.name,
                "color": role.color.value,
                "position": role.position,
                "permissions": str(role.permissions.value)
            }).execute()
        
        for channel in guild.channels:
            overwrites = {}
            for target, perm in channel.overwrites.items():
                overwrites[str(target.id)] = {
                    "allow": perm.allow.value,
                    "deny": perm.deny.value
                }

            supabase.table("channels").upsert({
                "id": channel.id,
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "category_id": channel.category_id if hasattr(channel, 'category_id') and channel.category_id else None,
                "permission_overwrites": overwrites
            }).execute()
    except Exception as e:
        print(f"Errore sincronizzazione struttura server: {e}")

# --- COMANDO SLASH: /avvia_backup (Con Debug Ultra-Dettagliato) ---
@bot.tree.command(name="avvia_backup", description="Esegue il backup completo con debug avanzato")
@app_commands.describe(password="La password segreta per avviare il backup")
@app_commands.checks.has_permissions(administrator=True)
async def avvia_backup(interaction: discord.Interaction, password: str):
    if password != BACKUP_PASSWORD:
        await interaction.response.send_message("❌ **Password segreta errata!** Operazione negata.", ephemeral=True)
        return

    await interaction.response.send_message("🔍 **Backup con Debug avviato!** Controlla i tuoi Messaggi Privati (DM).", ephemeral=True)

    user = interaction.user
    guild = interaction.guild

    try:
        status_msg = await user.send("🔍 **[DEBUG] Inizializzazione comando in corso...**")
    except Exception:
        status_msg = await interaction.followup.send(f"⚠️ {user.mention}, non posso inviarti DM! Segui qui l'avanzamento.", ephemeral=False)

    print(f"\n================ [DEBUG BACKUP AVVIATO] ================")
    print(f"[DEBUG] Server: {guild.name} (ID: {guild.id})")
    print(f"[DEBUG] Utente richiedente: {user} (ID: {user.id})")

    # 1. TEST CONNESSIONE SUPABASE
    try:
        await status_msg.edit(content="🔍 **[DEBUG] Test connessione a Supabase...**")
        print(f"[DEBUG] Test connessione a Supabase in corso...")
        test_res = supabase.table("roles").select("id", count="exact").limit(1).execute()
        print(f"[DEBUG] Connessione a Supabase riuscita! Tabella roles raggiungibile.")
    except Exception as db_test_err:
        print(f"[DEBUG ERRORE CRITICO SUPABASE] Impossibile connettersi al database: {db_test_err}")
        await status_msg.edit(content=f"❌ **[DEBUG ERRORE]** Connessione a Supabase fallita: `{db_test_err}`")
        return

    # 2. SINCRONIZZAZIONE STRUTTURA
    try:
        await status_msg.edit(content="🔍 **[DEBUG] Sincronizzazione ruoli e canali...**")
        print(f"[DEBUG] Avvio sync_guild_structure...")
        await sync_guild_structure(guild)
        print(f"[DEBUG] sync_guild_structure completato con successo.")
    except Exception as sync_err:
        print(f"[DEBUG ERRORE] Errore durante la sincronizzazione della struttura: {sync_err}")

    # 3. FILTRAGGIO CANALI
    try:
        await status_msg.edit(content="🔍 **[DEBUG] Filtraggio canali del server...**")
        all_guild_channels = guild.channels
        print(f"[DEBUG] Canali totali grezzi nel server: {len(all_guild_channels)}")
        
        text_channels = [c for c in guild.channels if c.type in (discord.ChannelType.text, discord.ChannelType.news)]
        format_channels = len(text_channels)
        print(f"[DEBUG] Canali di testo/annunci filtrati idonei: {format_channels}")
        
        for c in text_channels:
            print(f"   -> Canale trovato: #{c.name} (ID: {c.id}, Tipo: {c.type})")

        await user.send(f"📁 **[DEBUG]** Canali totali: `{len(all_guild_channels)}` | Canali di testo validi da scansionare: `{format_channels}`")
    except Exception as chan_err:
        print(f"[DEBUG ERRORE] Errore nel filtraggio canali: {chan_err}")
        await status_msg.edit(content=f"❌ **[DEBUG ERRORE]** Filtraggio canali fallito: `{chan_err}`")
        return

    if format_channels == 0:
        print(f"[DEBUG ATTENZIONE] Nessun canale di testo trovato.")
        await status_msg.edit(content="⚠️ **[DEBUG]** Nessun canale di testo o annuncio trovato da scansionare!")
        return

    total_saved = 0

    # 4. SCANSIONE MESSAGGI
    for index, channel in enumerate(text_channels, start=1):
        print(f"\n--- [DEBUG] INIZIO CANALE #{channel.name} ({index}/{format_channels}) ---")
        try:
            await status_msg.edit(content=f"🔄 **Backup in corso...** Canale `#{channel.name}` ({index}/{format_channels})\n💾 Salvati finora: **{total_saved}**")
        except Exception:
            pass

        try:
            existing_res = supabase.table("messages").select("id").eq("channel_id", channel.id).execute()
            existing_ids = {row["id"] for row in existing_res.data}
            print(f"[DEBUG] Messaggi già presenti nel DB per #{channel.name}: {len(existing_ids)}")
        except Exception as db_read_err:
            print(f"[DEBUG ERRORE] Impossibile leggere i messaggi esistenti da Supabase per #{channel.name}: {db_read_err}")
            existing_ids = set()

        channel_messages_count = 0
        messages_read_in_channel = 0

        try:
            async for message in channel.history(limit=None, oldest_first=True):
                messages_read_in_channel += 1
                if messages_read_in_channel <= 3:  # Logga i primi 3 messaggi per ogni canale
                    print(f"   [DEBUG MSG] Letto ID {message.id} | Autore: {message.author} | Contenuto: {repr(message.content[:20])}")

                if message.id in existing_ids:
                    continue

                attachments_urls = [att.url for att in message.attachments] if message.attachments else []
                embeds_data = [embed.to_dict() for embed in message.embeds] if message.embeds else []

                msg_data = {
                    "id": message.id,
                    "channel_id": channel.id,
                    "author_id": message.author.id,
                    "author_name": message.author.display_name,
                    "author_avatar": str(message.author.display_avatar.url),
                    "content": message.content or "",
                    "attachments": attachments_urls,
                    "embeds": embeds_data
                }
                
                try:
                    supabase.table("messages").insert(msg_data).execute()
                    total_saved += 1
                    channel_messages_count += 1
                except Exception as insert_err:
                    print(f"   [DEBUG ERRORE INSERT] Fallito inserimento messaggio ID {message.id}: {insert_err}")
            
            print(f"[DEBUG] Fine canale #{channel.name}: Letti {messages_read_in_channel} messaggi, Salvati {channel_messages_count} nuovi messaggi.")
        except discord.Forbidden:
            print(f"❌ [DEBUG ERRORE PERMESSO] Il bot non ha i permessi di lettura per il canale #{channel.name}")
            try:
                await user.send(f"❌ **Permesso negato** per leggere il canale `#{channel.name}`.")
            except Exception:
                pass
        except Exception as e:
            print(f"❌ [DEBUG ERRORE CRITICO] Errore lettura cronologia #{channel.name}: {e}")

    print(f"\n================ [DEBUG BACKUP TERMINATO] ================")
    print(f"[DEBUG] Totale complessivo messaggi salvati: {total_saved}")

    try:
        await status_msg.edit(content=f"✅ **Backup e Debug completati con successo!**\nCanali analizzati: `{format_channels}`\n💾 Totale messaggi salvati: **{total_saved}**")
        await user.send(f"🎯 **[DEBUG RIEPILOGO]** Operazione completata senza crash. Controlla i log di Render per i dettagli completi.")
    except Exception:
        pass

# --- COMANDO SLASH: /verifica_db (Verifica lo stato della connessione a Supabase) ---
@bot.tree.command(name="verifica_db", description="Verifica lo stato della connessione e la lettura delle tabelle su Supabase")
@app_commands.checks.has_permissions(administrator=True)
async def verifica_db(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    status_text = "🔄 **Test di connessione a Supabase in corso...**"
    await interaction.followup.send(status_text, ephemeral=True)

    try:
        # Test tabella roles
        roles_res = supabase.table("roles").select("id", count="exact").execute()
        roles_count = roles_res.count if hasattr(roles_res, 'count') else len(roles_res.data)

        # Test tabella channels
        channels_res = supabase.table("channels").select("id", count="exact").execute()
        channels_count = channels_res.count if hasattr(channels_res, 'count') else len(channels_res.data)

        # Test tabella messages
        messages_res = supabase.table("messages").select("id", count="exact").execute()
        messages_count = messages_res.count if hasattr(messages_res, 'count') else len(messages_res.data)

        success_msg = (
            "✅ **Connessione a Supabase stabilita con successo!**\n\n"
            f"📊 **Statistiche database attuali:**\n"
            f"• Ruoli salvati: `{roles_count}`\n"
            f"• Canali salvati: `{channels_count}`\n"
            f"• Messaggi salvati: `{messages_count}`"
        )
        await interaction.edit_original_response(content=success_msg)
        print("[DEBUG] Comando /verifica_db eseguito con successo: Database online.")

    except Exception as e:
        error_msg = f"❌ **Errore di connessione a Supabase!**\nDettagli:\n`{e}`"
        await interaction.edit_original_response(content=error_msg)
        print(f"[DEBUG ERRORE] /verifica_db fallito: {e}")

@verifica_db.error
async def verifica_db_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Devi essere amministratore per usare questo comando.", ephemeral=True)

# --- COMANDO SLASH: /ripristina_tutto ---
@bot.tree.command(name="ripristina_tutto", description="Ricostruisce ruoli, categorie, canali e messaggi")
@app_commands.describe(password="La password segreta di ripristino")
@app_commands.checks.has_permissions(administrator=True)
async def ripristina_tutto(interaction: discord.Interaction, password: str):
    if password != BACKUP_PASSWORD:
        await interaction.response.send_message("❌ **Password segreta errata!** Operazione negata.", ephemeral=True)
        return

    await interaction.response.send_message("🚀 **Ripristino totale avviato!** Controlla i tuoi Messaggi Privati (DM).", ephemeral=True)

    user = interaction.user
    guild = interaction.guild

    try:
        status_msg = await user.send("🚀 **Avvio ripristino totale...** Ricostruzione ruoli in corso.")
    except Exception:
        status_msg = await interaction.followup.send(f"⚠️ {user.mention}, non posso inviarti DM!", ephemeral=False)

    try:
        roles_res = supabase.table("roles").select("*").order("position", desc=False).execute()
        for r_data in roles_res.data:
            try:
                await guild.create_role(
                    name=r_data["name"],
                    colour=discord.Colour(r_data["color"]),
                    permissions=discord.Permissions(int(r_data["permissions"]))
                )
            except Exception:
                pass
    except Exception as e:
        print(f"Errore ripristino ruoli: {e}")

    category_mapping = {} 
    text_channel_mapping = {} 

    try:
        channels_res = supabase.table("channels").select("*").order("position", desc=False).execute()
        channels_data = channels_res.data

        for c_data in channels_data:
            if "category" in str(c_data["type"]).lower():
                try:
                    new_cat = await guild.create_category(name=c_data["name"])
                    category_mapping[c_data["id"]] = new_cat
                except Exception:
                    pass

        for c_data in channels_data:
            if "text" in str(c_data["type"]).lower() or "news" in str(c_data["type"]).lower():
                cat_id = c_data.get("category_id")
                target_category = category_mapping.get(cat_id) if cat_id in category_mapping else None
                try:
                    new_channel = await guild.create_text_channel(name=c_data["name"], category=target_category)
                    text_channel_mapping[c_data["id"]] = new_channel
                except Exception:
                    pass
    except Exception as e:
        print(f"Errore ripristino canali: {e}")

    try:
        await status_msg.edit(content="🚀 Struttura creata. Ripristino messaggi in corso...")
    except Exception:
        pass

    total_restored = 0
    webhook_cache = {}

    try:
        messages_res = supabase.table("messages").select("*").order("id", desc=False).execute()
        messages_data = messages_res.data

        for msg in messages_data:
            old_channel_id = msg["channel_id"]
            if old_channel_id not in text_channel_mapping:
                continue
            
            target_channel = text_channel_mapping[old_channel_id]

            if old_channel_id not in webhook_cache:
                try:
                    webhooks = await target_channel.webhooks()
                    webhook = next((w for w in webhooks if w.name == "BackupRestoreBot"), None)
                    if not webhook:
                        webhook = await target_channel.create_webhook(name="BackupRestoreBot")
                    webhook_cache[old_channel_id] = webhook
                except Exception:
                    continue

            webhook = webhook_cache[old_channel_id]
            content_to_send = msg.get("content", "")
            attachments = msg.get("attachments", [])
            if attachments:
                content_to_send += "\n" + "\n".join(attachments)

            raw_embeds = msg.get("embeds", [])

            payload = {
                "content": content_to_send if content_to_send else "[Contenuto multimediale]",
                "username": msg["author_name"],
                "avatar_url": msg["author_avatar"],
                "embeds": raw_embeds
            }

            try:
                requests.post(webhook.url, json=payload, timeout=5)
                total_restored += 1
                if total_restored % 20 == 0:
                    try:
                        await status_msg.edit(content=f"🚀 Ripristino in corso... ({total_restored} messaggi inviati)")
                    except Exception:
                        pass
                await asyncio.sleep(0.4)
            except Exception:
                pass
    except Exception as e:
        print(f"Errore ripristino messaggi: {e}")

    try:
        await status_msg.edit(content=f"✅ **Ripristino completato!** {total_restored} messaggi ripristinati.")
    except Exception:
        pass

# --- EVENTI IN TEMPO REALE (Messaggi, Modifiche, Canali, Ruoli) ---

@bot.event
async def on_message(message: discord.Message):
    attachments_urls = [att.url for att in message.attachments] if message.attachments else []
    embeds_data = [embed.to_dict() for embed in message.embeds] if message.embeds else []

    data = {
        "id": message.id,
        "channel_id": message.channel.id,
        "author_id": message.author.id,
        "author_name": message.author.display_name,
        "author_avatar": str(message.author.display_avatar.url),
        "content": message.content or "",
        "attachments": attachments_urls,
        "embeds": embeds_data
    }
    
    try:
        supabase.table("messages").insert(data).execute()
    except Exception as e:
        print(f"Errore salvataggio realtime messaggio: {e}")

    await bot.process_commands(message)

@bot.event
async def on_message_update(before: discord.Message, after: discord.Message):
    if before.content == after.content:
        return

    try:
        supabase.table("message_edits").insert({
            "message_id": before.id,
            "old_content": before.content,
            "new_content": after.content
        }).execute()
    except Exception as e:
        print(f"Errore salvataggio modifica messaggio: {e}")

@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    await sync_guild_structure(channel.guild)

@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    await sync_guild_structure(after.guild)

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    try:
        supabase.table("channels").delete().eq("id", channel.id).execute()
    except Exception as e:
        print(f"Errore eliminazione canale da DB: {e}")

@bot.event
async def on_guild_role_create(role: discord.Role):
    await sync_guild_structure(role.guild)

@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    await sync_guild_structure(after.guild)

@bot.event
async def on_guild_role_delete(role: discord.Role):
    try:
        supabase.table("roles").delete().eq("id", role.id).execute()
    except Exception as e:
        print(f"Errore eliminazione ruolo da DB: {e}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot.run(DISCORD_TOKEN)
