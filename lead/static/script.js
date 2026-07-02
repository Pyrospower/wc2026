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
const CARD_URL = 'https://baburu-wc2026-cards.hf.space/card';

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

// 🌐 Cache-busting helper to ensure we skip CDN/Browser caching layers
async function fetchFresh(url) {
  const separator = url.includes('?') ? '&' : '?';
  return fetch(`${url}${separator}_cb=${Date.now()}`, { cache: 'no-store' });
}

// Dynamic Google Sheets Matrix Parser Engine
async function fetchLiveWinRates() {
  try {
    const response = await fetchFresh(SCORING_SHEET_CSV_URL);
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
    const freshEndpointUrl = `${ENDPOINTS[boardKey]}?_cb=${Date.now()}`;
    const res = await fetch(freshEndpointUrl);
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

// Loads a single player's card image into the vault
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
  document.querySelector('.content-wrap').classList.add('wide-layout');
  document.getElementById('card-panel').style.display = 'none';
  loadPredictions();
});

// Parses the Matches CSV and returns a map of { matchNumber -> outcome }
async function fetchMatchOutcomes() {
  const outcomeMap = {};
  try {
    const res = await fetchFresh(MATCHES_SHEET_CSV_URL);
    if (!res.ok) return outcomeMap;
    const csvText = await res.text();
    const rows = csvText.split(/\r?\n/).map(row => row.split(','));

    console.log('📋 Matches CSV sample rows:');
    rows.slice(0, 6).forEach((r, i) => console.log('Row ' + i + ':', JSON.stringify(r)));

    let outcomeColIndex = 6; 
    let matchColIndex   = 1; 
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
    const [predRes, outcomeMap] = await Promise.all([
      fetchFresh(PREDICTIONS_SHEET_CSV_URL),
      fetchMatchOutcomes(),
    ]);

    if (!predRes.ok) throw new Error("Could not fetch predictions spreadsheet");
    const csvText = await predRes.text();

    const rows = csvText.split(/\r?\n/).map(row => row.split(','));
    if (rows.length < 3) throw new Error("Spreadsheet contains empty data");

    const headerRow = rows[1]; 
    const players = [];
    for (let c = 4; c <= 17; c++) {
      if (headerRow[c]) players.push(headerRow[c].trim());
    }

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

      if (!matchNum && (team1.includes("Phase") || team1.includes("Round") || team1.includes("Quarter") || team1.includes("Semi") || team1.includes("Third") || team1.includes("Final"))) {
        html += `<div class="stage-header-row-flex">
                   <div class="stage-header-title">${escHtml(team1 || team2)}</div>
                 </div>`;
        continue;
      }

      if (matchNum && !isNaN(matchNum)) {
        const actualOutcome = outcomeMap[matchNum] || ''; 

        html += `<div class="pred-row">
                   <div class="cell-match-info">
                     <span class="m-num">${matchNum}</span>
                     <div class="m-fixture">
                       <span class="m-team-name">${escHtml(team1)}</span>
                       <span class="m-vs-badge">VS</span>
                       <span class="m-team-name">${escHtml(team2)}</span>
                     </div>
                   </div>`;

        for (let c = 4; c <= 17; c++) {
          const pred = row[c] ? row[c].trim().toUpperCase() : '';

          let cellClass = '';
          if (!pred) {
            cellClass = '';
          } else if (actualOutcome) {
            cellClass = pred === actualOutcome ? 'pred-correct' : 'pred-wrong';
          } else {
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
//  Performance Ticker Bar now lives in ticker.js
//  (shared/loaded on every page). This file just calls the
//  global window.initTicker() that ticker.js exposes,
//  from refreshActiveView() further down, on refresh clicks.
// ══════════════════════════════════════════════════════

// 🎬 Initialization Pipeline
const leadBoardPromise = loadBoard('lead');
fetchLiveWinRates();

const wakePingPromise = fetch('https://wc2026-i9es.onrender.com/', { mode: 'no-cors' }).catch(() => {});

Promise.all([leadBoardPromise, wakePingPromise]).then(() => {
  triggerBackgroundPreload();
});

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

  document.querySelector('.content-wrap').classList.add('wide-layout');
  document.getElementById('card-panel').style.display = 'none';
  
  renderLiveAnalysisChart();
  generateMarketShocks();
  loadAnalysisArticles();
});

async function fetchChartSeries() {
  const res = await fetchFresh(SCORING_SHEET_CSV_URL);
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
      playerSeries[name] = [0]; 
    }
  });

  const playerCols = Object.keys(colToPlayer).map(Number);

  for (let r = 3; r < rows.length; r++) {
    const row = rows[r];
    if (!row || row.length < 3) continue;

    const matchNumStr = (row[1] || '').trim();
    const matchNum = parseInt(matchNumStr, 10);
    
    if (isNaN(matchNum) || matchNum < 1 || matchNum > 104) continue;

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
      else playerSeries[name].push(lastVal); 
    });
  }
  return playerSeries;
}

async function renderLiveAnalysisChart() {
  const ctx = document.getElementById('analysisChart');
  if (!ctx) return;

  const series = await fetchChartSeries();
  if (!series) return;

  const playerNames = Object.keys(series);
  const maxMatches = Math.max(...playerNames.map(name => series[name].length));
  
  const labels = Array.from({ length: maxMatches }, (_, i) => i === 0 ? "IPO" : `${i}`);

  const colors = [
    '#1fc269', '#f4c542', '#ef3b46', '#1E90FF', '#FF00FF', 
    '#00FFFF', '#FFA500', '#ADFF2F', '#D2691E', '#8A2BE2'
  ];

  const datasets = playerNames.map((name, i) => {
    const dollarValues = series[name].map(score => 100 + score);
    return {
      label: name,
      data: dollarValues,
      borderColor: colors[i % colors.length],
      backgroundColor: 'transparent',
      borderWidth: 2,
      tension: 0.2, 
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

async function generateMarketShocks() {
  const container = document.getElementById('shocks-list');
  if (!container) return;

  try {
    const [predRes, outcomeMap] = await Promise.all([
      fetchFresh(PREDICTIONS_SHEET_CSV_URL),
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

// 🌐 Article visual identity — derived dynamically from analysis.json, no hardcoded list needed
const ARTICLE_COLOR_PALETTE = [
  { color: '#f4c542', accent: '#c99b35' }, // gold
  { color: '#8acdff', accent: '#5faae0' }, // blue
  { color: '#1fc269', accent: '#17a356' }, // green
  { color: '#ef3b46', accent: '#c22e38' }, // red
  { color: '#c8dcc0', accent: '#9eb89a' }, // sage
  { color: '#b896ff', accent: '#9170d9' }, // purple
];

function hashKeyToIndex(key, mod) {
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  return hash % mod;
}

function getArticleMeta(key, article) {
  // Icon: leading emoji from the title, falling back to a generic icon
  const emojiMatch = article.title.match(/^[\p{Emoji}\u200d\ufe0f]+/u);
  const icon = emojiMatch ? emojiMatch[0].trim() : '📋';
  // Category: straight from the JSON, falling back to a generic label
  const category = (article.category || 'ANALYSIS').toUpperCase();
  // Color: stable pseudo-random pick per article key, so it's consistent across loads
  const palette = ARTICLE_COLOR_PALETTE[hashKeyToIndex(key, ARTICLE_COLOR_PALETTE.length)];
  return { category, icon, color: palette.color, accent: palette.accent };
}

function buildArticleThumbnail(key, article, meta) {
  const color = meta.color;
  const accent = meta.accent;
  const icon = meta.icon;

  // If the article supplies a real thumbnail image, use it as the background art —
  // light overlay just for contrast against the accent bar, photo stays clear throughout
  const bgStyle = article.thumbnail
    ? `background-image:linear-gradient(180deg, rgba(7,19,15,0.02) 0%, rgba(7,19,15,0.08) 100%), url('${escHtml(article.thumbnail)}');background-size:cover;background-position:center 22%;`
    : '';

  // Skip the emoji icon when there's an actual photo — the image carries the visual weight instead
  const iconHtml = article.thumbnail ? '' : `<div class="article-thumb-icon">${icon}</div>`;

  return `
    <div class="article-thumb" style="--thumb-color:${color};--thumb-accent:${accent};${bgStyle}">
      ${iconHtml}
      <div class="article-thumb-bar"></div>
    </div>`;
}

function getArticlePreview(text) {
  // First ~120 chars of the body text, cut at a word boundary
  const plain = text.replace(/\n/g, ' ').trim();
  return plain.length > 130 ? plain.slice(0, 127).replace(/\s\S+$/, '') + '…' : plain;
}

// 🌐 Dynamic Commentary Generator & Article Compiler
async function loadAnalysisArticles() {
  const grid = document.getElementById('analysis-grid');
  if (!grid) return;

  const shocksContainer = document.getElementById('market-shocks-container');

  try {
    const [articlesRes] = await Promise.all([
      fetch(`/ui/analysis.json?_cb=${Date.now()}`),
    ]);

    if (!articlesRes.ok) throw new Error("Could not load analysis.json");
    const data = await articlesRes.json();

    // Reset grid while preserving the fixed Market Shocks card at the top
    grid.innerHTML = '';
    if (shocksContainer) grid.appendChild(shocksContainer);

    // Render each article as a clickable card thumbnail
    Object.keys(data).forEach(key => {
      const article = data[key];
      const meta = getArticleMeta(key, article);
      const preview = article.excerpt || getArticlePreview(article.text);
      const href = `/ui/article.html?id=${encodeURIComponent(key)}`;

      const card = document.createElement('a');
      card.className = 'article-card';
      card.href = href;
      // Open in same tab so back button works
      card.innerHTML = `
        ${buildArticleThumbnail(key, article, meta)}
        <div class="article-card-body">
          <div class="article-card-category" style="color:${meta.color}">${escHtml(meta.category)}</div>
          <div class="article-card-title">${escHtml(article.title.replace(/^[\p{Emoji}\s]+/u, '').trim())}</div>
          <p class="article-card-preview">${escHtml(preview)}</p>
          <span class="article-card-read">Read article →</span>
        </div>
      `;
      grid.appendChild(card);
    });

  } catch (err) {
    console.warn("⚠️ Failed to load analysis articles:", err);
    const errorCard = document.createElement('div');
    errorCard.className = 'analysis-card';
    errorCard.innerHTML = `<div class="analysis-card-header">Error loading commentary.</div>`;
    grid.appendChild(errorCard);
  }
}

// 🌐 Consolidated function to handle reloading all active views seamlessly
async function refreshActiveView() {
  await fetchLiveWinRates();
  await initTicker();

  if (btnStandings.classList.contains('active')) {
    await loadBoard(activeBoard);
  } else if (btnPredictions.classList.contains('active')) {
    await loadPredictions();
  } else if (btnAnalysis.classList.contains('active')) {
    await renderLiveAnalysisChart();
    await generateMarketShocks();
    await loadAnalysisArticles();
  }
}

// Wire standard refresh-btn to run the dynamic tab-specific updates
document.getElementById('refresh-btn').addEventListener('click', () => {
  refreshActiveView();
});