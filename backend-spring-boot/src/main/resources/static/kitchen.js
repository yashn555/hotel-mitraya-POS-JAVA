/**
 * Hotel Mitraya - Kitchen Display Client (Simple, Pure Read-Only)
 * ==============================================================
 * Displays active orders with Menu items, Quantities, and Table Numbers.
 * Completely read-only with auto-refresh every 3.5 seconds and audio alert.
 */

(function () {
    "use strict";

    let soundEnabled = true;
    let knownOrderIds = new Set();
    let isFirstLoad = true;
    let pollInterval = null;

    const ticketsGrid = document.getElementById("kitchen-tickets-grid");
    const activeOrdersCountEl = document.getElementById("active-orders-count");
    const lastSyncTimeEl = document.getElementById("last-sync-time");
    const kitchenClockEl = document.getElementById("kitchen-clock");
    const btnSoundToggle = document.getElementById("btn-sound-toggle");
    const soundLabel = document.getElementById("sound-label");

    // Audio Chime (Web Audio API Synthesizer - No external file dependency)
    function playChime() {
        if (!soundEnabled) return;
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctx = new AudioCtx();

            const playTone = (freq, start, duration) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
                gain.gain.setValueAtTime(0.3, ctx.currentTime + start);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + start);
                osc.stop(ctx.currentTime + start + duration);
            };

            playTone(587.33, 0.0, 0.25); // D5
            playTone(880.00, 0.15, 0.4); // A5
        } catch (e) {
            console.warn("Audio chime error:", e);
        }
    }

    function updateClock() {
        const now = new Date();
        if (kitchenClockEl) {
            kitchenClockEl.textContent = now.toLocaleTimeString();
        }
    }

    async function fetchKitchenOrders() {
        try {
            const res = await fetch("/api/orders/kitchen");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            if (data.success && Array.isArray(data.orders)) {
                renderKitchenTickets(data.orders);
                if (activeOrdersCountEl) {
                    activeOrdersCountEl.textContent = data.orders.length;
                }
                if (lastSyncTimeEl) {
                    lastSyncTimeEl.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
                }

                // Check for new orders to trigger audio chime
                const currentIds = new Set(data.orders.map(o => o.id));
                if (!isFirstLoad) {
                    let hasNew = false;
                    currentIds.forEach(id => {
                        if (!knownOrderIds.has(id)) hasNew = true;
                    });
                    if (hasNew) playChime();
                }
                knownOrderIds = currentIds;
                isFirstLoad = false;
            }
        } catch (err) {
            console.error("Error fetching kitchen orders:", err);
            if (lastSyncTimeEl) {
                lastSyncTimeEl.textContent = "Sync error (retrying...)";
            }
        }
    }

    function renderKitchenTickets(orders) {
        if (!ticketsGrid) return;

        if (orders.length === 0) {
            ticketsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-circle-check" style="color: #10b981;"></i>
                    <h3>All Orders Cleared!</h3>
                    <p>No active kitchen orders at the moment.</p>
                </div>
            `;
            return;
        }

        ticketsGrid.innerHTML = "";

        orders.forEach(order => {
            const card = document.createElement("div");
            card.className = "ticket-card";

            const isWalkin = !order.table_number;
            const tableClass = isWalkin ? "table-tag walkin" : "table-tag";
            const tableIcon = isWalkin ? "fa-person-walking" : "fa-chair";

            let itemsHtml = "";
            (order.items || []).forEach(item => {
                const qtyVal = Number(item.quantity) % 1 === 0 ? Number(item.quantity).toFixed(0) : Number(item.quantity).toFixed(1);
                itemsHtml += `
                    <div class="item-row">
                        <div class="item-qty-badge">${qtyVal}x</div>
                        <div class="item-content">
                            <div class="item-name">${item.item_name}</div>
                            ${item.notes ? `<div class="item-note-inline"><i class="fa-solid fa-comment-dots"></i> ${item.notes}</div>` : ""}
                        </div>
                    </div>
                `;
            });

            card.innerHTML = `
                <div class="ticket-header">
                    <div class="${tableClass}">
                        <i class="fa-solid ${tableIcon}"></i>
                        <span>${order.table_label}</span>
                    </div>
                    <div class="time-badge">
                        <i class="fa-regular fa-clock"></i>
                        <span>${order.created_at_time || "Now"}</span>
                        <span class="elapsed-tag">(${order.elapsed_minutes || 0}m ago)</span>
                    </div>
                </div>

                ${order.notes ? `<div class="ticket-notes"><i class="fa-solid fa-triangle-exclamation"></i> <strong>Note:</strong> ${order.notes}</div>` : ""}

                <div class="items-list">
                    ${itemsHtml || '<div style="color:var(--text-muted); font-size:14px;">No items in order</div>'}
                </div>
            `;

            ticketsGrid.appendChild(card);
        });
    }

    function setupSoundToggle() {
        if (!btnSoundToggle) return;
        btnSoundToggle.addEventListener("click", () => {
            soundEnabled = !soundEnabled;
            if (soundEnabled) {
                btnSoundToggle.classList.add("active");
                soundLabel.textContent = "Sound ON";
                btnSoundToggle.querySelector("i").className = "fa-solid fa-volume-high";
                playChime();
            } else {
                btnSoundToggle.classList.remove("active");
                soundLabel.textContent = "Sound OFF";
                btnSoundToggle.querySelector("i").className = "fa-solid fa-volume-xmark";
            }
        });
    }

    // Initialize
    window.addEventListener("DOMContentLoaded", () => {
        updateClock();
        setInterval(updateClock, 1000);
        setupSoundToggle();
        fetchKitchenOrders();
        pollInterval = setInterval(fetchKitchenOrders, 3500);
    });

})();
