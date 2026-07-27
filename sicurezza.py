import discord
from discord.ext import commands
import os
import time
from collections import defaultdict
from supabase import create_client, Client
from threading import Thread
from flask import Flask

# ==========================================
# 🌐 MINI SERVER FLASK (Per Hosting)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Madison State Logs & Security is Online!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()


# ==========================================
# ⚙️ CONFIGURAZIONE INIZIALE & SUPABASE
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") or "IL_TUO_TOKEN_QUI"

SUPABASE_URL = os.getenv("SUPABASE_URL") or "IL_TUO_SUPABASE_URL"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "IL_TUO_SUPABASE_ANON_KEY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.bans = True
intents.voice_states = True
intents.emojis = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)

DEFAULT_SECURITY_CONFIG = {
    "anti_link": {"enabled": True, "action": "delete", "timeout_minutes": 1, "whitelist": []},
    "anti_invite": {"enabled": True, "action": "timeout", "timeout_minutes": 5, "whitelist": []},
    "anti_spam": {"enabled": True, "action": "timeout", "timeout_minutes": 1, "whitelist": []},
    "anti_bot_add": {"enabled": True, "action": "kick", "whitelist": []},
    "anti_role_create": {"enabled": True, "action": "delete", "whitelist": []},
    "anti_role_delete": {"enabled": True, "action": "kick", "whitelist": []},
    "anti_dangerous_role": {"enabled": True, "action": "remove_perms", "whitelist": []},
    "anti_channel_create": {"enabled": True, "action": "delete", "whitelist": []},
    "anti_channel_delete": {"enabled": True, "action": "kick", "whitelist": []}
}

DEFAULT_LOG_CHANNELS = {
    "messages": None, "members": None, "channels": None,
    "roles": None, "voice": None, "server": None, "security": None
}

spam_tracker = defaultdict(list)


# ==========================================
# 🗄️ GESTIONE DATABASE SUPABASE
# ==========================================

async def load_settings_from_db():
    """Carica o inizializza le impostazioni da Supabase"""
    try:
        res_sec = supabase.table("bot_settings").select("*").eq("key", "security").execute()
        if not res_sec.data:
            supabase.table("bot_settings").upsert({"key": "security", "value": DEFAULT_SECURITY_CONFIG}).execute()
        else:
            # Compatibilità per vecchi record senza la chiave whitelist nei singoli moduli
            data = res_sec.data[0]["value"]
            updated = False
            for mod in DEFAULT_SECURITY_CONFIG:
                if mod in data and "whitelist" not in data[mod]:
                    data[mod]["whitelist"] = []
                    updated = True
            if updated:
                supabase.table("bot_settings").upsert({"key": "security", "value": data}).execute()
        
        res_log = supabase.table("bot_settings").select("*").eq("key", "log_channels").execute()
        if not res_log.data:
            supabase.table("bot_settings").upsert({"key": "log_channels", "value": DEFAULT_LOG_CHANNELS}).execute()
            
        print("⚙️ Configurazioni caricate con successo dal Database Supabase.")
    except Exception as e:
        print(f"[ERRORE CARICAMENTO DB]: {e}")

def get_db_security():
    try:
        res = supabase.table("bot_settings").select("value").eq("key", "security").execute()
        if res.data:
            return res.data[0]["value"]
    except Exception:
        pass
    return DEFAULT_SECURITY_CONFIG

def save_db_security(data):
    try:
        supabase.table("bot_settings").upsert({"key": "security", "value": data}).execute()
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO SECURITY DB]: {e}")

def get_db_log_channels():
    try:
        res = supabase.table("bot_settings").select("value").eq("key", "log_channels").execute()
        if res.data:
            return res.data[0]["value"]
    except Exception:
        pass
    return DEFAULT_LOG_CHANNELS

def save_db_log_channels(data):
    try:
        supabase.table("bot_settings").upsert({"key": "log_channels", "value": data}).execute()
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO LOGS DB]: {e}")


# --- FUNZIONI WHITELIST (Globale + Categoria) ---

def is_whitelisted_db(member: discord.Member) -> bool:
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True
    try:
        res = supabase.table("bot_whitelist").select("id").execute()
        if res.data:
            whitelist_ids = [row["id"] for row in res.data]
            if member.id in whitelist_ids:
                return True
            for role in member.roles:
                if role.id in whitelist_ids:
                    return True
    except Exception:
        pass
    return False

def is_module_whitelisted(member: discord.Member, module_key: str) -> bool:
    if is_whitelisted_db(member):
        return True
    sec = get_db_security()
    mod_whitelist = sec.get(module_key, {}).get("whitelist", [])
    if member.id in mod_whitelist:
        return True
    for role in member.roles:
        if role.id in mod_whitelist:
            return True
    return False


@bot.event
async def on_ready():
    print(f"Bot online come {bot.user} (ID: {bot.user.id})")
    await load_settings_from_db()
    try:
        synced = await bot.tree.sync()
        print(f"Comandi Slash sincronizzati: {len(synced)}")
    except Exception as e:
        print(f"Errore nella sincronizzazione dei comandi: {e}")


async def is_owner_or_guild_owner(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    is_bot_owner = await bot.is_owner(interaction.user)
    is_server_owner = interaction.user.id == interaction.guild.owner_id
    return is_bot_owner or is_server_owner


@bot.tree.command(name="setup-logs", description="Crea automaticamente tutti i canali dei log nella categoria specificata (Usabile una sola volta)")
async def setup_logs_command(interaction: discord.Interaction):
    if not await is_owner_or_guild_owner(interaction):
        return await interaction.response.send_message("❌ Non hai i permessi necessari.", ephemeral=True)
    
    guild = interaction.guild
    logs_dict = get_db_log_channels()
    
    # Controlla se è già stato fatto un setup salvato nel DB
    if any(logs_dict.values()):
        return await interaction.response.send_message("❌ I canali di log risultano già configurati nel database! Usa il pannello `/setting` se desideri modificarli.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    try:
        # 1. Recupero della categoria esistente tramite ID
        target_category_id = 1501639663218069666
        category = guild.get_channel(target_category_id)
        
        if not category or not isinstance(category, discord.CategoryChannel):
            return await interaction.followup.send(f"❌ Impossibile trovare la categoria con ID `{target_category_id}` nel server. Assicurati che l'ID sia corretto.", ephemeral=True)

        # 2. Definizione dei canali con le sole iniziali maiuscole nel font stilizzato
        channels_to_create = [
            ("messages", "『💬』𝐋𝐨𝐠𝐬-𝐌𝐞𝐬𝐬𝐚𝐠𝐠𝐢"),
            ("members", "『👤』𝐋𝐨𝐠𝐬-𝐌𝐞𝐦𝐛𝐫𝐢"),
            ("channels", "『📁』𝐋𝐨𝐠𝐬-𝐂𝐚𝐧𝐚𝐥𝐢"),
            ("roles", "『🏷️』𝐋𝐨𝐠𝐬-𝐑𝐮𝐨𝐥𝐢"),
            ("voice", "『🔊』𝐋𝐨𝐠𝐬-𝐕𝐨𝐜𝐚𝐥𝐢"),
            ("server", "『📊』𝐋𝐨𝐠𝐬-𝐒𝐞𝐫𝐯𝐞𝐫")
        ]

        created_channels_summary = []

        for log_key, channel_name in channels_to_create:
            new_channel = await guild.create_text_channel(channel_name, category=category, reason=f"Setup log: {log_key}")
            logs_dict[log_key] = new_channel.id
            created_channels_summary.append(f"{new_channel.mention} (`{log_key}`)")

        # 3. Salvataggio automatico su Supabase
        save_db_log_channels(logs_dict)

        embed = discord.Embed(
            title="✅ Setup Canali Log Completato con Successo",
            description=f"I canali sono stati creati con successo all'interno della categoria **{category.name}** e salvati su Supabase:\n\n" + "\n".join(created_channels_summary),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Si è verificato un errore durante la creazione dei canali: `{e}`", ephemeral=True)

# ==========================================
# 🌟 SISTEMA LOG AVANZATO & SPETTACOLARE
# ==========================================

async def send_typed_log(guild: discord.Guild, log_type: str, embed: discord.Embed):
    log_channels_dict = get_db_log_channels()
    channel_id = log_channels_dict.get(log_type) or log_channels_dict.get("security" if log_type == "security" else "server")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            embed.set_footer(
                text="Madison State Security & Logs", 
                icon_url=guild.icon.url if guild.icon else None
            )
            await channel.send(embed=embed)
        except Exception:
            pass


# 1. MESSAGGI: ELIMINAZIONE & MODIFICA
@bot.event
async def on_message_delete(message: discord.Message):
    if not message.guild or message.author.bot:
        return
    
    embed = discord.Embed(
        title="🗑️ Registro Eventi — Messaggio Eliminato", 
        color=discord.Color.from_rgb(231, 76, 60), 
        timestamp=discord.utils.utcnow()
    )
    if message.author.avatar:
        embed.set_thumbnail(url=message.author.display_avatar.url)
        
    embed.add_field(name="👤 Autore", value=f"{message.author.mention}\n`ID: {message.author.id}`", inline=True)
    embed.add_field(name="📍 Canale", value=message.channel.mention, inline=True)
    
    content = message.content or "*[Nessun testo / Contenuto multimediale o allegato]*"
    if len(content) > 1024: 
        content = content[:1021] + "..."
    embed.add_field(name="💬 Testo del Messaggio", value=f"```{content}```", inline=False)
    
    await send_typed_log(message.guild, "messages", embed)


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if not before.guild or before.author.bot or before.content == after.content:
        return
        
    embed = discord.Embed(
        title="✏️ Registro Eventi — Messaggio Modificato", 
        color=discord.Color.from_rgb(241, 196, 15), 
        timestamp=discord.utils.utcnow()
    )
    if before.author.avatar:
        embed.set_thumbnail(url=before.author.display_avatar.url)
        
    embed.add_field(name="👤 Autore", value=f"{before.author.mention}\n`ID: {before.author.id}`", inline=True)
    embed.add_field(name="📍 Canale", value=before.channel.mention, inline=True)
    
    old_c = before.content or "*[Vuoto]*"
    new_c = after.content or "*[Vuoto]*"
    if len(old_c) > 500: old_c = old_c[:497] + "..."
    if len(new_c) > 500: new_c = new_c[:497] + "..."
    
    embed.add_field(name="📜 Prima della modifica", value=f"```{old_c}```", inline=False)
    embed.add_field(name="✨ Dopo la modifica", value=f"```{new_c}```", inline=False)
    
    await send_typed_log(before.guild, "messages", embed)


# 2. MEMBRI: INGRESSI, USCITE, BAN
@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        sec = get_db_security().get("anti_bot_add", {})
        if sec.get("enabled"):
            guild = member.guild
            adder = None
            try:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
                    if entry.target.id == member.id:
                        adder = entry.user
                        break
            except:
                pass

            if adder and not is_module_whitelisted(adder, "anti_bot_add"):
                action = sec.get("action", "kick")
                action_desc = await apply_generic_action(guild, adder, action, "Aggiunta bot non autorizzata")
                try:
                    await member.kick(reason="Bot aggiunto senza autorizzazione")
                except:
                    pass

                embed = discord.Embed(title="🚨 Madison Security — Bot Non Autorizzato", color=discord.Color.from_rgb(204, 41, 41), timestamp=discord.utils.utcnow())
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="🤖 Bot Rilevato", value=f"{member} (`{member.id}`)", inline=False)
                embed.add_field(name="👤 Aggiunto Da", value=f"{adder.mention} (`{adder.id}`)", inline=False)
                embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
                await send_typed_log(guild, "security", embed)
                return

    embed = discord.Embed(
        title="📥 Registro Membri — Nuovo Ingresso", 
        color=discord.Color.from_rgb(46, 204, 113), 
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Utente", value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 Account Creato il", value=f"<t:{int(member.created_at.timestamp())}:D> (<t:{int(member.created_at.timestamp())}:R>)", inline=False)
    
    await send_typed_log(member.guild, "members", embed)


@bot.event
async def on_member_remove(member: discord.Member):
  guild = member.guild
  moderator = None
  kick_reason = 'Nessun motivo specificato'
  is_kick = False

  # Controlliamo nell'audit log se si tratta di un kick recente
  try:
    async for entry in guild.audit_logs(
        limit=5, action=discord.AuditLogAction.kick
    ):
      if entry.target and entry.target.id == member.id:
        # Verifichiamo che l'azione sia avvenuta negli ultimi secondi per evitare falsi positivi storici
        if (
            discord.utils.utcnow() - entry.created_at
        ).total_seconds() < 10:
          is_kick = True
          moderator = entry.user
          if entry.reason:
            kick_reason = entry.reason
          break
  except Exception:
    pass

  if is_kick:
    # --- LOG KICK (Espulsione) ---
    embed = discord.Embed(
        title='👢 Registro Membri — Utente Espulso (Kick)',
        color=discord.Color.from_rgb(230, 126, 34),
        timestamp=discord.utils.utcnow(),
    )
    if member.avatar:
      embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name='👤 Utente', value=f'{member.mention}\n`{member}`', inline=True
    )
    embed.add_field(name='🆔 ID', value=f'`{member.id}`', inline=True)

    if moderator:
      embed.add_field(
          name='👮 Moderatore Responsabile',
          value=f'{moderator.mention}\n`ID: {moderator.id}`',
          inline=False,
      )

    embed.add_field(
        name='📝 Motivo dell\'Espulsione',
        value=f'```{kick_reason}```',
        inline=False,
    )

    await send_typed_log(guild, 'members', embed)

  else:
    # --- LOG USCITA STANDARD (Abbandono volontario) ---
    embed = discord.Embed(
        title='📤 Registro Membri — Uscita dal Server',
        color=discord.Color.from_rgb(149, 165, 166),
        timestamp=discord.utils.utcnow(),
    )
    if member.avatar:
      embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name='👤 Utente', value=f'{member.mention}\n`{member}`', inline=True
    )
    embed.add_field(name='🆔 ID', value=f'`{member.id}`', inline=True)

    roles = [r.mention for r in member.roles if r != guild.default_role]
    if roles:
      roles_str = ', '.join(roles[:10])
      if len(roles) > 10:
        roles_str += f' e altri {len(roles) - 10} ruoli'
      embed.add_field(
          name=f'🏷️ Ruoli Posseduti ({len(roles)})',
          value=roles_str,
          inline=False,
      )

    await send_typed_log(guild, 'members', embed)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
  moderator = None
  ban_reason = 'Nessun motivo specificato'

  try:
    async for entry in guild.audit_logs(
        limit=5, action=discord.AuditLogAction.ban
    ):
      if entry.target and entry.target.id == user.id:
        moderator = entry.user
        if entry.reason:
          ban_reason = entry.reason
        break
  except Exception:
    pass

  embed = discord.Embed(
      title='🔨 Registro Membri — Utente Bannato',
      color=discord.Color.from_rgb(192, 57, 43),
      timestamp=discord.utils.utcnow(),
  )
  if user.avatar:
    embed.set_thumbnail(url=user.display_avatar.url)

  embed.add_field(
      name='👤 Utente', value=f'{user.mention}\n`{user}`', inline=True
  )
  embed.add_field(name='🆔 ID', value=f'`{user.id}`', inline=True)

  if moderator:
    embed.add_field(
        name='👮 Moderatore Responsabile',
        value=f'{moderator.mention}\n`ID: {moderator.id}`',
        inline=False,
    )

  embed.add_field(
      name='📝 Motivo del Ban',
      value=f'```{ban_reason}```',
      inline=False,
  )

  await send_typed_log(guild, 'members', embed)

# 3. CANALI: CREAZIONE & ELIMINAZIONE
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    embed = discord.Embed(
        title="📁 Registro Canali — Creato", 
        color=discord.Color.from_rgb(52, 152, 219), 
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📌 Nome Canale", value=f"#{channel.name}" if isinstance(channel, discord.TextChannel) else f"🔊 {channel.name}", inline=True)
    embed.add_field(name="📂 Categoria", value=channel.category.name if channel.category else "Nessuna", inline=True)
    embed.add_field(name="🆔 ID Canale", value=f"`{channel.id}`", inline=True)
    
    await send_typed_log(channel.guild, "channels", embed)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    embed = discord.Embed(
        title="❌ Registro Canali — Eliminato", 
        color=discord.Color.from_rgb(231, 76, 60), 
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📌 Nome Canale", value=f"#{channel.name}" if isinstance(channel, discord.TextChannel) else f"🔊 {channel.name}", inline=True)
    embed.add_field(name="🆔 ID Canale", value=f"`{channel.id}`", inline=True)
    
    await send_typed_log(channel.guild, "channels", embed)


# 4. RUOLI: CREAZIONE & ELIMINAZIONE
@bot.event
async def on_guild_role_create(role: discord.Role):
    embed = discord.Embed(
        title="🏷️ Registro Ruoli — Creato", 
        color=discord.Color.from_rgb(155, 89, 182), 
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📌 Nome Ruolo", value=role.mention, inline=True)
    embed.add_field(name="🆔 ID Ruolo", value=f"`{role.id}`", inline=True)
    embed.add_field(name="🎨 Colore", value=f"`{role.color}`", inline=True)
    
    await send_typed_log(role.guild, "roles", embed)


@bot.event
async def on_guild_role_delete(role: discord.Role):
    embed = discord.Embed(
        title="🗑️ Registro Ruoli — Eliminato", 
        color=discord.Color.from_rgb(231, 76, 60), 
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📌 Nome Ruolo", value=f"**{role.name}**", inline=True)
    embed.add_field(name="🆔 ID Ruolo", value=f"`{role.id}`", inline=True)
    
    await send_typed_log(role.guild, "roles", embed)

# 5. VOCALI: SPOSTAMENTI, CONNESSIONI E DISCONNESSIONI DETTAGLIATE
@bot.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
  if member.bot:
    return

  guild = member.guild

  # Connessione a un canale vocale
  if before.channel is None and after.channel is not None:
    embed = discord.Embed(
        title='🔊 Attività Vocale — Connessione',
        color=discord.Color.from_rgb(52, 152, 219),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name='👤 Utente',
        value=f'{member.mention}\n`{member}`',
        inline=True,
    )
    embed.add_field(
        name='🎙️ Canale Vocale', value=f'`{after.channel.name}`', inline=True
    )
    await send_typed_log(guild, 'voice', embed)

  # Disconnessione da un canale vocale
  elif before.channel is not None and after.channel is None:
    embed = discord.Embed(
        title='🔇 Attività Vocale — Disconnessione',
        color=discord.Color.from_rgb(127, 140, 141),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name='👤 Utente',
        value=f'{member.mention}\n`{member}`',
        inline=True,
    )
    embed.add_field(
        name='🎙️ Canale Precedente',
        value=f'`{before.channel.name}`',
        inline=True,
    )
    await send_typed_log(guild, 'voice', embed)

  # Spostamento da un canale vocale all'altro
  elif (
      before.channel is not None
      and after.channel is not None
      and before.channel.id != after.channel.id
  ):
    moderator = None
    try:
      async for entry in guild.audit_logs(
          limit=5, action=discord.AuditLogAction.member_move
      ):
        if entry.target and entry.target.id == member.id:
          if (
              discord.utils.utcnow() - entry.created_at
          ).total_seconds() < 10:
            moderator = entry.user
            break
    except Exception:
      pass

    embed = discord.Embed(
        title='🔀 Attività Vocale — Spostato',
        color=discord.Color.from_rgb(155, 89, 182),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='👤 Utente', value=f'{member.mention}', inline=True)
    embed.add_field(name='🎙️ Da', value=f'`{before.channel.name}`', inline=True)
    embed.add_field(name='🎙️ A', value=f'`{after.channel.name}`', inline=True)

    if moderator:
      embed.add_field(
          name='👮 Moderatore Responsabile',
          value=f'{moderator.mention}\n`ID: {moderator.id}`',
          inline=False,
      )

    await send_typed_log(guild, 'voice', embed)

  # Variazione Stati Mutamento Vocale (Mute/Deafen)
  elif before.channel is not None and after.channel is not None:
    status_changes = []
    if before.self_mute != after.self_mute:
      status_changes.append(
          'Microfono Mutato' if after.self_mute else 'Microfono Smutato'
      )
    if before.self_deaf != after.self_deaf:
      status_changes.append(
          'Audio Sordina' if after.self_deaf else 'Audio Dissordina'
      )
    if before.mute != after.mute:
      status_changes.append(
          'Muto Server Applicato'
          if after.mute
          else 'Muto Server Rimosso'
      )
    if before.deaf != after.deaf:
      status_changes.append(
          'Sordo Server Applicato'
          if after.deaf
          else 'Sordo Server Rimosso'
      )

    if status_changes:
      embed = discord.Embed(
          title='🎧 Attività Vocale — Stato Modificato',
          color=discord.Color.from_rgb(241, 196, 15),
          timestamp=discord.utils.utcnow(),
      )
      embed.set_thumbnail(url=member.display_avatar.url)
      embed.add_field(
          name='👤 Utente',
          value=f'{member.mention}\n`{member}`',
          inline=True,
      )
      embed.add_field(
          name='🎙️ Canale', value=f'`{after.channel.name}`', inline=True
      )
      embed.add_field(
          name='⚙️ Modifiche Stato',
          value='\n'.join([f'• {change}' for change in status_changes]),
          inline=False,
      )
      await send_typed_log(guild, 'voice', embed)


# ==========================================
# 🎛️ PANNELLO DI SETTING INTERATTIVO (DB FIRST)
# ==========================================

class ModuleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Anti-Link", value="anti_link", description="Gestisci blocchi e azioni per i link esterni", emoji="🔗"),
            discord.SelectOption(label="Anti-Invite", value="anti_invite", description="Gestisci blocchi per inviti Discord", emoji="📨"),
            discord.SelectOption(label="Anti-Spam", value="anti_spam", description="Gestisci protezione anti-spam", emoji="⚡"),
            discord.SelectOption(label="Anti-Bot Add", value="anti_bot_add", description="Protezione contro aggiunta bot non autorizzati", emoji="🤖"),
            discord.SelectOption(label="Anti-Role Create", value="anti_role_create", description="Gestisci creazione ruoli", emoji="🏷️"),
            discord.SelectOption(label="Anti-Role Delete", value="anti_role_delete", description="Gestisci eliminazione ruoli", emoji="🗑️"),
            discord.SelectOption(label="Anti-Dangerous Role", value="anti_dangerous_role", description="Protezione ruoli con permessi pericolosi", emoji="⚠️"),
            discord.SelectOption(label="Anti-Channel Create", value="anti_channel_create", description="Gestisci creazione canali", emoji="📁"),
            discord.SelectOption(label="Anti-Channel Delete", value="anti_channel_delete", description="Gestisci eliminazione canali", emoji="❌"),
        ]
        super().__init__(placeholder="Seleziona un modulo di sicurezza da configurare...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi necessari.", ephemeral=True)
        
        module_key = self.values[0]
        view = ModuleConfigView(module_key)
        security_config = get_db_security()
        mod_info = security_config.get(module_key, {})
        
        status_str = "✅ Abilitato" if mod_info.get("enabled") else "❌ Disabilitato"
        wl_count = len(mod_info.get("whitelist", []))
        desc = (
            f"**Modulo Selezionato:** `{module_key.replace('_', ' ').title()}`\n"
            f"**Stato Attuale:** {status_str}\n"
            f"**Azione:** `{mod_info.get('action', 'N/D')}`\n"
            f"**Elementi in Whitelist Categoria:** `{wl_count}`\n"
        )
        if "timeout_minutes" in mod_info:
            desc += f"**Durata Timeout:** `{mod_info.get('timeout_minutes')} minuti`\n"
            
        embed = discord.Embed(title=f"🛡️ Madison Security — {module_key.replace('_', ' ').title()}", description=desc, color=discord.Color.dark_blue())
        await interaction.response.edit_message(embed=embed, view=view)


class ModuleConfigView(discord.ui.View):
    def __init__(self, module_key: str):
        super().__init__(timeout=180)
        self.module_key = module_key

    @discord.ui.button(label="Attiva/Disattiva", style=discord.ButtonStyle.blurple, emoji="🔄", row=0)
    async def toggle_enabled(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        sec = get_db_security()
        curr = sec[self.module_key].get("enabled", True)
        sec[self.module_key]["enabled"] = not curr
        save_db_security(sec)
        
        await interaction.response.send_message(f"✅ Stato del modulo modificato a: **{'Abilitato' if not curr else 'Disabilitato'}**", ephemeral=True)

    @discord.ui.button(label="Cambia Parametri", style=discord.ButtonStyle.green, emoji="⚙️", row=0)
    async def change_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        modal = ModuleSettingsModal(self.module_key)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Gestisci Whitelist Modulo", style=discord.ButtonStyle.secondary, emoji="🛡️", row=1)
    async def manage_module_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        view = ModuleWhitelistView(self.module_key)
        embed = discord.Embed(
            title=f"🛡️ Whitelist Categoria — {self.module_key.replace('_', ' ').title()}",
            description="Seleziona un ruolo o utente da aggiungere o rimuovere dalla whitelist esclusiva di questo modulo.",
            color=discord.Color.dark_green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⬅️ Torna al Menu", style=discord.ButtonStyle.grey, row=1)
    async def back_to_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        embed = discord.Embed(
            title="🛡️ Madison State — Pannello di Controllo",
            description="Usa i menu e i pulsanti sottostanti per configurare interamente i sistemi di sicurezza e log.",
            color=discord.Color.dark_blue()
        )
        view = SettingsMainView(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


class ModuleSettingsModal(discord.ui.Modal, title="Modifica Parametri Modulo"):
    def __init__(self, module_key: str):
        super().__init__()
        self.module_key = module_key
        
        sec = get_db_security()
        curr_action = sec[module_key].get("action", "delete")
        curr_timeout = str(sec[module_key].get("timeout_minutes", 1))
        
        self.action_input = discord.ui.TextInput(label="Azione (delete, timeout, kick, ban...)", default=curr_action, required=True, max_length=20)
        self.timeout_input = discord.ui.TextInput(label="Minuti di Timeout (se applicabile)", default=curr_timeout, required=False, max_length=5)
        self.add_item(self.action_input)
        self.add_item(self.timeout_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi necessari.", ephemeral=True)
            
        sec = get_db_security()
        new_action = self.action_input.value.strip().lower()
        sec[self.module_key]["action"] = new_action
        
        if self.timeout_input.value and self.timeout_input.value.isdigit():
            sec[self.module_key]["timeout_minutes"] = int(self.timeout_input.value.strip())
            
        save_db_security(sec)
        await interaction.response.send_message(f"✅ Parametri aggiornati con successo per `{self.module_key}` nel DB!", ephemeral=True)


# --- GESTIONE WHITELIST PER SINGOLA CATEGORIA ---

class ModuleWhitelistView(discord.ui.View):
    def __init__(self, module_key: str):
        super().__init__(timeout=180)
        self.module_key = module_key

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Seleziona un ruolo...", min_values=1, max_values=1, row=0)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        role = select.values[0]
        view = ModuleWhitelistActionView(self.module_key, role.id, role.name)
        await interaction.response.edit_message(content=f"⚙️ Ruolo selezionato: **{role.name}**\nCosa desideri fare per questo modulo?", view=view, embed=None)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Seleziona un utente...", min_values=1, max_values=1, row=1)
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        user = select.values[0]
        view = ModuleWhitelistActionView(self.module_key, user.id, str(user))
        await interaction.response.edit_message(content=f"⚙️ Utente selezionato: **{user}**\nCosa desideri fare per questo modulo?", view=view, embed=None)


class ModuleWhitelistActionView(discord.ui.View):
    def __init__(self, module_key: str, target_id: int, target_name: str):
        super().__init__(timeout=180)
        self.module_key = module_key
        self.target_id = target_id
        self.target_name = target_name

    @discord.ui.button(label="Aggiungi alla Whitelist del Modulo", style=discord.ButtonStyle.success, emoji="✅")
    async def add_mw(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        sec = get_db_security()
        if "whitelist" not in sec[self.module_key]:
            sec[self.module_key]["whitelist"] = []
            
        if self.target_id not in sec[self.module_key]["whitelist"]:
            sec[self.module_key]["whitelist"].append(self.target_id)
            save_db_security(sec)
            
        await interaction.response.edit_message(content=f"✅ Elemento **{self.target_name}** (`{self.target_id}`) aggiunto con successo alla whitelist del modulo `{self.module_key}`!", view=None)

    @discord.ui.button(label="Rimuovi dalla Whitelist del Modulo", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_mw(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        sec = get_db_security()
        if "whitelist" in sec[self.module_key] and self.target_id in sec[self.module_key]["whitelist"]:
            sec[self.module_key]["whitelist"].remove(self.target_id)
            save_db_security(sec)
            
        await interaction.response.edit_message(content=f"✅ Elemento **{self.target_name}** (`{self.target_id}`) rimosso dalla whitelist del modulo `{self.module_key}`!", view=None)


# --- GESTIONE GLOBAL WHITELIST SU TABELLA DB ---

class GlobalWhitelistView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Seleziona un ruolo dalla lista...", min_values=1, max_values=1, row=0)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        role = select.values[0]
        view = WhitelistActionConfirmView(target_id=role.id, target_name=role.name, target_type="role")
        await interaction.response.edit_message(content=f"⚙️ Ruolo selezionato: **{role.name}**\nCosa desideri fare?", view=view, embed=None)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Seleziona un utente dalla lista...", min_values=1, max_values=1, row=1)
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        user = select.values[0]
        view = WhitelistActionConfirmView(target_id=user.id, target_name=str(user), target_type="user")
        await interaction.response.edit_message(content=f"⚙️ Utente selezionato: **{user}**\nCosa desideri fare?", view=view, embed=None)


class WhitelistActionConfirmView(discord.ui.View):
    def __init__(self, target_id: int, target_name: str, target_type: str):
        super().__init__(timeout=180)
        self.target_id = target_id
        self.target_name = target_name
        self.target_type = target_type

    @discord.ui.button(label="Aggiungi alla Global Whitelist", style=discord.ButtonStyle.success, emoji="✅")
    async def add_wh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        try:
            supabase.table("bot_whitelist").upsert({
                "id": self.target_id,
                "target_type": self.target_type,
                "target_name": self.target_name
            }, on_conflict="id").execute()
            tipo = "Ruolo" if self.target_type == "role" else "Utente"
            await interaction.response.edit_message(content=f"✅ {tipo} **{self.target_name}** (`{self.target_id}`) aggiunto con successo alla tabella Global Whitelist del DB!", view=None)
        except Exception as e:
            await interaction.response.edit_message(content=f"❌ Errore durante il salvataggio su Supabase: `{e}`", view=None)

    @discord.ui.button(label="Rimuovi dalla Global Whitelist", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_wh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        try:
            supabase.table("bot_whitelist").delete().eq("id", self.target_id).execute()
            tipo = "Ruolo" if self.target_type == "role" else "Utente"
            await interaction.response.edit_message(content=f"✅ {tipo} **{self.target_name}** (`{self.target_id}`) rimosso con successo dalla tabella Global Whitelist del DB!", view=None)
        except Exception as e:
            await interaction.response.edit_message(content=f"❌ Errore durante la rimozione su Supabase: `{e}`", view=None)


# --- CONFIGURAZIONE CANALI LOG SU DB (CON PAGINAZIONE A BLOCCHI) ---

class LogChannelSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        options = [
            discord.SelectOption(label="Messaggi (messages)", value="messages", description="Log eliminazione e modifica messaggi"),
            discord.SelectOption(label="Membri (members)", value="members", description="Log ingressi, uscite, ban e timeout"),
            discord.SelectOption(label="Canali (channels)", value="channels", description="Log creazione e rimozione canali"),
            discord.SelectOption(label="Ruoli (roles)", value="roles", description="Log creazione e rimozione ruoli"),
            discord.SelectOption(label="Vocali (voice)", value="voice", description="Log attività nei canali vocali"),
            discord.SelectOption(label="Server (server)", value="server", description="Log generali di server"),
            discord.SelectOption(label="Sicurezza (security)", value="security", description="Log di tutti i moduli di protezione"),
        ]
        super().__init__(placeholder="Seleziona la categoria di log da configurare...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        log_type = self.values[0]
        view = ChannelPickerView(log_type, self.guild, page=0)
        embed = discord.Embed(
            title=f"📋 Scegli il canale per: `{log_type}` (Pagina 1)",
            description="Seleziona il canale di testo desiderato dal menu sottostante. Usa i pulsanti per cambiare pagina se hai molti canali.",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelPickerSelect(discord.ui.Select):
    def __init__(self, log_type: str, guild: discord.Guild, page: int = 0):
        self.log_type = log_type
        text_channels = [ch for ch in guild.text_channels]
        
        # Suddividiamo i canali in blocchi da 25
        self.chunk_size = 25
        self.total_pages = max(1, (len(text_channels) + self.chunk_size - 1) // self.chunk_size)
        self.current_page = max(0, min(page, self.total_pages - 1))
        
        start_idx = self.current_page * self.chunk_size
        end_idx = start_idx + self.chunk_size
        current_channels = text_channels[start_idx:end_idx]
        
        options = [
            discord.SelectOption(label=f"#{ch.name}", value=str(ch.id), description=f"ID: {ch.id}")
            for ch in current_channels
        ]
        if not options:
            options.append(discord.SelectOption(label="Nessun canale disponibile", value="none"))
            
        super().__init__(placeholder=f"Scegli il canale (Pagina {self.current_page + 1}/{self.total_pages})...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        if self.values[0] == "none":
            return await interaction.response.send_message("❌ Nessun canale valido selezionato.", ephemeral=True)
        ch_id = int(self.values[0])
        logs = get_db_log_channels()
        logs[self.log_type] = ch_id
        save_db_log_channels(logs)
        await interaction.response.edit_message(content=f"✅ Canale log per `{self.log_type}` impostato con successo su <#{ch_id}> nel DB!", embed=None, view=None)


class ChannelPickerView(discord.ui.View):
    def __init__(self, log_type: str, guild: discord.Guild, page: int = 0):
        super().__init__(timeout=180)
        self.log_type = log_type
        self.guild = guild
        self.page = page
        
        # Calcoliamo il totale delle pagine per gestire lo stato dei pulsanti
        text_channels = [ch for ch in guild.text_channels]
        total_pages = max(1, (len(text_channels) + 24) // 25)
        self.total_pages = total_pages
        
        # Aggiungiamo il selettore dei canali per la pagina corrente
        self.picker_select = ChannelPickerSelect(log_type, guild, page)
        self.add_item(self.picker_select)

    @discord.ui.button(label="⬅️ Indietro", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        if self.page > 0:
            self.page -= 1
            new_view = ChannelPickerView(self.log_type, self.guild, self.page)
            embed = discord.Embed(
                title=f"📋 Scegli il canale per: `{self.log_type}` (Pagina {self.page + 1}/{self.total_pages})",
                description="Seleziona il canale di testo desiderato dal menu sottostante.",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Avanti ➡️", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        if self.page < self.total_pages - 1:
            self.page += 1
            new_view = ChannelPickerView(self.log_type, self.guild, self.page)
            embed = discord.Embed(
                title=f"📋 Scegli il canale per: `{self.log_type}` (Pagina {self.page + 1}/{self.total_pages})",
                description="Seleziona il canale di testo desiderato dal menu sottostante.",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.defer()


class LogChannelSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.add_item(LogChannelSelect(guild))

class SettingsMainView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.guild = guild
        self.add_item(ModuleSelect())

    @discord.ui.button(label="Global Whitelist", style=discord.ButtonStyle.success, emoji="🌐", row=1)
    async def global_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        view = GlobalWhitelistView()
        embed = discord.Embed(
            title="🌐 Gestione Global Whitelist (Database)",
            description="Seleziona un ruolo o un utente dai menu sottostanti per gestirlo direttamente sul database Supabase.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Configura Canali Log", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def log_channels_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        view = LogChannelSelectView(interaction.guild)
        embed = discord.Embed(
            title="📋 Configurazione Canali Log",
            description="Scegli dal menu a tendina quale categoria di log associare a uno specifico canale.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="setting", description="Apre il pannello di controllo completo e interattivo di Madison State")
async def setting_command(interaction: discord.Interaction):
    if not await is_owner_or_guild_owner(interaction):
        return await interaction.response.send_message("❌ Questo comando può essere eseguito solo dal proprietario.", ephemeral=True)
    embed = discord.Embed(
        title="🛡️ Madison State — Pannello di Controllo",
        description="Gestisci in modo centralizzato tutti i protocolli di sicurezza, le whitelist e i canali log istituzionali.",
        color=discord.Color.dark_blue()
    )
    view = SettingsMainView(interaction.guild)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==========================================
# 🛡️ CONTROLLI DI SICUREZZA IN TEMPO REALE
# ==========================================

async def apply_generic_action(guild: discord.Guild, member: discord.Member, action: str, reason: str):
    if not member or member.guild_permissions.administrator:
        return "Nessuna azione (Utente amministratore o protetto)"
    try:
        if action == "kick":
            await guild.kick(member, reason=reason)
            return "Espulsione Eseguita (Kick)"
        elif action == "ban":
            await guild.ban(member, reason=reason)
            return "Bando Eseguito (Ban)"
    except Exception as e:
        return f"Errore esecuzione: {e}"
    return "Nessuna azione eseguita"


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    member = message.author
    content_lower = message.content.lower()
    sec = get_db_security()

    # 1. Anti-Invite
    if sec.get("anti_invite", {}).get("enabled") and ("discord.gg/" in content_lower or "discord.com/invite/" in content_lower):
        if not is_module_whitelisted(member, "anti_invite"):
            action = sec["anti_invite"].get("action", "delete")
            minutes = sec["anti_invite"].get("timeout_minutes", 1)
            try:
                await message.delete()
            except:
                pass
            action_desc = "Messaggio eliminato"
            if action == "timeout":
                until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
                await member.timeout(until, reason="Invito Discord non autorizzato")
                action_desc = f"Timeout applicato ({minutes} min)"
            elif action in ["kick", "ban"]:
                action_desc = await apply_generic_action(message.guild, member, action, "Invito Discord non autorizzato")

            embed = discord.Embed(title="🚨 Madison Security — Invito Bloccato", color=discord.Color.from_rgb(217, 130, 43), timestamp=discord.utils.utcnow())
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Utente Segnalato", value=f"{member.mention}\n`ID: {member.id}`", inline=True)
            embed.add_field(name="📍 Canale", value=message.channel.mention, inline=True)
            embed.add_field(name="🛡️ Protocollo", value="Anti-Invite", inline=True)
            embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
            await send_typed_log(message.guild, "security", embed)
            return

    # 2. Anti-Link
    if sec.get("anti_link", {}).get("enabled") and ("http://" in content_lower or "https://" in content_lower):
        if "discord.gg" not in content_lower and "youtube.com" not in content_lower:
            if not is_module_whitelisted(member, "anti_link"):
                action = sec["anti_link"].get("action", "delete")
                minutes = sec["anti_link"].get("timeout_minutes", 1)
                try:
                    await message.delete()
                except:
                    pass
                action_desc = "Messaggio eliminato"
                if action == "timeout":
                    until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
                    await member.timeout(until, reason="Link esterno non consentito")
                    action_desc = f"Timeout applicato ({minutes} min)"
                elif action in ["kick", "ban"]:
                    action_desc = await apply_generic_action(message.guild, member, action, "Link esterno non consentito")

                embed = discord.Embed(title="🚨 Madison Security — Link Bloccato", color=discord.Color.from_rgb(217, 130, 43), timestamp=discord.utils.utcnow())
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="👤 Utente Segnalato", value=f"{member.mention}\n`ID: {member.id}`", inline=True)
                embed.add_field(name="📍 Canale", value=message.channel.mention, inline=True)
                embed.add_field(name="🛡️ Protocollo", value="Anti-Link Esterno", inline=True)
                embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
                await send_typed_log(message.guild, "security", embed)
                return

    # 3. Anti-Spam
    if sec.get("anti_spam", {}).get("enabled"):
        if not is_module_whitelisted(member, "anti_spam"):
            user_id = member.id
            now = time.time()
            spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 4]
            spam_tracker[user_id].append(now)

            if len(spam_tracker[user_id]) > 5:
                action = sec["anti_spam"].get("action", "timeout")
                minutes = sec["anti_spam"].get("timeout_minutes", 1)
                try:
                    await message.delete()
                except:
                    pass
                action_desc = "Messaggio eliminato"
                if action == "timeout":
                    until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
                    await member.timeout(until, reason="Spam rapido rilevato")
                    action_desc = f"Timeout applicato ({minutes} min)"
                elif action in ["kick", "ban"]:
                    action_desc = await apply_generic_action(message.guild, member, action, "Spam rapido rilevato")

                embed = discord.Embed(title="🚨 Madison Security — Spam Rilevato", color=discord.Color.from_rgb(204, 41, 41), timestamp=discord.utils.utcnow())
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="👤 Utente Segnalato", value=f"{member.mention}\n`ID: {member.id}`", inline=True)
                embed.add_field(name="🛡️ Protocollo", value="Anti-Spam Rapido", inline=True)
                embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
                await send_typed_log(message.guild, "security", embed)
                return

    await bot.process_commands(message)


if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
