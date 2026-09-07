/**
 * Hotel Mitraya - Billing Counter POS & Direct Thermal Printing Station
 * ======================================================================
 * Features:
 * 1. Automatic Printer Hardware Detection on load (58mm/80mm, Bluetooth, Spooler).
 * 2. Real-time Status Badge & Welcome Slip generation.
 * 3. High-ergonomics Walk-in Quick Billing + Large Touch Cards.
 * 4. 12 Restaurant Dining Tables visual floor grid with live tab settlement.
 * 5. Direct settlement and thermal print dispatch with disconnected printer alerts.
 */

(function () {
    "use strict";

    // Application State
    let catalog = [];
    let allMenuItems = [];
    let activeCategory = "all";
    let walkinCart = {}; // key: menu_item_id -> { item, quantity, notes }
    let currentMode = "WALK_IN"; // "WALK_IN" or "DINING"
    let selectedDiningTableNo = null;
    let selectedDiningOrder = null;
    let tablesData = [];
    let currentPaymentMode = "CASH";
    let discountAmount = 0.0;
    let pollTimer = null;
    let lastGeneratedBill = null;

    // Printer Hardware State (Universal for Any USB, Windows, Bluetooth or Network Printer)
    const savedPaperWidth = parseInt(localStorage.getItem("mitraya_paper_width")) || 58;
    let printerState = {
        connected: true,
        name: "Universal Printer",
        type: "SYSTEM",
        paperWidth: savedPaperWidth,
        systemPrinters: [],
        activeSystemPrinter: ""
    };

    // DOM Elements
    const itemSearchInput = document.getElementById("item-search-input");
    const categoryPillsBar = document.getElementById("category-pills-bar");
    const menuItemsGrid = document.getElementById("menu-items-grid");

    const tabModeWalkin = document.getElementById("tab-mode-walkin");
    const tabModeDining = document.getElementById("tab-mode-dining");
    const activeTablesBadge = document.getElementById("active-tables-badge");

    const walkinCatalogContainer = document.getElementById("walkin-catalog-container");
    const diningFloorContainer = document.getElementById("dining-floor-container");
    const counterTablesGrid = document.getElementById("counter-tables-grid");
    const btnRefreshTablesCounter = document.getElementById("btn-refresh-tables-counter");

    const currentCartTitle = document.getElementById("current-cart-title");
    const cartItemsList = document.getElementById("cart-items-list");
    const cartCountBadge = document.getElementById("cart-count-badge");
    const btnClearCart = document.getElementById("btn-clear-cart");

    const cartSubtotalEl = document.getElementById("cart-subtotal");
    const cartDiscountInput = document.getElementById("cart-discount-input");
    const cartNetTotalEl = document.getElementById("cart-net-total");

    const paymentTabs = document.querySelectorAll(".pm-tab-btn");
    const cashTenderContainer = document.getElementById("cash-tender-container");
    const cashReceivedInput = document.getElementById("cash-received-input");
    const changeDisplay = document.getElementById("change-display");
    const btnExactCash = document.getElementById("btn-exact-cash");
    const quickCashBtns = document.querySelectorAll(".quick-cash-btn[data-val]");

    const btnCheckoutOrder = document.getElementById("btn-checkout-order");
    const btnCheckoutText = document.getElementById("btn-checkout-text");
    const btnSettleTableTab = document.getElementById("btn-settle-table-tab");
    const btnSettleTabText = document.getElementById("btn-settle-tab-text");

    // Header Printer Badge
    const btnPrinterStatusBadge = document.getElementById("btn-printer-status-badge");
    const printerStatusDot = document.getElementById("printer-status-dot");
    const printerStatusText = document.getElementById("printer-status-text");
    const printerConnectHint = document.getElementById("printer-connect-hint");

    // Printer Control Modal
    const printerControlModal = document.getElementById("printer-control-modal");
    const btnClosePrinterModal = document.getElementById("btn-close-printer-modal");
    const btnDismissPrinterModal = document.getElementById("btn-dismiss-printer-modal");
    const printerModalDeviceName = document.getElementById("printer-modal-device-name");
    const printerModalStatusPill = document.getElementById("printer-modal-status-pill");
    const btnPaper80 = document.getElementById("btn-paper-80");
    const btnPaper58 = document.getElementById("btn-paper-58");
    const systemPrintersSelect = document.getElementById("system-printers-select");
    const btnBtScanConnect = document.getElementById("btn-bt-scan-connect");
    const btnPrintWelcomeSlip = document.getElementById("btn-print-welcome-slip");
    const btnPrintTestSlip = document.getElementById("btn-print-test-slip");

    // Receipt Modal
    const receiptModal = document.getElementById("receipt-modal");
    const btnCloseReceiptModal = document.getElementById("btn-close-receipt-modal");
    const btnDismissReceipt = document.getElementById("btn-dismiss-receipt");
    const btnPrintReceipt = document.getElementById("btn-print-receipt");
    const btnBtDirectPrint = document.getElementById("btn-bt-direct-print");

    // Recent Bills Modal
    const recentBillsModal = document.getElementById("recent-bills-modal");
    const btnOpenRecentBills = document.getElementById("btn-open-recent-bills");
    const btnCloseRecentModal = document.getElementById("btn-close-recent-modal");
    const btnDismissRecentModal = document.getElementById("btn-dismiss-recent-modal");
    const recentBillsList = document.getElementById("recent-bills-list");

    const btnLogout = document.getElementById("btn-logout");
    const toastContainer = document.getElementById("toast-container");

    // ─── INITIALIZATION ────────────────────────────────────────────────────────
    async function init() {
        setupEventListeners();
        setupKeyboardShortcuts();
        
        // Step 1: Scan & Identify Connected Printer
        await scanConnectedPrinter();

        // Step 2: Load Catalog & Tables in parallel
        await Promise.all([loadCatalog(), loadCounterTables()]);

        // Step 3: Live Polling for Tables & Kitchen Status
        startLivePolling();
    }

    // ─── TOAST NOTIFICATIONS ──────────────────────────────────────────────────
    function showToast(message, type = "success", duration = 4000) {
        if (!toastContainer) return;
        const toast = document.createElement("div");
        toast.className = `pos-toast ${type}`;
        const icon = type === "success" ? "fa-circle-check" : (type === "warning" ? "fa-triangle-exclamation" : "fa-circle-xmark");
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    // ─── PRINTER DETECTION & STATUS ENGINE ─────────────────────────────────────
    async function scanConnectedPrinter() {
        updatePrinterBadgeUI("scanning", "Scanning Hardware...");
        
        try {
            // 1. Check Web Bluetooth status
            if (window.MitrayaBluetoothPrinter && window.MitrayaBluetoothPrinter.isConnected()) {
                const btName = window.MitrayaBluetoothPrinter.getDeviceName();
                const width = window.MitrayaBluetoothPrinter.getPaperWidth();
                setPrinterConnectedState("BLUETOOTH", btName, width);
                return;
            }

            // 2. Query Server Hardware & Thermal Status
            const [statusRes, listRes] = await Promise.all([
                fetch("/api/printer/status").then(r => r.json()).catch(() => null),
                fetch("/api/printer/list").then(r => r.json()).catch(() => null)
            ]);

            if (listRes && listRes.success && listRes.printers) {
                printerState.systemPrinters = listRes.printers;
                populateSystemPrintersDropdown(listRes.printers);
            }

            if (statusRes && statusRes.success && statusRes.connected) {
                const name = statusRes.identified_printer || "Thermal Printer";
                const width = statusRes.paper_width || 58;
                setPrinterConnectedState("SYSTEM", name, width);
                return;
            }

            // If no physical thermal printer is connected
            setPrinterDisconnectedState();

        } catch (e) {
            console.warn("Printer scan error:", e);
            setPrinterDisconnectedState();
        }
    }

    function setPrinterConnectedState(type, name, paperWidth) {
        printerState.connected = true;
        printerState.type = type;
        printerState.name = name;
        printerState.paperWidth = paperWidth;

        const label = `${name.length > 18 ? name.substring(0, 18) + '...' : name} (${paperWidth}mm)`;
        updatePrinterBadgeUI("connected", label);
        updatePrinterModalUI(true, name, paperWidth);
    }

    function setPrinterDisconnectedState() {
        printerState.connected = false;
        printerState.type = "NONE";
        printerState.name = "Not Connected";

        updatePrinterBadgeUI("disconnected", "Printer: Not Connected");
        updatePrinterModalUI(false, "No Thermal Printer Detected", printerState.paperWidth);
    }

    function updatePrinterBadgeUI(status, label) {
        if (!btnPrinterStatusBadge) return;
        btnPrinterStatusBadge.className = `printer-status-badge ${status}`;
        if (printerStatusText) printerStatusText.textContent = label;
        if (printerConnectHint) {
            printerConnectHint.style.display = (status === "disconnected") ? "inline-block" : "none";
        }
    }

    function updatePrinterModalUI(connected, name, paperWidth) {
        if (printerModalDeviceName) printerModalDeviceName.textContent = name;
        if (printerModalStatusPill) {
            printerModalStatusPill.className = `table-status-pill ${connected ? 'vacant' : 'occupied'}`;
            printerModalStatusPill.textContent = connected ? "ONLINE & READY" : "NOT CONNECTED";
        }
        if (btnPaper80 && btnPaper58) {
            if (paperWidth === 58) {
                btnPaper58.classList.add("active");
                btnPaper80.classList.remove("active");
            } else {
                btnPaper80.classList.add("active");
                btnPaper58.classList.remove("active");
            }
        }
    }

    function populateSystemPrintersDropdown(printers) {
        if (!systemPrintersSelect) return;
        systemPrintersSelect.innerHTML = "";
        printers.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.name;
            opt.textContent = `${p.name} ${p.is_default ? '(Default)' : ''}`;
            if (p.name === printerState.name) opt.selected = true;
            systemPrintersSelect.appendChild(opt);
        });
    }

    // ─── WELCOME SLIP DISPATCH ────────────────────────────────────────────────
    async function printWelcomeSlip() {
        showToast("Sending Welcome Confirmation Slip...", "warning", 2000);

        try {
            // If Bluetooth printer is active
            if (printerState.type === "BLUETOOTH" && window.MitrayaBluetoothPrinter && window.MitrayaBluetoothPrinter.isConnected()) {
                await window.MitrayaBluetoothPrinter.printWelcomeSlip();
                showToast("Welcome slip printed successfully on Bluetooth printer!", "success");
                return;
            }

            // Otherwise dispatch via Server Thermal Spooler
            const res = await fetch("/api/printer/startup-init", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Welcome slip sent to '${data.identified_printer}'!`, "success");
            } else {
                showToast(`Print failed: ${data.error || 'Check printer connection'}`, "error");
            }
        } catch (e) {
            showToast(`Print Error: ${e.message}`, "error");
        }
    }

    // ─── TEST RECEIPT DISPATCH ────────────────────────────────────────────────
    async function printTestReceipt() {
        try {
            if (printerState.type === "BLUETOOTH" && window.MitrayaBluetoothPrinter && window.MitrayaBluetoothPrinter.isConnected()) {
                await window.MitrayaBluetoothPrinter.printTestReceipt();
                showToast("Test receipt printed on Bluetooth printer!", "success");
                return;
            }

            const res = await fetch("/api/printer/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    paper_width: printerState.paperWidth,
                    printer_name: printerState.name
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast("Test receipt sent to thermal printer!", "success");
            } else {
                showToast(`Test print failed: ${data.error}`, "error");
            }
        } catch (e) {
            showToast(`Print Error: ${e.message}`, "error");
        }
    }

    // ─── BLUETOOTH SCAN & CONNECT ─────────────────────────────────────────────
    async function connectBluetoothPrinter() {
        if (!window.MitrayaBluetoothPrinter) {
            showToast("Bluetooth printing library not loaded.", "error");
            return;
        }

        try {
            showToast("Searching for nearby Bluetooth printers...", "warning", 3000);
            await window.MitrayaBluetoothPrinter.connect();
            const name = window.MitrayaBluetoothPrinter.getDeviceName();
            const width = window.MitrayaBluetoothPrinter.getPaperWidth();
            setPrinterConnectedState("BLUETOOTH", name, width);
            showToast(`Connected to '${name}'! Welcome slip printed.`, "success");
        } catch (e) {
            console.warn("BT Connect cancelled or failed:", e);
            if (!e.message.includes("cancelled")) {
                showToast(`Bluetooth Error: ${e.message}`, "error");
            }
        }
    }

    // ─── EVENT LISTENERS ──────────────────────────────────────────────────────
    function setupEventListeners() {
        // Mode switch tabs
        if (tabModeWalkin) tabModeWalkin.addEventListener("click", () => switchMode("WALK_IN"));
        if (tabModeDining) tabModeDining.addEventListener("click", () => switchMode("DINING"));

        // Search input
        if (itemSearchInput) itemSearchInput.addEventListener("input", () => renderMenuItems());

        // Clear Cart
        if (btnClearCart) btnClearCart.addEventListener("click", clearWalkinCart);

        // Discount input
        if (cartDiscountInput) cartDiscountInput.addEventListener("input", updateFinancials);

        // Payment Mode
        paymentTabs.forEach(tab => {
            tab.addEventListener("click", () => setPaymentMode(tab.getAttribute("data-mode")));
        });

        // Cash tender inputs
        if (cashReceivedInput) cashReceivedInput.addEventListener("input", updateChangeCalculation);
        if (btnExactCash) {
            btnExactCash.addEventListener("click", () => {
                const net = getNetTotal();
                if (cashReceivedInput) {
                    cashReceivedInput.value = Math.ceil(net);
                    updateChangeCalculation();
                }
            });
        }
        quickCashBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                const val = parseFloat(btn.getAttribute("data-val"));
                if (cashReceivedInput) {
                    cashReceivedInput.value = val;
                    updateChangeCalculation();
                }
            });
        });

        // Checkouts
        if (btnCheckoutOrder) btnCheckoutOrder.addEventListener("click", performWalkinCheckout);
        if (btnSettleTableTab) btnSettleTableTab.addEventListener("click", performTableSettlement);

        // Printer Badge & Modal
        if (btnPrinterStatusBadge) {
            btnPrinterStatusBadge.addEventListener("click", () => {
                printerControlModal.classList.add("active");
            });
        }
        if (btnClosePrinterModal) btnClosePrinterModal.addEventListener("click", () => printerControlModal.classList.remove("active"));
        if (btnDismissPrinterModal) btnDismissPrinterModal.addEventListener("click", () => printerControlModal.classList.remove("active"));

        if (btnPaper80) {
            btnPaper80.addEventListener("click", () => setPaperWidth(80));
        }
        if (btnPaper58) {
            btnPaper58.addEventListener("click", () => setPaperWidth(58));
        }

        if (systemPrintersSelect) {
            systemPrintersSelect.addEventListener("change", async (e) => {
                const selected = e.target.value;
                if (selected) {
                    setPrinterConnectedState("SYSTEM", selected, printerState.paperWidth);
                    // Save to server
                    await fetch("/api/printer/config", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            printer_name: selected,
                            paper_width: printerState.paperWidth
                        })
                    }).catch(() => {});
                    showToast(`Active printer set to: ${selected}`, "success");
                }
            });
        }

        if (btnBtScanConnect) btnBtScanConnect.addEventListener("click", connectBluetoothPrinter);
        if (btnPrintWelcomeSlip) btnPrintWelcomeSlip.addEventListener("click", printWelcomeSlip);
        if (btnPrintTestSlip) btnPrintTestSlip.addEventListener("click", printTestReceipt);

        // Recent Bills Modal
        if (btnOpenRecentBills) btnOpenRecentBills.addEventListener("click", openRecentBillsModal);
        if (btnCloseRecentModal) btnCloseRecentModal.addEventListener("click", () => recentBillsModal.classList.remove("active"));
        if (btnDismissRecentModal) btnDismissRecentModal.addEventListener("click", () => recentBillsModal.classList.remove("active"));

        // Receipt Modal
        if (btnCloseReceiptModal) btnCloseReceiptModal.addEventListener("click", () => receiptModal.classList.remove("active"));
        if (btnDismissReceipt) btnDismissReceipt.addEventListener("click", () => receiptModal.classList.remove("active"));
        if (btnPrintReceipt) btnPrintReceipt.addEventListener("click", () => window.print());
        if (btnBtDirectPrint) {
            btnBtDirectPrint.addEventListener("click", async () => {
                if (lastGeneratedBill && window.MitrayaBluetoothPrinter) {
                    try {
                        await window.MitrayaBluetoothPrinter.printReceipt(lastGeneratedBill);
                        showToast("Receipt sent to Bluetooth printer!", "success");
                    } catch (e) {
                        showToast(`BT Print Error: ${e.message}`, "error");
                    }
                }
            });
        }

        // Table Refresh
        if (btnRefreshTablesCounter) btnRefreshTablesCounter.addEventListener("click", loadCounterTables);

        // Logout
        if (btnLogout) {
            btnLogout.addEventListener("click", async () => {
                if (confirm("Do you want to lock the POS counter and logout?")) {
                    try {
                        await fetch("/api/logout", { method: "POST" });
                    } catch (e) {}
                    window.location.replace("/login");
                }
            });
        }
    }

    function setPaperWidth(width) {
        printerState.paperWidth = width;
        localStorage.setItem("mitraya_paper_width", width);
        if (window.MitrayaBluetoothPrinter) {
            window.MitrayaBluetoothPrinter.setPaperWidth(width);
        }
        updatePrinterModalUI(printerState.connected, printerState.name, width);
        // Save to server
        fetch("/api/printer/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ paper_width: width, printer_name: printerState.name })
        }).catch(() => {});
        showToast(`Paper format set to ${width}mm (${width === 58 ? '2-inch Thermal' : '3-inch / Standard'})`, "success");
    }

    // ─── KEYBOARD SHORTCUTS (F2, F4, F7, F10, Ctrl+Enter, Alt+1/2/3) ───────────
    function setupKeyboardShortcuts() {
        window.addEventListener("keydown", (e) => {
            // F2 or '/' to focus search
            if (e.key === "F2" || (e.key === "/" && document.activeElement !== itemSearchInput)) {
                e.preventDefault();
                if (currentMode !== "WALK_IN") switchMode("WALK_IN");
                if (itemSearchInput) itemSearchInput.focus();
            }
            // F4 to focus cash received
            else if (e.key === "F4") {
                e.preventDefault();
                if (cashReceivedInput) cashReceivedInput.focus();
            }
            // F7 to focus discount
            else if (e.key === "F7") {
                e.preventDefault();
                if (cartDiscountInput) cartDiscountInput.focus();
            }
            // F10 to clear cart
            else if (e.key === "F10") {
                e.preventDefault();
                clearWalkinCart();
            }
            // Alt + 1 : Cash
            else if (e.altKey && e.key === "1") {
                e.preventDefault();
                setPaymentMode("CASH");
            }
            // Alt + 2 : UPI
            else if (e.altKey && e.key === "2") {
                e.preventDefault();
                setPaymentMode("UPI");
            }
            // Alt + 3 : Card
            else if (e.altKey && e.key === "3") {
                e.preventDefault();
                setPaymentMode("CARD");
            }
            // Ctrl + Enter : Checkout / Settle
            else if (e.ctrlKey && e.key === "Enter") {
                e.preventDefault();
                if (currentMode === "WALK_IN") {
                    performWalkinCheckout();
                } else {
                    performTableSettlement();
                }
            }
        });
    }

    // ─── MODE SWITCHING (WALK-IN vs DINING TABLES) ─────────────────────────────
    function switchMode(mode) {
        currentMode = mode;
        if (mode === "WALK_IN") {
            tabModeWalkin.classList.add("active");
            tabModeDining.classList.remove("active");
            walkinCatalogContainer.style.display = "flex";
            diningFloorContainer.style.display = "none";

            currentCartTitle.textContent = "Walk-in Order";
            btnCheckoutOrder.style.display = "flex";
            btnSettleTableTab.style.display = "none";
            renderWalkinCart();
        } else {
            tabModeWalkin.classList.remove("active");
            tabModeDining.classList.add("active");
            walkinCatalogContainer.style.display = "none";
            diningFloorContainer.style.display = "flex";

            btnCheckoutOrder.style.display = "none";
            btnSettleTableTab.style.display = "flex";
            loadCounterTables();
            if (selectedDiningOrder) {
                renderDiningTableCart(selectedDiningOrder);
            } else {
                renderEmptyDiningCart();
            }
        }
        updateFinancials();
    }

    // ─── CATALOG & DISH RENDERING ─────────────────────────────────────────────
    async function loadCatalog() {
        try {
            const res = await fetch("/api/pos/catalog");
            const data = await res.json();
            if (data.success) {
                catalog = data.categories || [];
                allMenuItems = [];
                catalog.forEach(cat => {
                    if (cat.items) {
                        cat.items.forEach(item => {
                            allMenuItems.push({ ...item, category_name: cat.name });
                        });
                    }
                });
                renderCategoryPills();
                renderMenuItems();
            }
        } catch (e) {
            console.error("Failed to load catalog:", e);
        }
    }

    function renderCategoryPills() {
        if (!categoryPillsBar) return;
        categoryPillsBar.innerHTML = `<button type="button" class="category-pill ${activeCategory === 'all' ? 'active' : ''}" data-cat-id="all">All Items (${allMenuItems.length})</button>`;
        catalog.forEach(cat => {
            const count = (cat.items || []).length;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = `category-pill ${activeCategory === String(cat.id) ? 'active' : ''}`;
            btn.setAttribute("data-cat-id", String(cat.id));
            btn.textContent = `${cat.name} (${count})`;
            btn.addEventListener("click", () => {
                activeCategory = String(cat.id);
                document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
                btn.classList.add("active");
                renderMenuItems();
            });
            categoryPillsBar.appendChild(btn);
        });

        // Add listener to 'All Items'
        categoryPillsBar.querySelector('[data-cat-id="all"]').addEventListener("click", () => {
            activeCategory = "all";
            document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
            categoryPillsBar.querySelector('[data-cat-id="all"]').classList.add("active");
            renderMenuItems();
        });
    }

    function renderMenuItems() {
        if (!menuItemsGrid) return;
        const query = (itemSearchInput ? itemSearchInput.value : "").trim().toLowerCase();

        let filtered = allMenuItems.filter(item => {
            const matchCat = activeCategory === "all" || String(item.category_id) === activeCategory;
            const matchQuery = !query || item.name.toLowerCase().includes(query) || (item.category_name && item.category_name.toLowerCase().includes(query));
            return matchCat && matchQuery && item.is_available !== false;
        });

        if (filtered.length === 0) {
            menuItemsGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
                    <i class="fa-solid fa-utensils fa-2x" style="opacity: 0.3;"></i>
                    <p style="margin-top: 10px;">No matching dishes found.</p>
                </div>
            `;
            return;
        }

        menuItemsGrid.innerHTML = "";
        filtered.forEach(item => {
            const card = document.createElement("div");
            card.className = "dish-card";
            const inCartQty = walkinCart[item.id] ? walkinCart[item.id].quantity : 0;

            card.innerHTML = `
                ${inCartQty > 0 ? `<span class="dish-badge-qty">${inCartQty}</span>` : ''}
                <div class="dish-card-header">
                    <div style="display: flex; align-items: flex-start; gap: 8px;">
                        <span class="veg-icon"><span class="veg-icon-dot"></span></span>
                        <div class="dish-title">${item.name}</div>
                    </div>
                </div>
                <div class="dish-card-footer">
                    <span class="dish-price">₹${Number(item.price).toFixed(0)}</span>
                    <button type="button" class="dish-add-btn" title="Add to cart">
                        <i class="fa-solid fa-plus"></i>
                    </button>
                </div>
            `;

            card.addEventListener("click", () => {
                addDishToWalkinCart(item);
            });

            menuItemsGrid.appendChild(card);
        });
    }

    function addDishToWalkinCart(item) {
        if (walkinCart[item.id]) {
            walkinCart[item.id].quantity += 1;
        } else {
            walkinCart[item.id] = {
                item: item,
                quantity: 1,
                notes: ""
            };
        }
        renderWalkinCart();
        renderMenuItems(); // Update badge on card
    }

    function updateWalkinItemQty(itemId, delta) {
        if (!walkinCart[itemId]) return;
        walkinCart[itemId].quantity += delta;
        if (walkinCart[itemId].quantity <= 0) {
            delete walkinCart[itemId];
        }
        renderWalkinCart();
        renderMenuItems();
    }

    function clearWalkinCart() {
        walkinCart = {};
        renderWalkinCart();
        renderMenuItems();
        showToast("Cart cleared", "warning", 1500);
    }

    function renderWalkinCart() {
        if (!cartItemsList) return;
        const entries = Object.values(walkinCart);
        const totalCount = entries.reduce((sum, e) => sum + e.quantity, 0);
        if (cartCountBadge) cartCountBadge.textContent = `${totalCount} items`;

        if (entries.length === 0) {
            cartItemsList.innerHTML = `
                <div class="cart-empty-state">
                    <i class="fa-solid fa-utensils"></i>
                    <p>No dishes added yet.<br><small>Click on any dish card to add to order.</small></p>
                </div>
            `;
            updateFinancials();
            return;
        }

        cartItemsList.innerHTML = "";
        entries.forEach(entry => {
            const row = document.createElement("div");
            row.className = "cart-item-row";
            const lineTotal = entry.quantity * entry.item.price;

            row.innerHTML = `
                <div class="cart-item-info">
                    <div class="cart-item-name">${entry.item.name}</div>
                    <div class="cart-item-meta">₹${Number(entry.item.price).toFixed(0)} each</div>
                </div>
                <div class="cart-qty-controls">
                    <button type="button" class="btn-qty btn-minus"><i class="fa-solid fa-minus"></i></button>
                    <span class="qty-val">${entry.quantity}</span>
                    <button type="button" class="btn-qty btn-plus"><i class="fa-solid fa-plus"></i></button>
                </div>
                <div class="cart-item-total">₹${lineTotal.toFixed(2)}</div>
                <button type="button" class="btn-item-delete" title="Remove"><i class="fa-solid fa-trash-can"></i></button>
            `;

            row.querySelector(".btn-minus").addEventListener("click", (e) => {
                e.stopPropagation();
                updateWalkinItemQty(entry.item.id, -1);
            });
            row.querySelector(".btn-plus").addEventListener("click", (e) => {
                e.stopPropagation();
                updateWalkinItemQty(entry.item.id, 1);
            });
            row.querySelector(".btn-item-delete").addEventListener("click", (e) => {
                e.stopPropagation();
                delete walkinCart[entry.item.id];
                renderWalkinCart();
                renderMenuItems();
            });

            cartItemsList.appendChild(row);
        });

        updateFinancials();
    }

    // ─── 12 RESTAURANT DINING TABLES FLOOR ─────────────────────────────────────
    async function loadCounterTables() {
        try {
            const res = await fetch("/api/pos/tables");
            const data = await res.json();
            if (data.success && data.tables) {
                tablesData = data.tables;
                renderDiningTablesGrid(data.tables);

                // Update active table count badge
                const occupiedCount = data.tables.filter(t => t.status === "OCCUPIED").length;
                if (activeTablesBadge) {
                    activeTablesBadge.textContent = occupiedCount;
                    activeTablesBadge.style.display = occupiedCount > 0 ? "inline-block" : "none";
                }
            }
        } catch (e) {
            console.error("Failed to load tables:", e);
        }
    }

    function renderDiningTablesGrid(tables) {
        if (!counterTablesGrid) return;
        counterTablesGrid.innerHTML = "";

        tables.forEach(table => {
            const isOccupied = (table.status === "OCCUPIED" || (table.items && table.items.length > 0) || !!table.order_id);
            const isSelected = (selectedDiningTableNo === table.table_number);
            const card = document.createElement("div");
            card.className = `table-box-card ${isOccupied ? 'occupied' : 'vacant'} ${isSelected ? 'selected' : ''}`;

            const order = table.active_bill || table.active_order || table;
            const subtotal = order ? (order.subtotal || order.total_amount || 0) : 0;
            const itemsCount = (order && order.items) ? order.items.length : (table.items_count || 0);
            const waiter = (order && (order.created_by || order.created_by_role || order.server_name)) || "Staff";

            card.innerHTML = `
                <div class="table-box-header">
                    <span class="table-number-label">TABLE ${String(table.table_number).padStart(2, '0')}</span>
                    <span class="table-status-pill ${isOccupied ? 'occupied' : 'vacant'}">${isOccupied ? 'OCCUPIED' : 'VACANT'}</span>
                </div>
                <div class="table-details-body">
                    ${isOccupied ? `
                        <div class="table-occupied-info">
                            <span class="table-running-amount">₹${Number(subtotal).toFixed(2)}</span>
                            <span class="table-meta-text"><i class="fa-solid fa-bowl-food"></i> ${itemsCount} dishes ordered</span>
                            <span class="table-meta-text"><i class="fa-solid fa-user-tie"></i> Server: ${waiter}</span>
                        </div>
                    ` : `
                        <div class="table-vacant-info">
                            <i class="fa-solid fa-circle-check" style="color: #10b981;"></i> Table Ready for Guests
                        </div>
                    `}
                </div>
                <div class="table-box-footer">
                    <span>${isOccupied ? '⚡ Click to Settle & Bill' : 'Tap to take order'}</span>
                    <i class="fa-solid fa-chevron-right"></i>
                </div>
            `;

            card.addEventListener("click", () => {
                selectDiningTable(table);
            });

            counterTablesGrid.appendChild(card);
        });
    }

    function selectDiningTable(table) {
        selectedDiningTableNo = table.table_number;
        const isOccupied = (table.status === "OCCUPIED" || (table.items && table.items.length > 0) || !!table.order_id);

        // Highlight selected card
        document.querySelectorAll(".table-box-card").forEach(c => c.classList.remove("selected"));

        if (isOccupied) {
            selectedDiningOrder = table.active_bill || table.active_order || table;
            renderDiningTableCart(selectedDiningOrder);
            showToast(`Table ${table.table_number} tab loaded into settlement panel`, "success", 2000);
        } else {
            selectedDiningOrder = null;
            renderEmptyDiningCart(table.table_number);
            showToast(`Table ${table.table_number} is vacant`, "warning", 2000);
        }
    }

    function renderDiningTableCart(order) {
        if (!cartItemsList) return;
        currentCartTitle.textContent = `Table ${order.table_number || selectedDiningTableNo} Settle`;
        
        const items = order.items || [];
        if (cartCountBadge) cartCountBadge.textContent = `${items.length} items`;

        cartItemsList.innerHTML = "";
        items.forEach(item => {
            const row = document.createElement("div");
            row.className = "cart-item-row";
            const qty = item.quantity || 1;
            const price = item.unit_price || item.price || 0;
            const lineTotal = item.total_price || (qty * price);

            row.innerHTML = `
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.item_name || item.name}</div>
                    <div class="cart-item-meta">₹${Number(price).toFixed(0)} × ${qty} ${item.item_notes ? `(${item.item_notes})` : ''}</div>
                </div>
                <div class="cart-item-total">₹${lineTotal.toFixed(2)}</div>
            `;
            cartItemsList.appendChild(row);
        });

        if (btnSettleTabText) {
            btnSettleTabText.textContent = `Settle Table ${order.table_number || selectedDiningTableNo} & Print`;
        }

        updateFinancials();
    }

    function renderEmptyDiningCart(tableNo) {
        if (!cartItemsList) return;
        currentCartTitle.textContent = tableNo ? `Table ${tableNo} (Vacant)` : "Select Table";
        if (cartCountBadge) cartCountBadge.textContent = "0 items";
        cartItemsList.innerHTML = `
            <div class="cart-empty-state">
                <i class="fa-solid fa-chair"></i>
                <p>Click on any occupied table on the left to view active dishes and settle bill.</p>
            </div>
        `;
        if (btnSettleTabText) {
            btnSettleTabText.textContent = "Select Table to Settle";
        }
        updateFinancials();
    }

    // ─── FINANCIAL CALCULATIONS & PAYMENT MODES ───────────────────────────────
    function getSubtotal() {
        if (currentMode === "WALK_IN") {
            return Object.values(walkinCart).reduce((sum, e) => sum + (e.quantity * e.item.price), 0);
        } else {
            if (!selectedDiningOrder) return 0;
            return selectedDiningOrder.subtotal || selectedDiningOrder.total_amount || 0;
        }
    }

    function getNetTotal() {
        const sub = getSubtotal();
        const disc = parseFloat(cartDiscountInput ? cartDiscountInput.value : 0) || 0;
        return Math.max(0, sub - disc);
    }

    function updateFinancials() {
        const sub = getSubtotal();
        const disc = parseFloat(cartDiscountInput ? cartDiscountInput.value : 0) || 0;
        const net = Math.max(0, sub - disc);

        if (cartSubtotalEl) cartSubtotalEl.textContent = `₹${sub.toFixed(2)}`;
        if (cartNetTotalEl) cartNetTotalEl.textContent = `₹${net.toFixed(2)}`;

        if (btnCheckoutText) {
            btnCheckoutText.textContent = `Charge ₹${net.toFixed(2)} & Print Bill`;
        }
        if (btnSettleTabText && selectedDiningOrder) {
            btnSettleTabText.textContent = `Settle ₹${net.toFixed(2)} & Print Bill`;
        }

        updateChangeCalculation();
    }

    function setPaymentMode(mode) {
        currentPaymentMode = mode;
        paymentTabs.forEach(tab => {
            if (tab.getAttribute("data-mode") === mode) {
                tab.classList.add("active");
            } else {
                tab.classList.remove("active");
            }
        });

        if (cashTenderContainer) {
            cashTenderContainer.style.display = (mode === "CASH") ? "flex" : "none";
        }
    }

    function updateChangeCalculation() {
        if (currentPaymentMode !== "CASH" || !cashReceivedInput || !changeDisplay) return;
        const rec = parseFloat(cashReceivedInput.value) || 0;
        const net = getNetTotal();
        const change = Math.max(0, rec - net);
        changeDisplay.textContent = `Change: ₹${change.toFixed(2)}`;
    }

    // ─── DIRECT WALK-IN CHECKOUT WITH PRINTER DISPATCH ─────────────────────────
    async function performWalkinCheckout() {
        const entries = Object.values(walkinCart);
        if (entries.length === 0) {
            showToast("Please add items to cart before checkout!", "warning");
            return;
        }

        const net = getNetTotal();
        const disc = parseFloat(cartDiscountInput ? cartDiscountInput.value : 0) || 0;
        const rec = currentPaymentMode === "CASH" ? (parseFloat(cashReceivedInput ? cashReceivedInput.value : net) || net) : net;

        const payload = {
            order_type: "WALK_IN",
            customer_name: "Walk-in Customer",
            payment_mode: currentPaymentMode,
            discount: disc,
            received_amount: rec,
            items: entries.map(e => ({
                menu_item_id: e.item.id,
                name: e.item.name,
                unit_price: e.item.price,
                quantity: e.quantity,
                notes: e.notes || ""
            }))
        };

        btnCheckoutOrder.disabled = true;
        btnCheckoutOrder.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Bill...`;

        try {
            const res = await fetch("/api/pos/checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.success && data.bill) {
                lastGeneratedBill = data.bill;
                
                // Clear cart immediately
                walkinCart = {};
                if (cartDiscountInput) cartDiscountInput.value = "0";
                if (cashReceivedInput) cashReceivedInput.value = "";
                renderWalkinCart();
                renderMenuItems();

                // Step: Direct Thermal Print Execution
                await handleDirectThermalPrint(data.bill);

            } else {
                showToast(`Checkout Failed: ${data.error || 'Server error'}`, "error");
            }
        } catch (e) {
            showToast(`Connection Error: ${e.message}`, "error");
        } finally {
            btnCheckoutOrder.disabled = false;
            updateFinancials();
        }
    }

    // ─── DIRECT TABLE SETTLEMENT WITH PRINTER DISPATCH ─────────────────────────
    async function performTableSettlement() {
        if (!selectedDiningTableNo || !selectedDiningOrder) {
            showToast("Please select an occupied table to settle!", "warning");
            return;
        }

        const net = getNetTotal();
        const disc = parseFloat(cartDiscountInput ? cartDiscountInput.value : 0) || 0;
        const rec = currentPaymentMode === "CASH" ? (parseFloat(cashReceivedInput ? cashReceivedInput.value : net) || net) : net;

        const payload = {
            table_number: selectedDiningTableNo,
            payment_mode: currentPaymentMode,
            discount: disc,
            received_amount: rec,
            customer_name: selectedDiningOrder.customer_name || `Table ${selectedDiningTableNo}`
        };

        btnSettleTableTab.disabled = true;
        btnSettleTableTab.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Finalizing Table...`;

        try {
            const res = await fetch("/api/pos/tables/settle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.success && data.bill) {
                lastGeneratedBill = data.bill;

                showToast(`Table ${selectedDiningTableNo} Settled! Bill #${data.bill.bill_number}`, "success");

                // Reset selection & refresh floor tables
                selectedDiningOrder = null;
                selectedDiningTableNo = null;
                if (cartDiscountInput) cartDiscountInput.value = "0";
                if (cashReceivedInput) cashReceivedInput.value = "";
                renderEmptyDiningCart();
                await loadCounterTables();

                // Step: Direct Thermal Print Execution
                await handleDirectThermalPrint(data.bill);

            } else {
                showToast(`Settlement Failed: ${data.error || 'Check active order'}`, "error");
            }
        } catch (e) {
            showToast(`Connection Error: ${e.message}`, "error");
        } finally {
            btnSettleTableTab.disabled = false;
            updateFinancials();
        }
    }

    // ─── DIRECT THERMAL PRINTING IN BROWSER TO WIRED USB PRINTER ──────────────
    async function handleDirectThermalPrint(bill) {
        if (!bill) return;

        // 1. Populate receipt modal for on-screen reference
        openReceiptPreviewModal(bill);

        // 2. Direct Browser Thermal Print to Connected USB/Windows Default Printer (HOIN HOP-H58)
        printDirectBrowserReceipt(bill);
    }

    function printDirectBrowserReceipt(bill) {
        const is58 = printerState.paperWidth === 58;
        const widthMm = is58 ? "56mm" : "76mm";
        const pageMm = is58 ? "58mm" : "80mm";
        const fontSize = is58 ? "11px" : "12px";

        const itemsHtml = (bill.items || []).map(i => `
            <tr>
                <td style="text-align: left; padding: 2px 0; font-weight: 700; word-break: break-word;">${i.item_name || i.name}</td>
                <td style="text-align: center; padding: 2px 0;">${i.quantity}</td>
                <td style="text-align: right; padding: 2px 0;">${Number(i.unit_price).toFixed(0)}</td>
                <td style="text-align: right; padding: 2px 0; font-weight: 700;">${Number(i.total_price || (i.quantity * i.unit_price)).toFixed(2)}</td>
            </tr>
        `).join("");

        const receiptDoc = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Bill #${bill.bill_number}</title>
                <style>
                    @page { size: ${pageMm} auto; margin: 0; }
                    body {
                        font-family: 'JetBrains Mono', 'Courier New', monospace;
                        width: ${widthMm};
                        margin: 0 auto;
                        padding: 4px 2px;
                        color: #000;
                        background: #fff;
                        font-size: ${fontSize};
                        line-height: 1.3;
                    }
                    .center { text-align: center; }
                    .bold { font-weight: bold; }
                    .divider { border-bottom: 1px dashed #000; margin: 4px 0; }
                    .double-divider { border-bottom: 2px solid #000; margin: 4px 0; }
                    .table-row { display: flex; justify-content: space-between; margin: 2px 0; }
                    table { width: 100%; border-collapse: collapse; margin: 3px 0; font-size: ${fontSize}; }
                    .title { font-size: 14px; font-weight: 900; }
                    .large-total { font-size: 14px; font-weight: 900; }
                </style>
            </head>
            <body>
                <div class="center">
                    <div class="title">HOTEL MITRAYA</div>
                    <div style="font-size: 10px;">Pure Veg Restaurant &amp; Caterers</div>
                    <div style="font-size: 9px;">Akurdi, Pune - 411035</div>
                    <div style="font-size: 9px;">Ph: +91 9158691003</div>
                </div>
                <div class="divider"></div>
                <div class="table-row bold">
                    <span>${bill.order_type === 'DINING' ? 'TABLE: Table ' + bill.table_number : (bill.notes ? 'TABLE: ' + bill.notes : 'WALK-IN')}</span>
                    <span>${bill.bill_number}</span>
                </div>
                <div class="table-row" style="font-size: 9px;">
                    <span>Date: ${bill.created_at || new Date().toLocaleString("en-IN")}</span>
                    <span>Mode: ${bill.payment_mode || 'CASH'}</span>
                </div>
                <div class="divider"></div>
                <table>
                    <thead>
                        <tr style="border-bottom: 1px solid #000; font-size: 10px;">
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
                    <span>Sub Total:</span>
                    <span>₹${Number(bill.subtotal || 0).toFixed(2)}</span>
                </div>
                ${bill.discount > 0 ? `
                <div class="table-row">
                    <span>Discount:</span>
                    <span>-₹${Number(bill.discount).toFixed(2)}</span>
                </div>` : ''}
                <div class="double-divider"></div>
                <div class="table-row large-total">
                    <span>GRAND TOTAL:</span>
                    <span>₹${Number(bill.total_amount || 0).toFixed(2)}</span>
                </div>
                <div class="double-divider"></div>
                ${(bill.payment_mode === 'CASH' && bill.received_amount) ? `
                <div class="table-row" style="font-size: 10px;">
                    <span>Cash Tendered:</span>
                    <span>₹${Number(bill.received_amount).toFixed(2)}</span>
                </div>
                <div class="table-row" style="font-size: 10px;">
                    <span>Change Return:</span>
                    <span>₹${Number(bill.change_amount || 0).toFixed(2)}</span>
                </div>
                <div class="divider"></div>` : ''}
                <div class="center" style="font-size: 10px; margin-top: 4px;">
                    Thank You! Visit Again.<br>
                    *** Have a Delicious Day ***
                </div>
            </body>
            </html>
        `;

        let iframe = document.getElementById("direct-print-frame");
        if (iframe) iframe.remove();

        iframe = document.createElement("iframe");
        iframe.id = "direct-print-frame";
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
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        }, 250);
    }

    // ─── RECEIPT MODAL PREVIEW & POPULATION ───────────────────────────────────
    function openReceiptPreviewModal(bill) {
        if (!receiptModal) return;
        lastGeneratedBill = bill;

        // Populate receipt fields
        const rcptTableNo = document.getElementById("rcpt-table-no");
        const rcptBillNo = document.getElementById("rcpt-bill-no");
        const rcptDate = document.getElementById("rcpt-date");
        const rcptCashier = document.getElementById("rcpt-cashier");
        const rcptMode = document.getElementById("rcpt-mode");
        const rcptOrderType = document.getElementById("rcpt-order-type");
        const rcptItemsBody = document.getElementById("rcpt-items-body");
        const rcptSubtotal = document.getElementById("rcpt-subtotal");
        const rcptDiscount = document.getElementById("rcpt-discount");
        const rcptTotal = document.getElementById("rcpt-total");
        const rcptTendered = document.getElementById("rcpt-tendered");
        const rcptChange = document.getElementById("rcpt-change");
        const rcptBarcodeText = document.getElementById("rcpt-barcode-text");

        if (rcptTableNo) rcptTableNo.textContent = bill.table_number ? `TABLE: ${bill.table_number}` : `TABLE: Walk-in`;
        if (rcptBillNo) rcptBillNo.textContent = `Bill: ${bill.bill_number}`;
        if (rcptDate) rcptDate.textContent = bill.created_at || new Date().toLocaleString("en-IN");
        if (rcptCashier) rcptCashier.textContent = `Cashier: ${bill.cashier_role || "Staff"}`;
        if (rcptMode) rcptMode.textContent = `Mode: ${bill.payment_mode || "CASH"}`;
        if (rcptOrderType) rcptOrderType.textContent = `Type: ${bill.order_type || "WALK-IN"}`;
        if (rcptSubtotal) rcptSubtotal.textContent = `₹${Number(bill.subtotal || 0).toFixed(2)}`;
        if (rcptDiscount) rcptDiscount.textContent = `-₹${Number(bill.discount || 0).toFixed(2)}`;
        if (rcptTotal) rcptTotal.textContent = `₹${Number(bill.total_amount || 0).toFixed(2)}`;
        if (rcptTendered) rcptTendered.textContent = `₹${Number(bill.received_amount || bill.total_amount || 0).toFixed(2)}`;
        if (rcptChange) rcptChange.textContent = `₹${Number(bill.change_amount || 0).toFixed(2)}`;
        if (rcptBarcodeText) rcptBarcodeText.textContent = bill.bill_number;

        if (rcptItemsBody) {
            rcptItemsBody.innerHTML = "";
            (bill.items || []).forEach(item => {
                const tr = document.createElement("tr");
                const qty = item.quantity || 1;
                const rate = item.unit_price || 0;
                const amt = item.total_price || (qty * rate);
                tr.innerHTML = `
                    <td class="col-item">${item.item_name || item.name}</td>
                    <td class="col-qty">${qty}</td>
                    <td class="col-rate">${Number(rate).toFixed(0)}</td>
                    <td class="col-amt">${Number(amt).toFixed(2)}</td>
                `;
                rcptItemsBody.appendChild(tr);
            });
        }

        receiptModal.classList.add("active");
    }

    // ─── RECENT BILLS DRAWER ──────────────────────────────────────────────────
    async function openRecentBillsModal() {
        if (!recentBillsModal) return;
        recentBillsModal.classList.add("active");
        if (recentBillsList) {
            recentBillsList.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading recent bills...</div>`;
        }

        try {
            const res = await fetch("/api/pos/bills/recent");
            const data = await res.json();
            if (data.success && data.bills && data.bills.length > 0) {
                recentBillsList.innerHTML = "";
                data.bills.forEach(bill => {
                    const item = document.createElement("div");
                    item.className = "cart-item-row";
                    item.style.padding = "12px";

                    item.innerHTML = `
                        <div class="cart-item-info">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <strong style="color:#ffffff; font-family:var(--font-mono);">${bill.bill_number}</strong>
                                <span class="table-status-pill ${bill.order_type === 'DINING' ? 'occupied' : 'vacant'}" style="font-size:10px;">${bill.order_type}</span>
                            </div>
                            <div class="cart-item-meta" style="margin-top:4px;">
                                <span>${bill.created_at || ''}</span> • 
                                <span>Mode: ${bill.payment_mode}</span> • 
                                <span style="color:#38bdf8; font-weight:800;">₹${Number(bill.total_amount).toFixed(2)}</span>
                            </div>
                        </div>
                        <button type="button" class="btn-header btn-reprint" style="padding:6px 12px; font-size:11px;">
                            <i class="fa-solid fa-print"></i> Reprint
                        </button>
                    `;

                    item.querySelector(".btn-reprint").addEventListener("click", async () => {
                        await reprintBill(bill);
                    });

                    recentBillsList.appendChild(item);
                });
            } else {
                recentBillsList.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">No bills generated yet today.</div>`;
            }
        } catch (e) {
            recentBillsList.innerHTML = `<div style="text-align:center; padding:20px; color:#f87171;">Failed to load recent bills.</div>`;
        }
    }

    async function reprintBill(bill) {
        showToast(`Reprinting Bill #${bill.bill_number}...`, "warning", 2000);
        try {
            // Check Bluetooth
            if (printerState.type === "BLUETOOTH" && window.MitrayaBluetoothPrinter && window.MitrayaBluetoothPrinter.isConnected()) {
                await window.MitrayaBluetoothPrinter.printReceipt(bill);
                showToast(`Reprinted #${bill.bill_number} on Bluetooth!`, "success");
                return;
            }

            // Otherwise call reprint API
            const res = await fetch(`/api/printer/reprint/${bill.id}`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                showToast(`Bill #${bill.bill_number} dispatched to printer!`, "success");
            } else {
                // Fallback to receipt modal
                openReceiptPreviewModal(bill);
            }
        } catch (e) {
            openReceiptPreviewModal(bill);
        }
    }

    // ─── BACKGROUND POLLING (TABLES & KITCHEN PROGRESSION) ─────────────────────
    function startLivePolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async () => {
            if (currentMode === "DINING") {
                await loadCounterTables();
            }
        }, 5000);
    }

    // Run on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
