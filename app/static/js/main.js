// 메인 피드 JavaScript

const tooltip = document.getElementById('tooltip');
let tooltipTimer = null;

// ===== 오늘의 핵심 이슈 로드 =====
async function loadDailySummary() {
  try {
    const res = await fetch('/api/daily-summary');
    const data = await res.json();
    const box = document.getElementById('dailySummary');
    const timeEl = document.getElementById('updateTime');

    if (data.summary) {
      box.textContent = data.summary;
      if (data.created_at) {
        const dt = new Date(data.created_at);
        timeEl.textContent = `업데이트: ${dt.toLocaleString('ko-KR', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`;
      }
    } else {
      box.innerHTML = '<span style="color:var(--text-muted)">아직 오늘의 이슈가 없습니다. 설정에서 수집을 실행해주세요.</span>';
    }
  } catch (e) {
    document.getElementById('dailySummary').textContent = '이슈를 불러오지 못했습니다.';
  }
}

// ===== 뉴스 피드 로드 =====
async function loadArticles() {
  const feed = document.getElementById('newsFeed');
  const loading = document.getElementById('loadingIndicator');
  const empty = document.getElementById('emptyState');
  const countEl = document.getElementById('feedCount');

  try {
    const res = await fetch('/api/articles?limit=50');
    const data = await res.json();
    const articles = data.articles || [];

    loading.style.display = 'none';

    if (articles.length === 0) {
      empty.style.display = 'block';
      return;
    }

    countEl.textContent = `총 ${articles.length}개`;

    articles.forEach((article, idx) => {
      const card = createCard(article, idx + 1);
      feed.appendChild(card);
    });

  } catch (e) {
    loading.style.display = 'none';
    empty.style.display = 'block';
  }
}

// ===== 뉴스 카드 생성 =====
function createCard(article, rank) {
  const wrapper = document.createElement('div');
  wrapper.className = 'card-wrapper';
  wrapper.dataset.id = article.id;

  const rankClass = rank <= 3 ? `rank-${rank}` : 'rank-other';

  wrapper.innerHTML = `
    <div class="news-card" onclick="toggleExpand(${article.id})">
      <div class="rank-badge ${rankClass}">${rank}</div>
      <div class="card-body">
        <div class="card-meta">
          <span class="source-tag">${escapeHtml(article.source || '')}</span>
        </div>
        <div class="card-title">${escapeHtml(article.title_original || '')}</div>
        <div class="card-footer">
          <div class="card-stats">
            ${article.comment_count > 0 ? `<span class="stat">댓글 ${formatNum(article.comment_count)}</span>` : ''}
            ${article.score > 0 ? `<span class="stat">추천 ${formatNum(article.score)}</span>` : ''}
          </div>
          <span class="expand-hint">클릭하여 번역 보기</span>
        </div>
      </div>
    </div>
    <div class="card-expand" id="expand-${article.id}" style="display:none">
      <div class="expand-inner" id="expand-content-${article.id}">
        <div class="translate-loading">번역 불러오는 중...</div>
      </div>
    </div>
  `;

  return wrapper;
}

// ===== 카드 확장/접기 =====
const translatedCache = {};

async function toggleExpand(articleId) {
  const expandEl = document.getElementById(`expand-${articleId}`);
  const contentEl = document.getElementById(`expand-content-${articleId}`);

  // 이미 열려 있으면 닫기
  if (expandEl.style.display !== 'none') {
    expandEl.style.display = 'none';
    const wrapper = expandEl.closest('.card-wrapper');
    wrapper.querySelector('.expand-hint').textContent = '클릭하여 번역 보기';
    return;
  }

  // 열기
  expandEl.style.display = 'block';
  const wrapper = expandEl.closest('.card-wrapper');
  wrapper.querySelector('.expand-hint').textContent = '접기';

  // 캐시에 있으면 바로 렌더링
  if (translatedCache[articleId]) {
    renderTranslation(contentEl, translatedCache[articleId]);
    return;
  }

  // 로딩 표시
  contentEl.innerHTML = '<div class="translate-loading"><div class="spinner"></div> 번역 중... (5~15초 소요)</div>';

  try {
    const res = await fetch(`/api/articles/${articleId}/translate`, { method: 'POST' });
    if (!res.ok) throw new Error('번역 실패');
    const data = await res.json();

    translatedCache[articleId] = data;
    renderTranslation(contentEl, data);
  } catch (e) {
    contentEl.innerHTML = '<div class="translate-error">번역 중 오류가 발생했습니다. 다시 클릭해보세요.</div>';
  }
}

// ===== 번역 결과 렌더링 =====
function renderTranslation(el, data) {
  const keywords = Array.isArray(data.keywords) ? data.keywords : [];
  const keywordHTML = keywords.map(kw =>
    `<span class="keyword-tag"
      data-keyword="${escapeHtml(kw)}"
      onmouseenter="showTooltip(event, '${escapeHtml(kw)}')"
      onmouseleave="hideTooltip()">${escapeHtml(kw)}</span>`
  ).join('');

  el.innerHTML = `
    <div class="translated-title">${escapeHtml(data.title_ko || data.title_original || '')}</div>
    ${data.summary_ko ? `<div class="translated-summary">${escapeHtml(data.summary_ko)}</div>` : ''}
    ${keywordHTML ? `<div class="keyword-row">${keywordHTML}</div>` : ''}
    <div class="expand-actions">
      <a href="${escapeHtml(data.url)}" target="_blank" rel="noopener" class="btn-original">
        원문 보기 →
      </a>
    </div>
  `;
}

// ===== 키워드 툴팁 =====
async function showTooltip(event, keyword) {
  clearTimeout(tooltipTimer);
  tooltipTimer = setTimeout(async () => {
    tooltip.innerHTML = '<div class="spinner" style="margin:4px auto"></div>';
    positionTooltip(event);
    tooltip.style.display = 'block';

    try {
      const res = await fetch(`/api/keyword-tooltip/${encodeURIComponent(keyword)}`);
      const data = await res.json();

      let html = `<strong>${escapeHtml(keyword)}</strong><br><br>${escapeHtml(data.explanation || '')}`;
      if (data.image_url) {
        html += `<br><img src="${escapeHtml(data.image_url)}" alt="${escapeHtml(keyword)}" class="tooltip-img">`;
      }
      tooltip.innerHTML = html;
      positionTooltip(event);
    } catch (e) {
      tooltip.textContent = '설명을 불러오지 못했습니다.';
    }
  }, 400);
}

function hideTooltip() {
  clearTimeout(tooltipTimer);
  tooltip.style.display = 'none';
}

function positionTooltip(event) {
  const x = event.clientX + 12;
  const y = event.clientY + 12;
  tooltip.style.left = `${Math.min(x, window.innerWidth - 320)}px`;
  tooltip.style.top = `${Math.min(y, window.innerHeight - 200)}px`;
}

// ===== 유틸 =====
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function formatNum(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

// ===== 초기화 =====
loadDailySummary();
loadArticles();
