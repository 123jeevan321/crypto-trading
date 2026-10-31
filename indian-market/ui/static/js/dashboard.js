/**
 * J1 TRADER — Institutional Dashboard JavaScript
 * Minimal Front Face Posters with Smooth Drill-Down Accordion Drawer,
 * Live Dynamic Quotes, Module Visibility Toggles, and Collapsible Navbar.
 */

let currentChartSymbol = 'NSE:PCJEWELLER';
let currentChartTf = '5';
let intradayFilter = 'ALL';
let allIntradaySignals = [];
let isNavCollapsed = false;

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initModuleTabs();
  initModuleToggles();
  initTradingView();

  // Load All Core Modules with Live Data
  fetchCommodities();
  fetchMarketStatus();
  fetchSwingSignals();
  fetchIntradaySignals();
  fetchIpoData();
  fetchPortfolio();

  // Scheduled Polling
  setInterval(fetchCommodities, 30000);
  setInterval(fetchMarketStatus, 60000);
  setInterval(fetchPortfolio, 15000);
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

// -----------------------------------------------------------------------------
// MODULE TABS & CUSTOMIZATION (ENABLE / DISABLE MODULES & COLLAPSE)
// -----------------------------------------------------------------------------
function initModuleTabs() {
  const btns = document.querySelectorAll('.nav-btn');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.module-view').forEach(v => v.classList.remove('active'));

      btn.classList.add('active');
      const targetId = `tab-${btn.getAttribute('data-tab')}`;
      const target = document.getElementById(targetId);
      if (target) target.classList.add('active');

      if (btn.getAttribute('data-tab') === 'charts') {
        setTimeout(initTradingView, 100);
      }
    });
  });
}

function toggleSettingsDrawer() {
  const drawer = document.getElementById('modulesToggleDrawer');
  if (drawer.style.display === 'none' || !drawer.style.display) {
    drawer.style.display = 'block';
  } else {
    drawer.style.display = 'none';
  }
}

function toggleNavCollapse() {
  isNavCollapsed = !isNavCollapsed;
  const nav = document.getElementById('moduleNav');
  const btn = document.getElementById('btnCollapseNav');
  if (isNavCollapsed) {
    nav.classList.add('collapsed');
    btn.innerText = '⬇️';
    btn.title = 'Show Navigation Bar';
  } else {
    nav.classList.remove('collapsed');
    btn.innerText = '⬆️';
    btn.title = 'Hide Navigation Bar';
  }
}

function updateModuleVisibility(moduleKey) {
  const checkbox = document.getElementById(`toggle${capitalize(moduleKey)}`);
  const navBtn = document.getElementById(`navBtn-${moduleKey}`);
  const view = document.getElementById(`tab-${moduleKey}`);

  if (checkbox && navBtn) {
    if (checkbox.checked) {
      navBtn.style.display = 'inline-flex';
    } else {
      navBtn.style.display = 'none';
      if (navBtn.classList.contains('active')) {
        // Switch to the first visible module
        const firstVisible = document.querySelector('.nav-btn:not([style*="display: none"])');
        if (firstVisible) firstVisible.click();
      }
    }
  }
}

function initModuleToggles() {
  ['swing', 'intraday', 'ipo', 'charts', 'portfolio'].forEach(key => {
    updateModuleVisibility(key);
  });
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// -----------------------------------------------------------------------------
// MARKET STATUS & COMMODITIES
// -----------------------------------------------------------------------------
async function fetchMarketStatus() {
  try {
    const res = await fetch('/api/market-status');
    const json = await res.json();
    if (json.success && json.data) {
      const d = json.data;
      const pill = document.getElementById('marketStatusPill');
      const text = document.getElementById('marketStatusText');
      if (d.is_open) {
        pill.className = 'market-pill open';
        text.innerText = `MARKET LIVE (${d.session || 'REGULAR'})`;
      } else {
        pill.className = 'market-pill closed';
        text.innerText = `WEEKEND CLOSED • MONDAY LIVE SETUPS READY`;
      }
      if (d.vix) {
        document.getElementById('tickerVix').innerText = `${d.vix.toFixed(2)}`;
      }
    }
  } catch (err) {
    console.error('Market status error:', err);
  }
}

async function fetchCommodities() {
  try {
    const res = await fetch('/api/commodities');
    const json = await res.json();
    if (json.success && json.data) {
      const d = json.data;
      if (d.gold) updateTickerItem('tickerGold', d.gold);
      if (d.crude) updateTickerItem('tickerCrude', d.crude);
      if (d.usd_inr) updateTickerItem('tickerUsdInr', d.usd_inr);
    }
  } catch (err) {
    console.error('Commodities error:', err);
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
// MODULE 1: SWING TRADE POSTERS (CLEAN FRONT FACE WITH DRILL-DOWN)
// -----------------------------------------------------------------------------
async function fetchSwingSignals() {
  const priorityWrap = document.getElementById('swingPriorityPosterWrap');
  const grid = document.getElementById('swingPostersGrid');
  const countEl = document.getElementById('swingLiveCount');

  try {
    const res = await fetch('/api/swing-signals');
    const json = await res.json();
    const signals = Array.isArray(json.data) ? json.data : (json.data && json.data.signals ? json.data.signals : []);

    if (signals.length === 0) {
      grid.innerHTML = '<div class="loading-spinner">No swing setups available right now. Market neutral.</div>';
      return;
    }

    countEl.innerText = `${signals.length} Institutional setups synced with live market`;

    // 1. Render Priority #1 Poster at Top
    priorityWrap.innerHTML = renderCompactPosterCard(signals[0], true, 1, 'swing');

    // 2. Render Remaining Posters (Rank 2 to 15)
    const remaining = signals.slice(1);
    grid.innerHTML = remaining.map((s, idx) => renderCompactPosterCard(s, false, idx + 2, 'swing')).join('');

  } catch (err) {
    console.error('Swing fetch error:', err);
    grid.innerHTML = '<div class="loading-spinner text-red">Error loading live swing setups.</div>';
  }
}

// -----------------------------------------------------------------------------
// MODULE 2: INTRADAY SCALP POSTERS
// -----------------------------------------------------------------------------
async function fetchIntradaySignals() {
  const grid = document.getElementById('intradayPostersGrid');
  try {
    const res = await fetch('/api/intraday-signals');
    const json = await res.json();
    allIntradaySignals = Array.isArray(json.data) ? json.data : (json.data && json.data.signals ? json.data.signals : []);

    if (allIntradaySignals.length === 0) {
      grid.innerHTML = '<div class="loading-spinner">No intraday scalps available right now.</div>';
      return;
    }

    renderIntradayView();

  } catch (err) {
    console.error('Intraday fetch error:', err);
    grid.innerHTML = '<div class="loading-spinner text-red">Error loading live intraday setups.</div>';
  }
}

function filterIntradayCards(mode) {
  intradayFilter = mode;
  document.querySelectorAll('.intraday-filter-bar .filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  renderIntradayView();
}

function renderIntradayView() {
  const priorityWrap = document.getElementById('intradayPriorityPosterWrap');
  const grid = document.getElementById('intradayPostersGrid');
  const countEl = document.getElementById('intradayLiveCount');

  let list = allIntradaySignals;
  if (intradayFilter === 'BUY') list = allIntradaySignals.filter(s => s.direction === 'BUY');
  if (intradayFilter === 'SELL') list = allIntradaySignals.filter(s => s.direction === 'SELL');

  countEl.innerText = `${list.length} setups in view (${intradayFilter})`;

  if (list.length === 0) {
    priorityWrap.innerHTML = '';
    grid.innerHTML = `<div class="loading-spinner">No ${intradayFilter} setups available.</div>`;
    return;
  }

  // Render Priority #1
  priorityWrap.innerHTML = renderCompactPosterCard(list[0], true, 1, 'intraday');

  // Render Remaining
  const remaining = list.slice(1);
  grid.innerHTML = remaining.map((s, idx) => renderCompactPosterCard(s, false, idx + 2, 'intraday')).join('');
}

// -----------------------------------------------------------------------------
// MINIMAL FRONT-FACE POSTER WITH DRILL-DOWN DRAWER
// -----------------------------------------------------------------------------
function renderCompactPosterCard(s, isMaster = false, rank = 1, moduleType = 'swing') {
  const isBuy = s.direction === 'BUY';
  const cardBorderClass = isBuy ? 'card-buy' : 'card-sell';
  const pillClass = isBuy ? 'pill-buy' : 'pill-sell';
  const btnClass = isBuy ? 'btn-poster-execute' : 'btn-poster-execute btn-poster-sell';
  const dirText = isBuy ? '🟢 BUY ⬆' : '🔴 SELL ⬇';

  const masterClass = isMaster ? 'master-poster' : '';
  const crownTag = isMaster
    ? `<span class="poster-crown-tag crown-master">👑 PRIORITY #1 SETUP — ${s.confidence}% CONVICTION</span>`
    : `<span class="poster-crown-tag crown-standard">RANK #${rank} • ${s.confidence}% CONFLUENCE</span>`;

  const timeLabel = s.holding_period || s.time_window || 'Immediate Execution';
  const uniqueId = `drawer-${moduleType}-${rank}-${s.symbol}`;

  return `
    <div class="poster-card ${cardBorderClass} ${masterClass}">
      <!-- Crown / Time Bar -->
      <div class="poster-crown-bar">
        ${crownTag}
        <span class="poster-time-tag">⏱ ${timeLabel}</span>
      </div>

      <!-- Header: Symbol + Name + Direction Pill -->
      <div class="poster-head">
        <div>
          <h3 class="poster-stock-sym">${s.symbol}</h3>
          <p class="poster-stock-name">${s.nse_name || s.symbol}</p>
        </div>
        <div class="poster-dir-pill ${pillClass}">${dirText}</div>
      </div>

      <!-- 4-Level Matrix (Entry, Target, Stop Loss, Risk:Reward) -->
      <div class="poster-levels-grid">
        <div class="lvl-cell">
          <span class="lvl-lbl">ENTRY (LTP)</span>
          <span class="lvl-num">₹${s.entry_price.toFixed(2)}</span>
        </div>
        <div class="lvl-cell">
          <span class="lvl-lbl">TARGET</span>
          <span class="lvl-num text-green">₹${s.target_price.toFixed(2)}</span>
        </div>
        <div class="lvl-cell">
          <span class="lvl-lbl">STOP LOSS</span>
          <span class="lvl-num text-red">₹${s.stop_loss.toFixed(2)}</span>
        </div>
        <div class="lvl-cell">
          <span class="lvl-lbl">RISK:REWARD</span>
          <span class="lvl-num text-accent">1 : ${s.risk_reward}</span>
        </div>
      </div>

      <!-- Financial Execution Strip -->
      <div class="poster-finance-strip">
        <div>Capital: <strong>₹${(s.capital || 100000).toLocaleString('en-IN')}</strong> (${s.quantity} Qty)</div>
        <div>Target Gain: <strong class="text-green">+₹${s.potential_profit ? s.potential_profit.toLocaleString('en-IN') : '--'} (+${s.potential_percent || ''}%)</strong></div>
        <div>Max Risk: <strong class="text-red">-₹${s.max_loss ? s.max_loss.toLocaleString('en-IN') : '--'}</strong></div>
      </div>

      <!-- Interactive Drill-Down Arrow Button -->
      <button class="btn-drilldown-toggle" onclick="toggleCardDrawer('${uniqueId}', this)">
        <span>⬇️ Analysis, Institutional Buyer &amp; Monday Setup</span>
      </button>

      <!-- Expandable Drill-Down Details Drawer (Hidden by default) -->
      <div class="drilldown-drawer" id="${uniqueId}" style="display:none;">
        <div class="callout-row">
          <div class="callout-tag-title text-gold">📅 MONDAY SETUP PREDICTION (${s.confidence}% CHANCE):</div>
          <div style="color:#fff9c4;">${s.monday_prediction}</div>
        </div>
        <div class="callout-row">
          <div class="callout-tag-title text-purple">🏛️ INSTITUTIONAL ACCUMULATION &amp; BUYER:</div>
          <div style="color:#ede7f6;">${s.institutional_buyer || 'Institutional DII/FII Active Accumulation'}</div>
        </div>
        <div class="callout-row">
          <div class="callout-tag-title text-accent">📰 RECENT NEWS &amp; EVENT CATALYST:</div>
          <div style="color:#e3f2fd;">${s.catalyst}</div>
        </div>
        <div class="callout-row">
          <div class="callout-tag-title text-green">⚡ ORDER FLOW DELTA:</div>
          <div class="text-green">${s.orderflow_delta || '+75% Inflow'}</div>
        </div>
      </div>

      <!-- Primary 1-Click Execution Button -->
      <button class="${btnClass}" onclick="executePaperTrade('${s.symbol}', '${s.direction}', ${s.entry_price}, ${s.quantity}, ${s.target_price}, ${s.stop_loss})">
        ⚡ EXECUTE PAPER TRADE (₹${(s.capital || 100000).toLocaleString('en-IN')})
      </button>
    </div>
  `;
}

function toggleCardDrawer(drawerId, btn) {
  const drawer = document.getElementById(drawerId);
  if (!drawer) return;

  if (drawer.style.display === 'none' || !drawer.style.display) {
    drawer.style.display = 'block';
    btn.innerHTML = '<span>⬆️ Hide Details</span>';
  } else {
    drawer.style.display = 'none';
    btn.innerHTML = '<span>⬇️ Analysis, Institutional Buyer &amp; Monday Setup</span>';
  }
}

// -----------------------------------------------------------------------------
// MODULE 3: IPO DESK (MAINBOARD & 3-ACCOUNT OPTIMIZER)
// -----------------------------------------------------------------------------
async function fetchIpoData() {
  const grid = document.getElementById('ipoPostersGrid');
  try {
    const res = await fetch('/api/ipo/strategy');
    const json = await res.json();
    const ipos = json.data || [];

    if (ipos.length === 0) {
      grid.innerHTML = '<div class="loading-spinner text-red">Unable to load IPO data.</div>';
      return;
    }

    grid.innerHTML = ipos.map(ipo => renderIpoPoster(ipo)).join('');
  } catch (err) {
    console.error('IPO error:', err);
    grid.innerHTML = '<div class="loading-spinner text-red">Error fetching IPO Desk.</div>';
  }
}

function renderIpoPoster(ipo) {
  const isRising = ipo.gmp_trend === 'RISING';
  const trendTag = isRising ? '📈 RISING' : (ipo.gmp_trend === 'FALLING' ? '📉 FALLING' : '➡️ STABLE');
  const trendClass = isRising ? 'text-green' : (ipo.gmp_trend === 'FALLING' ? 'text-red' : 'text-gold');

  return `
    <div class="poster-card card-buy">
      <div class="poster-crown-bar">
        <span class="poster-crown-tag" style="background:rgba(41,121,255,0.2); color:#2979ff; border:1px solid #2979ff;">
          NSE MAINBOARD • ${ipo.status}
        </span>
        <span class="poster-time-tag">${ipo.safety_status}</span>
      </div>

      <div class="poster-head">
        <div>
          <h3 class="poster-stock-sym">${ipo.name}</h3>
          <p class="poster-stock-name">NSE SYMBOL: <strong>${ipo.symbol}</strong></p>
        </div>
        <div style="text-align:right;">
          <span style="font-size:0.68rem; color:#78909c; display:block;">ESTIMATED GMP</span>
          <span style="font-size:1.35rem; font-weight:900; font-family:var(--font-mono);" class="text-green">+₹${ipo.gmp_rs}</span>
          <span style="font-size:0.75rem; font-weight:700;" class="${trendClass}">${trendTag} (+${ipo.gmp_percent.toFixed(1)}%)</span>
        </div>
      </div>

      <div class="poster-levels-grid" style="grid-template-columns: repeat(4, 1fr);">
        <div class="lvl-cell">
          <span class="lvl-lbl">RETAIL SUB</span>
          <span class="lvl-num ${ipo.retail_sub <= 1.0 ? 'text-green' : ''}">${ipo.retail_sub}x</span>
        </div>
        <div class="lvl-cell">
          <span class="lvl-lbl">sHNI (2L-10L)</span>
          <span class="lvl-num">${ipo.shni_sub}x</span>
        </div>
        <div class="lvl-cell">
          <span class="lvl-lbl">1-ACCT ODDS</span>
          <span class="lvl-num">${ipo.prob_1_retail}%</span>
        </div>
        <div class="lvl-cell" style="background:rgba(0,230,118,0.1); border-radius:8px;">
          <span class="lvl-lbl" style="color:#00e676;">3-PAN ODDS</span>
          <span class="lvl-num text-green">${ipo.prob_3_accounts}%</span>
        </div>
      </div>

      <div class="drilldown-drawer" style="display:block; margin-top:8px;">
        <div class="callout-tag-title text-green">🎯 ALLOTMENT STRATEGY &amp; ACTION PLAN:</div>
        <div style="font-weight:800; font-size:0.85rem; color:#fff; margin-bottom:4px;">${ipo.recommendation}</div>
        <ul style="padding-left:18px; margin:0; font-size:0.75rem; color:#cfd8dc;">
          ${(ipo.action_plan || []).map(step => `<li>${step}</li>`).join('')}
        </ul>
      </div>

      <div class="poster-finance-strip" style="margin-top:10px;">
        <div>Capital for 3 PANs: <strong>₹${ipo.min_investment_3accounts.toLocaleString('en-IN')}</strong></div>
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
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px; margin-top:16px; font-size:0.85rem; background:rgba(0,0,0,0.35); padding:16px; border-radius:12px; border:1px solid rgba(0,230,118,0.3);">
          <div>1 Retail Account Odds: <strong>${d.prob_1_account_pct}%</strong></div>
          <div class="text-green">Combined <strong>${d.accounts} Family PANs</strong> Odds: <strong>${d.prob_all_accounts_pct}%</strong></div>
          <div>sHNI Category Odds: <strong>${d.prob_shni_pct}%</strong></div>
          <div>Profit per Allotted Lot: <strong class="text-green">+₹${d.profit_per_lot.toLocaleString('en-IN')}</strong></div>
          <div style="grid-column:1/-1; background:rgba(41,121,255,0.12); padding:10px; border-radius:8px; border:1px solid #2979ff;">
            Recommendation: <strong class="text-accent">${d.recommendation}</strong> — Deploy ₹${d.total_capital_deployed.toLocaleString('en-IN')} across ${d.accounts} PANs.
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.error('Calculation error:', err);
  }
}

// -----------------------------------------------------------------------------
// MODULE 4: INTERACTIVE TRADINGVIEW CHART EMBED
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
    "toolbar_bg": "#10101c",
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
  document.querySelectorAll('.tf-btn-group .btn-tf').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  initTradingView();
}

// -----------------------------------------------------------------------------
// MODULE 5: PAPER TRADING PORTFOLIO (₹1,00,000)
// -----------------------------------------------------------------------------
async function executePaperTrade(symbol, direction, entry, qty, target, stop_loss) {
  if (!confirm(`Confirm Paper Trade Execution:\n${direction} ${qty} shares of ${symbol} at ₹${entry.toFixed(2)}?\nTarget: ₹${target.toFixed(2)} | Stop Loss: ₹${stop_loss.toFixed(2)}`)) {
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
      alert(`✅ Trade Executed Successfully!\n${direction} ${qty} shares of ${symbol} active in Paper Portfolio.`);
      fetchPortfolio();
    } else {
      alert(`⚠️ Trade could not be executed: ${json.error || 'Check available cash'}`);
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
    pnlEl.className = `metric-val ${pnl >= 0 ? 'text-green' : 'text-red'}`;

    if (d.win_rate !== undefined) {
      document.getElementById('portWinRate').innerText = `${d.win_rate.toFixed(1)}%`;
    }

    const posTable = document.getElementById('openPositionsTable');
    if (d.holdings && d.holdings.length > 0) {
      posTable.innerHTML = `
        <table class="data-table" style="width:100%; border-collapse:collapse; font-size:0.85rem;">
          <thead>
            <tr style="text-align:left; color:#78909c; border-bottom:1px solid var(--border);">
              <th style="padding:10px;">Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Target</th><th>SL</th><th>Unrealized P&amp;L</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${d.holdings.map(h => `
              <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:10px;"><strong>${h.symbol}</strong></td>
                <td class="${h.direction === 'BUY' ? 'text-green' : 'text-red'}"><strong>${h.direction}</strong></td>
                <td>${h.qty}</td>
                <td>₹${h.entry.toFixed(2)}</td>
                <td class="text-green">₹${h.target.toFixed(2)}</td>
                <td class="text-red">₹${h.stop_loss.toFixed(2)}</td>
                <td class="${(h.unrealized_pnl || 0) >= 0 ? 'text-green' : 'text-red'}">
                  ${(h.unrealized_pnl || 0) >= 0 ? '+' : ''}₹${(h.unrealized_pnl || 0).toFixed(2)}
                </td>
                <td><button style="background:rgba(255,23,68,0.2); color:#ff1744; border:1px solid #ff1744; padding:4px 10px; border-radius:6px; cursor:pointer;" onclick="closePaperPosition('${h.symbol}', ${h.entry})">Close</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } else {
      posTable.innerHTML = '<p class="text-muted" style="padding:16px;">No active open positions. Click "⚡ EXECUTE PAPER TRADE" on any poster.</p>';
    }

  } catch (err) {
    console.error('Portfolio error:', err);
  }
}

async function closePaperPosition(symbol, exit_price) {
  if (!confirm(`Close paper position for ${symbol}?`)) return;
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
