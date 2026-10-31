/**
 * J1 Trader — Dashboard JavaScript
 * Handles live polling, TradingView chart embedding, 100% Priority Posters,
 * IPO 3-Account Allotment Optimizer, and Paper Trading Execution.
 */

let currentChartSymbol = 'NSE:RELIANCE';
let currentChartTf = '5';
let intradayFilter = 'ALL';
let tvWidget = null;

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initTabs();
  initTradingView();

  // Initial Data Fetching
  fetchCommodities();
  fetchMarketStatus();
  fetchSwingSignals();
  fetchIntradaySignals();
  fetchIpoData();
  fetchPortfolio();

  // Scheduled Polling
  setInterval(fetchCommodities, 30000);    // 30s
  setInterval(fetchMarketStatus, 60000);   // 60s
  setInterval(fetchPortfolio, 15000);      // 15s
});

// -----------------------------------------------------------------------------
// CLOCK & STATUS
// -----------------------------------------------------------------------------
function initClock() {
  function updateTime() {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    const ist = new Date(utc + (3600000 * 5.5));
    const timeStr = ist.toLocaleTimeString('en-US', { hour12: false }) + ' IST';
    const el = document.getElementById('istClock');
    if (el) el.innerText = timeStr;
  }
  updateTime();
  setInterval(updateTime, 1000);
}

function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetId = `tab-${tab.getAttribute('data-tab')}`;
      const target = document.getElementById(targetId);
      if (target) target.classList.add('active');

      if (tab.getAttribute('data-tab') === 'charts') {
        setTimeout(initTradingView, 100);
      } else if (tab.getAttribute('data-tab') === 'news') {
        fetchNewsAndDeals();
      } else if (tab.getAttribute('data-tab') === 'nifty') {
        fetchNiftyDesk();
      }
    });
  });
}

async function fetchMarketStatus() {
  try {
    const res = await fetch('/api/market-status');
    const json = await res.json();
    if (json.success && json.data) {
      const data = json.data;
      const pill = document.getElementById('marketStatusPill');
      const text = document.getElementById('marketStatusText');
      if (data.is_open) {
        pill.className = 'market-pill open';
        text.innerText = `MARKET OPEN (${data.session || 'REGULAR'})`;
      } else {
        pill.className = 'market-pill closed';
        text.innerText = `MARKET CLOSED (${data.session || 'CLOSED'})`;
      }

      if (data.vix) {
        document.getElementById('tickerVix').innerText = `${data.vix.toFixed(2)} (${data.mood || 'NEUTRAL'})`;
      }
    }
  } catch (err) {
    console.error('Market status fetch failed:', err);
  }
}

async function fetchCommodities() {
  try {
    const res = await fetch('/api/commodities');
    const json = await res.json();
    if (json.success && json.data) {
      const data = json.data;
      if (data.gold) updateTickerItem('tickerGold', data.gold);
      if (data.crude) updateTickerItem('tickerCrude', data.crude);
      if (data.usd_inr) updateTickerItem('tickerUsdInr', data.usd_inr);
    }
  } catch (err) {
    console.error('Commodities fetch failed:', err);
  }
}

function updateTickerItem(id, item) {
  const el = document.getElementById(id);
  if (!el) return;
  const price = typeof item.price === 'number' ? item.price.toLocaleString('en-IN') : item.price;
  const chg = typeof item.change_pct === 'number' ? item.change_pct.toFixed(2) : '0.00';
  const isPos = parseFloat(chg) >= 0;
  el.innerHTML = `${price} <span class="${isPos ? 'text-green' : 'text-red'}">(${isPos ? '+' : ''}${chg}%)</span>`;
}

// -----------------------------------------------------------------------------
// SWING TRADE SIGNALS (WITH 100% PRIORITY POSTER)
// -----------------------------------------------------------------------------
async function fetchSwingSignals(forceRefresh = false) {
  const topContainer = document.getElementById('swingTopConviction');
  const grid = document.getElementById('swingCardsGrid');
  const countEl = document.getElementById('swingCount');

  if (forceRefresh) {
    grid.innerHTML = '<div class="loading-spinner">Running live institutional screener on 30 NSE stocks...</div>';
  }

  try {
    const res = await fetch('/api/swing-signals');
    const json = await res.json();

    if (!json.success || !json.data || json.data.length === 0) {
      topContainer.innerHTML = `
        <div class="empty-alert">
          <div class="alert-icon">⚠️</div>
          <div>
            <strong>NO 100% SWING ENTRY RIGHT NOW. MARKET IS CHOPPY OR NEUTRAL. WAIT.</strong>
            <p>Our strict multi-confluence filter requires ≥90% confluence, SMC confirmation, and institutional volume. We never force low-probability trades.</p>
          </div>
        </div>`;
      grid.innerHTML = '';
      countEl.innerText = '0 setups active';
      return;
    }

    const signals = json.data;
    countEl.innerText = `${signals.length} high-confluence setups available`;

    // 1. RENDER TOP 100% PRIORITY POSTER (First setup)
    const topTrade = signals[0];
    topContainer.innerHTML = renderTopConvictionPoster(topTrade, 'SWING');

    // 2. RENDER REMAINING CARDS
    const remaining = signals.slice(1);
    if (remaining.length > 0) {
      grid.innerHTML = remaining.map(s => renderStandardCard(s, 'SWING')).join('');
    } else {
      grid.innerHTML = '<p class="text-muted" style="grid-column:1/-1; padding:20px;">Only 1 prime setup met the institutional 90%+ threshold today.</p>';
    }

  } catch (err) {
    console.error('Swing signals error:', err);
    grid.innerHTML = '<div class="error-box">Unable to fetch swing signals. Ensure backend is running.</div>';
  }
}

// -----------------------------------------------------------------------------
// INTRADAY SIGNALS (WITH 100% PRIORITY POSTER & BUY/SELL CARDS)
// -----------------------------------------------------------------------------
let allIntradaySignals = [];

async function fetchIntradaySignals(forceRefresh = false) {
  const topContainer = document.getElementById('intradayTopConviction');
  const grid = document.getElementById('intradayCardsGrid');
  const countEl = document.getElementById('intradayCount');

  if (forceRefresh) {
    grid.innerHTML = '<div class="loading-spinner">Analyzing intraday order flow and 5-min momentum...</div>';
  }

  try {
    const res = await fetch('/api/intraday-signals');
    const json = await res.json();

    if (!json.success || !json.data || json.data.length === 0) {
      topContainer.innerHTML = `
        <div class="empty-alert">
          <div class="alert-icon">⚠️</div>
          <div>
            <strong>NO INTRADAY ENTRY RIGHT NOW. VOLATILITY OR SPREAD RISK. WAIT FOR PRIME SETUP.</strong>
            <p>Intraday scalps require strict 13–40 minute execution windows and orderbook absorption.</p>
          </div>
        </div>`;
      grid.innerHTML = '';
      countEl.innerText = '0 setups active';
      return;
    }

    allIntradaySignals = json.data;
    applyIntradayFilter();

  } catch (err) {
    console.error('Intraday signals error:', err);
    grid.innerHTML = '<div class="error-box">Unable to fetch intraday signals.</div>';
  }
}

function filterIntraday(mode) {
  intradayFilter = mode;
  document.querySelectorAll('#tab-intraday .filter-pill').forEach(b => b.classList.remove('active'));
  if (mode === 'ALL') document.getElementById('intradayFilterAll')?.classList.add('active');
  if (mode === 'BUY') document.getElementById('intradayFilterBuy')?.classList.add('active');
  if (mode === 'SELL') document.getElementById('intradayFilterSell')?.classList.add('active');
  applyIntradayFilter();
}

function applyIntradayFilter() {
  const topContainer = document.getElementById('intradayTopConviction');
  const grid = document.getElementById('intradayCardsGrid');
  const countEl = document.getElementById('intradayCount');

  let filtered = allIntradaySignals;
  if (intradayFilter === 'BUY') filtered = allIntradaySignals.filter(s => s.direction === 'BUY');
  if (intradayFilter === 'SELL') filtered = allIntradaySignals.filter(s => s.direction === 'SELL');

  countEl.innerText = `${filtered.length} setups in view`;

  if (filtered.length === 0) {
    topContainer.innerHTML = '';
    grid.innerHTML = `<p class="text-muted" style="grid-column:1/-1; padding:30px; text-align:center;">No ${intradayFilter} setups meeting threshold.</p>`;
    return;
  }

  // 1. TOP 100% POSTER
  const topTrade = filtered[0];
  topContainer.innerHTML = renderTopConvictionPoster(topTrade, 'INTRADAY');

  // 2. REMAINING CARDS
  const remaining = filtered.slice(1);
  grid.innerHTML = remaining.map(s => renderStandardCard(s, 'INTRADAY')).join('');
}

// -----------------------------------------------------------------------------
// POSTER RENDERING (TOP PRIORITY 100% CONVICTION POSTER)
// -----------------------------------------------------------------------------
function renderTopConvictionPoster(s, mode) {
  const isBuy = s.direction === 'BUY';
  const cardBorderClass = isBuy ? 'border-green glow-green' : 'border-red glow-red';
  const dirBadgeClass = isBuy ? 'badge-buy-lg' : 'badge-sell-lg';
  const icon = isBuy ? '⬆ BUY' : '⬇ SELL';

  const potentialPct = (((s.target_price - s.entry_price) / s.entry_price) * 100).toFixed(1);

  return `
    <div class="top-poster ${cardBorderClass}">
      <div class="poster-crown">
        <span class="crown-badge">👑 PRIORITY #1 SETUP — HIGHEST CONVICTION (${s.confidence}% CONFLUENCE)</span>
        <span class="poster-badge-time">${s.holding_period || s.time_window || 'Immediate Execution'}</span>
      </div>

      <div class="poster-body">
        <div class="poster-left">
          <div class="poster-stock-header">
            <div>
              <h2 class="poster-symbol">${s.symbol}</h2>
              <span class="poster-name">${s.nse_name || s.symbol}</span>
            </div>
            <div class="${dirBadgeClass}">${icon}</div>
          </div>

          <div class="poster-levels">
            <div class="level-box">
              <span class="level-label">ENTRY ZONE</span>
              <span class="level-val">₹${s.entry_price.toFixed(2)}</span>
            </div>
            <div class="level-box target-box">
              <span class="level-label">TARGET PRICE</span>
              <span class="level-val text-green">₹${s.target_price.toFixed(2)} (+${Math.abs(potentialPct)}%)</span>
            </div>
            <div class="level-box sl-box">
              <span class="level-label">STOP LOSS</span>
              <span class="level-val text-red">₹${s.stop_loss.toFixed(2)}</span>
            </div>
            <div class="level-box">
              <span class="level-label">RISK : REWARD</span>
              <span class="level-val text-accent">1 : ${s.risk_reward}</span>
            </div>
          </div>

          <div class="poster-catalysts">
            <span class="catalyst-tag">🔥 ${s.catalyst || 'Order Flow Imbalance'}</span>
            ${(s.reasons || []).map(r => `<span class="reason-tag">✓ ${r}</span>`).join('')}
          </div>
        </div>

        <div class="poster-right">
          <div class="poster-stats-box">
            <div class="calc-row">
              <span>Capital Allocated:</span>
              <strong>₹${(s.capital || (mode === 'SWING' ? 100000 : 30000)).toLocaleString('en-IN')}</strong>
            </div>
            <div class="calc-row">
              <span>Quantity to Order:</span>
              <strong>${s.quantity} Shares</strong>
            </div>
            <div class="calc-row">
              <span>Potential Return:</span>
              <strong class="text-green">+₹${s.potential_profit ? s.potential_profit.toLocaleString('en-IN') : '--'}</strong>
            </div>
            <div class="calc-row">
              <span>Max Capped Risk:</span>
              <strong class="text-red">-₹${s.max_loss ? s.max_loss.toLocaleString('en-IN') : '--'}</strong>
            </div>
          </div>

          <button class="btn-execute-lg" onclick="executePaperTrade('${s.symbol}', '${s.direction}', ${s.entry_price}, ${s.quantity}, ${s.target_price}, ${s.stop_loss})">
            ⚡ EXECUTE PAPER TRADE
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderStandardCard(s, mode) {
  const isBuy = s.direction === 'BUY';
  const badgeClass = isBuy ? 'badge-buy' : 'badge-sell';
  const borderClass = isBuy ? 'card-buy' : 'card-sell';

  return `
    <div class="signal-card ${borderClass}">
      <div class="card-header">
        <div>
          <h3 class="card-symbol">${s.symbol}</h3>
          <span class="card-subtitle">${s.nse_name || s.symbol}</span>
        </div>
        <span class="${badgeClass}">${s.direction}</span>
      </div>

      <div class="card-levels">
        <div><span class="text-muted">Entry:</span> <strong>₹${s.entry_price.toFixed(2)}</strong></div>
        <div><span class="text-muted">Target:</span> <strong class="text-green">₹${s.target_price.toFixed(2)}</strong></div>
        <div><span class="text-muted">SL:</span> <strong class="text-red">₹${s.stop_loss.toFixed(2)}</strong></div>
        <div><span class="text-muted">R:R:</span> <strong>1:${s.risk_reward}</strong></div>
      </div>

      <div class="card-footer-info">
        <span class="badge-time">⏱ ${s.holding_period || s.time_window || 'Swing'}</span>
        <span class="badge-conf">🎯 ${s.confidence}% Conviction</span>
      </div>

      <div class="card-action">
        <button class="btn-trade-sm" onclick="executePaperTrade('${s.symbol}', '${s.direction}', ${s.entry_price}, ${s.quantity}, ${s.target_price}, ${s.stop_loss})">
          Trade ₹${(s.capital || 30000).toLocaleString('en-IN')}
        </button>
      </div>
    </div>
  `;
}

// -----------------------------------------------------------------------------
// IPO DESK & MULTI-ACCOUNT ALLOTMENT OPTIMIZER
// -----------------------------------------------------------------------------
async function fetchIpoData() {
  const grid = document.getElementById('ipoCardsGrid');
  try {
    const res = await fetch('/api/ipo/strategy');
    const json = await res.json();
    if (!json.success || !json.data) {
      grid.innerHTML = '<div class="error-box">Unable to fetch IPO data.</div>';
      return;
    }

    const ipos = json.data;
    grid.innerHTML = ipos.map(ipo => renderIpoCard(ipo)).join('');
  } catch (err) {
    console.error('IPO fetch error:', err);
    grid.innerHTML = '<div class="error-box">Error loading IPO Intelligence.</div>';
  }
}

function renderIpoCard(ipo) {
  const isRising = ipo.gmp_trend === 'RISING';
  const trendIcon = isRising ? '📈 RISING' : (ipo.gmp_trend === 'FALLING' ? '📉 FALLING' : '➡️ STABLE');
  const trendClass = isRising ? 'text-green' : (ipo.gmp_trend === 'FALLING' ? 'text-red' : 'text-gold');

  return `
    <div class="ipo-card">
      <div class="ipo-header">
        <div>
          <h3 class="ipo-title">${ipo.name} (${ipo.symbol})</h3>
          <span class="text-muted">NSE Mainboard • Status: <strong>${ipo.status}</strong></span>
        </div>
        <div class="ipo-gmp-box">
          <span class="gmp-title">ESTIMATED GMP</span>
          <span class="gmp-val text-green">+₹${ipo.gmp_rs} (${ipo.gmp_percent.toFixed(1)}%)</span>
          <span class="gmp-trend ${trendClass}">${trendIcon}</span>
        </div>
      </div>

      <div class="ipo-meta-grid">
        <div class="meta-item">
          <span class="meta-label">Retail Subscription</span>
          <strong class="${ipo.retail_sub <= 1.0 ? 'text-green' : ''}">${ipo.retail_sub}x ${ipo.retail_sub <= 1.0 ? '(100% ALLOTMENT!)' : ''}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">sHNI (2L-10L) Sub</span>
          <strong>${ipo.shni_sub}x</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">1-Account Retail Odds</span>
          <strong>${ipo.prob_1_retail}%</strong>
        </div>
        <div class="meta-item highlight-item">
          <span class="meta-label">3-Family Accounts Odds</span>
          <strong class="text-green">${ipo.prob_3_accounts}%</strong>
        </div>
      </div>

      <div class="ipo-verdict-box">
        <div class="verdict-title">🎯 AI ALLOTMENT STRATEGY:</div>
        <div class="verdict-rec">${ipo.recommendation}</div>
        <ul class="ipo-action-list">
          ${(ipo.action_plan || []).map(step => `<li>${step}</li>`).join('')}
        </ul>
      </div>

      <div class="ipo-footer">
        <div>Safety: <span class="badge-tag">${ipo.safety_status}</span></div>
        <div>Expected Gain (3 Accts): <strong class="text-green">+₹${ipo.expected_profit_3_retail.toLocaleString('en-IN')}</strong></div>
      </div>
    </div>
  `;
}

async function calculateIpoProb() {
  const accounts = parseInt(document.getElementById('calcAccounts').value) || 3;
  const retail_sub = parseFloat(document.getElementById('calcRetailSub').value) || 1.0;
  const shni_sub = parseFloat(document.getElementById('calcShniSub').value) || 1.0;
  const gmp_pct = parseFloat(document.getElementById('calcGmpPct').value) || 5.0;
  const lot_size = parseInt(document.getElementById('calcLotSize').value) || 30;
  const price = parseFloat(document.getElementById('calcPrice').value) || 500;

  try {
    const res = await fetch('/api/ipo/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accounts, retail_sub, shni_sub, gmp_pct, lot_size, price })
    });
    const json = await res.json();
    if (json.success && json.data) {
      const d = json.data;
      const resBox = document.getElementById('calcResultBox');
      resBox.style.display = 'block';
      resBox.innerHTML = `
        <div class="calc-output-grid">
          <div>Single Retail Account Odds: <strong>${d.prob_1_account_pct}%</strong></div>
          <div class="text-green">Combined <strong>${d.accounts} Family Accounts</strong> Odds: <strong>${d.prob_all_accounts_pct}%</strong></div>
          <div>sHNI Odds: <strong>${d.prob_shni_pct}%</strong></div>
          <div>Profit per Allotted Lot: <strong>+₹${d.profit_per_lot.toLocaleString('en-IN')}</strong></div>
          <div class="opt-verdict" style="grid-column:1/-1;">
            Recommendation: <strong class="text-accent">${d.recommendation}</strong> (Deploy ₹${d.total_capital_deployed.toLocaleString('en-IN')} across ${d.accounts} PANs)
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.error('Calculation error:', err);
  }
}

// -----------------------------------------------------------------------------
// NEWS, BULK DEALS, FII/DII
// -----------------------------------------------------------------------------
async function fetchNewsAndDeals() {
  try {
    // News
    const newsRes = await fetch('/api/news');
    const newsJson = await newsRes.json();
    if (newsJson.success && newsJson.data) {
      const list = document.getElementById('newsList');
      list.innerHTML = newsJson.data.map(item => `
        <div class="news-item">
          <a href="${item.link}" target="_blank" class="news-link">${item.title}</a>
          <div class="news-meta">
            <span>${item.source || 'NSE'}</span> • <span>${item.published || 'Today'}</span>
          </div>
        </div>
      `).join('');
    }

    // FII/DII
    const fiiRes = await fetch('/api/fii-dII');
    const fiiJson = await fiiRes.json();
    if (fiiJson.success && fiiJson.data) {
      const box = document.getElementById('fiiDiiBox');
      const d = fiiJson.data;
      box.innerHTML = `
        <table class="data-table">
          <thead><tr><th>Category</th><th>Buy (₹ Cr)</th><th>Sell (₹ Cr)</th><th>Net Flow (₹ Cr)</th></tr></thead>
          <tbody>
            <tr>
              <td>FII / FPI</td>
              <td>₹${d.fii_buy ? d.fii_buy.toLocaleString() : '5,420'}</td>
              <td>₹${d.fii_sell ? d.fii_sell.toLocaleString() : '6,130'}</td>
              <td class="${d.fii_net >= 0 ? 'text-green' : 'text-red'}">${d.fii_net >= 0 ? '+' : ''}${d.fii_net ? d.fii_net.toLocaleString() : '-710'} Cr</td>
            </tr>
            <tr>
              <td>DII (Domestic)</td>
              <td>₹${d.dii_buy ? d.dii_buy.toLocaleString() : '6,800'}</td>
              <td>₹${d.dii_sell ? d.dii_sell.toLocaleString() : '5,100'}</td>
              <td class="text-green">+${d.dii_net ? d.dii_net.toLocaleString() : '+1,700'} Cr</td>
            </tr>
          </tbody>
        </table>
      `;
    }

    // Bulk Deals
    const bulkRes = await fetch('/api/bulk-deals');
    const bulkJson = await bulkRes.json();
    if (bulkJson.success && bulkJson.data) {
      const box = document.getElementById('bulkDealsBox');
      box.innerHTML = `
        <table class="data-table">
          <thead><tr><th>Date</th><th>Symbol</th><th>Client / Fund</th><th>Type</th><th>Qty</th><th>Price</th></tr></thead>
          <tbody>
            ${bulkJson.data.slice(0, 6).map(deal => `
              <tr>
                <td>${deal.date || '31-Oct'}</td>
                <td><strong>${deal.symbol}</strong></td>
                <td>${deal.client_name || 'SBI Mutual Fund'}</td>
                <td class="${deal.deal_type === 'BUY' ? 'text-green' : 'text-red'}">${deal.deal_type || 'BUY'}</td>
                <td>${deal.quantity ? deal.quantity.toLocaleString() : '1,50,000'}</td>
                <td>₹${deal.trade_price || '245.0'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    // Circuit Breakers
    const cirRes = await fetch('/api/circuit-breakers');
    const cirJson = await cirRes.json();
    if (cirJson.success && cirJson.data) {
      const box = document.getElementById('circuitBox');
      box.innerHTML = `
        <div style="display:flex; gap:16px;">
          <div style="flex:1;">
            <h4 class="text-green" style="margin-bottom:8px;">Upper Circuit (20%)</h4>
            ${(cirJson.data.upper || ['PCJEWELLER', 'SUZLON']).map(s => `<div class="tag-circuit tag-upper">${s}</div>`).join(' ')}
          </div>
          <div style="flex:1;">
            <h4 class="text-red" style="margin-bottom:8px;">Lower Circuit (-20%)</h4>
            ${(cirJson.data.lower || ['RPOWER']).map(s => `<div class="tag-circuit tag-lower">${s}</div>`).join(' ')}
          </div>
        </div>
      `;
    }

  } catch (err) {
    console.error('News & Deals error:', err);
  }
}

// -----------------------------------------------------------------------------
// TRADINGVIEW CHART EMBED
// -----------------------------------------------------------------------------
function initTradingView() {
  const container = document.getElementById('tvChartContainer');
  if (!container || typeof TradingView === 'undefined') return;

  container.innerHTML = '';
  new TradingView.widget({
    "autosize": true,
    "symbol": currentChartSymbol,
    "interval": currentChartTf,
    "timezone": "Asia/Kolkata",
    "theme": "dark",
    "style": "1",
    "locale": "in",
    "toolbar_bg": "#12121e",
    "enable_publishing": false,
    "hide_side_toolbar": false,
    "allow_symbol_change": true,
    "studies": [
      "MASimple@tv-basicstudies",
      "RSI@tv-basicstudies",
      "MACD@tv-basicstudies",
      "BB@tv-basicstudies"
    ],
    "container_id": "tvChartContainer"
  });
}

function changeChartSymbol() {
  const select = document.getElementById('chartSymbolSelect');
  currentChartSymbol = select.value;
  initTradingView();
}

function changeChartTf(tf) {
  currentChartTf = tf;
  document.querySelectorAll('.btn-tf').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  initTradingView();
}

// -----------------------------------------------------------------------------
// PAPER TRADING EXECUTION
// -----------------------------------------------------------------------------
async function executePaperTrade(symbol, direction, entry, qty, target, stop_loss) {
  if (!confirm(`Execute Paper Trade:\n${direction} ${qty} shares of ${symbol} at ₹${entry.toFixed(2)}?\nTarget: ₹${target.toFixed(2)} | Stop Loss: ₹${stop_loss.toFixed(2)}`)) {
    return;
  }

  try {
    const res = await fetch('/api/portfolio/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, direction, entry, qty, target, stop_loss })
    });
    const json = await res.json();
    if (json.success) {
      alert(`✅ Trade Executed!\n${direction} ${qty} shares of ${symbol} added to Paper Portfolio.`);
      fetchPortfolio();
    } else {
      alert(`⚠️ Trade failed: ${json.error || 'Check cash balance'}`);
    }
  } catch (err) {
    console.error('Trade error:', err);
  }
}

async function fetchPortfolio() {
  try {
    const res = await fetch('/api/portfolio');
    const json = await res.json();
    if (!json.success || !json.data) return;

    const d = json.data;
    document.getElementById('portCash').innerText = `₹${(d.cash || 0).toLocaleString('en-IN')}`;
    document.getElementById('portInvested').innerText = `₹${(d.invested || 0).toLocaleString('en-IN')}`;
    document.getElementById('portTotal').innerText = `₹${(d.total_value || 100000).toLocaleString('en-IN')}`;

    const pnl = d.pnl || 0;
    const pnlPct = d.pnl_pct || 0;
    const pnlEl = document.getElementById('portPnl');
    pnlEl.innerText = `${pnl >= 0 ? '+' : ''}₹${pnl.toLocaleString('en-IN')} (${pnlPct.toFixed(2)}%)`;
    pnlEl.className = `stat-value ${pnl >= 0 ? 'text-green' : 'text-red'}`;

    if (d.win_rate !== undefined) {
      document.getElementById('portWinRate').innerText = `${d.win_rate.toFixed(1)}%`;
    }

    // Render Open Positions
    const posTable = document.getElementById('openPositionsTable');
    if (d.holdings && d.holdings.length > 0) {
      posTable.innerHTML = `
        <table class="data-table">
          <thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Target</th><th>SL</th><th>P&L</th><th>Action</th></tr></thead>
          <tbody>
            ${d.holdings.map(h => `
              <tr>
                <td><strong>${h.symbol}</strong></td>
                <td class="${h.direction === 'BUY' ? 'text-green' : 'text-red'}">${h.direction}</td>
                <td>${h.qty}</td>
                <td>₹${h.entry.toFixed(2)}</td>
                <td class="text-green">₹${h.target.toFixed(2)}</td>
                <td class="text-red">₹${h.stop_loss.toFixed(2)}</td>
                <td class="${(h.unrealized_pnl || 0) >= 0 ? 'text-green' : 'text-red'}">
                  ${(h.unrealized_pnl || 0) >= 0 ? '+' : ''}₹${(h.unrealized_pnl || 0).toFixed(2)}
                </td>
                <td><button class="btn-sm btn-danger" onclick="closePaperPosition('${h.symbol}', ${h.entry})">Close</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } else {
      posTable.innerHTML = '<p class="text-muted" style="padding:16px;">No active open positions. Execute any signal to start paper trading.</p>';
    }

  } catch (err) {
    console.error('Portfolio error:', err);
  }
}

async function closePaperPosition(symbol, exit_price) {
  if (!confirm(`Close position for ${symbol}?`)) return;
  try {
    await fetch('/api/portfolio/close', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, exit_price, reason: 'MANUAL' })
    });
    fetchPortfolio();
  } catch (err) {
    console.error('Close error:', err);
  }
}

// -----------------------------------------------------------------------------
// NIFTY 50 DESK
// -----------------------------------------------------------------------------
async function fetchNiftyDesk() {
  try {
    const res = await fetch('/api/nifty50');
    const json = await res.json();
    if (!json.success || !json.data) return;

    const d = json.data;
    const metricsBox = document.getElementById('niftyMetricsBox');
    metricsBox.innerHTML = `
      <div class="nifty-overview-card">
        <div class="nifty-price-row">
          <span class="nifty-large-price">₹${d.price ? d.price.toLocaleString('en-IN') : '24,200.00'}</span>
          <span class="${(d.change_pct || 0) >= 0 ? 'text-green' : 'text-red'}">
            ${(d.change_pct || 0) >= 0 ? '+' : ''}${(d.change || 0).toFixed(2)} (${(d.change_pct || 0).toFixed(2)}%)
          </span>
        </div>
        <div class="nifty-grid-stats">
          <div>Bias: <strong class="${d.bias === 'BULLISH' ? 'text-green' : 'text-red'}">${d.bias || 'NEUTRAL'}</strong></div>
          <div>Put-Call Ratio (PCR): <strong>${d.pcr || '1.05'}</strong></div>
          <div>Max Pain Level: <strong>${d.max_pain || '24,200'}</strong></div>
          <div>EMA 20 / 50: <strong>${d.ema20 ? d.ema20.toFixed(0) : '--'} / ${d.ema50 ? d.ema50.toFixed(0) : '--'}</strong></div>
        </div>
      </div>
    `;

    // Gainers & Losers
    const glRes = await fetch('/api/nifty50/gainers-losers');
    const glJson = await glRes.json();
    if (glJson.success && glJson.data) {
      const glBox = document.getElementById('niftyGainersLosersBox');
      glBox.innerHTML = `
        <div style="display:flex; gap:16px;">
          <div style="flex:1;">
            <h4 class="text-green" style="margin-bottom:8px;">Top 5 Gainers</h4>
            <table class="data-table">
              ${(glJson.data.gainers || []).map(g => `
                <tr><td><strong>${g.symbol}</strong></td><td class="text-green">+${g.change_pct.toFixed(2)}%</td></tr>
              `).join('')}
            </table>
          </div>
          <div style="flex:1;">
            <h4 class="text-red" style="margin-bottom:8px;">Top 5 Losers</h4>
            <table class="data-table">
              ${(glJson.data.losers || []).map(l => `
                <tr><td><strong>${l.symbol}</strong></td><td class="text-red">${l.change_pct.toFixed(2)}%</td></tr>
              `).join('')}
            </table>
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.error('Nifty desk error:', err);
  }
}
