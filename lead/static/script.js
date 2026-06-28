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

// ⚽ Matches tab CSV (for live outcome colour-coding in the Predictions matrix):
const MATCHES_SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT8fEdr0djoTa4bc8diSdwH2xSDJ4JTlNgHUWho8lQ5btMR9Joe3sXhZPP72oTSE9MBdoYKrY4DlFl9/pub?gid=0&single=true&output=csv';

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


const TEAM_FLAGS = {
  'Mexico': '🇲🇽', 'South Africa': '🇿🇦', 'South Korea': '🇰🇷', 'Czechia': '🇨🇿',
  'Canada': '🇨🇦', 'Bosnia & Herz.': '🇧🇦', 'Bosnia': '🇧🇦', 'USA': '🇺🇸', 'Paraguay': '🇵🇾',
  'Qatar': '🇶🇦', 'Switzerland': '🇨🇭', 'Brazil': '🇧🇷', 'Morocco': '🇲🇦',
  'Haiti': '🇭🇹', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', 'Australia': '🇦🇺', 'Turkiye': '🇹🇷',
  'Germany': '🇩🇪', 'Curacao': '🇨🇼', 'Netherlands': '🇳🇱', 'Japan': '🇯🇵',
  'Ivory Coast': '🇨🇮', 'Ecuador': '🇪🇨', 'Sweden': '🇸🇪', 'Tunisia': '🇹🇳',
  'Spain': '🇪🇸', 'Cape Verde': '🇨🇻', 'Belgium': '🇧🇪', 'Egypt': '🇪🇬',
  'Saudi Arabia': '🇸🇦', 'Uruguay': '🇺🇾', 'Iran': '🇮🇷', 'New Zealand': '🇳🇿',
  'France': '🇫🇷', 'Senegal': '🇸🇳', 'Iraq': '🇮🇶', 'Norway': '🇳🇴',
  'Argentina': '🇦🇷', 'Algeria': '🇩🇿', 'Austria': '🇦🇹', 'Jordan': '🇯🇴',
  'Portugal': '🇵🇹', 'Congo DR': '🇨🇩', 'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Croatia': '🇭🇷',
  'Ghana': '🇬🇭', 'Panama': '🇵🇦', 'Uzbekistan': '🇺🇿', 'Colombia': '🇨🇴',
  'Denmark': '🇩🇰', 'Serbia': '🇷🇸', 'Poland': '🇵🇱', 'Nigeria': '🇳🇬',
  'Cameroon': '🇨🇲', 'Peru': '🇵🇪', 'Wales': '🏴󠁧󠁢󠁷󠁬󠁳󠁿',
};

function getFlag(team) {
  return TEAM_FLAGS[team] || '🏳️';
}

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
  panel.appendChild(innerLayout);

  const visibleClone = imgEl.cloneNode(true);
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

btnStandings.addEventListener('click', () => {
  btnStandings.classList.add('active');
  btnPredictions.classList.remove('active');
  btnAnalysis.classList.remove('active');
  viewStandings.style.display = 'block';
  viewPredictions.style.display = 'none';
  viewAnalysis.style.display = 'none';
  // Restore compact layout and show card panel for standings
  document.querySelector('.content-wrap').classList.remove('wide-layout');
  document.getElementById('card-panel').style.display = '';
});

btnPredictions.addEventListener('click', () => {
  btnPredictions.classList.add('active');
  btnStandings.classList.remove('active');
  btnAnalysis.classList.remove('active');
  viewStandings.style.display = 'none';
  viewPredictions.style.display = 'block';
  viewAnalysis.style.display = 'none';
  // Expand layout and hide card panel for the wide predictions matrix
  document.querySelector('.content-wrap').classList.add('wide-layout');
  document.getElementById('card-panel').style.display = 'none';
  loadPredictions();
});

// Parses the Matches CSV and returns a map of { matchNumber -> outcome }
// Auto-detects the "Outcome" and "Match" column positions from headers
async function fetchMatchOutcomes() {
  const outcomeMap = {};
  try {
    const res = await fetch(MATCHES_SHEET_CSV_URL);
    if (!res.ok) return outcomeMap;
    const csvText = await res.text();
    const rows = csvText.split(/\r?\n/).map(row => row.split(','));

    // Log sample rows to console for debugging
    console.log('📋 Matches CSV sample rows:');
    rows.slice(0, 6).forEach((r, i) => console.log('Row ' + i + ':', JSON.stringify(r)));

    // Auto-detect Outcome and Match column indices from any header row in first 10
    let outcomeColIndex = 6; // fallback: column G
    let matchColIndex   = 1; // fallback: column B
    for (let i = 0; i < Math.min(rows.length, 10); i++) {
      const row = rows[i];
      const oIdx = row.findIndex(c => c.trim().toLowerCase() === 'outcome');
      const mIdx = row.findIndex(c => c.trim().toLowerCase() === 'match');
      if (oIdx !== -1) { outcomeColIndex = oIdx; }
      if (mIdx !== -1) { matchColIndex   = mIdx; }
      if (oIdx !== -1 && mIdx !== -1) break;
    }
    console.log('✅ Match col index:', matchColIndex, '| Outcome col index:', outcomeColIndex);

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (!row || row.length < 3) continue;
      const matchNum = row[matchColIndex] ? row[matchColIndex].trim() : '';
      const outcome  = row[outcomeColIndex] ? row[outcomeColIndex].trim().toUpperCase() : '';
      if (matchNum && !isNaN(matchNum) && (outcome === '1' || outcome === '2' || outcome === 'X')) {
        outcomeMap[matchNum] = outcome;
      }
    }
    console.log('⚽ Final outcome map:', outcomeMap);
  } catch (err) {
    console.warn('⚠️ Could not fetch match outcomes:', err);
  }
  return outcomeMap;
}

async function loadPredictions() {
  const container = document.getElementById('predictions-container');
  container.innerHTML = `<div class="state-msg"><span class="icon">⏳</span>Loading tournament predictions...</div>`;

  try {
    // Fetch predictions and match outcomes in parallel
    const [predRes, outcomeMap] = await Promise.all([
      fetch(PREDICTIONS_SHEET_CSV_URL),
      fetchMatchOutcomes(),
    ]);

    if (!predRes.ok) throw new Error("Could not fetch predictions spreadsheet");
    const csvText = await predRes.text();

    const rows = csvText.split(/\r?\n/).map(row => row.split(','));
    if (rows.length < 3) throw new Error("Spreadsheet contains empty data");

    // Dynamic Header parser: Grabs players directly from Row 2 of the sheet (index 1 in CSV array)
    const headerRow = rows[1]; 
    const players = [];
    for (let c = 4; c <= 17; c++) {
      if (headerRow[c]) players.push(headerRow[c].trim());
    }

    // Build responsive flex matrix
    let html = `<div class="predictions-flex-container">
                  <div class="predictions-flex-table">
                    <div class="pred-header">
                      <div class="cell-match-info">Match</div>
                      ${players.map(p => `<div class="cell-player-header">${escHtml(p)}</div>`).join('')}
                    </div>
                    <div class="pred-body">`;

    for (let idx = 2; idx < rows.length; idx++) {
      const row = rows[idx];
      if (!row || row.length < 5) continue;

      const matchNum = row[1] ? row[1].trim() : '';
      const team1    = row[2] ? row[2].trim() : '';
      const team2    = row[3] ? row[3].trim() : '';

      // Detect visual stages (like "Group Phase", "Round of 32") in merged columns
      if (!matchNum && (team1.includes("Phase") || team1.includes("Round") || team1.includes("Quarter") || team1.includes("Semi") || team1.includes("Third") || team1.includes("Final"))) {
        html += `<div class="stage-header-row-flex">
                   <div class="stage-header-title">${escHtml(team1 || team2)}</div>
                 </div>`;
        continue;
      }

      // Render standard prediction row
      if (matchNum && !isNaN(matchNum)) {
        const actualOutcome = outcomeMap[matchNum] || ''; // e.g. "1", "2", "X", or "" if not played

        html += `<div class="pred-row">
                   <div class="cell-match-info">
                     <span class="m-num">${matchNum}</span>
                     <div class="m-fixture">
                       <span class="m-team-name">${escHtml(team1)}</span>
                       <span class="m-vs-badge">VS</span>
                       <span class="m-team-name">${escHtml(team2)}</span>
                     </div>
                   </div>`;

        // Render cell prediction values (Cols E to R -> indices 4 to 17)
        for (let c = 4; c <= 17; c++) {
          const pred = row[c] ? row[c].trim().toUpperCase() : '';

          let cellClass = '';
          if (!pred) {
            // Empty cell — no prediction made
            cellClass = '';
          } else if (actualOutcome) {
            // Match has a result — show correct (green) or wrong (red)
            cellClass = pred === actualOutcome ? 'pred-correct' : 'pred-wrong';
          } else {
            // Match not yet played — neutral muted tint, no right/wrong implied
            cellClass = 'pred-neutral';
          }

          html += `<div class="cell-player-pred ${cellClass}">${escHtml(pred)}</div>`;
        }
        html += `</div>`;
      }
    }

    html += `</div></div></div>`;
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

// ══════════════════════════════════════════════════════
//  Performance Ticker Bar — IPO Stock Market Model
//
//  Every player starts at $100.00 (IPO price).
//  Correct prediction  → +$1.00
//  Wrong prediction    → −$1.00
//
//  Display:  BABU  $124.00  ▲+2.41%
//
//  "Price"  = $100 + (rights − wrongs)  e.g. $124.00
//  "Change" = % move over last 5 predictions:
//             ( net_last5 / price_before_last5 ) * 100
//             This is a true financial % — no div-by-zero
//             because the base is always ≥ $100 - n, never 0
// ══════════════════════════════════════════════════════

const IPO_PRICE    = 100; // baseline share price
const TICKER_WINDOW = 5;  // last N predictions for the % change

async function buildTickerData() {
  const [overallRes, scoringRes] = await Promise.all([
    fetch(ENDPOINTS['lead']).then(r => r.ok ? r.json() : null).catch(() => null),
    fetch(SCORING_SHEET_CSV_URL).catch(() => null),
  ]);

  if (!overallRes || !overallRes.ok || !overallRes.players.length) return null;

  // playerSeq: { name: [1,0,1,1,0,...] } — only actual predictions (strict 1/0)
  const playerSeq = {};

  if (scoringRes && scoringRes.ok) {
    const csvText = await scoringRes.text();
    const rows = csvText.split(/\r?\n/).map(row => row.split(','));

    const headerRow = rows[2] || [];
    const colToPlayer = {};
    headerRow.forEach((cell, idx) => {
      const name = cell.trim();
      if (PLAYER_INFO[name]) {
        colToPlayer[idx] = name;
        playerSeq[name]  = [];
      }
    });

    const playerCols = Object.keys(colToPlayer).map(Number);

    for (let r = 3; r < rows.length; r++) {
      const row = rows[r];
      if (!row || row.length < 3) continue;

      // 1. Verify the row is an actual match (Match column is index 1)
      const matchNumStr = (row[1] || '').trim();
      const matchNum = parseInt(matchNumStr, 10);
      
      // If the match number is blank, not a number, or outside 1-72, skip the row
      if (isNaN(matchNum) || matchNum < 1 || matchNum > 72) {
        continue;
      }

      // 2. Only proceed if at least one player has a graded prediction in this row
      const isPlayedRow = playerCols.some(idx => {
        const v = (row[idx] || '').trim();
        return v === '1' || v === '0';
      });
      if (!isPlayedRow) continue;

      playerCols.forEach(idx => {
        const name = colToPlayer[idx];
        const val  = (row[idx] || '').trim();
        if (val === '1') playerSeq[name].push(1);
        if (val === '0') playerSeq[name].push(0);
        // blank = no prediction made → skip, don't penalise
      });
    }

    console.log('📈 Ticker IPO sequences:', Object.fromEntries(
      Object.entries(playerSeq).map(([k,v]) => {
        const net = v.reduce((a,b) => a + (b===1?1:-1), 0);
        return [k, `${v.length} played · price $${(IPO_PRICE + net).toFixed(2)} · last5: [${v.slice(-5)}]`];
      })
    ));
  }

  // Current stock price = IPO + net (+1 per right, -1 per wrong)
  function getPrice(name) {
    const seq = playerSeq[name] || [];
    if (!seq.length) return IPO_PRICE;
    const net = seq.reduce((a, b) => a + (b === 1 ? 1 : -1), 0);
    return IPO_PRICE + net;
  }

  // % change over last TICKER_WINDOW predictions
  // = (net_of_last_N / price_before_last_N) * 100
  // Base price is always ≥ ~$70 in practice — never zero, no math issues
  function getChange(name) {
    const seq = playerSeq[name] || [];
    if (seq.length < TICKER_WINDOW + 1) return { pct: null, trend: 'flat' };

    const window   = seq.slice(-TICKER_WINDOW);
    const netMoves = window.reduce((a, b) => a + (b === 1 ? 1 : -1), 0);

    // Price just before the window started
    const before    = seq.slice(0, -TICKER_WINDOW);
    const beforeNet = before.reduce((a, b) => a + (b === 1 ? 1 : -1), 0);
    const basePrice = IPO_PRICE + beforeNet;

    const pct = (netMoves / basePrice) * 100;

    return {
      pct,
      net:   netMoves,
      trend: netMoves > 0 ? 'up' : netMoves < 0 ? 'down' : 'flat',
    };
  }

  return overallRes.players.map((p, i) => {
    const price  = getPrice(p.name);
    const change = getChange(p.name);
    return {
      rank:   i + 1,
      name:   p.name,
      price,                    // e.g. 124.00
      ytd:    price - IPO_PRICE, // net profit vs IPO e.g. +24
      change,                   // { pct, net, trend }
      played: (playerSeq[p.name] || []).length,
    };
  });
}

function renderTickerItem(p) {
  // "Stock price"  →  $124.00
  const priceStr = '$' + p.price.toFixed(2);

  // YTD return  →  +24.00%
  const ytdPct    = ((p.price - IPO_PRICE) / IPO_PRICE) * 100;
  const ytdSign   = ytdPct >= 0 ? '+' : '';
  const ytdStr    = ytdSign + ytdPct.toFixed(2) + '%';
  const ytdCls    = ytdPct > 0 ? 'up' : ytdPct < 0 ? 'down' : 'flat';

  // Recent change  →  ▲+2.41%  or  ▼-1.94%
  let changeStr = '';
  let changeCls = 'flat';
  let arrow     = '●';

  if (p.change.pct !== null) {
    const sign = p.change.pct >= 0 ? '+' : '';
    changeStr  = sign + p.change.pct.toFixed(2) + '%';
    changeCls  = p.change.trend;
    arrow      = p.change.trend === 'up' ? '▲' : p.change.trend === 'down' ? '▼' : '●';
  }

  const tooltip = [
    p.name,
    `Price: ${priceStr}`,
    `YTD: ${ytdStr}`,
    p.change.pct !== null ? `Last ${TICKER_WINDOW}: ${arrow}${changeStr}` : '',
    `${p.played} predictions`,
  ].filter(Boolean).join(' · ');

  return `<span class="ticker-item" title="${tooltip}">
    <span class="ticker-rank">${p.rank}</span>
    <span class="ticker-name">${p.name}</span>
    <span class="ticker-price">${priceStr}</span>
    <span class="ticker-ytd ${ytdCls}">${ytdSign}${ytdPct.toFixed(2)}%</span>
    ${p.change.pct !== null
      ? `<span class="ticker-delta ${changeCls}">${arrow}${changeStr}</span>`
      : ''}
  </span>`;
}

async function initTicker() {
  const track = document.getElementById('ticker-track');
  if (!track) return;

  const players = await buildTickerData();

  if (!players || !players.length) {
    track.innerHTML = `<span class="ticker-loading">No data yet</span>`;
    return;
  }

  const html = players.map(renderTickerItem).join('');
  // Duplicate for seamless infinite scroll
  track.innerHTML = html + html;
  track.classList.add('running');

  // Adjust speed based on content width so it always feels smooth
  const totalW = track.scrollWidth / 2; // half = one full set
  const speed = Math.max(30, Math.min(60, totalW / 80)); // px/s → seconds
  track.style.animationDuration = speed + 's';
}

// Boot the ticker alongside the rest of the page
initTicker();

// ══════════════════════════════════════════════════════
//  Analysis Tab Navigation, Live Charting & Shock Detector
// ══════════════════════════════════════════════════════

const btnAnalysis = document.getElementById('btn-analysis');
const viewAnalysis = document.getElementById('view-analysis');
let chartInstance = null;

btnAnalysis.addEventListener('click', () => {
  btnAnalysis.classList.add('active');
  btnStandings.classList.remove('active');
  btnPredictions.classList.remove('active');
  
  viewStandings.style.display = 'none';
  viewPredictions.style.display = 'none';
  viewAnalysis.style.display = 'block';

  // Format layout for wide chart view
  document.querySelector('.content-wrap').classList.add('wide-layout');
  document.getElementById('card-panel').style.display = 'none';
  
  // Trigger loaders
  renderLiveAnalysisChart();
  generateMarketShocks();
  loadAnalysisArticles();
});

// Calculate raw prediction arrays for the chart dataset
async function fetchChartSeries() {
  const res = await fetch(SCORING_SHEET_CSV_URL);
  if (!res.ok) return null;
  const csvText = await res.text();
  const rows = csvText.split(/\r?\n/).map(row => row.split(','));

  const headerRow = rows[2] || [];
  const colToPlayer = {};
  const playerSeries = {};

  headerRow.forEach((cell, idx) => {
    const name = cell.trim();
    if (PLAYER_INFO[name]) {
      colToPlayer[idx] = name;
      playerSeries[name] = [0]; // All players start at 0 ($100 IPO)
    }
  });

  const playerCols = Object.keys(colToPlayer).map(Number);

  for (let r = 3; r < rows.length; r++) {
    const row = rows[r];
    if (!row || row.length < 3) continue;

    const matchNumStr = (row[1] || '').trim();
    const matchNum = parseInt(matchNumStr, 10);
    if (isNaN(matchNum) || matchNum < 1 || matchNum > 72) continue;

    const isPlayedRow = playerCols.some(idx => {
      const v = (row[idx] || '').trim();
      return v === '1' || v === '0';
    });
    if (!isPlayedRow) continue;

    playerCols.forEach(idx => {
      const name = colToPlayer[idx];
      const val  = (row[idx] || '').trim();
      const lastVal = playerSeries[name][playerSeries[name].length - 1];
      
      if (val === '1') playerSeries[name].push(lastVal + 1);
      else if (val === '0') playerSeries[name].push(lastVal - 1);
      else playerSeries[name].push(lastVal); // Keep previous flatline if match skipped
    });
  }
  return playerSeries;
}

// Generate the interactive Chart.js graph inside the container
async function renderLiveAnalysisChart() {
  const ctx = document.getElementById('analysisChart');
  if (!ctx) return;

  const series = await fetchChartSeries();
  if (!series) return;

  const playerNames = Object.keys(series);
  const maxMatches = Math.max(...playerNames.map(name => series[name].length));
  
  // X-Axis Labels (0, Match 1, Match 2, ...)
  const labels = Array.from({ length: maxMatches }, (_, i) => i === 0 ? "IPO" : `${i}`);

  const colors = [
    '#1fc269', '#f4c542', '#ef3b46', '#1E90FF', '#FF00FF', 
    '#00FFFF', '#FFA500', '#ADFF2F', '#D2691E', '#8A2BE2'
  ];

  const datasets = playerNames.map((name, i) => {
    // Translate score coordinates back to IPO dollar values ($100 basis)
    const dollarValues = series[name].map(score => 100 + score);
    return {
      label: name,
      data: dollarValues,
      borderColor: colors[i % colors.length],
      backgroundColor: 'transparent',
      borderWidth: 2,
      tension: 0.2, // Smoothed curves
      pointRadius: 1,
      pointHoverRadius: 4,
    };
  });

  if (chartInstance) {
    chartInstance.destroy();
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#f6f0df', font: { family: 'Oswald', size: 10 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: $${ctx.raw.toFixed(2)} (${((ctx.raw - 100)).toFixed(0)} pts)`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(41, 72, 58, 0.15)' },
          ticks: { color: '#8aaa8e', font: { family: 'Oswald', size: 10 } }
        },
        y: {
          grid: { color: 'rgba(41, 72, 58, 0.15)' },
          ticks: { color: '#8aaa8e', font: { family: 'Oswald', size: 10 } }
        }
      }
    }
  });
}

// Scans matrices dynamically for "Upset Shocks" (Matches where only 1 or 2 players got it right)
async function generateMarketShocks() {
  const container = document.getElementById('shocks-list');
  if (!container) return;

  try {
    const [predRes, outcomeMap] = await Promise.all([
      fetch(PREDICTIONS_SHEET_CSV_URL),
      fetchMatchOutcomes(),
    ]);

    if (!predRes.ok) return;
    const csvText = await predRes.text();
    const rows = csvText.split(/\r?\n/).map(row => row.split(','));

    const headerRow = rows[1] || [];
    const players = [];
    for (let c = 4; c <= 17; c++) {
      if (headerRow[c]) players.push(headerRow[c].trim());
    }

    const shocks = [];

    for (let idx = 2; idx < rows.length; idx++) {
      const row = rows[idx];
      if (!row || row.length < 5) continue;

      const matchNum = row[1] ? row[1].trim() : '';
      const team1    = row[2] ? row[2].trim() : '';
      const team2    = row[3] ? row[3].trim() : '';
      const actualOutcome = outcomeMap[matchNum] || '';

      if (matchNum && !isNaN(matchNum) && actualOutcome) {
        const correctTraders = [];
        
        for (let c = 4; c <= 17; c++) {
          const pred = row[c] ? row[c].trim().toUpperCase() : '';
          const playerName = headerRow[c] ? headerRow[c].trim() : '';
          if (pred === actualOutcome) {
            correctTraders.push(playerName);
          }
        }

        if (correctTraders.length === 1 || correctTraders.length === 2) {
          shocks.push({
            num: matchNum,
            fixture: `${team1} vs ${team2}`,
            traders: correctTraders.join(', ')
          });
        }
      }
    }

    if (!shocks.length) {
      container.innerHTML = `<span class="ticker-loading">No market anomalies or extreme upsets detected yet.</span>`;
      return;
    }

    container.innerHTML = shocks.map(s => `
      <div class="shock-item">
        <span class="m-num" style="border-color: rgba(244,197,66,0.3)">M${s.num}</span>
        <span class="shock-fixture">${escHtml(s.fixture)}</span>
        <span class="shock-traders">Correct: ${escHtml(s.traders)} ⚡</span>
      </div>
    `).join('');

  } catch (err) {
    container.innerHTML = `<span class="ticker-loading">Failed to scan market shocks.</span>`;
  }
}

// Fetch and populate analysis commentary from external JSON file
async function loadAnalysisArticles() {
  try {
    const res = await fetch('/ui/analysis.json');
    if (!res.ok) throw new Error("Could not load analysis.json");
    const data = await res.json();

    // Populate titles and text dynamically
    document.getElementById('q1-title').innerText = data.q1.title;
    document.getElementById('p1-text').innerText = data.q1.text;

    document.getElementById('q2-title').innerText = data.q2.title;
    document.getElementById('p2-text').innerText = data.q2.text;

    document.getElementById('q3-title').innerText = data.q3.title;
    document.getElementById('p3-text').innerText = data.q3.text;

    document.getElementById('macro-title').innerText = data.macro.title;
    document.getElementById('macro-text').innerText = data.macro.text;

  } catch (err) {
    console.warn("⚠️ Failed to load analysis articles:", err);
    ['q1', 'q2', 'q3', 'macro'].forEach(key => {
      const el = document.getElementById(`${key}-title`);
      if (el) el.innerText = "Error loading commentary.";
    });
  }
}