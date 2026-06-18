<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vinewood RP V3 - Pack Shop</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background-color: #0b0f19;
            color: #f3f4f6;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .blur-bg {
            backdrop-filter: blur(12px);
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">

    <nav class="border-b border-gray-800 bg-gray-950/80 sticky top-0 z-50 blur-bg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center gap-3">
                    <div id="site-logo-container" class="flex items-center gap-2">
                        <span id="site-text-logo" class="text-xl font-black tracking-wider text-amber-500">VINEWOOD RP V3</span>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <a href="https://discord.gg/vinewoodrpv3" target="_blank" class="bg-[#5865F2] hover:bg-[#4752C4] text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2">
                        <i class="fab fa-discord"></i> Discord Server
                    </a>
                    <div id="auth-buttons" class="flex gap-2">
                        </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
        
        <div id="shop-section" class="space-y-8">
            <div class="text-center max-w-2xl mx-auto space-y-3">
                <h1 class="text-4xl font-extrabold text-white sm:text-5xl">Potenzia la tua esperienza su <span class="text-amber-500">PS4</span></h1>
                <p class="text-gray-400 text-lg">Acquista i migliori pack esclusivi per Vinewood RP. Consegna rapida tramite ticket Discord.</p>
            </div>

            <div id="packs-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-6">
                </div>
        </div>

        <div id="auth-section" class="hidden max-w-md mx-auto bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-2xl my-12">
            <h2 id="auth-title" class="text-2xl font-bold text-center mb-6 text-white">Accedi al Portale</h2>
            <form id="auth-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1">Nickname PSN / Discord</label>
                    <input type="text" id="auth-username" required class="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1">Password</label>
                    <input type="password" id="auth-password" required class="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition">
                </div>
                <button type="submit" class="w-full bg-amber-500 hover:bg-amber-600 text-gray-950 font-bold py-2.5 rounded-lg transition mt-2">Procedi</button>
            </form>
            <p class="text-center text-sm text-gray-500 mt-4">
                <span id="auth-switch-text">Non hai un account?</span> 
                <button id="auth-switch-btn" class="text-amber-500 hover:underline ml-1 font-medium">Registrati</button>
            </p>
        </div>

        <div id="admin-section" class="hidden space-y-8">
            <div class="flex justify-between items-center border-b border-gray-800 pb-4">
                <h2 class="text-3xl font-bold text-white"><i class="fas fa-user-shield text-amber-500 mr-2"></i>Pannello Amministratore</h2>
                <button onclick="showSection('shop')" class="text-gray-400 hover:text-white flex items-center gap-2"><i class="fas fa-arrow-left"></i> Torna allo Shop</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="space-y-6">
                    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <h3 class="text-xl font-bold mb-4 text-white"><i class="fas fa-cogs text-amber-500 mr-2"></i>Impostazioni Sito</h3>
                        <form id="settings-form" class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-400 mb-1">Nome del Server / Testo</label>
                                <input type="text" id="settings-site-name" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-400 mb-1">URL Immagine Logo (Opzionale)</label>
                                <input type="url" id="settings-logo-url" placeholder="https://link-immagine.com/logo.png" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500">
                                <p class="text-xs text-gray-500 mt-1">Lascia vuoto per usare solo il testo.</p>
                            </div>
                            <button type="submit" class="w-full bg-amber-500 hover:bg-amber-600 text-gray-950 font-bold py-2 rounded-lg transition">Aggiorna Identità Sito</button>
                        </form>
                    </div>

                    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <h3 class="text-xl font-bold mb-4 text-white"><i class="fas fa-box-open text-amber-500 mr-2"></i>Crea / Modifica Pack</h3>
                        <form id="pack-form" class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-400 mb-1">Nome Pack</label>
                                <input type="text" id="pack-name" required class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-400 mb-1">Prezzo (€)</label>
                                <input type="number" step="0.01" id="pack-price" required class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-400 mb-1">URL Immagine Pack</label>
                                <input type="url" id="pack-image" placeholder="https://link-immagine.com/foto.png" required class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-400 mb-1">Descrizione</label>
                                <textarea id="pack-desc" rows="3" required class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500"></textarea>
                            </div>
                            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded-lg transition">Salva Pacchetto</button>
                        </form>
                    </div>
                </div>

                <div class="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6">
                    <h3 class="text-xl font-bold mb-4 text-white"><i class="fas fa-users text-amber-500 mr-2"></i>Gestione Utenti Registrati</h3>
                    <p class="text-sm text-gray-400 mb-4">Qui vedi tutti i nickname iscritti. Puoi promuoverli ad Admin cliccando sulla spunta.</p>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm text-gray-400">
                            <thead class="bg-gray-950 text-gray-300 uppercase text-xs">
                                <tr>
                                    <th class="px-4 py-3">Nickname</th>
                                    <th class="px-4 py-3">Ruolo</th>
                                    <th class="px-4 py-3 text-right">Azione</th>
                                </tr>
                            </thead>
                            <tbody id="users-table-body">
                                </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

    </main>

    <div id="purchase-modal" class="hidden fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
        <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 max-w-md w-full text-center space-y-4 shadow-2xl animate-fade-in">
            <div class="w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center text-3xl mx-auto">
                <i class="fas fa-check-circle"></i>
            </div>
            <h3 class="text-2xl font-bold text-white">Ordine Inizializzato!</h3>
            <p class="text-gray-400">Per completare il pagamento del pacchetto ed ottenerlo su PS4, apri un ticket nel nostro server Discord dedicato.</p>
            <div class="bg-gray-950 p-3 rounded-lg border border-gray-800 text-sm font-mono text-amber-500 break-all select-all">
                https://discord.gg/AEWw6RCvDh
            </div>
            <div class="flex gap-3 pt-2">
                <button onclick="closeModal()" class="w-1/2 bg-gray-800 hover:bg-gray-700 text-white font-medium py-2 rounded-lg transition">Chiudi</button>
                <a href="https://discord.gg/AEWw6RCvDh" target="_blank" class="w-1/2 bg-[#5865F2] hover:bg-[#4752C4] text-white font-medium py-2 rounded-lg transition flex items-center justify-center gap-2">
                    Apri Ticket <i class="fas fa-external-link-alt text-xs"></i>
                </a>
            </div>
        </div>
    </div>

    <footer class="border-t border-gray-800 bg-gray-950 py-6 mt-12 text-center text-sm text-gray-500">
        <p>&copy; 2026 <span id="footer-site-name">Vinewood RP V3</span>. Tutti i diritti riservati. Questo sito non è affiliato con Sony Interactive Entertainment o Rockstar Games.</p>
    </footer>

    <script>
        // Configurazione iniziale impostazioni (Logo e Nome Sito)
        if (!localStorage.getItem('siteSettings')) {
            const defaultSettings = {
                name: "VINEWOOD RP V3",
                logoUrl: ""
            };
            localStorage.setItem('siteSettings', JSON.stringify(defaultSettings));
        }

        // Dati Iniziali di Simulazione
        if (!localStorage.getItem('users')) {
            const defaultUsers = [
                { username: "Owner_Vinewood", password: "adminpassword", isAdmin: true },
                { username: "PlayerGamer", password: "password123", isAdmin: false }
            ];
            localStorage.setItem('users', JSON.stringify(defaultUsers));
        }
        if (!localStorage.getItem('packs')) {
            const defaultPacks = [
                { id: 1, name: "Pack Auto Custom VIP", price: "15.00", image: "https://images.unsplash.com/photo-1617788138017-80ad40651399?w=500", desc: "Sblocca l'accesso a 3 veicoli personalizzati con gestione modifiche estetica avanzata." },
                { id: 2, name: "Pack Starter Soldi & Case", price: "10.00", image: "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=500", desc: "Ricevi un conto iniziale maggiorato e un appartamento di lusso a Los Santos." }
            ];
            localStorage.setItem('packs', JSON.stringify(defaultPacks));
        }

        let currentUser = JSON.parse(sessionStorage.getItem('currentUser')) || null;
        let isRegisterMode = false;

        // Inizializzazione Applicazione
        function init() {
            renderSiteIdentity();
            renderAuthButtons();
            renderPacks();
            renderUsersTable();
            fillSettingsForm();
        }

        // Rendering dinamico del Logo o del Testo nella Navbar e Footer
        function renderSiteIdentity() {
            const settings = JSON.parse(localStorage.getItem('siteSettings'));
            const container = document.getElementById('site-logo-container');
            const footerName = document.getElementById('footer-site-name');
            
            footerName.innerText = settings.name;

            if (settings.logoUrl && settings.logoUrl.trim() !== "") {
                container.innerHTML = `
                    <img src="${settings.logoUrl}" alt="Logo" class="h-9 w-auto object-contain rounded">
                    <span class="text-xl font-black tracking-wider text-amber-500 hidden sm:inline">${settings.name}</span>
                `;
            } else {
                container.innerHTML = `
                    <span class="text-xl font-black tracking-wider text-amber-500">${settings.name}</span>
                `;
            }
        }

        // Popola i campi del form impostazioni nel pannello admin
        function fillSettingsForm() {
            const settings = JSON.parse(localStorage.getItem('siteSettings'));
            document.getElementById('settings-site-name').value = settings.name;
            document.getElementById('settings-logo-url').value = settings.logoUrl;
        }

        // Gestione invio impostazioni (Logo)
        document.getElementById('settings-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('settings-site-name').value.trim() || "VINEWOOD RP V3";
            const logoUrl = document.getElementById('settings-logo-url').value.trim();

            const newSettings = { name, logoUrl };
            localStorage.setItem('siteSettings', JSON.stringify(newSettings));
            
            renderSiteIdentity();
            alert("Identità del sito e logo aggiornati con successo!");
        });

        // Cambio Sezione Fluido
        function showSection(section) {
            document.getElementById('shop-section').classList.add('hidden');
            document.getElementById('auth-section').classList.add('hidden');
            document.getElementById('admin-section').classList.add('hidden');

            if (section === 'shop') document.getElementById('shop-section').classList.remove('hidden');
            if (section === 'auth') document.getElementById('auth-section').classList.remove('hidden');
            if (section === 'admin') document.getElementById('admin-section').classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // Render Bottone Login / Nome in Navbar
        function renderAuthButtons() {
            const container = document.getElementById('auth-buttons');
            if (currentUser) {
                container.innerHTML = `
                    ${currentUser.isAdmin ? `<button onclick="showSection('admin')" class="bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 px-4 py-2 rounded-lg text-sm font-medium transition cursor-pointer"><i class="fas fa-user-shield"></i> Admin</button>` : ''}
                    <span class="text-sm bg-gray-900 border border-gray-800 px-3 py-2 rounded-lg text-gray-300 flex items-center gap-2"><i class="far fa-user text-amber-500"></i> ${currentUser.username}</span>
                    <button onclick="logout()" class="text-gray-400 hover:text-rose-500 text-sm transition font-medium cursor-pointer">Esci</button>
                `;
            } else {
                container.innerHTML = `
                    <button onclick="openAuth(false)" class="text-gray-300 hover:text-white text-sm font-medium transition px-3 py-2 cursor-pointer">Accedi</button>
                    <button onclick="openAuth(true)" class="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition cursor-pointer">Registrati</button>
                `;
            }
        }

        // Render Griglia Pacchetti
        function renderPacks() {
            const grid = document.getElementById('packs-grid');
            const packsArray = JSON.parse(localStorage.getItem('packs')) || [];
            
            grid.innerHTML = '';
            packsArray.forEach(pack => {
                grid.innerHTML += `
                    <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg flex flex-col justify-between hover:border-gray-700 transition duration-300">
                        <img src="${pack.image}" alt="${pack.name}" class="w-full h-48 object-cover">
                        <div class="p-5 flex-grow flex flex-col justify-between space-y-4">
                            <div>
                                <h3 class="text-xl font-bold text-white mb-2">${pack.name}</h3>
                                <p class="text-gray-400 text-sm leading-relaxed">${pack.desc}</p>
                            </div>
                            <div class="flex items-center justify-between pt-2">
                                <span class="text-2xl font-black text-amber-500">${pack.price} €</span>
                                <button onclick="buyPack()" class="bg-amber-500 hover:bg-amber-600 text-gray-950 font-bold px-4 py-2 rounded-lg text-sm transition shadow-lg shadow-amber-500/10 flex items-center gap-2 cursor-pointer">
                                    <i class="fas fa-shopping-cart text-xs"></i> Acquista
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }

        // Render Tabella Utenti per l'Admin
        function renderUsersTable() {
            const tbody = document.getElementById('users-table-body');
            const users = JSON.parse(localStorage.getItem('users')) || [];
            tbody.innerHTML = '';

            users.forEach((user, index) => {
                tbody.innerHTML += `
                    <tr class="border-b border-gray-800 hover:bg-gray-950/50 transition">
                        <td class="px-4 py-3 font-medium text-white">${user.username}</td>
                        <td class="px-4 py-3">
                            <span class="px-2 py-1 rounded text-xs font-semibold ${user.isAdmin ? 'bg-amber-500/10 text-amber-500' : 'bg-gray-800 text-gray-400'}">
                                ${user.isAdmin ? 'Amministratore' : 'Utente'}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-right">
                            <button onclick="toggleAdmin(${index})" class="text-sm p-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 transition cursor-pointer" title="Cambia stato Admin">
                                <i class="fas ${user.isAdmin ? 'fa-user-minus text-rose-400' : 'fa-user-plus text-emerald-400'}"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
        }

        // Funzioni di Auth (Login/Registrazione)
        function openAuth(register = false) {
            isRegisterMode = register;
            document.getElementById('auth-title').innerText = register ? "Crea un nuovo account" : "Accedi al Portale";
            document.getElementById('auth-switch-text').innerText = register ? "Hai già un account?" : "Non hai un account?";
            document.getElementById('auth-switch-btn').innerText = register ? "Accedi" : "Registrati";
            showSection('auth');
        }

        document.getElementById('auth-switch-btn').addEventListener('click', () => openAuth(!isRegisterMode));

        document.getElementById('auth-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const userIn = document.getElementById('auth-username').value.trim();
            const passIn = document.getElementById('auth-password').value;
            let users = JSON.parse(localStorage.getItem('users')) || [];

            if (isRegisterMode) {
                if (users.some(u => u.username.toLowerCase() === userIn.toLowerCase())) {
                    alert("Questo nickname è già registrato!");
                    return;
                }
                const newUser = { username: userIn, password: passIn, isAdmin: false };
                users.push(newUser);
                localStorage.setItem('users', JSON.stringify(users));
                currentUser = newUser;
                alert("Registrazione completata con successo!");
            } else {
                const found = users.find(u => u.username.toLowerCase() === userIn.toLowerCase() && u.password === passIn);
                if (!found) {
                    alert("Nickname o password errati.");
                    return;
                }
                currentUser = found;
            }

            sessionStorage.setItem('currentUser', JSON.stringify(currentUser));
            document.getElementById('auth-form').reset();
            init();
            showSection('shop');
        });

        function logout() {
            currentUser = null;
            sessionStorage.removeItem('currentUser');
            init();
            showSection('shop');
        }

        // Promuovi / Retrocedi utenti ad Admin
        function toggleAdmin(index) {
            let users = JSON.parse(localStorage.getItem('users'));
            users[index].isAdmin = !users[index].isAdmin;
            localStorage.setItem('users', JSON.stringify(users));
            
            if (currentUser && currentUser.username === users[index].username) {
                currentUser.isAdmin = users[index].isAdmin;
                sessionStorage.setItem('currentUser', JSON.stringify(currentUser));
            }
            init();
        }

        // Aggiungi Pack da Admin
        document.getElementById('pack-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('pack-name').value;
            const price = parseFloat(document.getElementById('pack-price').value).toFixed(2);
            const image = document.getElementById('pack-image').value;
            const desc = document.getElementById('pack-desc').value;

            let packs = JSON.parse(localStorage.getItem('packs')) || [];
            packs.push({ id: Date.now(), name, price, image, desc });
            localStorage.setItem('packs', JSON.stringify(packs));

            document.getElementById('pack-form').reset();
            renderPacks();
            alert("Nuovo pacchetto inserito ed aggiornato!");
        });

        // Gestione Finestre di Acquisto
        function buyPack() {
            document.getElementById('purchase-modal').classList.remove('hidden');
        }

        function closeModal() {
            document.getElementById('purchase-modal').classList.add('hidden');
        }

        // Avvio iniziale del sito
        init();
    </script>
</body>
</html>
