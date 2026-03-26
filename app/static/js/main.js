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
      box.innerHTML = '<span style="color:var(--text-muted)">아직 오늘의 이슈가 생성되지 않았습니다. 소스 설정에서 크롤링을 실행해주세요.</span>';
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
      const rank = idx + 1;
      const card = createCard(article, rank);
      feed.appendChild(card);
    });

  } catch (e) {
    loading.style.display = 'none';
    empty.style.display = 'block';
  }
}

// ===== 뉴스 카드 생성 =====
function createCard(article, rank) {
  const card = document.createElement('div');
  card.className = 'news-card';
  card.onclick = () => window.open(article.url, '_blank');

  // 순위 배지
  const rankClass = rank <= 3 ? `rank-${rank}` : 'rank-other';
  const rankBadge = `<div class="rank-badge ${rankClass}">${rank}</div>`;

  // 키워드 태그
  const keywords = Array.isArray(article.keywords) ? article.keywords : [];
  const keywordHTML = keywords.map(kw =>
    `<span class="keyword-tag" data-keyword="${escapeHtml(kw)}"
      onmouseenter="showTooltip(event, '${escapeHtml(kw)}')"
      onmouseleave="hideTooltip()"
      onclick="event.stopPropagation()">${escapeHtml(kw)}</span>`
  ).join('');

  // 통계
  const stats = [
    article.comment_count > 0 ? `<span class="stat">💬 ${formatNum(article.comment_count)}</span>` : '',
    article.score > 0 ? `<span class="stat">⬆ ${formatNum(article.score)}</span>` : '',
  ].filter(Boolean).join('');

  const title = article.title_ko || article.title_original || '제목 없음';
  const summary = article.summary_ko || '';

  card.innerHTML = `
    ${rankBadge}
    <div class="card-body">
      <div class="card-meta">
        <span class="source-tag">${escapeHtml(article.source || '')}</span>
      </div>
      <a class="card-title" href="${escapeHtml(article.url)}" target="_blank" rel="noopener"
         title="${escapeHtml(article.title_original || '')}"
         onclick="event.stopPropagation()">${escapeHtml(title)}</a>
      ${summary ? `<div class="card-summary">${escapeHtml(summary)}</div>` : ''}
      <div class="card-footer">
        ${keywordHTML}
        <div class="card-stats">${stats}</div>
      </div>
    </div>
  `;

  return card;
}

// ===== 키워드 툴팁 =====
async function showTooltip(event, keyword) {
  // 이전 타이머 취소
  clearTimeout(tooltipTimer);

  tooltipTimer = setTimeout(async () => {
    tooltip.textContent = '불러오는 중...';
    positionTooltip(event);
    tooltip.style.display = 'block';

    try {
      const res = await fetch(`/api/keyword-tooltip/${encodeURIComponent(keyword)}`);
      const data = await res.json();
      tooltip.innerHTML = `<strong>${escapeHtml(keyword)}</strong><br><br>${escapeHtml(data.explanation || '')}`;
      positionTooltip(event);
    } catch (e) {
      tooltip.textContent = '설명을 불러오지 못했습니다.';
    }
  }, 400); // 400ms 딜레이 후 표시
}

function hideTooltip() {
  clearTimeout(tooltipTimer);
  tooltip.style.display = 'none';
}

function positionTooltip(event) {
  const x = event.clientX + 12;
  const y = event.clientY + 12;
  const maxX = window.innerWidth - 320;
  const maxY = window.innerHeight - 160;
  tooltip.style.left = `${Math.min(x, maxX)}px`;
  tooltip.style.top = `${Math.min(y, maxY)}px`;
}

// ===== 유틸 =====
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatNum(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

// ===== 초기화 =====
loadDailySummary();
loadArticles();
