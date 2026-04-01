let allClips = [];
let activeGame = 'all';

async function load() {
    const res = await fetch('/api/clips');
    allClips = await res.json();
    renderStats();
    renderFilters();
    renderGrid();
}

async function sync() {
    await fetch('/api/sync', { method: 'POST' });
    setTimeout(load, 3000);
}

function renderStats() {
    const total = allClips.length;
    const games = [...new Set(allClips.map(c => c.game))].length;
    const latest = allClips.length ? allClips[allClips.length - 1].uploaded_at.split('T')[0] : '—';

    document.getElementById('stats').innerHTML = `
        <div class="stat">
            <div class="stat-label">Total Clips</div>
            <div class="stat-value">${total}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Games</div>
            <div class="stat-value">${games}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Last Upload</div>
            <div class="stat-value" style="font-size:18px;margin-top:6px">${latest}</div>
        </div>
    `;
}

function renderFilters() {
    const games = [...new Set(allClips.map(c => c.game))];
    const counts = {};
    allClips.forEach(c => counts[c.game] = (counts[c.game] || 0) + 1);

    let html = `<button class="filter-btn ${activeGame === 'all' ? 'active' : ''}" onclick="setFilter('all')">
        All <span class="count">${allClips.length}</span>
    </button>`;

    games.forEach(g => {
        html += `<button class="filter-btn ${activeGame === g ? 'active' : ''}" onclick="setFilter('${g}')">
            ${g} <span class="count">${counts[g]}</span>
        </button>`;
    });

    document.getElementById('filters').innerHTML = html;
}

function renderGrid() {
    const filtered = activeGame === 'all' ? allClips : allClips.filter(c => c.game === activeGame);
    const reversed = [...filtered].reverse();

    if (!reversed.length) {
        document.getElementById('grid').innerHTML = '<div class="empty">NO CLIPS YET</div>';
        return;
    }

    document.getElementById('grid').innerHTML = reversed.map(clip => `
        <div class="clip-card">
            <div class="clip-thumb" onclick="openModal('${clip.video_id}', '${clip.title.replace(/'/g, "\\'")}')">
                <img src="https://img.youtube.com/vi/${clip.video_id}/mqdefault.jpg" alt="">
                <div class="play-overlay"><div class="play-icon"></div></div>
            </div>
            <div class="clip-info">
                <div class="clip-title">${clip.title}</div>
                <div class="clip-meta">
                    <span class="clip-game">${clip.game}</span>
                    <span>${clip.uploaded_at.split('T')[0]}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function setFilter(game) {
    activeGame = game;
    renderFilters();
    renderGrid();
}

function openModal(videoId, title) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-iframe').src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
    document.getElementById('modal').classList.add('open');
}

function closeModal() {
    document.getElementById('modal').classList.remove('open');
    document.getElementById('modal-iframe').src = '';
}

document.getElementById('modal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

load();
setInterval(load, 30000);