// 설정 페이지 JavaScript

// ===== 소스 목록 로드 =====
async function loadSources() {
  const list = document.getElementById('sourceList');
  try {
    const res = await fetch('/api/settings/sources');
    const data = await res.json();
    const sources = data.sources || [];

    list.innerHTML = sources.map(src => `
      <div class="source-item" id="source-${src.id}">
        <div style="flex:1; min-width:0;">
          <div class="source-name">${escapeHtml(src.name)}</div>
          <div class="source-url">${escapeHtml(src.url)}</div>
        </div>
        ${src.is_default
          ? '<span class="default-badge">기본</span>'
          : `<button class="btn-delete" onclick="deleteSource(${src.id})">삭제</button>`
        }
      </div>
    `).join('');

  } catch (e) {
    list.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">소스 목록을 불러오지 못했습니다.</p>';
  }
}

// ===== 소스 추가 =====
async function addSource() {
  const name = document.getElementById('sourceName').value.trim();
  const url = document.getElementById('sourceUrl').value.trim();
  const statusEl = document.getElementById('addStatus');

  if (!name || !url) {
    showStatus(statusEl, '이름과 URL을 모두 입력해주세요.', 'error');
    return;
  }

  try {
    const res = await fetch('/api/settings/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, url }),
    });
    const data = await res.json();

    if (res.ok) {
      showStatus(statusEl, data.message, 'success');
      document.getElementById('sourceName').value = '';
      document.getElementById('sourceUrl').value = '';
      loadSources();
    } else {
      showStatus(statusEl, data.detail || '추가 실패', 'error');
    }
  } catch (e) {
    showStatus(statusEl, '서버 오류가 발생했습니다.', 'error');
  }
}

// ===== 소스 삭제 =====
async function deleteSource(id) {
  if (!confirm('이 소스를 삭제할까요?')) return;

  try {
    const res = await fetch(`/api/settings/sources/${id}`, { method: 'DELETE' });
    const data = await res.json();

    if (res.ok) {
      document.getElementById(`source-${id}`)?.remove();
    } else {
      alert(data.detail || '삭제 실패');
    }
  } catch (e) {
    alert('서버 오류가 발생했습니다.');
  }
}

// ===== 수동 크롤링 실행 =====
async function runCrawl() {
  const btn = document.getElementById('crawlNowBtn');
  const statusEl = document.getElementById('crawlStatus');

  btn.disabled = true;
  btn.textContent = '⏳ 수집 중...';
  showStatus(statusEl, '크롤링 실행 중... 수십 초 소요될 수 있습니다.', 'running');

  try {
    const res = await fetch('/api/settings/crawl-now', { method: 'POST' });
    const data = await res.json();

    if (data.status === 'success') {
      showStatus(statusEl,
        `✅ 완료! 총 ${data.total_fetched}개 수집 → ${data.saved}개 신규 저장`,
        'success'
      );
    } else {
      showStatus(statusEl, `❌ ${data.message || '수집 실패'}`, 'error');
    }
  } catch (e) {
    showStatus(statusEl, '❌ 서버 오류가 발생했습니다.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔄 지금 수집 실행';
  }
}

// ===== 유틸 =====
function showStatus(el, msg, type) {
  el.textContent = msg;
  el.className = `crawl-status ${type}`;
  el.style.display = 'block';
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ===== 초기화 =====
loadSources();
