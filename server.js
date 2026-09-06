const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const DISCORD_BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

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

// Generatore di permutazioni per l'username
function generateUsernameVariations(baseName) {
  const clean = baseName.toLowerCase().replace(/[^a-z0-9._-]/g, '');
  const list = new Set([clean]);
  
  // Aggiunta varianti comuni usate online
  list.add(`${clean}_`);
  list.add(`real_${clean}`);
  list.add(`${clean}1`);
  list.add(`${clean}official`);

  return Array.from(list);
}

// Lista estesa di piattaforme target per la verifica delle impronte digitali
const TARGET_PLATFORMS = [
  // Social & Content
  { name: 'GitHub', url: 'https://github.com/{}' },
  { name: 'Reddit', url: 'https://www.reddit.com/user/{}' },
  { name: 'Twitch', url: 'https://www.twitch.tv/{}' },
  { name: 'Pinterest', url: 'https://www.pinterest.com/{}/' },
  { name: 'SoundCloud', url: 'https://soundcloud.com/{}' },
  { name: 'Medium', url: 'https://medium.com/@{}' },
  { name: 'TikTok', url: 'https://www.tiktok.com/@{}' },
  { name: 'Vimeo', url: 'https://vimeo.com/{}' },
  { name: 'DeviantArt', url: 'https://www.deviantart.com/{}' },
  // Gaming
  { name: 'Steam', url: 'https://steamcommunity.com/id/{}' },
  { name: 'Roblox', url: 'https://www.roblox.com/user.aspx?username={}' },
  { name: 'Chess.com', url: 'https://www.chess.com/member/{}' },
  // Coding & Tech
  { name: 'DockerHub', url: 'https://hub.docker.com/u/{}' },
  { name: 'Replit', url: 'https://replit.com/@{}' },
  { name: 'npm', url: 'https://www.npmjs.com/~{}' },
  // Monetizzazione & Donazioni Pubbliche
  { name: 'Linktree', url: 'https://linktr.ee/{}' },
  { name: 'Patreon', url: 'https://www.patreon.com/{}' },
  { name: 'BuyMeACoffee', url: 'https://www.buymeacoffee.com/{}' },
  { name: 'Ko-fi', url: 'https://ko-fi.com/{}' },
  { name: 'PayPal.me', url: 'https://www.paypal.com/paypalme/{}' }
];

app.get('/api/investigate/:id', async (req, res) => {
  const userId = req.params.id;

  if (!DISCORD_BOT_TOKEN) {
    return res.status(500).json({ error: 'Configura DISCORD_BOT_TOKEN su Render!' });
  }

  try {
    // 1. Estrazione dati Discord API
    const discordRes = await axios.get(`https://discord.com/api/v10/users/${userId}`, {
      headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}` }
    });

    const userData = discordRes.data;
    const baseUsername = userData.username;
    const avatarUrl = userData.avatar 
      ? `https://cdn.discordapp.com/avatars/${userData.id}/${userData.avatar}.png?size=512` 
      : null;

    // 2. Generazione varianti username
    const usernameVariations = generateUsernameVariations(baseUsername);

    // 3. Scansione parallela ad alta velocità
    const scanPromises = [];

    TARGET_PLATFORMS.forEach(platform => {
      // Per ogni piattaforma, testiamo sia l'username esatto sia le varianti
      usernameVariations.forEach(uname => {
        const targetUrl = platform.url.replace('{}', uname);
        scanPromises.push(
          axios.get(targetUrl, {
            timeout: 3500,
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
          }).then(response => {
            if (response.status === 200) {
              return { site: platform.name, usernameTested: uname, url: targetUrl, found: true };
            }
            return null;
          }).catch(() => null)
        );
      });
    });

    const resultsRaw = await Promise.all(scanPromises);
    // Filtraggio e rimozione duplicati
    const foundProfiles = resultsRaw.filter(r => r !== null);

    // 4. Sezione Dorking Avanzato per Motori di Ricerca
    const dorks = [
      { name: 'Menzioni e Quote Direct', url: `https://www.google.com/search?q="${baseUsername}"` },
      { name: 'Account Donazione / PayPal / Wallet', url: `https://www.google.com/search?q="${baseUsername}"+site:paypal.me+OR+site:ko-fi.com+OR+site:patreon.com+OR+site:buymeacoffee.com` },
      { name: 'Leak / Pastebin / Text Dumps', url: `https://www.google.com/search?q="${baseUsername}"+site:pastebin.com+OR+site:rentry.co+OR+site:ghostbin.com` },
      { name: 'Forum / Community Gaming', url: `https://www.google.com/search?q="${baseUsername}"+inurl:forum+OR+inurl:thread` },
      { name: 'Documenti / PDF / Repository', url: `https://www.google.com/search?q="${baseUsername}"+filetype:pdf+OR+filetype:txt` }
    ];

    // 5. Motori di ricerca immagini inversa per l'Avatar
    const reverseSearch = avatarUrl ? [
      { name: 'Google Lens (Repertorio Visivo Completo)', url: `https://lens.google.com/uploadbyurl?url=${encodeURIComponent(avatarUrl)}` },
      { name: 'Yandex Images (Migliore per Visi/Profilazioni)', url: `https://yandex.com/images/search?rpt=imageview&url=${encodeURIComponent(avatarUrl)}` },
      { name: 'TinEye (Mappatura Modifiche e Storico)', url: `https://tineye.com/search?url=${encodeURIComponent(avatarUrl)}` }
    ] : [];

    return res.json({
      discord: {
        id: userData.id,
        username: baseUsername,
        globalName: userData.global_name || 'Non impostato',
        createdAt: getCreationDate(userData.id),
        avatarUrl: avatarUrl
      },
      testedVariations: usernameVariations,
      detectedProfiles: foundProfiles,
      googleDorks: dorks,
      reverseImageSearch: reverseSearch
    });

  } catch (err) {
    if (err.response && err.response.status === 404) {
      return res.status(404).json({ error: 'Utente Discord non trovato.' });
    }
    return res.status(500).json({ error: 'Errore durante la scansione OSINT.' });
  }
});

app.listen(PORT, () => console.log(`OSINT Scanner attivo sulla porta ${PORT}`));
