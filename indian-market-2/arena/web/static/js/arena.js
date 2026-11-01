/**
 * Breaking Money — AI Trading Arena Web UI Controller
 */

async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) return;
        const data = await res.json();

        // Update elements
        document.getElementById("challenge-status").innerText = data.status;
        document.getElementById("current-day").innerText = data.current_day;
        document.getElementById("target-days").innerText = data.target_days;

        const pct = Math.min(100, (data.current_day / data.target_days) * 100);
        document.getElementById("progress-fill").style.width = `${pct}%`;

        document.getElementById("initial-cap").innerText = formatINR(data.initial_capital);
        document.getElementById("total-equity").innerText = formatINR(data.current_equity);
        document.getElementById("available-cash").innerText = formatINR(data.current_cash);

        const netPnl = data.metrics.total_net_pnl || 0;
        const pnlEl = document.getElementById("daily-pnl");
        const netPnlEl = document.getElementById("net-pnl");

        pnlEl.innerText = `${netPnl >= 0 ? '+' : ''}₹${formatINR(netPnl)} (${data.metrics.roi_pct || 0}%)`;
        pnlEl.className = `val ${netPnl >= 0 ? 'positive' : 'negative'}`;

        netPnlEl.innerText = `${netPnl >= 0 ? '+' : ''}₹${formatINR(netPnl)}`;
        netPnlEl.style.color = netPnl >= 0 ? '#00f298' : '#ff3366';

        document.getElementById("win-rate").innerText = (data.metrics.win_rate_pct || 0).toFixed(1);
        document.getElementById("win-loss-count").innerText = `${data.metrics.winning_trades || 0} W / ${data.metrics.losing_trades || 0} L`;
        document.getElementById("max-dd").innerText = (data.metrics.max_drawdown_pct || 0).toFixed(1);

        document.getElementById("open-count").innerText = data.open_positions_count;
        document.getElementById("pos-badge").innerText = `${data.open_positions_count} Open`;

        document.getElementById("active-brain-display").innerText = data.active_brain.toUpperCase();
        document.getElementById("active-profile-display").innerText = `Risk Profile: ${data.profile_name}`;
    } catch (e) {
        console.error("Status fetch error", e);
    }
}

async function fetchPositions() {
    try {
        const res = await fetch("/api/positions");
        if (!res.ok) return;
        const data = await res.json();

        const openBody = document.getElementById("open-positions-body");
        if (data.open.length === 0) {
            openBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No positions currently open. Waiting for market setup trigger.</td></tr>';
        } else {
            openBody.innerHTML = data.open.map(p => {
                const pnl = p.unrealized_pnl || 0;
                const pnlColor = pnl >= 0 ? '#00f298' : '#ff3366';
                return `
                <tr>
                    <td><strong>${p.symbol}</strong></td>
                    <td><span class="${p.side === 'BUY' ? 'tag-buy' : 'tag-sell'}">${p.side}</span></td>
                    <td>${p.quantity}</td>
                    <td>₹${formatINR(p.entry_price)}</td>
                    <td>₹${formatINR(p.current_price)}</td>
                    <td style="color:#ff3366;">₹${formatINR(p.stop_loss)}</td>
                    <td style="color:#00f298;">₹${formatINR(p.take_profit)}</td>
                    <td style="color:${pnlColor}; font-weight:bold;">${pnl >= 0 ? '+' : ''}₹${formatINR(pnl)}</td>
                    <td><small style="color:#94a3b8;">${p.engine_name}</small></td>
                </tr>
                `;
            }).join("");
        }

        const journalBody = document.getElementById("trade-journal-body");
        document.getElementById("journal-count").innerText = `${data.closed.length} Closed`;
        if (data.closed.length === 0) {
            journalBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No completed trades recorded for this challenge session yet.</td></tr>';
        } else {
            journalBody.innerHTML = data.closed.slice().reverse().map(p => {
                const pnl = p.net_pnl || 0;
                const pnlColor = pnl >= 0 ? '#00f298' : '#ff3366';
                return `
                <tr>
                    <td><small>${p.close_time || '-'}</small></td>
                    <td><strong>${p.symbol}</strong></td>
                    <td><span class="${p.side === 'BUY' ? 'tag-buy' : 'tag-sell'}">${p.side}</span></td>
                    <td>${p.quantity}</td>
                    <td>₹${formatINR(p.entry_price)}</td>
                    <td>₹${formatINR(p.close_price)}</td>
                    <td style="color:#94a3b8;">₹${formatINR(p.charges)}</td>
                    <td style="color:${pnlColor}; font-weight:bold;">${pnl >= 0 ? '+' : ''}₹${formatINR(pnl)}</td>
                    <td><small>${p.close_reason || '-'}</small></td>
                </tr>
                `;
            }).join("");
        }
    } catch (e) {
        console.error("Positions fetch error", e);
    }
}

async function fetchQuotes() {
    try {
        const res = await fetch("/api/quotes");
        if (!res.ok) return;
        const quotes = await res.json();
        const container = document.getElementById("watchlist-container");

        const keys = Object.keys(quotes);
        if (keys.length === 0) {
            container.innerHTML = '<div class="text-muted">No quote data available yet.</div>';
            return;
        }

        container.innerHTML = keys.map(sym => {
            const q = quotes[sym];
            const chg = q.change_pct || 0;
            const chgClass = chg >= 0 ? 'change-up' : 'change-down';
            return `
            <div class="stock-card">
                <div class="stock-sym">${sym}</div>
                <div class="stock-price">₹${formatINR(q.price)}</div>
                <div class="stock-change ${chgClass}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</div>
            </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Quotes fetch error", e);
    }
}

async function startChallenge() {
    await fetch("/api/challenge/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
    });
    fetchStatus();
}

async function pauseChallenge() {
    await fetch("/api/challenge/pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
    });
    fetchStatus();
}

function formatINR(num) {
    if (num === null || num === undefined || isNaN(num)) return "0.00";
    return Number(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Polling interval
fetchStatus();
fetchPositions();
fetchQuotes();

setInterval(() => {
    fetchStatus();
    fetchPositions();
}, 2000);

setInterval(() => {
    fetchQuotes();
}, 5000);
