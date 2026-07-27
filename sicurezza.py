import discord
from discord.ext import commands
import os
import json
import io
import time
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ==========================================
# ⚙️ CONFIGURAZIONE INIZIALE
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") or "IL_TUO_TOKEN_QUI"

# ID del canale Cloud sul server secondario/di backup dove salvare le configurazioni
CLOUD_JSON_CHANNEL_ID = 1531338600653000856  # Sostituisci con il tuo ID reale

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

# Configurazione globale (salvata e sincronizzata via Cloud Discord)
config_data = {
    "security": {
        "anti_link": {
            "enabled": True,
            "action": "delete", # "delete", "timeout", "kick", "ban"
            "timeout_minutes": 1,
            "whitelist_users": [],
            "whitelist_roles": []
        },
        "anti_invite": {
            "enabled": True,
            "action": "timeout",
            "timeout_minutes": 5,
            "whitelist_users": [],
            "whitelist_roles": []
        },
        "anti_spam": {
            "enabled": True,
            "action": "timeout",
            "timeout_minutes": 1,
            "whitelist_users": [],
            "whitelist_roles": []
        }
    },
    "log_channels": {
        "messages": None,   # Eliminati / Modificati
        "members": None,    # Ingressi / Uscite / Ban / Timeout
        "channels": None,   # Canali creati / modificati / eliminati
        "roles": None,      # Ruoli creati / modificati / eliminati
        "voice": None,      # Entrate / uscite / spostamenti vocali
        "server": None,     # Modifiche server / Emoji / Inviti
        "security": None    # 🛡️ Log dedicati alle violazioni di sicurezza
    }
}

spam_tracker = defaultdict(list)


# ==========================================
# ☁️ GESTIONE CONFIGURAZIONI NEL CLOUD DISCORD
# ==========================================

async def load_config_from_discord():
    global config_data
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        print("[AVVISO] Canale Cloud JSON non trovato. Uso i valori predefiniti.")
        return
    
    try:
        async for message in channel.history(limit=20):
            if message.author == bot.user and message.attachments:
                for att in message.attachments:
                    if att.filename == "bot_config.json":
                        file_bytes = await att.read()
                        loaded = json.loads(file_bytes.decode("utf-8"))
                        for key, value in loaded.items():
                            if key in config_data:
                                if isinstance(value, dict) and isinstance(config_data[key], dict):
                                    config_data[key].update(value)
                                else:
                                    config_data[key] = value
                        print("⚙️ Configurazioni caricate con successo dal Cloud Discord.")
                        return
    except Exception as e:
        print(f"[ERRORE CARICAMENTO CONFIG CLOUD]: {e}")

async def save_config_to_discord():
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        return

    json_str = json.dumps(config_data, indent=4, ensure_ascii=False)
    file_bytes = io.BytesIO(json_str.encode("utf-8"))
    discord_file = discord.File(file_bytes, filename="bot_config.json")

    try:
        async for message in channel.history(limit=20):
            if message.author == bot.user and message.attachments:
                for att in message.attachments:
                    if att.filename == "bot_config.json":
                        await message.delete()
    except Exception:
        pass

    try:
        await channel.send("⚙️ **Aggiornamento Configurazioni Bot & Log:**", file=discord_file)
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO CONFIG CLOUD]: {e}")


@bot.event
async def on_ready():
    print(f"Bot online come {bot.user} (ID: {bot.user.id})")
    await load_config_from_discord()
    try:
        synced = await bot.tree.sync()
        print(f"Comandi Slash sincronizzati: {len(synced)}")
    except Exception as e:
        print(f"Errore nella sincronizzazione dei comandi: {e}")


# ==========================================
# 🎨 FUNZIONE DI INVIO LOG SPECIFICO
# ==========================================

async def send_typed_log(guild: discord.Guild, log_type: str, embed: discord.Embed):
    log_channels_dict = config_data.get("log_channels", {})
    # Cerca il canale specifico; se non è impostato, ripiega sul canale server o di sicurezza
    channel_id = log_channels_dict.get(log_type) or log_channels_dict.get("security" if log_type == "security" else "server")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass


# ==========================================
# 🌐 WEB DASHBOARD INTEGRATA (HTML + HTTP SERVER)
# ==========================================

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            sec = config_data["security"]
            log_c = config_data["log_channels"]
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="it">
            <head>
                <meta charset="UTF-8">
                <title>Bot Security & Logs Dashboard</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
                    .container {{ max-width: 900px; margin: auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }}
                    h1 {{ color: #38bdf8; text-align: center; margin-bottom: 30px; }}
                    .section {{ margin-bottom: 25px; padding: 20px; background: #0f172a; border-radius: 8px; border: 1px solid #334155; }}
                    h3 {{ margin-top: 0; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
                    label {{ display: block; margin: 10px 0; font-size: 14px; cursor: pointer; }}
                    input[type="text"], select {{ width: 100%; padding: 10px; margin-top: 5px; background: #1e293b; border: 1px solid #475569; color: white; border-radius: 6px; box-sizing: border-box; }}
                    button {{ background: #0284c7; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; transition: background 0.2s; }}
                    button:hover {{ background: #0369a1; }}
                    .rule-box {{ background: #1e293b; padding: 15px; border-radius: 6px; margin-top: 15px; border: 1px solid #475569; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🛡️ Gestione Bot Security & Logs</h1>
                    <form method="POST" action="/update">
                        
                        <!-- REGOLA ANTI-LINK -->
                        <div class="section">
                            <h3>🔗 Regola Anti-Link</h3>
                            <label><input type="checkbox" name="al_enabled" {"checked" if sec["anti_link"]["enabled"] else ""}> Abilita Anti-Link</label>
                            <div class="rule-box">
                                <label>Conseguenza della violazione:
                                    <select name="al_action">
                                        <option value="delete" {"selected" if sec["anti_link"]["action"]=="delete" else ""}>Solo Elimina</option>
                                        <option value="timeout" {"selected" if sec["anti_link"]["action"]=="timeout" else ""}>Timeout (Silenzio)</option>
                                        <option value="kick" {"selected" if sec["anti_link"]["action"]=="kick" else ""}>Espelli (Kick)</option>
                                        <option value="ban" {"selected" if sec["anti_link"]["action"]=="ban" else ""}>Banna</option>
                                    </select>
                                </label>
                                <label>Durata Timeout (Minuti): <input type="text" name="al_time" value="{sec["anti_link"]["timeout_minutes"]}"></label>
                                <label>Whitelist ID Utenti (separati da virgola): <input type="text" name="al_w_users" value="{",".join(map(str, sec["anti_link"]["whitelist_users"]))}"></label>
                                <label>Whitelist ID Ruoli (separati da virgola): <input type="text" name="al_w_roles" value="{",".join(map(str, sec["anti_link"]["whitelist_roles"]))}"></label>
                            </div>
                        </div>

                        <!-- REGOLA ANTI-INVITE -->
                        <div class="section">
                            <h3>📨 Regola Anti-Invite</h3>
                            <label><input type="checkbox" name="ai_enabled" {"checked" if sec["anti_invite"]["enabled"] else ""}> Abilita Anti-Invite</label>
                            <div class="rule-box">
                                <label>Conseguenza della violazione:
                                    <select name="ai_action">
                                        <option value="delete" {"selected" if sec["anti_invite"]["action"]=="delete" else ""}>Solo Elimina</option>
                                        <option value="timeout" {"selected" if sec["anti_invite"]["action"]=="timeout" else ""}>Timeout (Silenzio)</option>
                                        <option value="kick" {"selected" if sec["anti_invite"]["action"]=="kick" else ""}>Espelli (Kick)</option>
                                        <option value="ban" {"selected" if sec["anti_invite"]["action"]=="ban" else ""}>Banna</option>
                                    </select>
                                </label>
                                <label>Durata Timeout (Minuti): <input type="text" name="ai_time" value="{sec["anti_invite"]["timeout_minutes"]}"></label>
                                <label>Whitelist ID Utenti (separati da virgola): <input type="text" name="ai_w_users" value="{",".join(map(str, sec["anti_invite"]["whitelist_users"]))}"></label>
                                <label>Whitelist ID Ruoli (separati da virgola): <input type="text" name="ai_w_roles" value="{",".join(map(str, sec["anti_invite"]["whitelist_roles"]))}"></label>
                            </div>
                        </div>

                        <!-- REGOLA ANTI-SPAM -->
                        <div class="section">
                            <h3>⚡ Regola Anti-Spam</h3>
                            <label><input type="checkbox" name="as_enabled" {"checked" if sec["anti_spam"]["enabled"] else ""}> Abilita Anti-Spam</label>
                            <div class="rule-box">
                                <label>Conseguenza della violazione:
                                    <select name="as_action">
                                        <option value="delete" {"selected" if sec["anti_spam"]["action"]=="delete" else ""}>Solo Elimina</option>
                                        <option value="timeout" {"selected" if sec["anti_spam"]["action"]=="timeout" else ""}>Timeout (Silenzio)</option>
                                        <option value="kick" {"selected" if sec["anti_spam"]["action"]=="kick" else ""}>Espelli (Kick)</option>
                                        <option value="ban" {"selected" if sec["anti_spam"]["action"]=="ban" else ""}>Banna</option>
                                    </select>
                                </label>
                                <label>Durata Timeout (Minuti): <input type="text" name="as_time" value="{sec["anti_spam"]["timeout_minutes"]}"></label>
                                <label>Whitelist ID Utenti (separati da virgola): <input type="text" name="as_w_users" value="{",".join(map(str, sec["anti_spam"]["whitelist_users"]))}"></label>
                                <label>Whitelist ID Ruoli (separati da virgola): <input type="text" name="as_w_roles" value="{",".join(map(str, sec["anti_spam"]["whitelist_roles"]))}"></label>
                            </div>
                        </div>
                        
                        <!-- CANALI LOG -->
                        <div class="section">
                            <h3>📋 ID Canali Log per Categoria</h3>
                            <label>Messaggi (Eliminati/Modificati):<input type="text" name="log_messages" value="{log_c["messages"] or ""}"></label>
                            <label>Membri (Join/Leave/Ban):<input type="text" name="log_members" value="{log_c["members"] or ""}"></label>
                            <label>Canali (Creati/Eliminati):<input type="text" name="log_channels_cat" value="{log_c["channels"] or ""}"></label>
                            <label>Ruoli (Creati/Eliminati):<input type="text" name="log_roles" value="{log_c["roles"] or ""}"></label>
                            <label>Vocali (Entrate/Spostamenti):<input type="text" name="log_voice" value="{log_c["voice"] or ""}"></label>
                            <label>Server & Altro (Emoji/Inviti):<input type="text" name="log_server" value="{log_c["server"] or ""}"></label>
                            <label>🛡️ Sicurezza (Azioni Anti-Abuso):<input type="text" name="log_security" value="{log_c["security"] or ""}"></label>
                        </div>
                        
                        <button type="submit">Salva e Aggiorna Impostazioni</button>
                    </form>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode("utf-8"))

    def do_POST(self):
        if self.path == "/update":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            params = {}
            for pair in post_data.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = requests_unquote(v)

            def parse_list(val):
                res = []
                for item in val.split(","):
                    item = item.strip()
                    if item.isdigit():
                        res.append(int(item))
                return res

            def parse_int(val, default):
                try:
                    return int(val.strip())
                except:
                    return default

            sec = config_data["security"]

            # Anti-Link
            sec["anti_link"]["enabled"] = "al_enabled" in params
            sec["anti_link"]["action"] = params.get("al_action", "delete")
            sec["anti_link"]["timeout_minutes"] = parse_int(params.get("al_time", "1"), 1)
            sec["anti_link"]["whitelist_users"] = parse_list(params.get("al_w_users", ""))
            sec["anti_link"]["whitelist_roles"] = parse_list(params.get("al_w_roles", ""))

            # Anti-Invite
            sec["anti_invite"]["enabled"] = "ai_enabled" in params
            sec["anti_invite"]["action"] = params.get("ai_action", "timeout")
            sec["anti_invite"]["timeout_minutes"] = parse_int(params.get("ai_time", "5"), 5)
            sec["anti_invite"]["whitelist_users"] = parse_list(params.get("ai_w_users", ""))
            sec["anti_invite"]["whitelist_roles"] = parse_list(params.get("ai_w_roles", ""))

            # Anti-Spam
            sec["anti_spam"]["enabled"] = "as_enabled" in params
            sec["anti_spam"]["action"] = params.get("as_action", "timeout")
            sec["anti_spam"]["timeout_minutes"] = parse_int(params.get("as_time", "1"), 1)
            sec["anti_spam"]["whitelist_users"] = parse_list(params.get("as_w_users", ""))
            sec["anti_spam"]["whitelist_roles"] = parse_list(params.get("as_w_roles", ""))

            def parse_id(val):
                try:
                    return int(val.strip()) if val.strip() != "" else None
                except:
                    return None

            config_data["log_channels"]["messages"] = parse_id(params.get("log_messages", ""))
            config_data["log_channels"]["members"] = parse_id(params.get("log_members", ""))
            config_data["log_channels"]["channels"] = parse_id(params.get("log_channels_cat", ""))
            config_data["log_channels"]["roles"] = parse_id(params.get("log_roles", ""))
            config_data["log_channels"]["voice"] = parse_id(params.get("log_voice", ""))
            config_data["log_channels"]["server"] = parse_id(params.get("log_server", ""))
            config_data["log_channels"]["security"] = parse_id(params.get("log_security", ""))
            
            asyncio_run_coroutine_threadsafe(save_config_to_discord(), bot.loop)

            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

def requests_unquote(string):
    import urllib.parse
    return urllib.parse.unquote_plus(string)

def run_web_dashboard():
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, DashboardHandler)
    print("🌐 Dashboard Web avviata sulla porta 8080")
    httpd.serve_forever()

def asyncio_run_coroutine_threadsafe(coro, loop):
    future = discord.utils.run_coroutine_threadsafe(coro, loop)
    return future


# ==========================================
# 🛡️ FUNZIONE DI APPLICAZIONE CONSEGUENZE
# ==========================================

async def apply_security_action(message: discord.Message, rule_config: dict, reason_text: str):
    action = rule_config.get("action", "delete")
    minutes = rule_config.get("timeout_minutes", 1)
    
    try:
        await message.delete()
    except Exception:
        pass

    action_taken_desc = "Messaggio eliminato"

    try:
        if action == "timeout":
            until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
            await message.author.timeout(until, reason=reason_text)
            action_taken_desc = f"Timeout di {minutes} minuto/i"
        elif action == "kick":
            await message.guild.kick(message.author, reason=reason_text)
            action_taken_desc = "Utente Espulso (Kick)"
        elif action == "ban":
            await message.guild.ban(message.author, reason=reason_text)
            action_taken_desc = "Utente Bannato"
    except Exception as e:
        action_taken_desc += f" (Errore esecuzione: {e})"

    return action_taken_desc


def is_whitelisted(member: discord.Member, rule_config: dict):
    if member.guild_permissions.administrator:
        return True
    if member.id in rule_config.get("whitelist_users", []):
        return True
    for role in member.roles:
        if role.id in rule_config.get("whitelist_roles", []):
            return True
    return False


# ==========================================
# 🔍 FILTRI DI SICUREZZA IN TEMPO REALE
# ==========================================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        try:
            member = message.guild.get_member(message.author.id) if message.guild else None
            if not member:
                await bot.process_commands(message)
                return
        except:
            await bot.process_commands(message)
            return
    else:
        member = message.author

    content_lower = message.content.lower()
    sec = config_data["security"]

    # 1. Anti-Invite
    if sec["anti_invite"]["enabled"] and ("discord.gg/" in content_lower or "discord.com/invite/" in content_lower):
        if not is_whitelisted(member, sec["anti_invite"]):
            action_desc = await apply_security_action(message, sec["anti_invite"], "Invito Discord non autorizzato")
            
            embed = discord.Embed(title="🛡️ Sicurezza: Invito Bloccato", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Utente", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
            embed.add_field(name="Canale", value=message.channel.mention, inline=False)
            embed.add_field(name="Contenuto", value=message.content, inline=False)
            embed.add_field(name="Conseguenza", value=action_desc, inline=False)
            await send_typed_log(message.guild, "security", embed)
            return

    # 2. Anti-Link
    if sec["anti_link"]["enabled"] and ("http://" in content_lower or "https://" in content_lower):
        if "discord.gg" not in content_lower and "youtube.com" not in content_lower:
            if not is_whitelisted(member, sec["anti_link"]):
                action_desc = await apply_security_action(message, sec["anti_link"], "Link esterno non consentito")
                
                embed = discord.Embed(title="🛡️ Sicurezza: Link Bloccato", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Utente", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
                embed.add_field(name="Canale", value=message.channel.mention, inline=False)
                embed.add_field(name="Link", value=message.content, inline=False)
                embed.add_field(name="Conseguenza", value=action_desc, inline=False)
                await send_typed_log(message.guild, "security", embed)
                return

    # 3. Anti-Spam
    if sec["anti_spam"]["enabled"]:
        if not is_whitelisted(member, sec["anti_spam"]):
            user_id = message.author.id
            now = time.time()
            spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 4]
            spam_tracker[user_id].append(now)

            if len(spam_tracker[user_id]) > 5:
                action_desc = await apply_security_action(message, sec["anti_spam"], "Spam rapido rilevato")
                
                embed = discord.Embed(title="🛡️ Sicurezza: Spam Rilevato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Utente", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
                embed.add_field(name="Conseguenza", value=action_desc, inline=False)
                await send_typed_log(message.guild, "security", embed)
                return

    await bot.process_commands(message)


# ==========================================
# 📊 EVENTI LOG ESTETICI E COMPLETI
# ==========================================

@bot.event
async def on_message_delete(message: discord.Message):
    if not message.guild or message.author.bot:
        return
    embed = discord.Embed(title="🗑️ Messaggio Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Autore", value=f"{message.author} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Canale", value=message.channel.mention, inline=True)
    embed.add_field(name="Contenuto", value=message.content or "*[Nessun testo / Solo allegati]*", inline=False)
    await send_typed_log(message.guild, "messages", embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if not before.guild or before.author.bot or before.content == after.content:
        return
    embed = discord.Embed(title="✏️ Messaggio Modificato", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Autore", value=f"{before.author} (`{before.author.id}`)", inline=True)
    embed.add_field(name="Canale", value=before.channel.mention, inline=True)
    embed.add_field(name="Prima", value=before.content or "*[Vuoto]*", inline=False)
    embed.add_field(name="Dopo", value=after.content or "*[Vuoto]*", inline=False)
    await send_typed_log(before.guild, "messages", embed)

@bot.event
async def on_member_join(member: discord.Member):
    embed = discord.Embed(title="📥 Nuovo Utente Entrato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utente", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Account Creato il", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=False)
    await send_typed_log(member.guild, "members", embed)

@bot.event
async def on_member_remove(member: discord.Member):
    embed = discord.Embed(title="📤 Utente Uscito / Bannato", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utente", value=f"{member} (`{member.id}`)", inline=False)
    await send_typed_log(member.guild, "members", embed)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    embed = discord.Embed(title="🔨 Utente Bannato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Utente", value=f"{user} (`{user.id}`)", inline=False)
    await send_typed_log(guild, "members", embed)

@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    embed = discord.Embed(title="🔓 Utente Sbobannato", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Utente", value=f"{user} (`{user.id}`)", inline=False)
    await send_typed_log(guild, "members", embed)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.timed_out_until != after.timed_out_until:
        embed = discord.Embed(title="⏳ Timeout Utente Modificato", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Utente", value=f"{after} (`{after.id}`)", inline=False)
        if after.timed_out_until:
            embed.add_field(name="Stato", value=f"Mutato fino a {after.timed_out_until}", inline=False)
        else:
            embed.add_field(name="Stato", value="Timeout rimosso", inline=False)
        await send_typed_log(after.guild, "members", embed)

@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    embed = discord.Embed(title="📁 Canale Creato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=channel.name, inline=True)
    embed.add_field(name="Tipo", value=str(channel.type), inline=True)
    await send_typed_log(channel.guild, "channels", embed)

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    embed = discord.Embed(title="❌ Canale Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=channel.name, inline=True)
    await send_typed_log(channel.guild, "channels", embed)

@bot.event
async def on_guild_role_create(role: discord.Role):
    embed = discord.Embed(title="🏷️ Ruolo Creato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=role.name, inline=True)
    await send_typed_log(role.guild, "roles", embed)

@bot.event
async def on_guild_role_delete(role: discord.Role):
    embed = discord.Embed(title="🗑️ Ruolo Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=role.name, inline=True)
    await send_typed_log(role.guild, "roles", embed)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if before.channel == after.channel:
        return
    embed = discord.Embed(title="🔊 Attività Vocale", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Utente", value=f"{member} (`{member.id}`)", inline=False)
    if before.channel is None and after.channel is not None:
        embed.add_field(name="Azione", value=f"Entrato in {after.channel.mention}", inline=False)
    elif before.channel is not None and after.channel is None:
        embed.add_field(name="Azione", value=f"Uscito da {before.channel.mention}", inline=False)
    elif before.channel is not None and after.channel is not None:
        embed.add_field(name="Azione", value=f"Spostato da {before.channel.mention} a {after.channel.mention}", inline=False)
    await send_typed_log(member.guild, "voice", embed)


if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web_dashboard, daemon=True)
    web_thread.start()
    bot.run(TOKEN)
