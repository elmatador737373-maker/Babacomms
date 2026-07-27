import discord
from discord.ext import commands
import os
import json
import time
from collections import defaultdict
from supabase import create_client, Client

# ==========================================
# ⚙️ CONFIGURAZIONE INIZIALE & SUPABASE
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") or "IL_TUO_TOKEN_QUI"

SUPABASE_URL = os.getenv("SUPABASE_URL") or "IL_TUO_SUPABASE_URL"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "IL_TUO_SUPABASE_ANON_KEY"

# Inizializzazione client Supabase
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

# Configurazione globale predefinita (usata solo se il database è vuoto)
DEFAULT_CONFIG = {
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

config_data = {}
spam_tracker = defaultdict(list)


# ==========================================
# 🗄️ GESTIONE CONFIGURAZIONI SU SUPABASE
# ==========================================

async def load_config_from_supabase():
    global config_data
    try:
        response = supabase.table("bot_settings").select("*").execute()
        data = response.data
        
        if data and len(data) > 0:
            db_config = {}
            for row in data:
                db_config[row["key"]] = row["value"]
            config_data = db_config
            print("⚙️ Configurazioni caricate con successo da Supabase.")
        else:
            print("⚙️ Tabella Supabase vuota, inizializzazione con i valori predefiniti...")
            config_data = DEFAULT_CONFIG.copy()
            await save_config_to_supabase()
    except Exception as e:
        print(f"[ERRORE CARICAMENTO SUPABASE]: {e}")
        config_data = DEFAULT_CONFIG.copy()

async def save_config_to_supabase():
    try:
        for key, value in config_data.items():
            supabase.table("bot_settings").upsert({
                "key": key,
                "value": value
            }, on_conflict="key").execute()
        print("⚙️ Configurazioni salvate con successo su Supabase.")
    except Exception as e:
        print(f"[ERRORE SALVATAGGIO SUPABASE]: {e}")


@bot.event
async def on_ready():
    print(f"Bot online come {bot.user} (ID: {bot.user.id})")
    await load_config_from_supabase()
    try:
        # Sincronizzazione istantanea per il tuo server specifico
        guild_id = discord.Object(id=1531305565496672266) 
        bot.tree.copy_global_to(guild=guild_id)
        synced = await bot.tree.sync(guild=guild_id)
        print(f"Comandi Slash sincronizzati sul server: {len(synced)}")
    except Exception as e:
        print(f"Errore nella sincronizzazione dei comandi: {e}")


# ==========================================
# 🎨 STYLING & INVIO LOG SPECIFICO (MADISON STATE)
# ==========================================

async def send_typed_log(guild: discord.Guild, log_type: str, embed: discord.Embed):
    log_channels_dict = config_data.get("log_channels", {})
    channel_id = log_channels_dict.get(log_type) or log_channels_dict.get("security" if log_type == "security" else "server")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            # Branding coerente per ogni log inviato
            embed.set_footer(
                text=f"Madison State • Security & Logs System", 
                icon_url=guild.icon.url if guild.icon else None
            )
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
# 🎛️ PANNELLO DI SETTING INTERATTIVO
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
            
        embed = discord.Embed(title=f"🛡️ Madison Security — {module_key.replace('_', ' ').title()}", description=desc, color=discord.Color.dark_blue())
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
        discord.utils.run_coroutine_threadsafe(save_config_to_supabase(), bot.loop)
        
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
            title="🛡️ Madison State — Pannello di Controllo",
            description="Usa i menu e i pulsanti sottostanti per configurare interamente i sistemi di sicurezza e log.",
            color=discord.Color.dark_blue()
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
            label="Azione (delete, timeout, kick, ban...)",
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
            return await interaction.response.send_message("❌ Non hai i permessi necessari.", ephemeral=True)
            
        new_action = self.action_input.value.strip().lower()
        config_data["security"][self.module_key]["action"] = new_action
        
        if self.timeout_input.value and self.timeout_input.value.isdigit():
            config_data["security"][self.module_key]["timeout_minutes"] = int(self.timeout_input.value.strip())
            
        discord.utils.run_coroutine_threadsafe(save_config_to_supabase(), bot.loop)
        await interaction.response.send_message(f"✅ Parametri aggiornati con successo per `{self.module_key}`!", ephemeral=True)


class SettingsMainView(discord.ui.View):
    def __init__(self, inter: discord.Interaction):
        super().__init__(timeout=180)
        self.inter = inter
        self.add_item(ModuleSelect())

    @discord.ui.button(label="Global Whitelist", style=discord.ButtonStyle.success, emoji="🌐", row=1)
    async def global_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        modal = GlobalWhitelistModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configura Canali Log", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def log_channels_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_guild_owner(interaction):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)
        
        view = LogChannelSelectView()
        embed = discord.Embed(
            title="📋 Configurazione Canali Log",
            description="Scegli dal menu a tendina quale categoria di log associare a uno specifico canale.",
            color=discord.Color.blurple()
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

        discord.utils.run_coroutine_threadsafe(save_config_to_supabase(), bot.loop)
        
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
        
        curr_id = config_data.get("log_channels", {}).get(log_type, "")
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
            
        if "log_channels" not in config_data:
            config_data["log_channels"] = {}
        config_data["log_channels"][self.log_type] = ch_val
        
        discord.utils.run_coroutine_threadsafe(save_config_to_supabase(), bot.loop)
        await interaction.response.send_message(f"✅ Canale log per `{self.log_type}` impostato con successo su <#{ch_val}>!", ephemeral=True)


@bot.tree.command(name="setting", description="Apre il pannello di controllo completo e interattivo di Madison State")
async def setting_command(interaction: discord.Interaction):
    if not await is_owner_or_guild_owner(interaction):
        return await interaction.response.send_message("❌ Questo comando può essere eseguito solo dal proprietario.", ephemeral=True)
    
    embed = discord.Embed(
        title="🛡️ Madison State — Pannello di Controllo",
        description="Gestisci in modo centralizzato tutti i protocolli di sicurezza, le whitelist e i canali log istituzionali.",
        color=discord.Color.dark_blue()
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
    sec = config_data.get("security", {})

    # 1. Anti-Invite
    if sec.get("anti_invite", {}).get("enabled") and ("discord.gg/" in content_lower or "discord.com/invite/" in content_lower):
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


# ==========================================
# 🤖 ANTI-BOT ADD
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        sec = config_data.get("security", {}).get("anti_bot_add", {})
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

            if adder and not (adder.guild_permissions.administrator or adder.id in sec.get("whitelist_users", [])):
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
            else:
                return

    embed = discord.Embed(title="📥 Madison State — Nuovo Ingresso", color=discord.Color.from_rgb(46, 204, 113), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Utente", value=f"{member.mention}\n`ID: {member.id}`", inline=True)
    embed.add_field(name="📅 Account Creato", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    await send_typed_log(member.guild, "members", embed)


# ==========================================
# 🏷️ ANTI-ROLE CREATE & DANGEROUS ROLE
# ==========================================
@bot.event
async def on_guild_role_create(role: discord.Role):
    guild = role.guild
    sec_create = config_data.get("security", {}).get("anti_role_create", {})
    sec_danger = config_data.get("security", {}).get("anti_dangerous_role", {})

    creator = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.role_create):
            if entry.target.id == role.id:
                creator = entry.user
                break
    except:
        pass

    if sec_create.get("enabled") and creator:
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

            embed = discord.Embed(title="🚨 Madison Security — Ruolo Bloccato", color=discord.Color.from_rgb(217, 130, 43), timestamp=discord.utils.utcnow())
            embed.add_field(name="👤 Autore", value=f"{creator.mention} (`{creator.id}`)", inline=True)
            embed.add_field(name="🏷️ Ruolo Coinvolto", value=f"`{role.name}`", inline=True)
            embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
            await send_typed_log(guild, "security", embed)
            return

    if sec_danger.get("enabled") and creator:
        if role.permissions.administrator or role.permissions.ban_members or role.permissions.kick_members:
            if not is_whitelisted(creator, sec_danger):
                action = sec_danger.get("action", "remove_perms")
                action_desc = "Permessi pericolosi rimossi"
                try:
                    if action == "remove_perms":
                        await role.edit(permissions=discord.Permissions.none(), reason="Anti-Dangerous Role attivo")
                    elif action in ["kick", "ban"]:
                        action_desc = await apply_generic_action(guild, creator, action, "Ruolo con permessi critici")
                        await role.delete(reason="Eliminato ruolo pericoloso")
                except Exception as e:
                    action_desc += f" (Errore: {e})"

                embed = discord.Embed(title="🚨 Madison Security — Ruolo Pericoloso", color=discord.Color.from_rgb(204, 41, 41), timestamp=discord.utils.utcnow())
                embed.add_field(name="👤 Autore", value=f"{creator.mention} (`{creator.id}`)", inline=True)
                embed.add_field(name="⚠️ Ruolo Pericoloso", value=f"`{role.name}`", inline=True)
                embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
                await send_typed_log(guild, "security", embed)
                return

    embed = discord.Embed(title="🏷️ Madison State — Ruolo Creato", color=discord.Color.from_rgb(52, 152, 219), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome Ruolo", value=f"`{role.name}`", inline=True)
    embed.add_field(name="ID Ruolo", value=f"`{role.id}`", inline=True)
    await send_typed_log(guild, "roles", embed)


# ==========================================
# 🗑️ ANTI-ROLE DELETE
# ==========================================
@bot.event
async def on_guild_role_delete(role: discord.Role):
    guild = role.guild
    sec = config_data.get("security", {}).get("anti_role_delete", {})
    
    deleter = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                deleter = entry.user
                break
    except:
        pass

    if sec.get("enabled") and deleter and not is_whitelisted(deleter, sec):
        action = sec.get("action", "kick")
        action_desc = await apply_generic_action(guild, deleter, action, "Eliminazione ruolo non autorizzata")

        embed = discord.Embed(title="🚨 Madison Security — Eliminazione Ruolo", color=discord.Color.from_rgb(204, 41, 41), timestamp=discord.utils.utcnow())
        embed.add_field(name="👤 Autore", value=f"{deleter.mention} (`{deleter.id}`)", inline=True)
        embed.add_field(name="🏷️ Ruolo Eliminato", value=f"`{role.name}`", inline=True)
        embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
        await send_typed_log(guild, "security", embed)
        return

    embed = discord.Embed(title="🗑️ Madison State — Ruolo Eliminato", color=discord.Color.from_rgb(231, 76, 60), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome Ruolo", value=f"`{role.name}`", inline=True)
    await send_typed_log(guild, "roles", embed)


# ==========================================
# 📁 ANTI-CHANNEL CREATE
# ==========================================
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    guild = channel.guild
    sec = config_data.get("security", {}).get("anti_channel_create", {})
    
    creator = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                creator = entry.user
                break
    except:
        pass

    if sec.get("enabled") and creator and not is_whitelisted(creator, sec):
        action = sec.get("action", "delete")
        action_desc = "Canale eliminato"
        try:
            if action == "delete":
                await channel.delete(reason="Anti-Channel Create attivo")
            else:
                action_desc = await apply_generic_action(guild, creator, action, "Creazione canale non autorizzata")
                await channel.delete(reason="Eliminato canale non autorizzato")
        except Exception as e:
            action_desc += f" (Errore: {e})"

        embed = discord.Embed(title="🚨 Madison Security — Canale Bloccato", color=discord.Color.from_rgb(217, 130, 43), timestamp=discord.utils.utcnow())
        embed.add_field(name="👤 Autore", value=f"{creator.mention} (`{creator.id}`)", inline=True)
        embed.add_field(name="📁 Canale", value=f"`{channel.name}`", inline=True)
        embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
        await send_typed_log(guild, "security", embed)
        return

    embed = discord.Embed(title="📁 Madison State — Canale Creato", color=discord.Color.from_rgb(52, 152, 219), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome Canale", value=f"{channel.mention} (`{channel.name}`)", inline=True)
    await send_typed_log(guild, "channels", embed)


# ==========================================
# ❌ ANTI-CHANNEL DELETE
# ==========================================
@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    sec = config_data.get("security", {}).get("anti_channel_delete", {})
    
    deleter = None
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                break
    except:
        pass

    if sec.get("enabled") and deleter and not is_whitelisted(deleter, sec):
        action = sec.get("action", "kick")
        action_desc = await apply_generic_action(guild, deleter, action, "Eliminazione canale non autorizzata")

        embed = discord.Embed(title="🚨 Madison Security — Eliminazione Canale", color=discord.Color.from_rgb(204, 41, 41), timestamp=discord.utils.utcnow())
        embed.add_field(name="👤 Autore", value=f"{deleter.mention} (`{deleter.id}`)", inline=True)
        embed.add_field(name="📁 Canale Eliminato", value=f"`{channel.name}`", inline=True)
        embed.add_field(name="⚡ Azione Correttiva", value=f"`{action_desc}`", inline=False)
        await send_typed_log(guild, "security", embed)
        return

    embed = discord.Embed(title="❌ Madison State — Canale Eliminato", color=discord.Color.from_rgb(231, 76, 60), timestamp=discord.utils.utcnow())
    embed.add_field(name="Nome Canale", value=f"`{channel.name}`", inline=True)
    await send_typed_log(guild, "channels", embed)


# ==========================================
# 📊 ALTRI EVENTI LOG (STILE ELEGANTE)
# ==========================================

@bot.event
async def on_message_delete(message: discord.Message):
    if not message.guild or message.author.bot:
        return
    embed = discord.Embed(title="🗑️ Madison State — Messaggio Eliminato", color=discord.Color.from_rgb(231, 76, 60), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.add_field(name="👤 Autore", value=f"{message.author.mention}\n`ID: {message.author.id}`", inline=True)
    embed.add_field(name="📍 Canale", value=message.channel.mention, inline=True)
    content = message.content or "*[Nessun testo / Solo allegati]*"
    if len(content) > 1024:
        content = content[:1021] + "..."
    embed.add_field(name="💬 Contenuto", value=content, inline=False)
    await send_typed_log(message.guild, "messages", embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if not before.guild or before.author.bot or before.content == after.content:
        return
    embed = discord.Embed(title="✏️ Madison State — Messaggio Modificato", color=discord.Color.from_rgb(241, 196, 15), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=before.author.display_avatar.url)
    embed.add_field(name="👤 Autore", value=f"{before.author.mention}\n`ID: {before.author.id}`", inline=True)
    embed.add_field(name="📍 Canale", value=before.channel.mention, inline=True)
    
    old_c = before.content or "*[Vuoto]*"
    new_c = after.content or "*[Vuoto]*"
    if len(old_c) > 1024: old_c = old_c[:1021] + "..."
    if len(new_c) > 1024: new_c = new_c[:1021] + "..."
    
    embed.add_field(name="📄 Prima della modifica", value=old_c, inline=False)
    embed.add_field(name="📄 Dopo la modifica", value=new_c, inline=False)
    await send_typed_log(before.guild, "messages", embed)

@bot.event
async def on_member_remove(member: discord.Member):
    embed = discord.Embed(title="📤 Madison State — Uscita Utente", color=discord.Color.from_rgb(149, 165, 166), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Utente", value=f"{member.mention}\n`ID: {member.id}`", inline=True)
    await send_typed_log(member.guild, "members", embed)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    embed = discord.Embed(title="🔨 Madison State — Utente Bannato", color=discord.Color.from_rgb(192, 57, 43), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="👤 Utente", value=f"{user.mention}\n`ID: {user.id}`", inline=True)
    await send_typed_log(guild, "members", embed)

@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    embed = discord.Embed(title="🔓 Madison State — Utente Sbobannato", color=discord.Color.from_rgb(41, 128, 185), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="👤 Utente", value=f"{user.mention}\n`ID: {user.id}`", inline=True)
    await send_typed_log(guild, "members", embed)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.timed_out_until != after.timed_out_until:
        embed = discord.Embed(title="⏳ Madison State — Timeout Modificato", color=discord.Color.from_rgb(230, 126, 34), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.add_field(name="👤 Utente", value=f"{after.mention}\n`ID: {after.id}`", inline=True)
        if after.timed_out_until:
            embed.add_field(name="⏱️ Scadenza Timeout", value=f"<t:{int(after.timed_out_until.timestamp())}:F>", inline=False)
        else:
            embed.add_field(name="⚡ Stato", value="`Timeout rimosso con successo`", inline=False)
        await send_typed_log(after.guild, "members", embed)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if before.channel == after.channel:
        return
    embed = discord.Embed(title="🔊 Madison State — Attività Vocale", color=discord.Color.from_rgb(155, 89, 182), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Utente", value=f"{member.mention}\n`ID: {member.id}`", inline=True)
    
    if before.channel is None and after.channel is not None:
        embed.add_field(name="🎧 Movimento", value=f"Entrato nel canale {after.channel.mention}", inline=False)
    elif before.channel is not None and after.channel is None:
        embed.add_field(name="🎧 Movimento", value=f"Uscito dal canale {before.channel.mention}", inline=False)
    elif before.channel is not None and after.channel is not None:
        embed.add_field(name="🎧 Movimento", value=f"Spostato da {before.channel.mention} a {after.channel.mention}", inline=False)
        
    await send_typed_log(member.guild, "voice", embed)


if __name__ == "__main__":
    bot.run(TOKEN)
