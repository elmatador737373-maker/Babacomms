import discord
from discord.ext import commands
import os
import json
import io
import time
from collections import defaultdict
from flask import Flask, render_template_string, request, redirect, url_for
import threading
import logging

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

# Configurazione globale (salvata e sincronizzata via Cloud Discord su server secondario)
config_data = {
    "security": {
        "anti_link": {
            "enabled": True,
            "action": "delete",
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
        },
        "anti_bot_add": {
            "enabled": True,
            "action": "kick",
            "whitelist_users": []
        },
        "anti_role_create": {
            "enabled": True,
            "action": "delete",
            "whitelist_users": [],
            "whitelist_roles": []
        },
        "anti_role_delete": {
            "enabled": True,
            "action": "kick",
            "whitelist_users": [],
            "whitelist_roles": []
        },
        "anti_dangerous_role": {
            "enabled": True,
            "action": "remove_perms",
            "whitelist_users": [],
            "whitelist_roles": []
        },
        "anti_channel_create": {
            "enabled": True,
            "action": "delete",
            "whitelist_users": [],
            "whitelist_roles": []
        },
        "anti_channel_delete": {
            "enabled": True,
            "action": "kick",
            "whitelist_users": [],
            "whitelist_roles": []
        }
    },
    "log_channels": {
        "messages": None,
        "members": None,
        "channels": None,
        "roles": None,
        "voice": None,
        "server": None,
        "security": None
    }
}

spam_tracker = defaultdict(list)


# ==========================================
# ☁️ GESTIONE CONFIGURAZIONI NEL CLOUD (SERVER SECONDARIO)
# ==========================================

async def load_config_from_discord():
    global config_data
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        print("[AVVISO] Canale Cloud JSON (sul server secondario) non trovato. Uso i valori predefiniti.")
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
                        print("⚙️ Configurazioni caricate con successo dal server secondario.")
                        return
    except Exception as e:
        print(f"[ERRORE CARICAMENTO CONFIG DA ALTRO SERVER]: {e}")

async def save_config_to_discord():
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        print("[ERRORE] Impossibile salvare: Canale Cloud JSON non trovato.")
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
        await channel.send("⚙️ **Aggiornamento Configurazioni Bot & Log (Server Secondario):**", file=discord_file)
        print("⚙️ Configurazioni salvate con successo sul server secondario.")
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO CONFIG SU ALTRO SERVER]: {e}")


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
# 🌐 FLASK WEB DASHBOARD (CON NOMI CANALI)
# ==========================================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Bot Security & Logs Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
        .container { max-width: 950px; margin: auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 25px; padding: 20px; background: #0f172a; border-radius: 8px; border: 1px solid #334155; }
        h3 { margin-top: 0; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        label { display: block; margin: 10px 0; font-size: 14px; cursor: pointer; }
        input[type="text"], select { width: 100%; padding: 10px; margin-top: 5px; background: #1e293b; border: 1px solid #475569; color: white; border-radius: 6px; box-sizing: border-box; }
        button { background: #0284c7; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; transition: background 0.2s; }
        button:hover { background: #0369a1; }
        .rule-box { background: #1e293b; padding: 15px; border-radius: 6px; margin-top: 15px; border: 1px solid #475569; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Gestione Bot Security & Logs</h1>
        <form method="POST" action="/update">
            
            <div class="section">
                <h3>🔗 Anti-Link</h3>
                <label><input type="checkbox" name="al_enabled" {% if sec.anti_link.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="al_action">
                            <option value="delete" {% if sec.anti_link.action == "delete" %}selected{% endif %}>Solo Elimina</option>
                            <option value="timeout" {% if sec.anti_link.action == "timeout" %}selected{% endif %}>Timeout</option>
                            <option value="kick" {% if sec.anti_link.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_link.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Durata Timeout (Min): <input type="text" name="al_time" value="{{ sec.anti_link.timeout_minutes }}"></label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="al_w_users" value="{{ ','.join(sec.anti_link.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="al_w_roles" value="{{ ','.join(sec.anti_link.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>📨 Anti-Invite</h3>
                <label><input type="checkbox" name="ai_enabled" {% if sec.anti_invite.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="ai_action">
                            <option value="delete" {% if sec.anti_invite.action == "delete" %}selected{% endif %}>Solo Elimina</option>
                            <option value="timeout" {% if sec.anti_invite.action == "timeout" %}selected{% endif %}>Timeout</option>
                            <option value="kick" {% if sec.anti_invite.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_invite.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Durata Timeout (Min): <input type="text" name="ai_time" value="{{ sec.anti_invite.timeout_minutes }}"></label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="ai_w_users" value="{{ ','.join(sec.anti_invite.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="ai_w_roles" value="{{ ','.join(sec.anti_invite.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>⚡ Anti-Spam</h3>
                <label><input type="checkbox" name="as_enabled" {% if sec.anti_spam.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="as_action">
                            <option value="delete" {% if sec.anti_spam.action == "delete" %}selected{% endif %}>Solo Elimina</option>
                            <option value="timeout" {% if sec.anti_spam.action == "timeout" %}selected{% endif %}>Timeout</option>
                            <option value="kick" {% if sec.anti_spam.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_spam.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Durata Timeout (Min): <input type="text" name="as_time" value="{{ sec.anti_spam.timeout_minutes }}"></label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="as_w_users" value="{{ ','.join(sec.anti_spam.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="as_w_roles" value="{{ ','.join(sec.anti_spam.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>🤖 Anti-Bot Add</h3>
                <label><input type="checkbox" name="aba_enabled" {% if sec.anti_bot_add.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="aba_action">
                            <option value="kick" {% if sec.anti_bot_add.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_bot_add.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Whitelist ID Utenti autorizzati (virgola): <input type="text" name="aba_w_users" value="{{ ','.join(sec.anti_bot_add.whitelist_users|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>🏷️ Anti-Role Create</h3>
                <label><input type="checkbox" name="arc_enabled" {% if sec.anti_role_create.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="arc_action">
                            <option value="delete" {% if sec.anti_role_create.action == "delete" %}selected{% endif %}>Elimina Ruolo</option>
                            <option value="kick" {% if sec.anti_role_create.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_role_create.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="arc_w_users" value="{{ ','.join(sec.anti_role_create.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="arc_w_roles" value="{{ ','.join(sec.anti_role_create.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>🗑️ Anti-Role Delete</h3>
                <label><input type="checkbox" name="ard_enabled" {% if sec.anti_role_delete.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="ard_action">
                            <option value="kick" {% if sec.anti_role_delete.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_role_delete.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="ard_w_users" value="{{ ','.join(sec.anti_role_delete.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="ard_w_roles" value="{{ ','.join(sec.anti_role_delete.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>⚠️ Anti-Dangerous Role</h3>
                <label><input type="checkbox" name="adr_enabled" {% if sec.anti_dangerous_role.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="adr_action">
                            <option value="remove_perms" {% if sec.anti_dangerous_role.action == "remove_perms" %}selected{% endif %}>Rimuovi Permessi</option>
                            <option value="kick" {% if sec.anti_dangerous_role.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_dangerous_role.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="adr_w_users" value="{{ ','.join(sec.anti_dangerous_role.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="adr_w_roles" value="{{ ','.join(sec.anti_dangerous_role.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>📁 Anti-Channel Create</h3>
                <label><input type="checkbox" name="acc_enabled" {% if sec.anti_channel_create.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="acc_action">
                            <option value="delete" {% if sec.anti_channel_create.action == "delete" %}selected{% endif %}>Elimina Canale</option>
                            <option value="kick" {% if sec.anti_channel_create.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_channel_create.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="acc_w_users" value="{{ ','.join(sec.anti_channel_create.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="acc_w_roles" value="{{ ','.join(sec.anti_channel_create.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>

            <div class="section">
                <h3>❌ Anti-Channel Delete</h3>
                <label><input type="checkbox" name="acd_enabled" {% if sec.anti_channel_delete.enabled %}checked{% endif %}> Abilita</label>
                <div class="rule-box">
                    <label>Conseguenza:
                        <select name="acd_action">
                            <option value="kick" {% if sec.anti_channel_delete.action == "kick" %}selected{% endif %}>Kick</option>
                            <option value="ban" {% if sec.anti_channel_delete.action == "ban" %}selected{% endif %}>Ban</option>
                        </select>
                    </label>
                    <label>Whitelist ID Utenti (virgola): <input type="text" name="acd_w_users" value="{{ ','.join(sec.anti_channel_delete.whitelist_users|map('string')) }}"></label>
                    <label>Whitelist ID Ruoli (virgola): <input type="text" name="acd_w_roles" value="{{ ','.join(sec.anti_channel_delete.whitelist_roles|map('string')) }}"></label>
                </div>
            </div>
            
            <div class="section">
                <h3>📋 Canali Log per Categoria</h3>
                
                <label>Messaggi:
                    <select name="log_messages">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.messages == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>

                <label>Membri:
                    <select name="log_members">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.members == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>

                <label>Canali:
                    <select name="log_channels_cat">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.channels == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>

                <label>Ruoli:
                    <select name="log_roles">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.roles == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>

                <label>Vocali:
                    <select name="log_voice">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.voice == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>

                <label>Server & Altro:
                    <select name="log_server">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.server == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>

                <label>🛡️ Sicurezza:
                    <select name="log_security">
                        <option value="">-- Disabilitato --</option>
                        {% for ch in channels %}
                            <option value="{{ ch.id }}" {% if log_c.security == ch.id %}selected{% endif %}>#{{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </label>
            </div>
            
            <button type="submit">Salva e Aggiorna Impostazioni</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/")
def dashboard_index():
    class SafeAccess(dict):
        def __getattr__(self, item):
            val = self.get(item)
            return SafeAccess(val) if isinstance(val, dict) else val

    sec_safe = SafeAccess(config_data["security"])
    log_safe = SafeAccess(config_data["log_channels"])
    
    # Raccoglie la lista di tutti i canali testuali da tutti i server in cui si trova il bot
    all_channels = []
    for guild in bot.guilds:
        for ch in guild.text_channels:
            all_channels.append({"id": ch.id, "name": f"{guild.name} / #{ch.name}"})

    return render_template_string(DASHBOARD_HTML, sec=sec_safe, log_c=log_safe, channels=all_channels)

@app.route("/update", methods=["POST"])
def dashboard_update():
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

    sec["anti_link"]["enabled"] = "al_enabled" in request.form
    sec["anti_link"]["action"] = request.form.get("al_action", "delete")
    sec["anti_link"]["timeout_minutes"] = parse_int(request.form.get("al_time", "1"), 1)
    sec["anti_link"]["whitelist_users"] = parse_list(request.form.get("al_w_users", ""))
    sec["anti_link"]["whitelist_roles"] = parse_list(request.form.get("al_w_roles", ""))

    sec["anti_invite"]["enabled"] = "ai_enabled" in request.form
    sec["anti_invite"]["action"] = request.form.get("ai_action", "timeout")
    sec["anti_invite"]["timeout_minutes"] = parse_int(request.form.get("ai_time", "5"), 5)
    sec["anti_invite"]["whitelist_users"] = parse_list(request.form.get("ai_w_users", ""))
    sec["anti_invite"]["whitelist_roles"] = parse_list(request.form.get("ai_w_roles", ""))

    sec["anti_spam"]["enabled"] = "as_enabled" in request.form
    sec["anti_spam"]["action"] = request.form.get("as_action", "timeout")
    sec["anti_spam"]["timeout_minutes"] = parse_int(request.form.get("as_time", "1"), 1)
    sec["anti_spam"]["whitelist_users"] = parse_list(request.form.get("as_w_users", ""))
    sec["anti_spam"]["whitelist_roles"] = parse_list(request.form.get("as_w_roles", ""))

    sec["anti_bot_add"]["enabled"] = "aba_enabled" in request.form
    sec["anti_bot_add"]["action"] = request.form.get("aba_action", "kick")
    sec["anti_bot_add"]["whitelist_users"] = parse_list(request.form.get("aba_w_users", ""))

    sec["anti_role_create"]["enabled"] = "arc_enabled" in request.form
    sec["anti_role_create"]["action"] = request.form.get("arc_action", "delete")
    sec["anti_role_create"]["whitelist_users"] = parse_list(request.form.get("arc_w_users", ""))
    sec["anti_role_create"]["whitelist_roles"] = parse_list(request.form.get("arc_w_roles", ""))

    sec["anti_role_delete"]["enabled"] = "ard_enabled" in request.form
    sec["anti_role_delete"]["action"] = request.form.get("ard_action", "kick")
    sec["anti_role_delete"]["whitelist_users"] = parse_list(request.form.get("ard_w_users", ""))
    sec["anti_role_delete"]["whitelist_roles"] = parse_list(request.form.get("ard_w_roles", ""))

    sec["anti_dangerous_role"]["enabled"] = "adr_enabled" in request.form
    sec["anti_dangerous_role"]["action"] = request.form.get("adr_action", "remove_perms")
    sec["anti_dangerous_role"]["whitelist_users"] = parse_list(request.form.get("adr_w_users", ""))
    sec["anti_dangerous_role"]["whitelist_roles"] = parse_list(request.form.get("adr_w_roles", ""))

    sec["anti_channel_create"]["enabled"] = "acc_enabled" in request.form
    sec["anti_channel_create"]["action"] = request.form.get("acc_action", "delete")
    sec["anti_channel_create"]["whitelist_users"] = parse_list(request.form.get("acc_w_users", ""))
    sec["anti_channel_create"]["whitelist_roles"] = parse_list(request.form.get("acc_w_roles", ""))

    sec["anti_channel_delete"]["enabled"] = "acd_enabled" in request.form
    sec["anti_channel_delete"]["action"] = request.form.get("acd_action", "kick")
    sec["anti_channel_delete"]["whitelist_users"] = parse_list(request.form.get("acd_w_users", ""))
    sec["anti_channel_delete"]["whitelist_roles"] = parse_list(request.form.get("acd_w_roles", ""))

    def parse_id(val):
        try:
            return int(val.strip()) if val.strip() != "" else None
        except:
            return None

    config_data["log_channels"]["messages"] = parse_id(request.form.get("log_messages", ""))
    config_data["log_channels"]["members"] = parse_id(request.form.get("log_members", ""))
    config_data["log_channels"]["channels"] = parse_id(request.form.get("log_channels_cat", ""))
    config_data["log_channels"]["roles"] = parse_id(request.form.get("log_roles", ""))
    config_data["log_channels"]["voice"] = parse_id(request.form.get("log_voice", ""))
    config_data["log_channels"]["server"] = parse_id(request.form.get("log_server", ""))
    config_data["log_channels"]["security"] = parse_id(request.form.get("log_security", ""))
    
    discord.utils.run_coroutine_threadsafe(save_config_to_discord(), bot.loop)

    return redirect(url_for('dashboard_index'))

def run_web_dashboard():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)


# ==========================================
# 🛡️ FUNZIONI DI UTILITÀ PER LA SICUREZZA
# ==========================================

def is_whitelisted(member: discord.Member, rule_config: dict):
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True
    if member.id in rule_config.get("whitelist_users", []):
        return True
    for role in member.roles:
        if role.id in rule_config.get("whitelist_roles", []):
            return True
    return False

async def apply_generic_action(guild: discord.Guild, member: discord.Member, action: str, reason: str):
    if not member or member.guild_permissions.administrator:
        return "Nessuna azione (Utente amministratore o non trovato)"
    try:
        if action == "kick":
            await guild.kick(member, reason=reason)
            return "Utente espulso (Kick)"
        elif action == "ban":
            await guild.ban(member, reason=reason)
            return "Utente bannato (Ban)"
    except Exception as e:
        return f"Errore esecuzione azione: {e}"
    return "Nessuna azione eseguita"


# ==========================================
# 🔍 FILTRI DI SICUREZZA IN TEMPO REALE
# ==========================================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    member = message.author
    content_lower = message.content.lower()
    sec = config_data["security"]

    # 1. Anti-Invite
    if sec["anti_invite"]["enabled"] and ("discord.gg/" in content_lower or "discord.com/invite/" in content_lower):
        if not is_whitelisted(member, sec["anti_invite"]):
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
                action_desc = f"Timeout ({minutes} min)"
            elif action in ["kick", "ban"]:
                action_desc = await apply_generic_action(message.guild, member, action, "Invito Discord non autorizzato")

            embed = discord.Embed(title="🛡️ Sicurezza: Invito Bloccato", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Utente", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed.add_field(name="Canale", value=message.channel.mention, inline=False)
            embed.add_field(name="Conseguenza", value=action_desc, inline=False)
            await send_typed_log(message.guild, "security", embed)
            return

    # 2. Anti-Link
    if sec["anti_link"]["enabled"] and ("http://" in content_lower or "https://" in content_lower):
        if "discord.gg" not in content_lower and "youtube.com" not in content_lower:
            if not is_whitelisted(member, sec["anti_link"]):
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
                    action_desc = f"Timeout ({minutes} min)"
                elif action in ["kick", "ban"]:
                    action_desc = await apply_generic_action(message.guild, member, action, "Link esterno non consentito")

                embed = discord.Embed(title="🛡️ Sicurezza: Link Bloccato", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Utente", value=f"{member.mention} (`{member.id}`)", inline=False)
                embed.add_field(name="Canale", value=message.channel.mention, inline=False)
                embed.add_field(name="Conseguenza", value=action_desc, inline=False)
                await send_typed_log(message.guild, "security", embed)
                return

    # 3. Anti-Spam
    if sec["anti_spam"]["enabled"]:
        if not is_whitelisted(member, sec["anti_spam"]):
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
                    action_desc = f"Timeout ({minutes} min)"
                elif action in ["kick", "ban"]:
                    action_desc = await apply_generic_action(message.guild, member, action, "Spam rapido rilevato")

                embed = discord.Embed(title="🛡️ Sicurezza: Spam Rilevato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Utente", value=f"{member.mention} (`{member.id}`)", inline=False)
                embed.add_field(name="Conseguenza", value=action_desc, inline=False)
                await send_typed_log(message.guild, "security", embed)
                return

    await bot.process_commands(message)


# ==========================================
# 🤖 ANTI-BOT ADD
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        sec = config_data["security"]["anti_bot_add"]
        if sec["enabled"]:
            guild = member.guild
            adder = None
            try:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
                    if entry.target.id == member.id:
                        adder = entry.user
                        break
            except:
                pass

            if adder and not (adder.guild_permissions.administrator or adder.id in sec["whitelist_users"]):
                action = sec.get("action", "kick")
                action_desc = await apply_generic_action(guild, adder, action, "Aggiunta bot non autorizzata")
                try:
                    await member.kick(reason="Bot aggiunto senza autorizzazione")
                except:
                    pass

                embed = discord.Embed(title="🛡️ Sicurezza: Bot Non Autorizzato Rilevato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Bot", value=f"{member} (`{member.id}`)", inline=False)
                embed.add_field(name="Aggiunto da", value=f"{adder.mention} (`{adder.id}`)", inline=False)
                embed.add_field(name="Conseguenza", value=action_desc, inline=False)
                await send_typed_log(guild, "security", embed)
                return

    embed = discord.Embed(title="📥 Nuovo Utente Entrato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utente", value=f"{member} (`{member.id}`)", inline=False)
    await send_typed_log(member.guild, "members", embed)


# ==========================================
# 🏷️ ANTI-ROLE CREATE & DANGEROUS ROLE
# ==========================================
@bot.event
async def on_guild_role_create(role: discord.Role):
    guild = role.guild
    sec_create = config_data["security"]["anti_role_create"]
    sec_danger = config_data["security"]["anti_dangerous_role"]

    creator = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.role_create):
            if entry.target.id == role.id:
                creator = entry.user
                break
    except:
        pass

    if sec_create["enabled"] and creator:
        if not is_whitelisted(creator, sec_create):
            action = sec_create.get("action", "delete")
            action_desc = "Ruolo eliminato"
            try:
                if action == "delete":
                    await role.delete(reason="Anti-Role Create attivo")
                else:
                    action_desc = await apply_generic_action(guild, creator, action, "Creazione ruolo non autorizzata")
                    await role.delete(reason="Creazione non autorizzata")
            except Exception as e:
                action_desc += f" (Errore: {e})"

            embed = discord.Embed(title="🛡️ Sicurezza: Creazione Ruolo Bloccata", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Creatore", value=f"{creator.mention} (`{creator.id}`)", inline=False)
            embed.add_field(name="Ruolo", value=role.name, inline=False)
            embed.add_field(name="Conseguenza", value=action_desc, inline=False)
            await send_typed_log(guild, "security", embed)
            return

    if sec_danger["enabled"] and creator:
        if role.permissions.administrator or role.permissions.ban_members or role.permissions.kick_members:
            if not is_whitelisted(creator, sec_danger):
                action = sec_danger.get("action", "remove_perms")
                action_desc = "Permessi pericolosi rimossi / Ruolo eliminato"
                try:
                    if action == "remove_perms":
                        await role.edit(permissions=discord.Permissions.none(), reason="Anti-Dangerous Role: permessi pericolosi bloccati")
                    elif action in ["kick", "ban"]:
                        action_desc = await apply_generic_action(guild, creator, action, "Creazione ruolo con permessi pericolosi")
                        await role.delete(reason="Ruolo pericoloso eliminato")
                except Exception as e:
                    action_desc += f" (Errore: {e})"

                embed = discord.Embed(title="🛡️ Sicurezza: Ruolo Pericoloso Bloccato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Creatore", value=f"{creator.mention} (`{creator.id}`)", inline=False)
                embed.add_field(name="Ruolo", value=role.name, inline=False)
                embed.add_field(name="Conseguenza", value=action_desc, inline=False)
                await send_typed_log(guild, "security", embed)
                return

    embed = discord.Embed(title="🏷️ Ruolo Creato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=role.name, inline=True)
    await send_typed_log(guild, "roles", embed)


# ==========================================
# 🗑️ ANTI-ROLE DELETE
# ==========================================
@bot.event
async def on_guild_role_delete(role: discord.Role):
    guild = role.guild
    sec = config_data["security"]["anti_role_delete"]
    if not sec["enabled"]:
        embed = discord.Embed(title="🗑️ Ruolo Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Nome", value=role.name, inline=True)
        await send_typed_log(guild, "roles", embed)
        return

    deleter = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                deleter = entry.user
                break
    except:
        pass

    if deleter and not is_whitelisted(deleter, sec):
        action = sec.get("action", "kick")
        action_desc = await apply_generic_action(guild, deleter, action, "Eliminazione ruolo non autorizzata")

        embed = discord.Embed(title="🛡️ Sicurezza: Eliminazione Ruolo Bloccata", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Autore", value=f"{deleter.mention} (`{deleter.id}`)", inline=False)
        embed.add_field(name="Ruolo Eliminato", value=role.name, inline=False)
        embed.add_field(name="Conseguenza", value=action_desc, inline=False)
        await send_typed_log(guild, "security", embed)
        return

    embed = discord.Embed(title="🗑️ Ruolo Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=role.name, inline=True)
    await send_typed_log(guild, "roles", embed)


# ==========================================
# 📁 ANTI-CHANNEL CREATE
# ==========================================
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    guild = channel.guild
    sec = config_data["security"]["anti_channel_create"]
    if not sec["enabled"]:
        embed = discord.Embed(title="📁 Canale Creato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Nome", value=channel.name, inline=True)
        await send_typed_log(guild, "channels", embed)
        return

    creator = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                creator = entry.user
                break
    except:
        pass

    if creator and not is_whitelisted(creator, sec):
        action = sec.get("action", "delete")
        action_desc = "Canale eliminato"
        try:
            if action == "delete":
                await channel.delete(reason="Anti-Channel Create attivo")
            else:
                action_desc = await apply_generic_action(guild, creator, action, "Creazione canale non autorizzata")
                await channel.delete(reason="Creazione non autorizzata")
        except Exception as e:
            action_desc += f" (Errore: {e})"

        embed = discord.Embed(title="🛡️ Sicurezza: Creazione Canale Bloccata", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Creatore", value=f"{creator.mention} (`{creator.id}`)", inline=False)
        embed.add_field(name="Canale", value=channel.name, inline=False)
        embed.add_field(name="Conseguenza", value=action_desc, inline=False)
        await send_typed_log(guild, "security", embed)
        return

    embed = discord.Embed(title="📁 Canale Creato", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=channel.name, inline=True)
    await send_typed_log(guild, "channels", embed)


# ==========================================
# ❌ ANTI-CHANNEL DELETE
# ==========================================
@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    sec = config_data["security"]["anti_channel_delete"]
    if not sec["enabled"]:
        embed = discord.Embed(title="❌ Canale Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Nome", value=channel.name, inline=True)
        await send_typed_log(guild, "channels", embed)
        return

    deleter = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                break
    except:
        pass

    if deleter and not is_whitelisted(deleter, sec):
        action = sec.get("action", "kick")
        action_desc = await apply_generic_action(guild, deleter, action, "Eliminazione canale non autorizzata")

        embed = discord.Embed(title="🛡️ Sicurezza: Eliminazione Canale Bloccata", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Autore", value=f"{deleter.mention} (`{deleter.id}`)", inline=False)
        embed.add_field(name="Canale Eliminato", value=channel.name, inline=False)
        embed.add_field(name="Conseguenza", value=action_desc, inline=False)
        await send_typed_log(guild, "security", embed)
        return

    embed = discord.Embed(title="❌ Canale Eliminato", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome", value=channel.name, inline=True)
    await send_typed_log(guild, "channels", embed)


# ==========================================
# 📊 ALTRI EVENTI LOG
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
