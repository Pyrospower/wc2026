const ENDPOINTS = {
  lead: '/preview',
  m1:   '/m1/preview',
  m2:   '/m2/preview',
  m3:   '/m3/preview',
  m4:   '/m4/preview', 
};

const MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' };

const CARD_URL = 'https://wc2026-i9es.onrender.com/card';

// Sheet name -> { avatar, discord username for card URL }
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
  const info = PLAYER_INFO[name];

  if (!info) {
    panel.innerHTML = `<div class="card-placeholder"><p>No card found for ${escHtml(name)}</p></div>`;
    return;
  }

  const url = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc`;

  panel.innerHTML = `
    <div class="card-inner">
      <div class="card-name">${escHtml(name)}</div>
      <img
        class="card-img"
        src="${url}"
        alt="${escHtml(name)}'s card"
        onerror="this.parentElement.innerHTML='<div class=\\'card-placeholder\\'><p>Card unavailable</p></div>'"
      />
    </div>`;

  // highlight selected row
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
    
    // 1. Render the main dashboard table layout
    container.innerHTML = renderTable(data.players);
    attachRowClicks();
    if (selectedPlayer) showCard(selectedPlayer);

    // 2. STAGGERED PRELOADER SEQUENCE: Silently caches players one-by-one
    console.log("🏁 Leaderboard loaded! Kicking off card preloader sequence...");
    const players = Object.keys(PLAYER_INFO);
    players.forEach((name, index) => {
      setTimeout(() => {
        const info = PLAYER_INFO[name];
        if (info) {
          const preloadImg = new Image();
          preloadImg.src = `${CARD_URL}?avatar=${info.avatar}&user=${encodeURIComponent(info.user)}&bg=gc`;
          console.log(`📡 Preloaded card in background for: ${name}`);
        }
      }, index * 300); // 300ms pause spacing stops Render from choking
    });

  } catch (err) {
    container.innerHTML = `
      <div class="state-msg">
        <span class="icon">⚠️</span>
        Couldn't load scores.<br>
        <small style="margin-top:6px;display:block;font-size:11px;opacity:0.7">${escHtml(err.message)}</small>
      </div>`;
  }
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

// Kick off initial call
loadBoard('lead');