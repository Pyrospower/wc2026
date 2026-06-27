const ENDPOINTS = {
  lead: '/preview',
  m1:   '/m1/preview',
  m2:   '/m2/preview',
  m3:   '/m3/preview',
  m4:   '/m4/preview', 
};

// 💎 Fully configured Google Sheets Scoring Data Stream URL:
const SCORING_SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT8fEdr0djoTa4bc8diSdwH2xSDJ4JTlNgHUWho8lQ5btMR9Joe3sXhZPP72oTSE9MBdoYKrY4DlFl9/pub?gid=865998988&single=true&output=csv';

// 🔮 Fully configured Google Sheets Predictions Data Stream URL:
const PREDICTIONS_SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT8fEdr0djoTa4bc8diSdwH2xSDJ4JTlNgHUWho8lQ5btMR9Joe3sXhZPP72oTSE9MBdoYKrY4DlFl9/pub?gid=793952308&single=true&output=csv';

const MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' };
const CARD_URL = 'https://wc2026-i9es.onrender.com/card';

// 🔄 CACHE BUSTING VERSION: Increment this number (e.g. '1.0.1', '1.0.2', etc.) 
// to instantly force all users to fetch new cards when scores or designs update.
const CARD_VERSION = '1.0.0';

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
let cachedWinRates = {}; // Memory bank tracking accuracy: { 'Babu': '65.15%' }

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Dynamic Google Sheets Matrix Parser Engine
async function fetchLiveWinRates() {
  try {
    const response = await fetch(SCORING_SHEET_CSV_URL);
    if (!response.ok) return;
    const csvText = await response.text();
    
    // Split into dimensional lines and compute rows safely
    const rows = csvText.split(/\r?\n/).map(row => row.split(','));
    if (rows.length < 77) return;

    // Row index 2 tracks player structural layout columns (C3:S3)
    const headerRow = rows[2];
    // Row index 76 houses final sheet calculations (=AVERAGE percentages)
    const winRateRow = rows[76];

    headerRow.forEach((colValue, idx) => {
      const cleanName = colValue.trim();
      if (PLAYER_INFO[cleanName] && winRateRow[idx]) {
        let rate = winRateRow[idx].trim();
        // Convert to percentage form factor if sheet drops bare float decimals
        if (!rate.includes('%') && !isNaN(rate) && rate !== '') {
          rate = (parseFloat(rate) * 100).toFixed(2) + '%';
        }
        cachedWinRates[cleanName] = rate;
      }
    });
    console.log("📊 Live Win Rates Synced:", cachedWinRates);
    
    // Live update open stats badge instantly if user has a card already up
    if (selectedPlayer) {
      const activeBadgeVal = document.getElementById('stat-val-node');
      if (activeBadgeVal && cachedWinRates[selectedPlayer]) {
        activeBadgeVal.innerText = cachedWinRates[selectedPlayer];
      }
    }
  } catch (err) {
    console.warn("⚠️ Syncing live sheet win-rates failed:", err);
  }
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

  let imgEl = vault ? vault.querySelector(`[data-preload-user="${name}"]`) : null;

  if (!imgEl) {
    // URL includes dynamic card version query parameter
    const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc&v=${CARD_VERSION}`;
    imgEl = new Image();
    imgEl.className = "card-img";
    imgEl.setAttribute('data-preload-user', name);
    imgEl.src = url;
    imgEl.alt = `${name}'s card`;
    if (vault) vault.appendChild(imgEl);
  }

  const progressContainer = document.getElementById('preload-progress-container');
  panel.innerHTML = '';
  
  if (progressContainer) panel.appendChild(progressContainer);
  if (vault) panel.appendChild(vault);

  // Extract prediction data or show loading spacer state
  const rateValue = cachedWinRates[name] || '⏳ Syncing...';

  const innerLayout = document.createElement('div');
  innerLayout.className = 'card-inner';
  innerLayout.innerHTML = `
    <div class="card-img-holder"></div>
    <div class="card-stat-badge">
      <span class="stat-label">Prediction Accuracy</span>
      <span class="stat-value" id="stat-val-node">${escHtml(rateValue)}</span>
    </div>
  `;

  const visibleClone = imgEl.cloneNode(true);
  panel.appendChild(innerLayout);
  panel.querySelector('.card-img-holder').appendChild(visibleClone);

  document.querySelectorAll('.player-row').forEach(row => {
    row.classList.toggle('selected', row.dataset.player === name);
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
      <div class="player-row${isSelected}" data-player="${escHtml(p.name)}">
        <div class="cell-rank rank${rankClass}">${rank}</div>
        <div class="cell-player player-name">${escHtml(p.name)}${medal ? `<span class="medal-inline">${medal}</span>` : ''}</div>
        <div class="cell-pts score-cell">${p.score}</div>
      </div>`;
  }).join('');

  return `
    <div class="leaderboard-flex" role="grid" aria-label="Leaderboard">
      <div class="board-header">
        <div class="cell-rank">#</div>
        <div class="cell-player">Player</div>
        <div class="cell-pts">Pts</div>
      </div>
      <div class="board-body">
        ${rows}
      </div>
    </div>`;
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

// Loads a single player's card image into the vault. Resolves once
// loaded (or failed) so the pool below knows when a slot frees up.
function preloadOne(name, vault) {
  return new Promise((resolve) => {
    if (vault.querySelector(`[data-preload-user="${name}"]`)) {
      resolve();
      return;
    }

    const info = PLAYER_INFO[name];
    if (!info) {
      resolve();
      return;
    }

    // URL includes dynamic card version query parameter
    const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc&v=${CARD_VERSION}`;
    const imgEl = new Image();
    imgEl.className = "card-img";
    imgEl.setAttribute('data-preload-user', name);
    imgEl.onload = resolve;
    imgEl.onerror = resolve;
    imgEl.src = url;
    vault.appendChild(imgEl);
  });
}

// Concurrency-limited preload pool: keeps PRELOAD_CONCURRENCY requests
// in flight at once instead of bursting all of them or drip-feeding
// them one every 60ms. Faster wall-clock completion, still gentle on
// the card-render endpoint.
const PRELOAD_CONCURRENCY = 3;

async function triggerBackgroundPreload() {
  const players = Object.keys(PLAYER_INFO);
  const totalPlayers = players.length;
  let preloadedCount = 0;

  const progressContainer = document.getElementById('preload-progress-container');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressPercentText = document.getElementById('progress-percent');
  const vault = document.getElementById('hidden-card-vault');

  if (!progressContainer || !progressBarFill || !progressPercentText || !vault) return;

  progressContainer.classList.remove('hidden');

  function handleItemProcessed() {
    preloadedCount++;
    const currentPercentage = Math.round((preloadedCount / totalPlayers) * 100);

    progressBarFill.style.width = `${currentPercentage}%`;
    progressPercentText.innerText = `${currentPercentage}%`;

    if (preloadedCount === totalPlayers) {
      setTimeout(() => {
        progressContainer.style.opacity = '0';
        setTimeout(() => {
          progressContainer.style.visibility = 'hidden';
          progressContainer.style.height = progressContainer.offsetHeight + 'px';
          progressContainer.classList.add('hidden');
        }, 400);
      }, 1200);
    }
  }

  let nextIndex = 0;

  async function worker() {
    while (nextIndex < players.length) {
      const name = players[nextIndex++];
      await preloadOne(name, vault);
      handleItemProcessed();
    }
  }

  const workerCount = Math.min(PRELOAD_CONCURRENCY, totalPlayers);
  await Promise.all(Array.from({ length: workerCount }, worker));
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
  fetchLiveWinRates(); 
});

// Initialization Pipeline
const leadBoardPromise = loadBoard('lead');
fetchLiveWinRates();

// Wake up the Render dyno immediately, and once that resolves (or the
// lead board has rendered, whichever is later) kick off the card
// preload pool — no more guessing a flat "safe" delay.
const wakePingPromise = fetch('https://wc2026-i9es.onrender.com/', { mode: 'no-cors' }).catch(() => {});

Promise.all([leadBoardPromise, wakePingPromise]).then(() => {
  triggerBackgroundPreload();
});

// 🛠️ Service Worker Registration 
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('Service Worker registered successfully:', reg.scope))
      .catch(err => console.warn('Service Worker registration failed:', err));
  });
}

// ── Predictions Tab Navigation and Flex Parser Logic ──

const btnStandings = document.getElementById('btn-standings');
const btnPredictions = document.getElementById('btn-predictions');
const viewStandings = document.getElementById('view-standings');
const viewPredictions = document.getElementById('view-predictions');
const cardPanel = document.getElementById('card-panel');
const contentWrap = document.querySelector('.content-wrap');

btnStandings.addEventListener('click', () => {
  btnStandings.classList.add('active');
  btnPredictions.classList.remove('active');
  viewStandings.style.display = 'block';
  viewPredictions.style.display = 'none';

  // Show the card panel and return container back to the regular width
  cardPanel.style.display = 'block';
  contentWrap.classList.remove('wide-layout');
});

btnPredictions.addEventListener('click', () => {
  btnPredictions.classList.add('active');
  btnStandings.classList.remove('active');
  viewStandings.style.display = 'none';
  viewPredictions.style.display = 'block';

  // Hide the card panel and widen the container to let columns fit comfortably
  cardPanel.style.display = 'none';
  contentWrap.classList.add('wide-layout');
  
  loadPredictions();
});

async function loadPredictions() {
  const container = document.getElementById('predictions-container');
  container.innerHTML = `<div class="state-msg"><span class="icon">⏳</span>Loading tournament predictions...</div>`;

  try {
    const res = await fetch(PREDICTIONS_SHEET_CSV_URL);
    if (!res.ok) throw new Error("Could not fetch predictions spreadsheet");
    const csvText = await res.text();

    const rows = csvText.split(/\r?\n/).map(row => row.split(','));
    if (rows.length < 3) throw new Error("Spreadsheet contains empty data");

    // 🔍 Dynamic Header Finder:
    // Scan the first 10 rows to locate the row containing player names
    let headerRow = null;
    let headerRowIdx = -1;
    for (let r = 0; r < Math.min(rows.length, 10); r++) {
      const row = rows[r];
      const hasBabu = row.some(cell => cell && cell.trim() === 'Babu');
      if (hasBabu) {
        headerRow = row;
        headerRowIdx = r;
        break;
      }
    }

    if (!headerRow) {
      throw new Error("Could not locate player headers in the spreadsheet");
    }

    // 🔍 Dynamic Column Mapper:
    // Safely maps each player name to their exact column index in the sheet
    const players = [];
    for (let c = 0; c < headerRow.length; c++) {
      const val = headerRow[c] ? headerRow[c].trim() : '';
      if (PLAYER_INFO[val]) {
        players.push({ name: val, colIndex: c });
      }
    }

    let html = '';
    let isContainerOpen = false;

    // Start looping through the rows immediately following the discovered header row
    for (let idx = headerRowIdx + 1; idx < rows.length; idx++) {
      const row = rows[idx];
      if (!row || row.length < 3) continue;

      // Column B (index 1) is match number
      // Column C (index 2) is Team 1
      // Column D (index 3) is Team 2
      const matchNum = row[1] ? row[1].trim() : '';
      const team1 = row[2] ? row[2].trim() : '';
      const team2 = row[3] ? row[3].trim() : '';

      // Detect Phase boundaries dynamically to split into standalone cards
      if (!matchNum && (team1.includes("Phase") || team1.includes("Round") || team1.includes("Quarter") || team1.includes("Semi") || team1.includes("Third") || team1.includes("Final"))) {
        
        // If there's already a phase card open, close it before opening the next one
        if (isContainerOpen) {
          html += `</div></div></div></div>`;
        }

        html += `
          <div class="predictions-stage-section">
            <div class="stage-section-header">
              <h3>${escHtml(team1 || team2)}</h3>
            </div>
            <div class="predictions-flex-container">
              <div class="predictions-flex-table">
                <div class="pred-header">
                  <div class="cell-match-info">Match</div>
                  ${players.map(p => `<div class="cell-player-header">${escHtml(p.name)}</div>`).join('')}
                </div>
                <div class="pred-body">`;

        isContainerOpen = true;
        continue;
      }

      // Render standard prediction row inside the current open card
      if (matchNum && !isNaN(matchNum)) {
        html += `<div class="pred-row">
                   <div class="cell-match-info">
                     <span class="m-num">${matchNum}</span>
                     <span class="m-teams">${escHtml(team1)} vs ${escHtml(team2)}</span>
                   </div>`;

        // Render player prediction values using their dynamically mapped columns
        for (let i = 0; i < players.length; i++) {
          const colIdx = players[i].colIndex;
          const pred = row[colIdx] ? row[colIdx].trim().toUpperCase() : '';
          let predClass = '';
          
          if (pred === '1') predClass = 'pred-home';
          else if (pred === '2') predClass = 'pred-away';
          else if (pred === 'X') predClass = 'pred-draw';

          html += `<div class="cell-player-pred ${predClass}">${escHtml(pred)}</div>`;
        }
        html += `</div>`;
      }
    }

    // Close the final active section card container
    if (isContainerOpen) {
      html += `</div></div></div></div>`;
    }

    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `
      <div class="state-msg">
        <span class="icon">⚠️</span>
        Couldn't load predictions spreadsheet.<br>
        <small style="margin-top:6px;display:block;font-size:11px;opacity:0.7">${escHtml(err.message)}</small>
      </div>`;
  }
}