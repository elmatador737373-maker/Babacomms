import discord
from discord.ext import commands
import os
import json
import io
import time
from collections import defaultdict

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

# Configurazione globale predefinita
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
# ☁️ GESTIONE CONFIGURAZIONI NEL CLOUD
# ==========================================

async def load_config_from_discord():
    global config_data
    channel = bot.get_channel(CLOUD_JSON_CHANNEL_ID)
    if not channel:
        print("[AVVISO] Canale Cloud JSON (sul server secondario) non trovato.")
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
        print(f"[ERRORE CARICAMENTO CONFIG]: {e}")

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
        await channel.send("⚙️ **Aggiornamento Configurazioni Bot & Log:**", file=discord_file)
        print("⚙️ Configurazioni salvate con successo sul server secondario.")
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO CONFIG]: {e}")


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
# 🎨 INVIO LOG SPECIFICO
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
# 🔒 CONTROLLO PRIVILEGI PROPRIETARIO
# ==========================================

async def is_owner_or_guild_owner(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    is_bot_owner = await bot.is_owner(interaction.user)
    is_server_owner = interaction.user.id == interaction.guild.owner_id
    return is_bot_owner or is_server_owner


# ==========================================
# 🎛️ PANNELLO DI SETTING COMPLETO INTERATTIVO
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
        mod_info = config_data["security"][module_key]
        
        status_str = "✅ Abilitato" if mod_info.get("enabled") else "❌ Disabilitato"
        desc = (
            f"**Modulo Selezionato:** `{module_key.replace('_', ' ').title()}`\n"
            f"**Stato Attuale:** {status_str}\n"
            f"**Azione:** `{mod_info.get('action', 'N/D')}`\n"
        )
        if "timeout_minutes" in mod_info:
            desc += f"**Durata Timeout:** `{mod_info.get('timeout_minutes')} minuti`\n"
            
        embed = discord.Embed(title=f"⚙️ Configurazione: {module_key.replace('_', ' ').title()}", description=desc, color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class ModuleConfigView(discord.ui.View):
    def __init__(self, module_key: str):
        super().__init__(timeout=180)
        self.module_key = module_key

    @discord.ui.button(label="Attiva/Disattiva", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def toggle_enabled(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        curr = config_data["security"][self.module_key].get("enabled", True)
        config_data["security"][self.module_key]["enabled"] = not curr
        discord.utils.run_coroutine_threadsafe(save_config_to_discord(), bot.loop)
        
        await interaction.response.send_message(f"✅ Stato del modulo modificato a: **{'Abilitato' if not curr else 'Disabilitato'}**", ephemeral=True)

    @discord.ui.button(label="Cambia Azione & Parametri", style=discord.ButtonStyle.green, emoji="⚙️")
    async def change_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        modal = ModuleSettingsModal(self.module_key)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⬅️ Torna al Menu", style=discord.ButtonStyle.grey)
    async def back_to_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        embed = discord.Embed(
            title="🎛️ Pannello di Controllo - Security & Logs",
            description="Usa i menu e i pulsanti sottostanti per configurare interamente il bot.",
            color=discord.Color.blurple()
        )
        view = SettingsMainView(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class ModuleSettingsModal(discord.ui.Modal, title="Modifica Parametri Modulo"):
    def __init__(self, module_key: str):
        super().__init__()
        self.module_key = module_key
        
        curr_action = config_data["security"][module_key].get("action", "delete")
        curr_timeout = str(config_data["security"][module_key].get("timeout_minutes", 1))
        
        self.action_input = discord.ui.TextInput(
            label="Azione (delete, timeout, kick, ban, remove_perms)",
            default=curr_action,
            required=True,
            max_length=20
        )
        self.timeout_input = discord.ui.TextInput(
            label="Minuti di Timeout (se applicabile)",
            default=curr_timeout,
            required=False,
            max_length=5
        )
        self.add_item(self.action_input)
        self.add_item(self.timeout_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
            
        new_action = self.action_input.value.strip().lower()
        config_data["security"][self.module_key]["action"] = new_action
        
        if self.timeout_input.value and self.timeout_input.value.isdigit():
            config_data["security"][self.module_key]["timeout_minutes"] = int(self.timeout_input.value.strip())
            
        discord.utils.run_coroutine_threadsafe(save_config_to_discord(), bot.loop)
        await interaction.response.send_message(f"✅ Parametri aggiornati con successo per `{self.module_key}`!", ephemeral=True)


class SettingsMainView(discord.ui.View):
    def __init__(self, inter: discord.Interaction):
        super().__init__(timeout=180)
        self.inter = inter
        self.add_item(ModuleSelect())

    @discord.ui.button(label="Global Whitelist", style=discord.ButtonStyle.success, emoji="🌐", row=1)
    async def global_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GlobalWhitelistModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configura Canali Log", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def log_channels_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LogChannelSelectView()
        embed = discord.Embed(
            title="📋 Seleziona Categoria Log da Configurare",
            description="Scegli dal menu a tendina quale tipo di log desideri associare a un canale.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class GlobalWhitelistModal(discord.ui.Modal, title="Gestione Global Whitelist"):
    target_id = discord.ui.TextInput(
        label="ID Utente o Ruolo da Whitelistare",
        placeholder="Inserisci l'ID numerico esatto...",
        required=True,
        max_length=25
    )
    action_type = discord.ui.TextInput(
        label="Azione (aggiungi / rimuovi)",
        placeholder="Scrivi 'aggiungi' o 'rimuovi'",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi necessari.", ephemeral=True)

        try:
            target_val = int(self.target_id.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ L'ID inserito non è valido.", ephemeral=True)
        
        action = self.action_type.value.strip().lower()
        if action not in ["aggiungi", "rimuovi"]:
            return await interaction.response.send_message("❌ Azione non valida. Scrivi 'aggiungi' o 'rimuovi'.", ephemeral=True)

        is_role = interaction.guild.get_role(target_val) is not None
        
        updated_count = 0
        for module_name, module_config in config_data["security"].items():
            if is_role:
                lst = module_config.setdefault("whitelist_roles", [])
                if action == "aggiungi" and target_val not in lst:
                    lst.append(target_val)
                    updated_count += 1
                elif action == "rimuovi" and target_val in lst:
                    lst.remove(target_val)
                    updated_count += 1
            else:
                lst = module_config.setdefault("whitelist_users", [])
                if action == "aggiungi" and target_val not in lst:
                    lst.append(target_val)
                    updated_count += 1
                elif action == "rimuovi" and target_val in lst:
                    lst.remove(target_val)
                    updated_count += 1

        discord.utils.run_coroutine_threadsafe(save_config_to_discord(), bot.loop)
        
        tipo_str = "Ruolo" if is_role else "Utente"
        await interaction.response.send_message(
            f"✅ Operazione completata! {tipo_str} (`{target_val}`) {'aggiunto a ' + str(updated_count) + ' moduli' if action == 'aggiungi' else 'rimosso da tutti i moduli'}.",
            ephemeral=True
        )


class LogChannelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Messaggi (messages)", value="messages", description="Log eliminazione e modifica messaggi"),
            discord.SelectOption(label="Membri (members)", value="members", description="Log ingressi, uscite, ban e timeout"),
            discord.SelectOption(label="Canali (channels)", value="channels", description="Log creazione e rimozione canali"),
            discord.SelectOption(label="Ruoli (roles)", value="roles", description="Log creazione e rimozione ruoli"),
            discord.SelectOption(label="Vocali (voice)", value="voice", description="Log attività nei canali vocali"),
            discord.SelectOption(label="Server (server)", value="server", description="Log generali di server"),
            discord.SelectOption(label="Sicurezza (security)", value="security", description="Log di tutti i moduli di protezione"),
        ]
        super().__init__(placeholder="Seleziona la categoria di log...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        log_type = self.values[0]
        modal = LogChannelIdModal(log_type)
        await interaction.response.send_modal(modal)


class LogChannelSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(LogChannelSelect())


class LogChannelIdModal(discord.ui.Modal, title="Imposta ID Canale Log"):
    def __init__(self, log_type: str):
        super().__init__()
        self.log_type = log_type
        
        curr_id = config_data["log_channels"].get(log_type, "")
        self.channel_id_input = discord.ui.TextInput(
            label=f"ID del canale per '{log_type}'",
            placeholder="Inserisci l'ID numerico esatto del canale...",
            default=str(curr_id) if curr_id else "",
            required=True,
            max_length=25
        )
        self.add_item(self.channel_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi necessari.", ephemeral=True)
            
        try:
            ch_val = int(self.channel_id_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ ID canale non valido. Deve essere numerico.", ephemeral=True)
            
        config_data["log_channels"][self.log_type] = ch_val
        discord.utils.run_coroutine_threadsafe(save_config_to_discord(), bot.loop)
        await interaction.response.send_message(f"✅ Canale log per `{self.log_type}` impostato con successo su <#{ch_val}>!", ephemeral=True)


@bot.tree.command(name="settings", description="Apre il pannello di controllo completo e interattivo del bot")
async def settings_command(interaction: discord.Interaction):
    if not await is_owner_or_guild_owner(interaction):
        return await interaction.response.send_message("❌ Questo comando può essere eseguito solo dal proprietario del bot o dal proprietario del server.", ephemeral=True)
    
    embed = discord.Embed(
        title="🎛️ Pannello di Controllo - Security & Logs",
        description="Usa il menu a tendina e i pulsanti sottostanti per gestire e configurare interamente ogni modulo di sicurezza, le whitelist e i canali log.",
        color=discord.Color.blurple()
    )
    view = SettingsMainView(interaction)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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
            else:
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
    
    deleter = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                deleter = entry.user
                break
    except:
        pass

    if sec["enabled"] and deleter and not is_whitelisted(deleter, sec):
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
    
    creator = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                creator = entry.user
                break
    except:
        pass

    if sec["enabled"] and creator and not is_whitelisted(creator, sec):
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
    
    deleter = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                break
    except:
        pass

    if sec["enabled"] and deleter and not is_whitelisted(deleter, sec):
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
    bot.run(TOKEN)
