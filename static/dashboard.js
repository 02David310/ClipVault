/* ── Animated Purple Grid Background ── */
(function () {
    const canvas = document.getElementById('grid-canvas');
    const ctx    = canvas.getContext('2d');

    let W, H;
    const SPACING = 38;
    const LINE_COLOR = [124, 58, 237]; // Purple color matching --purple
    const DOT_COLOR = [168, 85, 247];  // Brighter purple matching --purple-bright
    
    // Scrolling offsets
    let offsetX = 0;
    let offsetY = 0;
    
    // Speed of scrolling (pixels per frame)
    const SPEED_X = 0.25; 
    const SPEED_Y = 0.25;

    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);

        // Update offsets for scrolling animation
        offsetX = (offsetX + SPEED_X) % SPACING;
        offsetY = (offsetY + SPEED_Y) % SPACING;

        // Draw vertical lines
        const startX = (offsetX - SPACING);
        ctx.lineWidth = 0.6;
        ctx.strokeStyle = `rgba(${LINE_COLOR[0]}, ${LINE_COLOR[1]}, ${LINE_COLOR[2]}, 0.08)`;
        
        for (let x = startX; x < W + SPACING; x += SPACING) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, H);
            ctx.stroke();
        }

        // Draw horizontal lines
        const startY = (offsetY - SPACING);
        for (let y = startY; y < H + SPACING; y += SPACING) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(W, y);
            ctx.stroke();
        }

        // Draw intersection dots
        ctx.fillStyle = `rgba(${DOT_COLOR[0]}, ${DOT_COLOR[1]}, ${DOT_COLOR[2]}, 0.25)`;
        for (let x = startX; x < W + SPACING; x += SPACING) {
            for (let y = startY; y < H + SPACING; y += SPACING) {
                ctx.beginPath();
                ctx.arc(x, y, 1.2, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Floating ambient glow orbs (large, slow moving)
        const time = Date.now() * 0.0005;
        for (let i = 0; i < 3; i++) {
            const ox = (W * 0.2 + i * W * 0.3) + Math.sin(time + i * 2.1) * 80;
            const oy = (H * 0.35 + i * H * 0.12) + Math.cos(time * 1.1 + i * 1.4) * 60;
            const grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, 260 + i * 60);
            grad.addColorStop(0, `rgba(120, 40, 240, ${0.045 + i * 0.012})`);
            grad.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.beginPath();
            ctx.arc(ox, oy, 320 + i * 60, 0, Math.PI * 2);
            ctx.fillStyle = grad;
            ctx.fill();
        }

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize);
    resize();
    draw();
})();

/* ── App Logic ── */
let allClips  = [];
let activeGame = 'all';

async function load() {
    const res = await fetch('/api/clips');
    allClips  = await res.json();

    const userRes = await fetch('/api/me');
    const user    = await userRes.json();
    if (user) {
        const name = user.name.split(' ')[0];
        document.getElementById('username').textContent = name + "'s";
    }

    renderStats();
    renderFilters();
    renderGrid();
}

async function sync() {
    await fetch('/api/sync', { method: 'POST' });
    setTimeout(load, 3000);
}

function renderStats() {
    const total  = allClips.length;
    const games  = [...new Set(allClips.map(c => c.game))].length;
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
    const games  = [...new Set(allClips.map(c => c.game))];
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
    const reversed  = [...filtered].reverse();

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

document.getElementById('modal').addEventListener('click', function (e) {
    if (e.target === this) closeModal();
});

load();
setInterval(load, 30000);