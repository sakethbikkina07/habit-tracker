// ─── CONFIG ───
const API = '';
const ICONS = ['🏃','💪','📚','🧘','💧','🥗','😴','✍️','🎯','🎸','🧹','🌱','🧠','❤️','🏊','🚴','🎨','🍎','☕','🙏','💊','📝','🌅','🚶'];
const COLORS = ['#7c6ef8','#34d399','#f87171','#fbbf24','#60a5fa','#f472b6','#a78bfa','#4ade80','#fb923c','#22d3ee'];
const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

// ─── STATE ───
let selectedIcon = ICONS[0];
let selectedColor = COLORS[0];

// ─── INIT ───
document.addEventListener('DOMContentLoaded', () => {
  setGreeting();
  setSidebarDate();
  renderIconPicker();
  renderColorPicker();
  bindNav();
  bindModal();
  bindSidebar();
  loadPage('today');
});

// ─── SIDEBAR (hamburger) ───
function bindSidebar() {
  const hamburger = document.getElementById('hamburger');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const closeBtn = document.getElementById('sidebar-close');
  const topbarAdd = document.getElementById('topbar-add');

  function openSidebar() {
    sidebar.classList.add('open');
    hamburger.classList.add('open');
    overlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    hamburger.classList.remove('open');
    overlay.classList.remove('visible');
    document.body.style.overflow = '';
  }

  hamburger.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  closeBtn.addEventListener('click', closeSidebar);
  overlay.addEventListener('click', closeSidebar);

  // Close sidebar on nav item click (mobile)
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });

  // Topbar + button opens add modal
  if (topbarAdd) topbarAdd.addEventListener('click', openAddModal);
}

// ─── GREETING ───
function setGreeting() {
  const h = new Date().getHours();
  const el = document.getElementById('greeting-time');
  if (el) el.textContent = h < 12 ? 'Morning' : h < 17 ? 'Afternoon' : 'Evening';
}

function setSidebarDate() {
  const el = document.getElementById('sidebar-date');
  if (el) el.textContent = new Date().toLocaleDateString('en-US', { weekday:'long', month:'short', day:'numeric' });
}

// ─── NAVIGATION ───
function bindNav() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const page = btn.dataset.page;
      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadPage(page);
    });
  });
}

function loadPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  if (page === 'today') renderToday();
  else if (page === 'habits') renderHabits();
  else if (page === 'progress') renderProgress();
}

// ─── API HELPERS ───
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts
  });
  return res.json();
}

// ─── TODAY PAGE ───
async function renderToday() {
  const habits = await apiFetch('/api/habits');
  renderTodaySummary(habits);
  renderTodayList(habits);
}

function renderTodaySummary(habits) {
  const done = habits.filter(h => h.done_today).length;
  const total = habits.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  const bestStreak = habits.reduce((m, h) => Math.max(m, h.streak), 0);
  const el = document.getElementById('today-summary');
  el.innerHTML = `
    <div class="summary-card">
      <div class="card-label">Completed</div>
      <div class="card-value green">${done}/${total}</div>
      <div class="card-sub">habits today</div>
    </div>
    <div class="summary-card">
      <div class="card-label">Daily Progress</div>
      <div class="card-value accent">${pct}%</div>
      <div class="card-sub">${pct >= 80 ? '🔥 Great day!' : pct >= 50 ? '💪 Keep going' : '☀️ Just starting'}</div>
    </div>
    <div class="summary-card">
      <div class="card-label">Best Streak</div>
      <div class="card-value">${bestStreak}</div>
      <div class="card-sub">days in a row</div>
    </div>
  `;
}

function renderTodayList(habits) {
  const el = document.getElementById('today-habits');
  if (!habits.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">✦</div><p>Add your first habit to get started!</p></div>`;
    return;
  }
  el.innerHTML = habits.map(h => `
    <div class="habit-row ${h.done_today ? 'completed' : ''}" id="row-${h.id}">
      <button class="habit-check" onclick="toggleHabit(${h.id}, this)">
        ${h.done_today ? '✓' : ''}
      </button>
      <div class="habit-info">
        <div class="habit-name-row">
          <div class="habit-icon-badge" style="background:${hexOpacity(h.color,0.15)}">
            <span>${h.icon}</span>
          </div>
          <span class="habit-name">${h.name}</span>
        </div>
        <div class="habit-mini-week">
          ${h.week.map((d, i) => `
            <div class="mini-day ${d.done ? 'done' : ''} ${i === 6 ? 'today' : ''}" title="${d.date}"></div>
          `).join('')}
        </div>
      </div>
      <div class="habit-meta">
        <div class="streak-badge">🔥 ${h.streak}</div>
        <div class="rate-text">${h.rate}% this month</div>
      </div>
    </div>
  `).join('');
}

async function toggleHabit(id, btn) {
  const row = document.getElementById('row-' + id);
  const data = await apiFetch(`/api/habits/${id}/toggle`, { method: 'POST', body: JSON.stringify({}) });
  if (data.done) {
    row.classList.add('completed');
    btn.innerHTML = '✓';
    showToast('✓ Habit marked complete!');
  } else {
    row.classList.remove('completed');
    btn.innerHTML = '';
    showToast('Habit unmarked');
  }
  renderToday();
}

// ─── HABITS PAGE ───
async function renderHabits() {
  const habits = await apiFetch('/api/habits');
  const grid = document.getElementById('habits-grid');
  const empty = document.getElementById('habits-empty');
  if (!habits.length) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  grid.innerHTML = habits.map(h => `
    <div class="habit-card">
      <div class="habit-card-top">
        <div class="habit-card-icon" style="background:${hexOpacity(h.color,0.15)}">${h.icon}</div>
        <div class="habit-card-actions">
          <button class="icon-btn" onclick="openEditModal(${JSON.stringify(h).replace(/"/g,'&quot;')})" title="Edit">✎</button>
          <button class="icon-btn danger" onclick="deleteHabit(${h.id})" title="Delete">✕</button>
        </div>
      </div>
      <div class="habit-card-name">${h.name}</div>
      <div class="habit-card-stats">
        <div class="stat-item">
          <div class="stat-value" style="color:${h.color}">${h.streak}</div>
          <div class="stat-label">Streak</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${h.total}</div>
          <div class="stat-label">Total</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${h.rate}%</div>
          <div class="stat-label">Rate</div>
        </div>
      </div>
    </div>
  `).join('');
}

async function deleteHabit(id) {
  if (!confirm('Delete this habit and all its history?')) return;
  await apiFetch(`/api/habits/${id}`, { method: 'DELETE' });
  showToast('Habit deleted');
  renderHabits();
}

// ─── PROGRESS PAGE ───
async function renderProgress() {
  const stats = await apiFetch('/api/stats');
  const habits = await apiFetch('/api/habits');

  // Summary
  const el = document.getElementById('progress-summary');
  el.innerHTML = `
    <div class="summary-card">
      <div class="card-label">Total Habits</div>
      <div class="card-value accent">${stats.total_habits}</div>
      <div class="card-sub">being tracked</div>
    </div>
    <div class="summary-card">
      <div class="card-label">Done Today</div>
      <div class="card-value green">${stats.done_today}/${stats.total_habits}</div>
      <div class="card-sub">habits complete</div>
    </div>
    <div class="summary-card">
      <div class="card-label">Avg. Rate</div>
      <div class="card-value">${stats.avg_rate}%</div>
      <div class="card-sub">last 30 days</div>
    </div>
    <div class="summary-card">
      <div class="card-label">Best Streak</div>
      <div class="card-value">${stats.best_streak}</div>
      <div class="card-sub">days in a row</div>
    </div>
  `;

  // 7-day charts
  const chartsEl = document.getElementById('progress-charts');
  const today = new Date();
  if (!stats.per_habit.length) {
    chartsEl.innerHTML = `<div class="empty-state" style="padding:40px"><div class="empty-icon">◎</div><p>Add habits to see analytics</p></div>`;
  } else {
    chartsEl.innerHTML = stats.per_habit.map(h => `
      <div class="chart-row">
        <div class="chart-name">
          <div class="chart-icon-sm" style="background:${hexOpacity(h.color,0.15)}">
            ${habits.find(x=>x.id===h.id)?.icon || '⭐'}
          </div>
          <span>${h.name}</span>
        </div>
        <div class="chart-week">
          ${h.week.map((d, i) => {
            const date = new Date(d.date + 'T00:00:00');
            const dayLabel = DAYS[date.getDay()];
            return `
              <div class="chart-bar-col">
                <div class="chart-bar ${d.done ? 'done' : ''}" style="${d.done ? 'background:'+h.color : ''}">
                  ${d.done ? '✓' : ''}
                </div>
                <div class="chart-day-label">${dayLabel}</div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `).join('');
  }

  // Completion bars
  const barsEl = document.getElementById('completion-bars');
  if (!habits.length) {
    barsEl.innerHTML = '';
    return;
  }
  barsEl.innerHTML = habits.map(h => `
    <div class="comp-row">
      <div class="comp-row-header">
        <div class="comp-name">
          <div class="chart-icon-sm" style="background:${hexOpacity(h.color,0.15)}">${h.icon}</div>
          ${h.name}
        </div>
        <div class="comp-pct" style="color:${h.color}">${h.rate}%</div>
      </div>
      <div class="comp-bar-bg">
        <div class="comp-bar-fill" style="width:${h.rate}%;background:${h.color}"></div>
      </div>
    </div>
  `).join('');
}

// ─── MODAL ───
function bindModal() {
  document.getElementById('open-add-modal').addEventListener('click', openAddModal);
  document.getElementById('open-add-modal-2').addEventListener('click', openAddModal);
  document.getElementById('close-modal').addEventListener('click', closeModal);
  document.getElementById('cancel-modal').addEventListener('click', closeModal);
  document.getElementById('save-habit').addEventListener('click', saveHabit);
  document.getElementById('habit-modal').addEventListener('click', e => {
    if (e.target.id === 'habit-modal') closeModal();
  });
}

function openAddModal() {
  document.getElementById('modal-title').textContent = 'New Habit';
  document.getElementById('habit-name').value = '';
  document.getElementById('edit-habit-id').value = '';
  selectedIcon = ICONS[0];
  selectedColor = COLORS[0];
  refreshIconPicker();
  refreshColorPicker();
  document.getElementById('habit-modal').classList.add('open');
  document.getElementById('habit-name').focus();
}

function openEditModal(habit) {
  document.getElementById('modal-title').textContent = 'Edit Habit';
  document.getElementById('habit-name').value = habit.name;
  document.getElementById('edit-habit-id').value = habit.id;
  selectedIcon = habit.icon;
  selectedColor = habit.color;
  refreshIconPicker();
  refreshColorPicker();
  document.getElementById('habit-modal').classList.add('open');
}

function closeModal() {
  document.getElementById('habit-modal').classList.remove('open');
}

async function saveHabit() {
  const name = document.getElementById('habit-name').value.trim();
  if (!name) { document.getElementById('habit-name').focus(); return; }
  const editId = document.getElementById('edit-habit-id').value;
  const body = { name, icon: selectedIcon, color: selectedColor, target_days: 7 };
  if (editId) {
    await apiFetch(`/api/habits/${editId}`, { method: 'PUT', body: JSON.stringify(body) });
    showToast('Habit updated!');
  } else {
    await apiFetch('/api/habits', { method: 'POST', body: JSON.stringify(body) });
    showToast('Habit added!');
  }
  closeModal();
  // Refresh current active page
  const active = document.querySelector('.page.active').id.replace('page-', '');
  loadPage(active);
}

// ─── ICON & COLOR PICKERS ───
function renderIconPicker() {
  const el = document.getElementById('icon-picker');
  el.innerHTML = ICONS.map(ic => `
    <button class="icon-opt ${ic === selectedIcon ? 'selected' : ''}" data-icon="${ic}" onclick="selectIcon(this,'${ic}')">${ic}</button>
  `).join('');
}

function renderColorPicker() {
  const el = document.getElementById('color-picker');
  el.innerHTML = COLORS.map(c => `
    <div class="color-opt ${c === selectedColor ? 'selected' : ''}" style="background:${c}" data-color="${c}" onclick="selectColor(this,'${c}')"></div>
  `).join('');
}

function refreshIconPicker() {
  document.querySelectorAll('.icon-opt').forEach(el => {
    el.classList.toggle('selected', el.dataset.icon === selectedIcon);
  });
}

function refreshColorPicker() {
  document.querySelectorAll('.color-opt').forEach(el => {
    el.classList.toggle('selected', el.dataset.color === selectedColor);
  });
}

function selectIcon(el, icon) {
  selectedIcon = icon;
  document.querySelectorAll('.icon-opt').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
}

function selectColor(el, color) {
  selectedColor = color;
  document.querySelectorAll('.color-opt').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
}

// ─── TOAST ───
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}

// ─── UTILS ───
function hexOpacity(hex, alpha) {
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
