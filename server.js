const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const DISCORD_BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Calcolo della data di creazione dall'ID Discord
function getCreationDate(snowflakeId) {
  try {
    const discordEpoch = 1420070400000n;
    const id = BigInt(snowflakeId);
    const timestamp = Number((id >> 22n) + discordEpoch);
    return new Date(timestamp).toUTCString();
  } catch (e) {
    return 'ID Non Valido';
  }
}

// Lista dinamica di endpoint per l'enumerazione di massa su Fonti Aperte
const TARGET_SITES = [
  { name: 'GitHub', url: 'https://github.com/{}', check: 'status' },
  { name: 'Reddit', url: 'https://www.reddit.com/user/{}', check: 'status' },
  { name: 'Twitch', url: 'https://www.twitch.tv/{}', check: 'status' },
  { name: 'Pinterest', url: 'https://www.pinterest.com/{}/', check: 'status' },
  { name: 'SoundCloud', url: 'https://soundcloud.com/{}', check: 'status' },
  { name: 'Steam', url: 'https://steamcommunity.com/id/{}', check: 'status' },
  { name: 'DockerHub', url: 'https://hub.docker.com/u/{}', check: 'status' },
  { name: 'Medium', url: 'https://medium.com/@{}', check: 'status' },
  { name: 'Patreon', url: 'https://www.patreon.com/{}', check: 'status' },
  { name: 'Linktree', url: 'https://linktr.ee/{}', check: 'status' }
];

// Endpoint principale OSINT
app.get('/api/investigate/:id', async (req, res) => {
  const userId = req.params.id;

  if (!DISCORD_BOT_TOKEN) {
    return res.status(500).json({ error: 'Configura la variabile DISCORD_BOT_TOKEN su Render!' });
  }

  try {
    // 1. Estrazione dati nativi Discord API
    const discordRes = await axios.get(`https://discord.com/api/v10/users/${userId}`, {
      headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}` }
    });

    const userData = discordRes.data;
    const username = userData.username;
    const avatarHash = userData.avatar;
    const avatarUrl = avatarHash 
      ? `https://cdn.discordapp.com/avatars/${userData.id}/${avatarHash}.png` 
      : null;

    // 2. Scan simultaneo di massa dei Social Media / Piattaforme Web tramite Username
    const scanPromises = TARGET_SITES.map(async (site) => {
      const targetUrl = site.url.replace('{}', username);
      try {
        const response = await axios.get(targetUrl, {
          timeout: 4000,
          headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
        });
        if (response.status === 200) {
          return { site: site.name, url: targetUrl, found: true };
        }
      } catch (err) {
        // La maggior parte dei siti restituisce 404 se l'utente non esiste
      }
      return { site: site.name, url: targetUrl, found: false };
    });

    const scanResults = await Promise.all(scanPromises);
    const foundProfiles = scanResults.filter(p => p.found);

    // 3. Generazione automatica dei link di Dorking
    const googleDorks = [
      { name: 'Ricerca Mention Generica', url: `https://www.google.com/search?q="${username}"` },
      { name: 'Pastebin & Leak Dump', url: `https://www.google.com/search?q="${username}"+site:pastebin.com+OR+site:ghostbin.com` },
      { name: 'Donazioni / Crowdfunding', url: `https://www.google.com/search?q="${username}"+site:paypal.me+OR+site:ko-fi.com+OR+site:buymeacoffee.com` },
      { name: 'Forum & Community', url: `https://www.google.com/search?q="${username}"+inurl:forum+OR+inurl:viewtopic` }
    ];

    // 4. Reverse Image Search Links per l'Avatar
    const reverseImageLinks = avatarUrl ? {
      googleLens: `https://lens.google.com/uploadbyurl?url=${encodeURIComponent(avatarUrl)}`,
      yandex: `https://yandex.com/images/search?rpt=imageview&url=${encodeURIComponent(avatarUrl)}`,
      tineye: `https://tineye.com/search?url=${encodeURIComponent(avatarUrl)}`
    } : null;

    return res.json({
      discordInfo: {
        id: userData.id,
        username: username,
        globalName: userData.global_name || 'Nessuno',
        createdAt: getCreationDate(userData.id),
        avatarUrl: avatarUrl
      },
      detectedProfiles: foundProfiles,
      googleDorks: googleDorks,
      reverseImageSearch: reverseImageLinks
    });

  } catch (err) {
    if (err.response && err.response.status === 404) {
      return res.status(404).json({ error: 'ID Discord non trovato.' });
    }
    return res.status(500).json({ error: 'Errore durante il recupero dati.' });
  }
});

app.listen(PORT, () => {
  console.log(`Tool OSINT avviato sulla porta ${PORT}`);
});
