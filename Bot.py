import discord
import json
import asyncio

# Caricamento dei dati dal file JSON
with open('babajaga_community_full_vocal.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # Necessario per gestire i ruoli
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Loggato come {client.user}')
    
    # Sostituisci con l'ID del tuo server di test
    guild_id = int(input("Inserisci l'ID del server dove vuoi importare la struttura: "))
    guild = client.get_guild(guild_id)

    if not guild:
        print("Server non trovato. Assicurati che il bot sia dentro!")
        return

    print(f"Inizio creazione struttura su: {guild.name}")

    # 1. Creazione Ruoli
    role_map = {}
    for role_data in reversed(data['roles']): # Reversed per mantenere la gerarchia corretta
        color = discord.Color(role_data['color'])
        permissions = discord.Permissions()
        
        # Mapping base dei permessi (semplificato)
        if "ADMINISTRATOR" in role_data['permissions']:
            permissions.administrator = True
            
        new_role = await guild.create_role(
            name=role_data['name'],
            color=color,
            hoist=role_data['hoist'],
            mentionable=role_data['mentionable'],
            permissions=permissions
        )
        print(f"Creato ruolo: {new_role.name}")
        role_map[role_data['name']] = new_role

    # 2. Creazione Categorie e Canali
    for cat_data in data['categories']:
        category = await guild.create_category(cat_data['name'])
        print(f"Creato categoria: {category.name}")
        
        for channel_name in cat_data['channels']:
            # Se il nome contiene icone di volume o nomi tipici, crea canale vocale
            if "Voice" in channel_name or "Room" in channel_name or "🔊" in channel_name:
                await guild.create_voice_channel(channel_name, category=category)
            else:
                await guild.create_text_channel(channel_name, category=category)
            print(f"  - Creato canale: {channel_name}")

    print("\n✅ Importazione completata con successo!")
    await client.close()

client.run('IL_TUO_TOKEN_QUI')

