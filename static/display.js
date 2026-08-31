/**
 * Hotel Mitraya - Live Order Display & Wired Thermal Print Station
 * ================================================================
 * 1. Real-time background listener polling for new orders from any device/login.
 * 2. Displays new orders prominently with a 20-second active countdown timer.
 * 3. Plays a pleasant audio chime upon new order arrival.
 * 4. Automatically triggers print to the connected wired thermal receipt printer.
 * 5. Syncs live status for all 12 restaurant dining tables.
 */

(function () {
    "use strict";

    // Configuration & State
    const POLL_INTERVAL_MS = 2500;
    let lastMaxId = 0;
    let isFirstPoll = true;
    let isPaused = false;
    let activeTimerSeconds = 20;
    let countdownInterval = null;
    let currentAlertBill = null;
    let recentBills = [];

    // Settings
    let autoPrintEnabled = localStorage.getItem("mitraya_display_autoprint") !== "false";
    let soundEnabled = localStorage.getItem("mitraya_display_sound") !== "false";

    // DOM Elements
    const toggleAutoPrint = document.getElementById("toggle-autoprint");
    const toggleSound = document.getElementById("toggle-sound");
    const tablesRadarGrid = document.getElementById("tables-radar-grid");
    const activeTablesSummary = document.getElementById("active-tables-summary");
    const liveAlertModal = document.getElementById("live-alert-modal");
    const alertOrderTypeBadge = document.getElementById("alert-order-type-badge");
    const alertCountdownText = document.getElementById("alert-countdown-text");
    const alertProgressBar = document.getElementById("alert-progress-bar");
    const alertTableName = document.getElementById("alert-table-name");
    const alertBillNo = document.getElementById("alert-bill-no");
    const alertItemsContainer = document.getElementById("alert-items-container");
    const alertPaymentMode = document.getElementById("alert-payment-mode");
    const alertTotalAmount = document.getElementById("alert-total-amount");
    const btnAlertPrint = document.getElementById("btn-alert-print");
    const btnAlertPause = document.getElementById("btn-alert-pause");
    const pauseBtnText = document.getElementById("pause-btn-text");
    const btnAlertDismiss = document.getElementById("btn-alert-dismiss");
    const liveOrdersGrid = document.getElementById("live-orders-grid");
    const liveServerClock = document.getElementById("live-server-clock");
    const hiddenReceiptContainer = document.getElementById("hidden-receipt-container");

    // Initialize Checkbox States
    if (toggleAutoPrint) {
        toggleAutoPrint.checked = autoPrintEnabled;
        toggleAutoPrint.addEventListener("change", () => {
            autoPrintEnabled = toggleAutoPrint.checked;
            localStorage.setItem("mitraya_display_autoprint", autoPrintEnabled ? "true" : "false");
        });
    }

    if (toggleSound) {
        toggleSound.checked = soundEnabled;
        toggleSound.addEventListener("change", () => {
            soundEnabled = toggleSound.checked;
            localStorage.setItem("mitraya_display_sound", soundEnabled ? "true" : "false");
        });
    }

    // Audio Chime Generator using Web Audio API
    let audioCtx = null;
    function getAudioContext() {
        try {
            if (!audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) audioCtx = new AudioContext();
            }
            if (audioCtx && audioCtx.state === "suspended") {
                audioCtx.resume().catch(() => {});
            }
            return audioCtx;
        } catch (e) {
            return null;
        }
    }

    // Auto-unlock audio on user interaction
    document.addEventListener("click", () => {
        getAudioContext();
    }, { once: true });

    function playOrderChime() {
        if (!soundEnabled) return;
        try {
            const ctx = getAudioContext();
            if (!ctx) return;

            const playTone = (freq, startTime, duration) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, startTime);

                gain.gain.setValueAtTime(0.001, startTime);
                gain.gain.exponentialRampToValueAtTime(0.3, startTime + 0.05);
                gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(startTime);
                osc.stop(startTime + duration);
            };

            const now = ctx.currentTime;
            playTone(587.33, now, 0.25);        // D5
            playTone(880.00, now + 0.15, 0.45); // A5
            playTone(1174.66, now + 0.35, 0.6); // D6
        } catch (e) {
            console.warn("Audio chime play error:", e);
        }
    }


    // Currency Formatter
    function formatMoney(amount) {
        return "₹" + Number(amount || 0).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Print to Wired Thermal Printer
    function printWiredReceipt(bill) {
        if (!bill) return;

        // Build 80mm standard thermal printable HTML
        const itemsHtml = (bill.items || []).map(i => `
            <tr>
                <td style="text-align: left; padding: 3px 0; font-size: 13px; font-weight: 700;">${i.item_name || i.name}</td>
                <td style="text-align: center; padding: 3px 0; font-size: 13px;">${i.quantity}</td>
                <td style="text-align: right; padding: 3px 0; font-size: 13px;">${Number(i.unit_price).toFixed(0)}</td>
                <td style="text-align: right; padding: 3px 0; font-size: 13px; font-weight: 700;">${Number(i.total_price || (i.quantity * i.unit_price)).toFixed(2)}</td>
            </tr>
        `).join("");

        const receiptDoc = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Print Receipt - ${bill.bill_number}</title>
                <style>
                    @page { size: 80mm auto; margin: 0; }
                    body {
                        font-family: 'JetBrains Mono', 'Courier New', monospace;
                        width: 76mm;
                        margin: 0 auto;
                        padding: 6px 2px;
                        color: #000;
                        background: #fff;
                        font-size: 12px;
                    }
                    .center { text-align: center; }
                    .bold { font-weight: bold; }
                    .divider { border-bottom: 1px dashed #000; margin: 5px 0; }
                    .table-row { display: flex; justify-content: space-between; }
                    table { width: 100%; border-collapse: collapse; margin: 4px 0; }
                    .title { font-size: 16px; font-weight: 900; }
                    .large-total { font-size: 16px; font-weight: 900; }
                </style>
            </head>
            <body>
                <div class="center">
                    <div class="title">HOTEL MITRAYA</div>
                    <div>Pure Veg Restaurant &amp; Caterers</div>
                    <div style="font-size: 10px;">Dharmaraj chowk, Akurdi, Pune - 411035</div>
                    <div style="font-size: 10px;">Ph: +91 9158691003 | FSSAI: 21525037001433</div>
                </div>
                <div class="divider"></div>
                <div class="table-row bold">
                    <span>${bill.table_number ? 'TABLE: ' + bill.table_number : 'WALK-IN COUNTER'}</span>
                    <span>${bill.bill_number}</span>
                </div>
                <div class="table-row" style="font-size: 10px;">
                    <span>Date: ${bill.created_at || new Date().toLocaleString()}</span>
                    <span>Staff: ${bill.cashier_role || 'Staff'}</span>
                </div>
                <div class="divider"></div>
                <table>
                    <thead>
                        <tr style="border-bottom: 1px solid #000; font-size: 11px;">
                            <th style="text-align: left;">Item</th>
                            <th style="text-align: center;">Qty</th>
                            <th style="text-align: right;">Rate</th>
                            <th style="text-align: right;">Amt</th>
                        </tr>
                    </thead>
                    <tbody>${itemsHtml}</tbody>
                </table>
                <div class="divider"></div>
                <div class="table-row">
                    <span>Subtotal:</span>
                    <span>Rs.${Number(bill.subtotal || 0).toFixed(2)}</span>
                </div>
                ${bill.discount > 0 ? `
                <div class="table-row">
                    <span>Discount:</span>
                    <span>-Rs.${Number(bill.discount).toFixed(2)}</span>
                </div>` : ''}
                <div class="divider"></div>
                <div class="table-row large-total">
                    <span>NET TOTAL:</span>
                    <span>Rs.${Number(bill.total_amount || 0).toFixed(2)}</span>
                </div>
                <div class="divider"></div>
                <div class="table-row" style="font-size: 11px;">
                    <span>Payment Mode:</span>
                    <span>${bill.payment_mode || 'CASH'}</span>
                </div>
                ${bill.received_amount ? `
                <div class="table-row" style="font-size: 11px;">
                    <span>Tendered:</span>
                    <span>Rs.${Number(bill.received_amount).toFixed(2)}</span>
                </div>
                <div class="table-row" style="font-size: 11px;">
                    <span>Change:</span>
                    <span>Rs.${Number(bill.change_amount || 0).toFixed(2)}</span>
                </div>` : ''}
                <div class="divider"></div>
                <div class="center" style="font-size: 11px; margin-top: 6px;">
                    Thank You! Visit Again.<br>
                    *** Have a Delicious Day ***
                </div>
            </body>
            </html>
        `;

        // Create clean invisible iframe to invoke print dialog cleanly
        let iframe = document.getElementById("wired-print-frame");
        if (iframe) iframe.remove();

        iframe = document.createElement("iframe");
        iframe.id = "wired-print-frame";
        iframe.style.position = "fixed";
        iframe.style.right = "0";
        iframe.style.bottom = "0";
        iframe.style.width = "0";
        iframe.style.height = "0";
        iframe.style.border = "none";
        document.body.appendChild(iframe);

        const doc = iframe.contentWindow.document;
        doc.open();
        doc.write(receiptDoc);
        doc.close();

        setTimeout(() => {
            try {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            } catch (e) {
                console.warn("Direct iframe print error, fallback to window.print():", e);
                window.print();
            }
        }, 200);
    }

    // Trigger 20-Second Order Pop-up Alert
    function triggerOrderAlert(bill) {
        currentAlertBill = bill;
        isPaused = false;
        pauseBtnText.textContent = "Pause Timer";
        btnAlertPause.classList.remove("btn-active-paused");

        // Format Order Header
        const isDining = bill.order_type === "DINING" || (bill.table_number && bill.table_number > 0);
        if (isDining) {
            alertOrderTypeBadge.textContent = bill.status === "OPEN" ? "DINING ORDER / KOT" : "TABLE SETTLED";
            alertTableName.innerHTML = `<i class="fa-solid fa-utensils"></i> Table ${bill.table_number}`;
        } else {
            alertOrderTypeBadge.textContent = "WALK-IN ORDER";
            alertTableName.innerHTML = `<i class="fa-solid fa-person-walking"></i> Walk-in Counter`;
        }

        alertBillNo.textContent = bill.bill_number || "POS-000000";
        alertPaymentMode.textContent = `Mode: ${bill.payment_mode || 'CASH'}`;
        alertTotalAmount.textContent = formatMoney(bill.total_amount);

        // Populate Items
        alertItemsContainer.innerHTML = "";
        (bill.items || []).forEach(item => {
            const row = document.createElement("div");
            row.className = "alert-item-row";
            row.innerHTML = `
                <div style="display: flex; align-items: center;">
                    <span class="alert-item-qty">${item.quantity}×</span>
                    <span class="alert-item-name">${item.item_name || item.name}</span>
                </div>
                <div class="alert-item-rate">${formatMoney(item.total_price || (item.quantity * item.unit_price))}</div>
            `;
            alertItemsContainer.appendChild(row);
        });

        // Show Modal
        liveAlertModal.classList.add("active");

        // Audio Alert
        playOrderChime();

        // Auto Print to Wired Thermal Printer
        if (autoPrintEnabled) {
            printWiredReceipt(bill);
        }

        // Start 10-Second Countdown
        startCountdown(10);
    }

    // 10-Second Countdown Timer Controller
    function startCountdown(seconds) {
        if (countdownInterval) clearInterval(countdownInterval);

        activeTimerSeconds = seconds;
        updateCountdownUI(activeTimerSeconds);

        countdownInterval = setInterval(() => {
            if (!isPaused) {
                activeTimerSeconds -= 1;
                updateCountdownUI(activeTimerSeconds);

                if (activeTimerSeconds <= 0) {
                    dismissAlert();
                }
            }
        }, 1000);
    }

    function updateCountdownUI(secs) {
        alertCountdownText.textContent = `${secs}s`;
        const pct = Math.max(0, Math.min(100, (secs / 10) * 100));
        alertProgressBar.style.width = `${pct}%`;
    }

    function dismissAlert() {
        if (countdownInterval) clearInterval(countdownInterval);
        liveAlertModal.classList.remove("active");
        currentAlertBill = null;
    }

    // Alert Action Buttons
    btnAlertDismiss.addEventListener("click", dismissAlert);

    btnAlertPrint.addEventListener("click", () => {
        if (currentAlertBill) {
            printWiredReceipt(currentAlertBill);
        }
    });

    btnAlertPause.addEventListener("click", () => {
        isPaused = !isPaused;
        if (isPaused) {
            pauseBtnText.textContent = "Resume Timer";
            btnAlertPause.style.background = "#2563eb";
            btnAlertPause.style.color = "#fff";
        } else {
            pauseBtnText.textContent = "Pause Timer";
            btnAlertPause.style.background = "#1e293b";
            btnAlertPause.style.color = "#cbd5e1";
        }
    });

    // Render 12 Tables Status Radar
    function renderTablesRadar(tablesData) {
        tablesRadarGrid.innerHTML = "";
        let occupied = 0;

        (tablesData || []).forEach(t => {
            const card = document.createElement("div");
            const isOcc = t.status === "OCCUPIED";
            if (isOcc) occupied++;

            card.className = `table-radar-card ${isOcc ? "occupied" : "vacant"}`;
            card.innerHTML = `
                <div class="table-radar-num">T${t.table_number}</div>
                <div class="table-radar-status">${isOcc ? `₹${t.total_amount.toFixed(0)}` : "Free"}</div>
            `;
            tablesRadarGrid.appendChild(card);
        });

        activeTablesSummary.textContent = `${occupied} of 12 Tables Occupied`;
    }

    // Render Live Orders Grid (Strictly 5 Recent Orders)
    function renderLiveOrdersFeed(bills) {
        const top5Bills = (bills || []).slice(0, 5);

        if (top5Bills.length === 0) {
            liveOrdersGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: #64748b; padding: 60px 20px;">
                    <i class="fa-solid fa-mug-saucer fa-2x" style="opacity: 0.4;"></i>
                    <p style="margin-top: 12px;">No orders placed yet today.</p>
                </div>`;
            return;
        }

        liveOrdersGrid.innerHTML = "";
        top5Bills.forEach(b => {
            const isDining = b.order_type === "DINING" || (b.table_number && b.table_number > 0);
            const card = document.createElement("div");
            card.className = `order-card ${isDining ? "dining" : "walk-in"}`;

            const itemsSnippet = (b.items || []).map(i => `${i.quantity}× ${i.item_name || i.name}`).join(", ") || "No items";

            card.innerHTML = `
                <div class="order-card-top">
                    <div>
                        <div class="order-card-table">
                            ${isDining ? `<i class="fa-solid fa-utensils" style="color:#fbbf24;"></i> Table ${b.table_number}` : `<i class="fa-solid fa-person-walking" style="color:#38bdf8;"></i> Walk-in`}
                        </div>
                        <div style="font-size: 11px; font-family:'JetBrains Mono'; color:#93c5fd; margin-top:2px;">${b.bill_number}</div>
                    </div>
                    <div class="order-card-time">${b.created_at ? b.created_at.split(" ")[1] + " " + (b.created_at.split(" ")[2] || "") : ""}</div>
                </div>
                <div class="order-card-items-snippet" title="${itemsSnippet}">
                    ${itemsSnippet.length > 80 ? itemsSnippet.substring(0, 80) + "..." : itemsSnippet}
                </div>
                <div class="order-card-footer">
                    <div class="order-card-total">${formatMoney(b.total_amount)}</div>
                    <button type="button" class="btn-card-reprint" data-bill-id="${b.id}">
                        <i class="fa-solid fa-print"></i> Print (Wired)
                    </button>
                </div>
            `;

            card.querySelector(".btn-card-reprint").addEventListener("click", () => {
                printWiredReceipt(b);
            });

            liveOrdersGrid.appendChild(card);
        });
    }

    // Polling Loop
    async function pollLiveOrders() {
        try {
            // 1. Fetch live tables state
            const tablesRes = await fetch("/api/pos/tables");
            const tablesData = await tablesRes.json();
            if (tablesRes.ok && tablesData.success) {
                renderTablesRadar(tablesData.tables);
            }

            // 2. Fetch live orders stream
            const ordersRes = await fetch(`/api/display/live-orders?since_id=${isFirstPoll ? 0 : lastMaxId}&limit=5`);
            const ordersData = await ordersRes.json();

            if (ordersRes.ok && ordersData.success) {
                if (ordersData.server_time && liveServerClock) {
                    liveServerClock.textContent = `Server Time: ${ordersData.server_time}`;
                }

                if (isFirstPoll) {
                    isFirstPoll = false;
                    lastMaxId = ordersData.max_id || 0;
                    recentBills = (ordersData.bills || []).slice(0, 5);
                    renderLiveOrdersFeed(recentBills);
                } else {
                    lastMaxId = ordersData.max_id || lastMaxId;
                    if (ordersData.bills) {
                        recentBills = ordersData.bills.slice(0, 5);
                        renderLiveOrdersFeed(recentBills);
                    }

                    const newBills = ordersData.new_bills || [];
                    if (newBills.length > 0) {
                        // Trigger 10-second active screen popup & auto-print for newly completed checkout bill
                        triggerOrderAlert(newBills[newBills.length - 1]);
                    }
                }
            }

        } catch (err) {
            console.error("Live poll error:", err);
            if (liveServerClock) liveServerClock.textContent = "Connecting...";
        } finally {
            setTimeout(pollLiveOrders, POLL_INTERVAL_MS);
        }
    }

    // Startup
    function init() {
        pollLiveOrders();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();

