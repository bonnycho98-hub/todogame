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

// ── 행복 레벨 렌더링 ─────────────────────────────────────────────
function renderHappiness(h) {
  const blocks = Array.from({ length: h.total_blocks }, (_, i) =>
    `<div class="pixel-block${i < h.filled_blocks ? ' filled' : ''}"></div>`
  ).join('');
  return `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
      <span style="color:var(--yellow);font-size:20px">lv.${h.level}</span>
      <div class="pixel-blocks">${blocks}</div>
      <span style="color:var(--muted);font-size:11px">lv.${h.level + 1}까지 ${Math.round((1 - h.progress) * 100)}%</span>
    </div>
    <div style="color:var(--muted);font-size:10px">score: ${h.score}</div>
  `;
}

// ── 대시보드 ─────────────────────────────────────────────
async function loadDashboard() {
  const data = await api('GET', '/dashboard');
  state.dashboard = data;

  // 오늘의 퀘스트
  const todayEl = document.getElementById('today-list');
  if (!data.today_quests.length) {
    todayEl.innerHTML = '<span style="color:var(--muted)">오늘 퀘스트 없음</span>';
  } else {
    todayEl.innerHTML = data.today_quests.map(q => {
      const doneCount = q.subtasks.filter(s => s.is_done_today).length;
      return `
        <div style="margin-bottom:10px">
          <div style="color:var(--text);margin-bottom:4px">
            ${q.quest_type === 'daily' ? '◆' : '◇'} ${q.title}
            <span style="color:var(--muted);font-size:10px">${doneCount}/${q.subtasks.length}</span>
          </div>
          ${q.subtasks.map(st => `
            <div class="check-item${st.is_done_today ? ' done' : ''}">
              <input type="checkbox" ${st.is_done_today ? 'checked' : ''}
                onchange="completeSubtask('${st.id}', this)"
                ${st.is_done_today ? 'disabled' : ''}>
              <label>${st.title}</label>
            </div>
          `).join('')}
        </div>
      `;
    }).join('');
  }

  // NPC 목록
  const npcEl = document.getElementById('npc-list');
  npcEl.innerHTML = data.npcs.map(npc => `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
      ${renderSprite(npc.sprite, npc.color)}
      <div>
        <div style="color:var(--text)">${npc.name}</div>
        <div style="color:var(--muted);font-size:10px">친밀도 ${npc.intimacy_total}</div>
      </div>
    </div>
  `).join('') || '<span style="color:var(--muted)">NPC 없음</span>';

  // 행복 레벨
  document.getElementById('happiness-display').innerHTML = renderHappiness(data.happiness);

  // 레벨업 보상 팝업
  if (data.pending_level_reward) {
    const r = data.pending_level_reward;
    document.getElementById('levelup-message').textContent = `lv.${r.level} 달성!`;
    document.getElementById('levelup-reward').textContent = `✨ ${r.message}`;
    state.pendingRewardId = r.id;
    document.getElementById('modal-levelup').classList.add('open');
  }
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
  tabsEl.innerHTML = `
    <div class="tab${state.activeQuestTab === 'self' ? ' active' : ''}" onclick="selectQuestTab('self')">나 자신</div>
    ${npcs.map(n => `
      <div class="tab${state.activeQuestTab === n.id ? ' active' : ''}" onclick="selectQuestTab('${n.id}')">${n.name}</div>
    `).join('')}
  `;

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
}

function renderNeedAccordion(need, quests) {
  return `
    <div class="card" style="margin-bottom:8px">
      <div class="accordion-header" onclick="toggleAccordion('need-${need.id}')">
        <span class="accordion-arrow" id="arrow-need-${need.id}">▶</span>
        <span>${need.title}</span>
        <span style="color:var(--muted);font-size:10px;margin-left:auto">${quests.length}개</span>
        <button class="btn btn-sm" style="margin-left:8px" onclick="event.stopPropagation();openAddQuestModal('${need.id}')">+ 퀘스트</button>
        <button class="btn btn-sm" style="margin-left:4px" onclick="event.stopPropagation();editNeed('${need.id}','${need.title.replace(/'/g, "\\'")}')">✎</button>
        <button class="btn btn-sm" style="margin-left:4px;color:var(--red);border-color:var(--red)" onclick="event.stopPropagation();deleteNeed('${need.id}')">✕</button>
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
        <span style="color:var(--text)">${q.title}</span>
        <span style="color:var(--muted);font-size:10px;margin-left:8px">[${routineLabel}]</span>
        <span style="color:var(--muted);font-size:10px;margin-left:auto">${doneCount}/${q.subtasks.length}</span>
        <button class="btn btn-sm" style="margin-left:8px" onclick="event.stopPropagation();openAddSubtaskModal('${q.id}')">+ 항목</button>
        <button class="btn btn-sm" style="margin-left:4px" onclick="event.stopPropagation();editQuest('${q.id}','${q.title.replace(/'/g, "\\'")}',${q.intimacy_reward})">✎</button>
        <button class="btn btn-sm" style="margin-left:4px;color:var(--red);border-color:var(--red)" onclick="event.stopPropagation();deleteQuest('${q.id}')">✕</button>
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
    const maxIntimacy = 100;
    const pct = Math.min((npc.intimacy_total / maxIntimacy) * 100, 100);
    return `
      <div class="card">
        <div style="display:flex;gap:16px;align-items:flex-start">
          <div style="text-align:center;min-width:60px">
            ${renderSprite(npc.sprite, npc.color)}
            <div style="color:var(--text);margin-top:4px">${npc.name}</div>
            <div style="color:var(--muted);font-size:10px">${npc.relation_type}</div>
            <button class="btn btn-sm" style="margin-top:4px" onclick="regenSprite('${npc.id}')">재생성</button>
          </div>
          <div style="flex:1">
            <div style="color:var(--muted);font-size:10px;letter-spacing:1px;margin-bottom:4px">INTIMACY</div>
            <div class="intimacy-bar"><div class="intimacy-fill" style="width:${pct}%"></div></div>
            <div style="color:var(--muted);font-size:10px">${npc.intimacy_total} 누적</div>
            <button class="btn btn-sm" style="margin-top:8px;color:var(--red);border-color:var(--red)"
              onclick="deleteNPC('${npc.id}','${npc.name}')">삭제</button>
          </div>
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
    <div class="card" style="display:flex;align-items:center;justify-content:space-between">
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

// ── 모달 헬퍼 ─────────────────────────────────────────────
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function openAddNPCModal() {
  document.getElementById('npc-name').value = '';
  document.getElementById('npc-relationship').value = '';
  document.getElementById('modal-npc').classList.add('open');
}

async function submitNPC() {
  const name = document.getElementById('npc-name').value.trim();
  const rel = document.getElementById('npc-relationship').value.trim();
  if (!name) return alert('이름을 입력하세요');
  await api('POST', '/npcs', { name, relation_type: rel || '기타' });
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
