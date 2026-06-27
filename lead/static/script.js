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

const PERMANENT_IMAGE_CACHE = {};

let activeBoard = 'lead';
let selectedPlayer = null;

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showCard(name) {
  selectedPlayer = name;
  const panel = document.getElementById('card-panel');
  const info = PLAYER_INFO[name];

  if (!info) {
    panel.innerHTML = `<div class="card-placeholder"><p>No card found for ${escHtml(name)}</p></div>`;
    return;
  }

  if (!PERMANENT_IMAGE_CACHE[name]) {
    const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc`;
    const imgEl = new Image();
    imgEl.className = "card-img";
    imgEl.src = url;
    imgEl.alt = `${name}'s card`;
    imgEl.onerror = function() {
      this.parentElement.innerHTML = '<div class="card-placeholder"><p>Card unavailable</p></div>';
    };
    PERMANENT_IMAGE_CACHE[name] = imgEl;
  }

  const existingContainer = document.getElementById('preload-progress-container');
  panel.innerHTML = '';
  if (existingContainer) {
    panel.appendChild(existingContainer);
  }

  const innerLayout = document.createElement('div');
  innerLayout.className = 'card-inner';
  innerLayout.innerHTML = `
    <div class="card-name">${escHtml(name)}</div>
    <div class="card-img-holder"></div>
  `;
  panel.appendChild(innerLayout);
  panel.querySelector('.card-img-holder').appendChild(PERMANENT_IMAGE_CACHE[name]);

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

function triggerBackgroundPreload() {
  const players = Object.keys(PLAYER_INFO);
  const totalPlayers = players.length;
  let preloadedCount = 0;

  const progressContainer = document.getElementById('preload-progress-container');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressPercentText = document.getElementById('progress-percent');

  if (!progressContainer || !progressBarFill || !progressPercentText) return;

  progressContainer.classList.remove('hidden');
  
  players.forEach((name, index) => {
    setTimeout(() => {
      const info = PLAYER_INFO[name];
      if (info && !PERMANENT_IMAGE_CACHE[name]) {
        const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc`;
        const imgEl = new Image();
        imgEl.className = "card-img";
        imgEl.src = url;
        imgEl.alt = `${name}'s card`;
        imgEl.onerror = function() {
          this.parentElement.innerHTML = '<div class="card-placeholder"><p>Card unavailable</p></div>';
        };
        PERMANENT_IMAGE_CACHE[name] = imgEl;
      }

      preloadedCount++;
      const currentPercentage = Math.round((preloadedCount / totalPlayers) * 100);
      
      progressBarFill.style.width = `${currentPercentage}%`;
      progressPercentText.innerText = `${currentPercentage}%`;

      if (preloadedCount === totalPlayers) {
        setTimeout(() => {
          progressContainer.style.opacity = '0';
          setTimeout(() => {
            progressContainer.classList.add('hidden');
          }, 400); 
        }, 1200); 
      }

    }, index * 250);
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
setTimeout(triggerBackgroundPreload, 1200);