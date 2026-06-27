const ENDPOINTS = {
  lead: '/preview',
  m1:   '/m1/preview',
  m2:   '/m2/preview',
  m3:   '/m3/preview',
  m4:   '/m4/preview', 
};

const MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' };

const CARD_URL = 'https://wc2026-i9es.onrender.com/card';

const PLAYER_INFO = {
  'Babu':    { avatar: 29, user: 'baburubaburu' },
  'Hotarou': { avatar: 28, user: 'houtarou' },
  'Ziggs':   { avatar: 14, user: 'ziggssawpuzzle' },
  'Trel':    { avatar: 25, user: 'trel' },
  'Scorpy':  { avatar: 8,  user: 'scorpy' },
  'Pyro':    { avatar: 12, user: 'pyrospower' },
  'Edna':    { avatar: 26, user: 'edna_san' },
  'BimBim':  { avatar: 21, user: 'bimbastic' },
  'Squally': { avatar: 11, user: 'squallyy' },
  'Hype':    { avatar: 18, user: 'hypetrain' },
  'Sunny':   { avatar: 21, user: 'sunnyrainlight' },
  'D4':      { avatar: 14, user: 'akuma5336' },
  'Nyte':    { avatar: 8,  user: 'nyte_zero' },
  'Pffq':    { avatar: 20, user: 'xenter0384' },
};

let activeBoard = 'lead';
let selectedPlayer = null;

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showCard(name) {
  selectedPlayer = name;
  const panel = document.getElementById('card-panel');
  const vault = document.getElementById('hidden-card-vault');
  const info = PLAYER_INFO[name];

  if (!info) {
    panel.innerHTML = `
      <div id="hidden-card-vault" style="display: none !important;">${vault ? vault.innerHTML : ''}</div>
      <div class="card-placeholder"><p>No card found for ${escHtml(name)}</p></div>`;
    return;
  }

  // 1. Check if the element exists in our permanent invisible vault
  let imgEl = vault ? vault.querySelector(`[data-preload-user="${name}"]`) : null;

  // 2. Fallback: build on-demand if it hasn't finished preloading yet
  if (!imgEl) {
    const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc`;
    imgEl = new Image();
    imgEl.className = "card-img";
    imgEl.setAttribute('data-preload-user', name);
    imgEl.src = url;
    imgEl.alt = `${name}'s card`;
    imgEl.onerror = function() {
      this.parentElement.innerHTML = '<div class="card-placeholder"><p>Card unavailable</p></div>';
    };
    if (vault) vault.appendChild(imgEl);
  }

  // 3. Keep layout controls safe while resetting the container
  const progressContainer = document.getElementById('preload-progress-container');
  panel.innerHTML = '';
  
  if (progressContainer) panel.appendChild(progressContainer);
  if (vault) panel.appendChild(vault);

  // 4. Render layout frames
  const innerLayout = document.createElement('div');
  innerLayout.className = 'card-inner';
  innerLayout.innerHTML = `
    <div class="card-name">${escHtml(name)}</div>
    <div class="card-img-holder"></div>
  `;
  panel.appendChild(innerLayout);

  // 5. Clone image straight from the vault so the browser keeps the source node painted in RAM
  const visibleClone = imgEl.cloneNode(true);
  panel.querySelector('.card-img-holder').appendChild(visibleClone);

  document.querySelectorAll('.leaderboard tbody tr').forEach(tr => {
    tr.classList.toggle('selected', tr.dataset.player === name);
  });
}

function renderTable(players) {
  if (!players || players.length === 0) {
    return `<div class="state-msg"><span class="icon">📭</span>No scores yet.</div>`;
  }

  const rows = players.map((p, i) => {
    const rank = i + 1;
    const rankClass = rank <= 3 ? ` rank-${rank}` : '';
    const medal = MEDALS[rank] || '';
    const isSelected = p.name === selectedPlayer ? ' selected' : '';
    return `
      <tr class="player-row${isSelected}" data-player="${escHtml(p.name)}">
        <td class="rank${rankClass}">${rank}</td>
        <td class="player-name clickable">${escHtml(p.name)}</td>
        <td class="medal">${medal}</td>
        <td class="score-cell">${p.score}</td>
      </tr>`;
  }).join('');

  return `
    <table class="leaderboard" aria-label="Leaderboard">
      <thead>
        <tr>
          <th>#</th>
          <th>Player</th>
          <th></th>
          <th style="text-align:right">Pts</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function attachRowClicks() {
  document.querySelectorAll('.player-row').forEach(tr => {
    tr.addEventListener('click', () => showCard(tr.dataset.player));
  });
}

async function loadBoard(boardKey) {
  const container = document.getElementById('board-container');
  container.innerHTML = `<div class="state-msg"><span class="icon">⏳</span>Loading…</div>`;

  try {
    const res = await fetch(ENDPOINTS[boardKey]);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');
    
    container.innerHTML = renderTable(data.players);
    attachRowClicks();
    if (selectedPlayer) showCard(selectedPlayer);
  } catch (err) {
    container.innerHTML = `
      <div class="state-msg">
        <span class="icon">⚠️</span>
        Couldn't load scores.<br>
        <small style="margin-top:6px;display:block;font-size:11px;opacity:0.7">${escHtml(err.message)}</small>
      </div>`;
  }
}

// ── Diagnostic 60ms Fast-Stagger DOM Vault Preloader Engine ──
function triggerBackgroundPreload() {
  const players = Object.keys(PLAYER_INFO);
  const totalPlayers = players.length;
  let preloadedCount = 0;

  const progressContainer = document.getElementById('preload-progress-container');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressPercentText = document.getElementById('progress-percent');
  const vault = document.getElementById('hidden-card-vault');

  if (!progressContainer || !progressBarFill || !progressPercentText || !vault) return;

  progressContainer.classList.remove('hidden');

  console.log("🚀 Starting card preload sync loop...");

  function handleItemProcessed() {
    preloadedCount++;
    const currentPercentage = Math.round((preloadedCount / totalPlayers) * 100);
    
    progressBarFill.style.width = `${currentPercentage}%`;
    progressPercentText.innerText = `${currentPercentage}%`;

    if (preloadedCount === totalPlayers) {
      console.log("🏁 All 14 cards successfully anchored into layout memory!");
      setTimeout(() => {
        progressContainer.style.opacity = '0';
        setTimeout(() => {
          progressContainer.classList.add('hidden');
        }, 400); 
      }, 1200); 
    }
  }
  
  players.forEach((name, index) => {
    setTimeout(() => {
      const info = PLAYER_INFO[name];
      
      if (vault.querySelector(`[data-preload-user="${name}"]`)) {
        handleItemProcessed();
        return;
      }

      if (info) {
        const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc`;
        const startTime = performance.now();
        
        const imgEl = new Image();
        imgEl.className = "card-img";
        imgEl.setAttribute('data-preload-user', name);
        
        imgEl.onload = function() {
          const endTime = performance.now();
          const duration = ((endTime - startTime) / 1000).toFixed(2);
          console.log(`📡 [SUCCESS] Cached card for ${name} in ${duration}s`);
          handleItemProcessed();
        };
        
        imgEl.onerror = function() {
          console.warn(`⚠️ [FAILED] Card preload timed out for: ${name}`);
          handleItemProcessed();
        };

        imgEl.src = url;
        vault.appendChild(imgEl);
      }
    }, index * 60); // Clean 60ms pipelining speed
  });
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    activeBoard = tab.dataset.board;
    loadBoard(activeBoard);
  });
});

document.getElementById('refresh-btn').addEventListener('click', () => {
  loadBoard(activeBoard);
});

loadBoard('lead');

// Wake up Render Free Tier instantly via stealth handshake to bypass CORS checks
fetch('https://wc2026-i9es.onrender.com/', { mode: 'no-cors' }).catch(() => {});

setTimeout(triggerBackgroundPreload, 1200);