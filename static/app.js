// static/app.js
// ── 상태 ─────────────────────────────────────────────
const state = {
  npcs: [],
  dashboard: null,
  activeQuestTab: 'self',
  pendingRewardId: null,
};

// ── API 헬퍼 ─────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch('/api' + path, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${res.status}: ${err}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── 페이지 전환 ─────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.navbar-links a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');

  // sync bottom nav
  document.querySelectorAll('.bnav-item').forEach(el => el.classList.remove('active'));
  const bnav = document.getElementById('bnav-' + name);
  if (bnav) bnav.classList.add('active');

  if (name === 'dashboard') loadDashboard();
  if (name === 'quests') loadQuestBoard();
  if (name === 'npcs') loadNPCDetail();
  if (name === 'rewards') loadRewards();
}

// ── 스프라이트 렌더링 ─────────────────────────────────────────────
function renderSprite(spriteJson, color) {
  try {
    const data = typeof spriteJson === 'string' ? JSON.parse(spriteJson) : spriteJson;
    return `<pre class="sprite" style="color:${color || data.color}">${data.lines.join('\n')}</pre>`;
  } catch { return '<pre class="sprite">(?)</pre>'; }
}

function renderSpriteInline(spriteJson, color) {
  try {
    const data = typeof spriteJson === 'string' ? JSON.parse(spriteJson) : spriteJson;
    const firstLine = data.lines[0] || '?';
    return `<span style="color:${color || data.color};font-size:13px">${firstLine}</span>`;
  } catch { return '<span>?</span>'; }
}

// ── 행복 레벨 렌더링 ─────────────────────────────────────────────
function renderHappiness(h) {
  const display = document.getElementById('happiness-display');
  if (display) {
    display.innerHTML = `
      <div class="hp-level-row">
        <span class="hp-lv-num">${h.level}</span>
        <span class="hp-lv-lbl">LEVEL</span>
      </div>`;
  }
  const fill = document.getElementById('hero-bar-fill');
  if (fill) fill.style.width = `${Math.round(h.progress * 100)}%`;
  const xpText = document.getElementById('hero-xp-text');
  if (xpText) xpText.textContent = `다음 레벨까지 ${Math.round(h.progress * 100)}%`;
}

// ── 대시보드 렌더 헬퍼 ─────────────────────────────────────────────
let _nudgeFadeTimer = null;

function renderRoutineQuest(q) {
  const allDone = q.is_all_done_today;

  if (q.subtasks && q.subtasks.length > 0) {
    const subtaskRows = q.subtasks.map(s => {
      const done = s.is_done_today;
      return `
        <div class="routine-subtask-row${done ? ' done' : ''}">
          <div class="check-btn${done ? ' done' : ''}" ${!done ? `onclick="completeSubtaskDash('${s.id}', this)"` : ''}>${done ? '✓' : ''}</div>
          <div class="routine-subtask-name${done ? ' done' : ''}">${s.title}</div>
        </div>`;
    }).join('');
    return `
      <div class="routine-quest-block${allDone ? ' done' : ''}">
        <div class="routine-quest-header">
          <div class="quest-name${allDone ? ' done' : ''}">${q.title}</div>
          <div class="quest-xp">+${q.intimacy_reward || 10}</div>
        </div>
        <div class="routine-subtask-list">${subtaskRows}</div>
      </div>`;
  }

  return `
    <div class="quest-row${allDone ? ' done' : ''}">
      <div class="check-btn${allDone ? ' done' : ''}" ${!allDone ? `onclick="completeQuestDash('${q.id}')"` : ''}>${allDone ? '✓' : ''}</div>
      <div class="quest-name${allDone ? ' done' : ''}">${q.title}</div>
      <div class="quest-xp">+${q.intimacy_reward || 10}</div>
    </div>`;
}

function renderNeedWithQuests(nwq) {
  const need = nwq.need;
  const quests = nwq.quests || [];
  const doneCount = quests.filter(q => q.is_all_done_today).length;

  const questRows = quests.map(q => {
    const dots = (q.subtasks || []).map(s =>
      `<div class="qdot${s.is_done_today ? ' done' : ''}"></div>`
    ).join('');
    return `
      <div class="quest-row${q.is_all_done_today ? ' done' : ''}">
        <div class="check-btn${q.is_all_done_today ? ' done' : ''}" ${!q.is_all_done_today ? `onclick="completeQuestDash('${q.id}')"` : ''}>${q.is_all_done_today ? '✓' : ''}</div>
        <div class="quest-name${q.is_all_done_today ? ' done' : ''}">${q.title}</div>
        <div class="quest-dots">${dots}</div>
        <div class="quest-xp">+${q.intimacy_reward || 10}</div>
      </div>`;
  }).join('');

  return `
    <div class="need-block">
      <div class="need-header">
        <div class="need-icon">✦</div>
        <div class="need-name">${need.title}</div>
        <div class="need-progress">${doneCount}/${quests.length}</div>
        <button class="need-done-btn" onclick="completeNeed('${need.id}')">완료</button>
      </div>
      <div class="quest-list">${questRows}</div>
    </div>`;
}

function renderNPCSectionItem(item) {
  const npc = item.npc;
  const needs = item.needs || [];
  const locIcon = npc.location === 'home' ? '🏠' : '🏢';
  const firstChar = (npc.name || '?')[0];

  const needBlocks = needs.map(nwq => {
    const need = nwq.need;
    const quests = nwq.quests || [];
    const doneCount = quests.filter(q => q.is_all_done_today).length;

    const questRows = quests.map(q => {
      const dots = (q.subtasks || []).map(s =>
        `<div class="qdot${s.is_done_today ? ' done' : ''}"></div>`
      ).join('');
      return `
        <div class="quest-row${q.is_all_done_today ? ' done' : ''}">
          <div class="check-btn${q.is_all_done_today ? ' done' : ''}" ${!q.is_all_done_today ? `onclick="completeQuestDash('${q.id}')"` : ''}>${q.is_all_done_today ? '✓' : ''}</div>
          <div class="quest-name${q.is_all_done_today ? ' done' : ''}">${q.title}</div>
          <div class="quest-dots">${dots}</div>
          <div class="quest-xp">+${q.intimacy_reward || 10}</div>
        </div>`;
    }).join('');

    return `
      <div class="need-header" style="padding-left:32px; background: var(--bg-subtle);">
        <div class="need-icon">❤️</div>
        <div class="need-name">${need.title}</div>
        <div class="need-progress">${doneCount}/${quests.length}</div>
        <button class="need-done-btn" onclick="completeNeed('${need.id}')">완료</button>
      </div>
      <div class="quest-list">${questRows}</div>`;
  }).join('');

  return `
    <div class="need-block npc-block">
      <div class="npc-header">
        <div class="npc-avatar">${firstChar}</div>
        <div class="npc-info">
          <div class="npc-name">${npc.name}</div>
          <div class="npc-meta">${locIcon} ${npc.relation_type || ''}</div>
        </div>
        <div class="intimacy-pill">♥ ${npc.intimacy_total || 0}</div>
      </div>
      ${needBlocks}
    </div>`;
}

function findQuestInDashboard(questId) {
  if (!state.dashboard) return null;
  for (const q of state.dashboard.routine_quests) {
    if (q.id === questId) return q;
  }
  for (const nwq of state.dashboard.self_section.needs) {
    for (const q of nwq.quests) {
      if (q.id === questId) return q;
    }
  }
  for (const item of state.dashboard.npc_section) {
    for (const nwq of item.needs) {
      for (const q of nwq.quests) {
        if (q.id === questId) return q;
      }
    }
  }
  return null;
}

function renderRoutineNudgeBanner(routines, streak) {
  const banner = document.getElementById('routine-nudge-banner');
  if (!banner) return;

  if (_nudgeFadeTimer !== null) {
    clearTimeout(_nudgeFadeTimer);
    _nudgeFadeTimer = null;
  }
  banner.classList.remove('fade-out');

  const remaining = routines.filter(q => !q.is_all_done_today).length;
  const total = routines.length;

  if (total === 0) {
    banner.style.display = 'none';
    return;
  }

  if (remaining > 0) {
    banner.className = 'warn';
    banner.style.display = 'flex';
    banner.style.opacity = '1';
    banner.innerHTML = `
      <div class="nudge-icon">🔥</div>
      <div class="nudge-text">
        <div class="nudge-title">오늘 루틴 ${remaining}개 남았어요</div>
        <div class="nudge-sub">스트릭 ${streak}일 — 오늘 놓치면 리셋돼요!</div>
      </div>
      <button class="nudge-action" onclick="document.getElementById('routine-list').scrollIntoView({behavior:'smooth'})">지금 하기 →</button>
    `;
  } else {
    banner.className = 'done';
    banner.style.display = 'flex';
    banner.style.opacity = '1';
    banner.innerHTML = `
      <div class="nudge-icon">🎉</div>
      <div class="nudge-text">
        <div class="nudge-title">오늘 루틴 완료!</div>
        <div class="nudge-sub">스트릭 ${streak}일 달성 · 잘했어요 ✨</div>
      </div>
    `;
    _nudgeFadeTimer = setTimeout(() => {
      banner.classList.add('fade-out');
      _nudgeFadeTimer = setTimeout(() => {
        banner.style.display = 'none';
        _nudgeFadeTimer = null;
      }, 600);
    }, 3000);
  }
}

// ── 대시보드 ─────────────────────────────────────────────
async function loadDashboard() {
  const data = await api('GET', '/dashboard');
  state.dashboard = data;

  // 오늘의 루틴
  const routines = data.routine_quests || [];
  document.getElementById('routine-list').innerHTML =
    routines.length ? routines.map(renderRoutineQuest).join('') : '<div class="empty-hint">오늘 루틴이 없어요</div>';
  const routineDone = routines.filter(q => q.is_all_done_today).length;
  const badge = document.getElementById('routine-badge');
  if (badge) badge.textContent = `${routineDone} / ${routines.length}`;
  renderRoutineNudgeBanner(routines, data.streak || 0);

  // 나를 사랑하기
  const selfNeeds = (data.self_section && data.self_section.needs) || [];
  document.getElementById('self-section').innerHTML =
    selfNeeds.length ? selfNeeds.map(renderNeedWithQuests).join('') : '<div class="empty-hint">셀프 퀘스트가 없어요</div>';
  const selfDone = selfNeeds.flatMap(n => n.quests || []).filter(q => q.is_all_done_today).length;
  const selfTotal = selfNeeds.flatMap(n => n.quests || []).length;
  const selfBadge = document.getElementById('self-badge');
  if (selfBadge) selfBadge.textContent = `${selfDone} / ${selfTotal}`;

  // 타인을 사랑하기
  const npcSections = data.npc_section || [];
  document.getElementById('npc-list').innerHTML =
    npcSections.length ? npcSections.map(renderNPCSectionItem).join('') : '<div class="empty-hint">NPC가 없어요</div>';
  const npcBadge = document.getElementById('npc-badge');
  if (npcBadge) npcBadge.textContent = `${npcSections.length}명`;

  // 행복 레벨
  renderHappiness(data.happiness);

  // 히어로 통계
  const allQuests = [
    ...(data.routine_quests || []),
    ...((data.self_section && data.self_section.needs) || []).flatMap(n => n.quests || []),
    ...(data.npc_section || []).flatMap(s => (s.needs || []).flatMap(n => n.quests || []))
  ];
  const done = allQuests.filter(q => q.is_all_done_today).length;
  const remain = allQuests.filter(q => !q.is_all_done_today).length;
  const doneEl = document.getElementById('hero-done');
  const remainEl = document.getElementById('hero-remain');
  const streakEl = document.getElementById('hero-streak');
  if (doneEl) doneEl.textContent = done;
  if (remainEl) remainEl.textContent = remain;
  if (streakEl) streakEl.textContent = `🔥${data.streak || 0}`;

  // 레벨업 보상 팝업
  if (data.pending_level_reward) {
    const r = data.pending_level_reward;
    document.getElementById('levelup-message').textContent = `lv.${r.level} 달성!`;
    document.getElementById('levelup-reward').textContent = `✨ ${r.message}`;
    state.pendingRewardId = r.id;
    document.getElementById('modal-levelup').classList.add('open');
  }
}

async function completeQuestDash(id) {
  const result = await api('POST', `/quests/${id}/complete`);
  if (result && result.level_up) alert(`🎊 LEVEL UP! lv.${result.level_up}`);
  await loadDashboard();
}

async function completeSubtaskDash(id, el) {
  try {
    const result = await api('POST', `/subtasks/${id}/complete`);
    if (result.quest_done) {
      await loadDashboard();
    } else {
      el.classList.add('done');
      el.textContent = '✓';
      el.onclick = null;
      const row = el.closest('.routine-subtask-row');
      if (row) {
        row.classList.add('done');
        const nameEl = row.querySelector('.routine-subtask-name');
        if (nameEl) nameEl.classList.add('done');
      }
    }
  } catch (e) {
    alert(e.message);
  }
}

async function completeNeed(id) {
  if (!confirm('니즈를 완료할까요? 완료된 니즈는 목록에서 사라집니다.')) return;
  await api('POST', `/needs/${id}/complete`);
  await loadDashboard();
}

async function completeSubtask(id, checkbox) {
  try {
    const result = await api('POST', `/subtasks/${id}/complete`);
    if (result.quest_done) {
      await loadDashboard();
    } else {
      checkbox.disabled = true;
      checkbox.closest('.check-item').classList.add('done');
    }
  } catch (e) {
    checkbox.checked = false;
    alert(e.message);
  }
}

// ── 퀘스트 보드 ─────────────────────────────────────────────
async function loadQuestBoard() {
  const npcs = await api('GET', '/npcs');
  state.npcs = npcs;

  // 탭 렌더링
  const tabsEl = document.getElementById('quest-tabs');

  // NPC를 location으로 분류
  const homeNPCs = npcs.filter(n => n.location !== 'company');
  const companyNPCs = npcs.filter(n => n.location === 'company');

  let tabsHtml = `<div class="tab${state.activeQuestTab === 'self' ? ' active' : ''}" onclick="selectQuestTab('self')">나 자신</div>`;

  if (homeNPCs.length > 0) {
    tabsHtml += `<div class="tab-sep"></div>`;
    tabsHtml += homeNPCs.map(n => `
      <div class="tab${state.activeQuestTab === n.id ? ' active' : ''}" onclick="selectQuestTab('${n.id}')">🏠 ${n.name}</div>
    `).join('');
  }

  if (companyNPCs.length > 0) {
    tabsHtml += `<div class="tab-sep"></div>`;
    tabsHtml += companyNPCs.map(n => `
      <div class="tab${state.activeQuestTab === n.id ? ' active' : ''}" onclick="selectQuestTab('${n.id}')">🏢 ${n.name}</div>
    `).join('');
  }

  tabsEl.innerHTML = tabsHtml;

  await renderQuestContent();
}

async function selectQuestTab(tabId) {
  state.activeQuestTab = tabId;
  await loadQuestBoard();
}

async function renderQuestContent() {
  const contentEl = document.getElementById('quest-content');
  const isNPC = state.activeQuestTab !== 'self';
  const npcId = isNPC ? state.activeQuestTab : null;

  // 니즈 목록 로드
  const needsUrl = npcId ? `/needs?npc_id=${npcId}` : '/needs';
  const needs = await api('GET', needsUrl);

  contentEl.innerHTML = `
    <div style="margin-bottom:8px;display:flex;justify-content:flex-end;gap:6px">
      <button class="btn btn-sm" onclick="openAddNeedModal('${npcId || ''}')">+ 니즈 추가</button>
    </div>
    <div id="needs-accordion"></div>
  `;

  const accordion = document.getElementById('needs-accordion');
  for (const need of needs) {
    const quests = await api('GET', `/quests?need_id=${need.id}`);
    accordion.innerHTML += renderNeedAccordion(need, quests);
  }

  // 고아 퀘스트 (need 없는 퀘스트) 표시
  const orphans = await api('GET', '/quests/orphans');
  if (orphans.length) {
    accordion.innerHTML += `
      <div class="card" style="margin-bottom:8px;border-color:var(--red)">
        <div style="padding:8px 12px;color:var(--red);font-size:11px">⚠ 니즈 없는 퀘스트 (삭제 필요)</div>
        <div style="padding:0 12px 8px">
          ${orphans.map(q => `
            <div style="display:flex;align-items:center;gap:8px;padding:4px 0">
              <span style="flex:1;font-size:12px">${q.title}</span>
              <button class="btn btn-sm" style="color:var(--red);border-color:var(--red)"
                onclick="deleteQuest('${q.id}')">삭제</button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}

function renderNeedAccordion(need, quests) {
  return `
    <div class="card" style="margin-bottom:8px">
      <div class="accordion-header" onclick="toggleAccordion('need-${need.id}')">
        <span class="accordion-arrow" id="arrow-need-${need.id}">▶</span>
        <span class="accordion-title">${need.title}</span>
        <div class="accordion-actions" onclick="event.stopPropagation()">
          <span class="accordion-count">${quests.length}개</span>
          <button class="btn btn-sm" onclick="openAddQuestModal('${need.id}')">+ 퀘스트</button>
          <button class="btn btn-sm" onclick="editNeed('${need.id}','${need.title.replace(/'/g, "\\'")}')">✎</button>
          <button class="btn btn-sm" style="color:var(--red);border-color:var(--red)" onclick="deleteNeed('${need.id}')">✕</button>
        </div>
      </div>
      <div class="accordion-body" id="need-${need.id}">
        ${quests.map(q => renderQuestAccordion(q)).join('')}
      </div>
    </div>
  `;
}

function renderQuestAccordion(q) {
  const routineLabel = q.routine ? formatRoutine(q.routine) : '';
  const doneCount = q.subtasks.filter(s => s.is_done_today).length;
  return `
    <div style="margin-left:16px;margin-bottom:6px;border-left:1px solid var(--border);padding-left:12px">
      <div class="accordion-header" onclick="toggleAccordion('quest-${q.id}')">
        <span class="accordion-arrow" id="arrow-quest-${q.id}">▶</span>
        <span class="accordion-title">${q.title}${routineLabel ? `<span style="color:var(--muted);font-size:10px;margin-left:4px">[${routineLabel}]</span>` : ''}</span>
        <div class="accordion-actions" onclick="event.stopPropagation()">
          <span class="accordion-count">${doneCount}/${q.subtasks.length}</span>
          <button class="btn btn-sm" onclick="openAddSubtaskModal('${q.id}')">+ 항목</button>
          <button class="btn btn-sm" style="color:var(--green);border-color:var(--green)" onclick="completeQuest('${q.id}')">✔ 완료</button>
          <button class="btn btn-sm" onclick="editQuest('${q.id}','${q.title.replace(/'/g, "\\'")}',${q.intimacy_reward})">✎</button>
          <button class="btn btn-sm" style="color:var(--red);border-color:var(--red)" onclick="deleteQuest('${q.id}')">✕</button>
        </div>
      </div>
      <div class="accordion-body" id="quest-${q.id}">
        ${q.subtasks.map(st => `
          <div class="check-item${st.is_done_today ? ' done' : ''}" style="padding-left:12px;display:flex;align-items:center;gap:6px">
            <input type="checkbox" ${st.is_done_today ? 'checked disabled' : ''}
              onchange="completeSubtaskInBoard('${st.id}', this)">
            <label style="flex:1">${st.title}</label>
            <button class="btn btn-sm" style="padding:0 4px;font-size:10px" onclick="editSubtask('${st.id}','${st.title.replace(/'/g, "\\'")}')">✎</button>
            <button class="btn btn-sm" style="padding:0 4px;font-size:10px;color:var(--red);border-color:var(--red)" onclick="deleteSubtask('${st.id}')">✕</button>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function toggleAccordion(id) {
  const body = document.getElementById(id);
  const arrow = document.getElementById('arrow-' + id);
  if (!body) return;
  body.classList.toggle('open');
  if (arrow) arrow.textContent = body.classList.contains('open') ? '▼' : '▶';
}

function formatRoutine(routine) {
  const days = ['월','화','수','목','금','토','일'];
  if (routine.type === 'daily') return '매일';
  if (routine.type === 'weekly') return '매주 ' + (routine.days || []).map(d => days[d]).join('·');
  if (routine.type === 'monthly') return '매월 ' + (routine.dates || []).join('·') + '일';
  return routine.type;
}

async function completeSubtaskInBoard(id, checkbox) {
  try {
    await api('POST', `/subtasks/${id}/complete`);
    await renderQuestContent();
  } catch (e) {
    checkbox.checked = false;
    alert(e.message);
  }
}

// ── NPC 상세 ─────────────────────────────────────────────
async function loadNPCDetail() {
  const npcs = await api('GET', '/npcs');
  state.npcs = npcs;
  const el = document.getElementById('npc-detail-list');
  el.innerHTML = npcs.map(npc => {
    const locIcon = npc.location === 'company' ? '🏢' : '🏠';
    const maxIntimacy = 100;
    const pct = Math.min((npc.intimacy_total / maxIntimacy) * 100, 100);
    return `
      <div class="npc-manage-row">
        <div class="npc-manage-header">
          <span style="font-size:12px">${locIcon}</span>
          ${renderSprite(npc.sprite, npc.color)}
          <div style="flex:1">
            <span style="color:var(--yellow)">${npc.name}</span>
            <span style="color:var(--dim);font-size:11px;margin-left:6px">${npc.relation_type}</span>
          </div>
          <button class="btn btn-sm" onclick="regenSprite('${npc.id}')">재생성</button>
          <button class="btn btn-sm" style="color:var(--red);border-color:var(--red);margin-left:4px"
            onclick="deleteNPC('${npc.id}','${npc.name}')">삭제</button>
        </div>
        <div style="padding-left:20px">
          <div class="intimacy-bar"><div class="intimacy-fill" style="width:${pct}%"></div></div>
          <span style="font-size:10px;color:var(--dim)">${npc.intimacy_total} 누적</span>
        </div>
      </div>
    `;
  }).join('') || '<span style="color:var(--muted)">NPC 없음. 추가해보세요.</span>';
}

async function regenSprite(npcId) {
  await api('POST', `/npcs/${npcId}/regenerate-sprite`);
  await loadNPCDetail();
}

async function deleteNPC(id, name) {
  if (!confirm(`${name}을(를) 삭제할까요? 관련 퀘스트도 모두 삭제됩니다.`)) return;
  await api('DELETE', `/npcs/${id}`);
  await loadNPCDetail();
}

// ── 보상 관리 ─────────────────────────────────────────────
async function loadRewards() {
  const rewards = await api('GET', '/rewards');
  const el = document.getElementById('rewards-list');
  el.innerHTML = rewards.map(r => `
    <div class="reward-row">
      <div>
        <span style="color:var(--yellow)">lv.${r.level}</span>
        <span style="margin-left:12px;color:var(--text)">${r.message}</span>
        ${r.is_claimed ? '<span style="margin-left:8px;color:var(--muted);font-size:10px">✓ 수령완료</span>' : ''}
      </div>
      <button class="btn btn-sm" onclick="deleteReward('${r.id}')">삭제</button>
    </div>
  `).join('') || '<span style="color:var(--muted)">설정된 보상 없음</span>';
}

async function deleteReward(id) {
  await api('DELETE', `/rewards/${id}`);
  await loadRewards();
}

async function claimReward() {
  if (!state.pendingRewardId) return;
  await api('POST', `/rewards/${state.pendingRewardId}/claim`);
  state.pendingRewardId = null;
  closeModal('modal-levelup');
  await loadDashboard();
}

// ── 퀘스트 상세 모달 ─────────────────────────────────────────────
function openQuestModal(questId) {
  const quest = findQuestInDashboard(questId);
  if (!quest) return;

  const typeLabel = quest.quest_type === 'daily' ? 'DAILY QUEST' : 'QUEST';
  const subtasksHtml = quest.subtasks.length
    ? quest.subtasks.map(st => `
        <div class="check-item${st.is_done_today ? ' done' : ''}" style="padding:4px 0">
          <input type="checkbox" ${st.is_done_today ? 'checked disabled' : ''}
            onchange="completeSubtaskFromModal('${st.id}', '${questId}', this)">
          <label>${st.title}</label>
        </div>
      `).join('')
    : '<span style="color:var(--muted);font-size:11px">서브태스크 없음</span>';

  document.getElementById('quest-detail-type').textContent = typeLabel;
  document.getElementById('quest-detail-title').textContent = quest.title;
  document.getElementById('quest-detail-subtasks').innerHTML = subtasksHtml;
  document.getElementById('btn-complete-quest-modal').onclick = () => completeQuestFromModal(questId);
  document.getElementById('modal-quest-detail').classList.add('open');
}

async function completeSubtaskFromModal(subtaskId, questId, checkbox) {
  try {
    const result = await api('POST', `/subtasks/${subtaskId}/complete`);
    if (result.quest_done) {
      closeModal('modal-quest-detail');
      await loadDashboard();
    } else {
      checkbox.disabled = true;
      checkbox.closest('.check-item').classList.add('done');
    }
  } catch (e) {
    checkbox.checked = false;
    alert(e.message);
  }
}

async function completeQuestFromModal(questId) {
  try {
    const result = await api('POST', `/quests/${questId}/complete`);
    closeModal('modal-quest-detail');
    if (result.level_up) alert(`🎊 LEVEL UP! lv.${result.level_up}`);
    await loadDashboard();
  } catch (e) {
    alert(e.message);
  }
}

async function completeNeed(id) {
  if (!confirm('니즈를 완료 처리할까요?')) return;
  try {
    await api('POST', `/needs/${id}/complete`);
    await loadDashboard();
  } catch (e) {
    alert(e.message);
  }
}

// ── 모달 헬퍼 ─────────────────────────────────────────────
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function selectLocation(loc) {
  document.getElementById('npc-location').value = loc;
  document.getElementById('loc-home').classList.toggle('active', loc === 'home');
  document.getElementById('loc-company').classList.toggle('active', loc === 'company');
}

function openAddNPCModal() {
  document.getElementById('npc-name').value = '';
  document.getElementById('npc-relationship').value = '';
  selectLocation('home');
  document.getElementById('modal-npc').classList.add('open');
}

async function submitNPC() {
  const name = document.getElementById('npc-name').value.trim();
  const rel = document.getElementById('npc-relationship').value.trim();
  const location = document.getElementById('npc-location').value;
  if (!name) return alert('이름을 입력하세요');
  await api('POST', '/npcs', { name, relation_type: rel || '기타', location });
  closeModal('modal-npc');
  await loadNPCDetail();
}

function openAddNeedModal(npcId) {
  const title = prompt('니즈 내용 입력:');
  if (!title) return;
  api('POST', '/needs', { npc_id: npcId || null, title }).then(() => renderQuestContent());
}

async function editNeed(id, currentTitle) {
  const title = prompt('니즈 수정:', currentTitle);
  if (!title || title === currentTitle) return;
  await api('PATCH', `/needs/${id}`, { title });
  await renderQuestContent();
}

async function deleteNeed(id) {
  if (!confirm('니즈를 삭제할까요? 관련 퀘스트도 모두 삭제됩니다.')) return;
  await api('DELETE', `/needs/${id}`);
  await renderQuestContent();
}

async function completeQuest(id) {
  if (!confirm('퀘스트를 완료 처리할까요?')) return;
  const result = await api('POST', `/quests/${id}/complete`);
  if (result.level_up) alert(`🎊 LEVEL UP! lv.${result.level_up}`);
  await renderQuestContent();
  await loadDashboard();
}

async function editQuest(id, currentTitle, currentReward) {
  const title = prompt('퀘스트 제목 수정:', currentTitle);
  if (!title) return;
  const rewardStr = prompt('친밀도 보상:', currentReward);
  const intimacy_reward = parseInt(rewardStr) || currentReward;
  await api('PATCH', `/quests/${id}`, { title, intimacy_reward });
  await renderQuestContent();
}

async function deleteQuest(id) {
  if (!confirm('퀘스트를 삭제할까요?')) return;
  await api('DELETE', `/quests/${id}`);
  await renderQuestContent();
}

async function editSubtask(id, currentTitle) {
  const title = prompt('항목 수정:', currentTitle);
  if (!title || title === currentTitle) return;
  await api('PATCH', `/subtasks/${id}`, { title });
  await renderQuestContent();
}

async function deleteSubtask(id) {
  if (!confirm('항목을 삭제할까요?')) return;
  await api('DELETE', `/subtasks/${id}`);
  await renderQuestContent();
}

function openAddQuestModal(needId) {
  document.getElementById('quest-title').value = '';
  document.getElementById('quest-type').value = 'daily';
  document.getElementById('quest-reward').value = '10';
  document.getElementById('quest-need-id').value = needId || '';
  document.getElementById('routine-section').style.display = '';
  document.getElementById('routine-type').value = 'daily';
  document.getElementById('routine-days').style.display = 'none';
  document.getElementById('routine-dates').style.display = 'none';
  document.getElementById('modal-quest').classList.add('open');
}

function toggleRoutine() {
  const type = document.getElementById('quest-type').value;
  document.getElementById('routine-section').style.display = type === 'daily' ? '' : 'none';
}

function toggleRoutineDetail() {
  const type = document.getElementById('routine-type').value;
  document.getElementById('routine-days').style.display = type === 'weekly' ? '' : 'none';
  document.getElementById('routine-dates').style.display = type === 'monthly' ? '' : 'none';
}

async function submitQuest() {
  const title = document.getElementById('quest-title').value.trim();
  if (!title) return alert('제목을 입력하세요');

  const questType = document.getElementById('quest-type').value;
  const needId = document.getElementById('quest-need-id').value || null;
  const reward = parseInt(document.getElementById('quest-reward').value) || 10;

  let routine = null;
  if (questType === 'daily') {
    const rType = document.getElementById('routine-type').value;
    if (rType === 'daily') {
      routine = { type: 'daily' };
    } else if (rType === 'weekly') {
      const checked = [...document.querySelectorAll('#routine-days input:checked')].map(c => parseInt(c.value));
      if (!checked.length) return alert('요일을 선택하세요');
      routine = { type: 'weekly', days: checked };
    } else {
      const raw = document.getElementById('routine-dates-input').value;
      const dates = raw.split(',').map(d => parseInt(d.trim())).filter(d => d >= 1 && d <= 31);
      if (!dates.length) return alert('날짜를 입력하세요');
      routine = { type: 'monthly', dates };
    }
  }

  await api('POST', '/quests', {
    need_id: needId, title, quest_type: questType, routine, intimacy_reward: reward
  });
  closeModal('modal-quest');
  await renderQuestContent();
}

function openAddSubtaskModal(questId) {
  const title = prompt('서브태스크 내용:');
  if (!title) return;
  api('POST', '/subtasks', { quest_id: questId, title, order: 0 }).then(() => renderQuestContent());
}

function openAddRewardModal() {
  document.getElementById('reward-level').value = '';
  document.getElementById('reward-message').value = '';
  document.getElementById('modal-reward').classList.add('open');
}

async function submitReward() {
  const level = parseInt(document.getElementById('reward-level').value);
  const message = document.getElementById('reward-message').value.trim();
  if (!level || !message) return alert('레벨과 보상 내용을 입력하세요');
  await api('POST', '/rewards', { level, message });
  closeModal('modal-reward');
  await loadRewards();
}

// ── 초기화 ─────────────────────────────────────────────
loadDashboard();
