/**
 * Hotel Mitraya Quick POS Client Application
 * ===========================================
 * Handles menu catalog, shopping cart, cash tender calculations,
 * sequential checkout, mobile drawer controls, keyboard shortcuts,
 * and 80mm thermal receipt printing & reprinting.
 */

(function () {
    "use strict";

    // Application State
    let catalog = [];
    let cart = []; // [{ item_id, name, unit_price, quantity }]
    let activeCategoryId = "all";
    let paymentMode = "CASH";
    let discountAmount = 0;
    let cashReceived = 0;
    let currentFilteredItems = [];

    // Dual Billing & 12 Tables State
    let orderMode = "WALK_IN"; // "WALK_IN" or "DINING"
    let selectedTableNumber = 1;
    let currentTableOrder = null; // Active PosBill on selected table if any

    // DOM Elements
    const categoryBar = document.getElementById("category-pills-bar");
    const menuGrid = document.getElementById("menu-items-grid");
    const searchInput = document.getElementById("item-search-input");
    const cartPane = document.getElementById("pos-cart-pane");
    const cartList = document.getElementById("cart-items-list");
    const cartCountBadge = document.getElementById("cart-count-badge");
    const cartSubtotalEl = document.getElementById("cart-subtotal");
    const cartDiscountInput = document.getElementById("cart-discount-input");
    const cartNetTotalEl = document.getElementById("cart-net-total");
    const btnClearCart = document.getElementById("btn-clear-cart");
    const paymentModeButtons = document.querySelectorAll(".pm-tab-btn");
    const cashTenderBox = document.getElementById("cash-tender-container");
    const cashReceivedInput = document.getElementById("cash-received-input");
    const changeDisplay = document.getElementById("change-display");
    const btnExactCash = document.getElementById("btn-exact-cash");
    const quickCashButtons = document.querySelectorAll(".quick-cash-btn[data-val]");
    const btnCheckout = document.getElementById("btn-checkout-order");
    const btnCheckoutText = document.getElementById("btn-checkout-text");

    // Dual Mode & 12 Tables Elements
    const tabModeWalkin = document.getElementById("tab-mode-walkin");
    const tabModeDining = document.getElementById("tab-mode-dining");
    const diningTableBanner = document.getElementById("dining-table-banner");
    const cartSelectedTableBadge = document.getElementById("cart-selected-table-badge");
    const cartTableStatusPill = document.getElementById("cart-table-status-pill");
    const btnChangeTable = document.getElementById("btn-change-table");
    const diningActionButtons = document.getElementById("dining-action-buttons");
    const walkinTableContainer = document.getElementById("walkin-table-container");
    const walkinTableSelect = document.getElementById("walkin-table-select");
    const btnSaveTableTab = document.getElementById("btn-save-table-tab");
    const btnSaveTabText = document.getElementById("btn-save-tab-text");
    const btnSettleTableTab = document.getElementById("btn-settle-table-tab");
    const btnSettleTabText = document.getElementById("btn-settle-tab-text");
    const cartHeadingTitle = document.getElementById("cart-heading-title");


    // Tables Modal Elements
    const tablesModal = document.getElementById("tables-modal");
    const btnOpenTablesModal = document.getElementById("btn-open-tables-modal");
    const btnCloseTablesModal = document.getElementById("btn-close-tables-modal");
    const btnDismissTablesModal = document.getElementById("btn-dismiss-tables-modal");
    const modalTablesGrid = document.getElementById("modal-tables-grid");
    const headerTablesLabel = document.getElementById("header-tables-label");

    // Mobile Elements
    const btnOpenMobileCart = document.getElementById("btn-open-mobile-cart");
    const btnMobileCloseCart = document.getElementById("btn-mobile-close-cart");
    const mobileCartCount = document.getElementById("mobile-cart-count");
    const mobileCartTotal = document.getElementById("mobile-cart-total");

    // Modals & Bluetooth Elements
    const receiptModal = document.getElementById("receipt-modal");
    const btnCloseReceipt = document.getElementById("btn-close-receipt-modal");
    const btnDismissReceipt = document.getElementById("btn-dismiss-receipt");
    const btnPrintReceipt = document.getElementById("btn-print-receipt");
    const btnBtDirectPrint = document.getElementById("btn-bt-direct-print");
    const recentBillsModal = document.getElementById("recent-bills-modal");
    const btnOpenRecent = document.getElementById("btn-open-recent-bills");
    const btnCloseRecent = document.getElementById("btn-close-recent-modal");
    const btnCloseRecentFooter = document.getElementById("btn-close-recent-modal-btn");
    const recentBillsTbody = document.getElementById("recent-bills-table-body");
    const shortcutsModal = document.getElementById("shortcuts-modal");
    const btnOpenShortcuts = document.getElementById("btn-open-shortcuts-modal");
    const btnCloseShortcuts = document.getElementById("btn-close-shortcuts-modal");
    const btnDismissShortcuts = document.getElementById("btn-dismiss-shortcuts");
    const btnLogout = document.getElementById("btn-logout");

    // Bluetooth Printer Modal Elements
    const btnBtPrinter = document.getElementById("btn-bt-printer");
    const btBtnLabel = document.getElementById("bt-btn-label");
    const btPrinterModal = document.getElementById("bt-printer-modal");
    const btnCloseBtModal = document.getElementById("btn-close-bt-modal");
    const btnDismissBtModal = document.getElementById("btn-dismiss-bt-modal");
    const btnBtConnect = document.getElementById("btn-bt-connect");
    const btnBtDisconnect = document.getElementById("btn-bt-disconnect");
    const btnBtTestPrint = document.getElementById("btn-bt-test-print");
    const btModalDeviceName = document.getElementById("bt-modal-device-name");
    const btModalStatusDot = document.getElementById("bt-modal-status-dot");
    const btModalStatusText = document.getElementById("bt-modal-status-text");
    const btAutoprintToggle = document.getElementById("bt-autoprint-toggle");
    const btPaperWidthSelect = document.getElementById("bt-paper-width-select");

    let currentReceiptBill = null;

    // Toast Notifications
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        const icon = type === "success" ? "fa-circle-check" : "fa-circle-exclamation";
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 250);
        }, 2800);
    }

    // Format Currency
    function formatMoney(amount) {
        return "₹" + Number(amount || 0).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Load Catalog from API
    async function loadCatalog() {
        try {
            const res = await fetch("/api/pos/catalog");
            const data = await res.json();

            if (res.ok && data.success) {
                catalog = data.categories || [];
                renderCategoryBar();
                renderMenuGrid();
            } else {
                menuGrid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; color: var(--accent-rose); padding: 40px;">
                        <i class="fa-solid fa-circle-exclamation fa-2x"></i>
                        <p style="margin-top: 10px;">Failed to load menu catalog (${data.error || "Error"})</p>
                    </div>`;
            }
        } catch (err) {
            console.error("Error loading catalog:", err);
            menuGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: var(--accent-rose); padding: 40px;">
                    <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                    <p style="margin-top: 10px;">Network error loading menu catalog.</p>
                </div>`;
        }
    }

    // Render Category Pills
    function renderCategoryBar() {
        categoryBar.innerHTML = `<button type="button" class="category-pill ${activeCategoryId === "all" ? "active" : ""}" data-cat-id="all">All Items</button>`;

        catalog.forEach(cat => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = `category-pill ${activeCategoryId == cat.id ? "active" : ""}`;
            btn.dataset.catId = cat.id;
            btn.textContent = `${cat.name} (${cat.items ? cat.items.length : 0})`;
            btn.addEventListener("click", () => {
                activeCategoryId = cat.id;
                document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
                btn.classList.add("active");
                renderMenuGrid();
            });
            categoryBar.appendChild(btn);
        });

        // Click handler for All Items
        const allBtn = categoryBar.querySelector('[data-cat-id="all"]');
        if (allBtn) {
            allBtn.addEventListener("click", () => {
                activeCategoryId = "all";
                document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
                allBtn.classList.add("active");
                renderMenuGrid();
            });
        }
    }

    // Render Menu Items Grid with Search Filter
    function renderMenuGrid() {
        const query = (searchInput.value || "").trim().toLowerCase();
        let itemsToDisplay = [];

        catalog.forEach(cat => {
            if (activeCategoryId === "all" || activeCategoryId == cat.id) {
                if (cat.items) {
                    itemsToDisplay.push(...cat.items);
                }
            }
        });

        // Filter by search query
        if (query) {
            itemsToDisplay = itemsToDisplay.filter(item =>
                item.name.toLowerCase().includes(query) ||
                (item.code && item.code.toLowerCase().includes(query)) ||
                (item.category_name && item.category_name.toLowerCase().includes(query))
            );
        }

        currentFilteredItems = itemsToDisplay;

        if (itemsToDisplay.length === 0) {
            menuGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 50px 20px;">
                    <i class="fa-solid fa-bowl-food fa-2x" style="opacity: 0.4;"></i>
                    <p style="margin-top: 10px; font-size: 14px;">No matching food items found.</p>
                </div>`;
            return;
        }

        menuGrid.innerHTML = "";
        itemsToDisplay.forEach(item => {
            const card = document.createElement("div");
            card.className = "menu-item-card";
            card.innerHTML = `
                <div>
                    <span class="item-card-code">${item.code || ""}</span>
                    <h4 class="item-card-name">${item.name}</h4>
                </div>
                <div class="item-card-bottom">
                    <span class="item-card-price">${formatMoney(item.price)}</span>
                    <div class="item-add-badge"><i class="fa-solid fa-plus"></i></div>
                </div>
            `;
            card.addEventListener("click", () => {
                addToCart(item);
            });
            menuGrid.appendChild(card);
        });
    }

    // Search input listener
    searchInput.addEventListener("input", renderMenuGrid);

    // Search input Enter key handler: adds first match to cart
    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            if (currentFilteredItems && currentFilteredItems.length > 0) {
                addToCart(currentFilteredItems[0]);
                searchInput.value = "";
                renderMenuGrid();
            }
        }
    });

    // Cart Management
    function addToCart(item) {
        const existing = cart.find(c => c.item_id === item.id);
        if (existing) {
            existing.quantity += 1;
        } else {
            cart.push({
                item_id: item.id,
                name: item.name,
                unit_price: Number(item.price),
                quantity: 1
            });
        }
        updateCartUI();
        showToast(`+1 ${item.name}`, "success");
    }

    function updateCartItemQty(index, delta) {
        if (!cart[index]) return;
        cart[index].quantity += delta;
        if (cart[index].quantity <= 0) {
            cart.splice(index, 1);
        }
        updateCartUI();
    }

    function removeCartItem(index) {
        if (!cart[index]) return;
        cart.splice(index, 1);
        updateCartUI();
    }

    function clearCart() {
        if (cart.length === 0) return;
        cart = [];
        discountAmount = 0;
        if (cartDiscountInput) cartDiscountInput.value = 0;
        if (cashReceivedInput) cashReceivedInput.value = "";
        updateCartUI();
        showToast("Cart cleared", "success");
    }

    btnClearCart.addEventListener("click", clearCart);

    // Update Cart UI & Financial Calculations
    function updateCartUI() {
        const totalItemsCount = cart.reduce((sum, item) => sum + item.quantity, 0);
        cartCountBadge.textContent = totalItemsCount;

        let subtotal = 0;
        if (cart.length === 0) {
            cartList.innerHTML = `
                <div class="cart-empty-state">
                    <i class="fa-solid fa-utensils"></i>
                    <p>No items added yet.<br><small>Click on any dish card to add to order.</small></p>
                </div>`;
            cartSubtotalEl.textContent = formatMoney(0);
            cartNetTotalEl.textContent = formatMoney(0);
            btnCheckout.disabled = true;
            btnCheckoutText.textContent = "Charge ₹0.00 & Print";
            changeDisplay.textContent = "Change: ₹0.00";

            if (mobileCartCount) mobileCartCount.textContent = "0 items";
            if (mobileCartTotal) mobileCartTotal.textContent = "₹0.00";
            return;
        }

        cartList.innerHTML = "";

        cart.forEach((item, idx) => {
            const lineTotal = item.quantity * item.unit_price;
            subtotal += lineTotal;

            const row = document.createElement("div");
            row.className = "cart-item-row";
            row.innerHTML = `
                <div class="cart-item-info">
                    <div class="cart-item-name" title="${item.name}">${item.name}</div>
                    <div class="cart-item-rate">${formatMoney(item.unit_price)} × ${item.quantity}</div>
                </div>
                <div class="cart-qty-control">
                    <button type="button" class="qty-btn btn-qty-minus" data-idx="${idx}"><i class="fa-solid fa-minus"></i></button>
                    <span class="qty-val">${item.quantity}</span>
                    <button type="button" class="qty-btn btn-qty-plus" data-idx="${idx}"><i class="fa-solid fa-plus"></i></button>
                </div>
                <div class="cart-item-total">${formatMoney(lineTotal)}</div>
                <button type="button" class="btn-remove-item" data-idx="${idx}" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            `;

            row.querySelector(".btn-qty-minus").addEventListener("click", (e) => {
                e.stopPropagation();
                updateCartItemQty(idx, -1);
            });
            row.querySelector(".btn-qty-plus").addEventListener("click", (e) => {
                e.stopPropagation();
                updateCartItemQty(idx, 1);
            });
            row.querySelector(".btn-remove-item").addEventListener("click", (e) => {
                e.stopPropagation();
                removeCartItem(idx);
            });

            cartList.appendChild(row);
        });

        // Discount & Net Total
        discountAmount = Math.max(0, parseFloat(cartDiscountInput.value) || 0);
        discountAmount = Math.min(discountAmount, subtotal);
        const netTotal = Math.max(0, subtotal - discountAmount);

        cartSubtotalEl.textContent = formatMoney(subtotal);
        cartNetTotalEl.textContent = formatMoney(netTotal);

        btnCheckout.disabled = false;
        btnCheckoutText.textContent = `Charge ${formatMoney(netTotal)} & Print`;

        // Update Mobile Bar
        if (mobileCartCount) mobileCartCount.textContent = `${totalItemsCount} item${totalItemsCount > 1 ? 's' : ''}`;
        if (mobileCartTotal) mobileCartTotal.textContent = formatMoney(netTotal);

        // Update Cash Tender and Change
        updateCashTenderCalculations(netTotal);
    }

    // Discount input changes
    cartDiscountInput.addEventListener("input", updateCartUI);

    // Payment Mode Switching
    function setPaymentMode(mode) {
        paymentMode = mode;
        paymentModeButtons.forEach(b => {
            if (b.dataset.mode === mode) {
                b.classList.add("active");
            } else {
                b.classList.remove("active");
            }
        });

        if (paymentMode === "CASH") {
            cashTenderBox.style.display = "flex";
        } else {
            cashTenderBox.style.display = "none";
        }
        updateCartUI();
    }

    paymentModeButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            setPaymentMode(btn.dataset.mode);
        });
    });

    // Cash Tender Helpers
    function updateCashTenderCalculations(netTotal) {
        if (paymentMode !== "CASH") return;

        const rawReceived = parseFloat(cashReceivedInput.value);
        if (isNaN(rawReceived) || rawReceived <= 0) {
            cashReceived = netTotal;
            changeDisplay.textContent = "Change: ₹0.00";
        } else {
            cashReceived = rawReceived;
            const change = Math.max(0, cashReceived - netTotal);
            changeDisplay.textContent = `Change: ${formatMoney(change)}`;
        }
    }

    cashReceivedInput.addEventListener("input", () => {
        const netTotal = getNetTotal();
        updateCashTenderCalculations(netTotal);
    });

    btnExactCash.addEventListener("click", () => {
        const net = getNetTotal();
        cashReceivedInput.value = net > 0 ? net : "";
        updateCashTenderCalculations(net);
    });

    quickCashButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const val = parseFloat(btn.dataset.val);
            cashReceivedInput.value = val;
            updateCashTenderCalculations(getNetTotal());
        });
    });

    function getNetTotal() {
        const subtotal = cart.reduce((sum, i) => sum + (i.quantity * i.unit_price), 0);
        const disc = Math.min(subtotal, Math.max(0, parseFloat(cartDiscountInput.value) || 0));
        return Math.max(0, subtotal - disc);
    }

    // Mobile Drawer Controls
    if (btnOpenMobileCart && cartPane) {
        btnOpenMobileCart.addEventListener("click", () => {
            cartPane.classList.add("mobile-open");
        });
    }

    if (btnMobileCloseCart && cartPane) {
        btnMobileCloseCart.addEventListener("click", () => {
            cartPane.classList.remove("mobile-open");
        });
    }

    // =========================================================================
    // Dual Billing Mode (Walk-in vs Dining) & 12 Tables Management
    // =========================================================================

    function setOrderMode(mode, loadTab = true) {
        orderMode = mode;
        if (mode === "DINING") {
            tabModeDining.classList.add("active");
            tabModeWalkin.classList.remove("active");
            diningTableBanner.style.display = "flex";
            diningActionButtons.style.display = "flex";
            if (walkinTableContainer) walkinTableContainer.style.display = "none";
            btnCheckout.style.display = "none";
            cartHeadingTitle.textContent = `Table ${selectedTableNumber} Order`;
            cartSelectedTableBadge.innerHTML = `<i class="fa-solid fa-chair"></i> Table ${selectedTableNumber}`;
            if (loadTab) {
                loadTableActiveOrder(selectedTableNumber);
            }
        } else {
            orderMode = "WALK_IN";
            tabModeWalkin.classList.add("active");
            tabModeDining.classList.remove("active");
            diningTableBanner.style.display = "none";
            diningActionButtons.style.display = "none";
            if (walkinTableContainer) walkinTableContainer.style.display = "flex";
            btnCheckout.style.display = "flex";
            cartHeadingTitle.textContent = "Walk-in Order";
        }
        updateCartUI();
    }


    if (tabModeWalkin) {
        tabModeWalkin.addEventListener("click", () => setOrderMode("WALK_IN"));
    }

    if (tabModeDining) {
        tabModeDining.addEventListener("click", () => {
            setOrderMode("DINING");
            openTablesModal();
        });
    }

    // Load active order on a specific Table (1-12)
    async function loadTableActiveOrder(tableNo) {
        try {
            const res = await fetch(`/api/pos/tables/${tableNo}`);
            const data = await res.json();
            if (res.ok && data.success) {
                if (data.status === "OCCUPIED" && data.bill) {
                    currentTableOrder = data.bill;
                    cart = (data.bill.items || []).map(i => ({
                        item_id: i.menu_item_id,
                        name: i.item_name,
                        unit_price: Number(i.unit_price),
                        quantity: Number(i.quantity)
                    }));
                    cartDiscountInput.value = data.bill.discount || 0;
                    cartTableStatusPill.textContent = `Running Tab (${formatMoney(data.bill.total_amount)})`;
                    cartTableStatusPill.style.background = "rgba(245, 158, 11, 0.25)";
                    cartTableStatusPill.style.color = "#fbbf24";
                    showToast(`Loaded Table ${tableNo} (${cart.length} items)`, "info");
                } else {
                    currentTableOrder = null;
                    cart = [];
                    discountAmount = 0;
                    if (cartDiscountInput) cartDiscountInput.value = 0;
                    if (cashReceivedInput) cashReceivedInput.value = "";
                    cartTableStatusPill.textContent = "Vacant / New Tab";
                    cartTableStatusPill.style.background = "rgba(16, 185, 129, 0.2)";
                    cartTableStatusPill.style.color = "#34d399";
                }
                updateCartUI();
            }
        } catch (err) {
            console.error("Error loading table order:", err);
        }
    }


    // Select Table from Modal
    function selectTable(tableNo) {
        selectedTableNumber = tableNo;
        setOrderMode("DINING", false);
        loadTableActiveOrder(tableNo);
        closeTablesModal();
    }

    // Tables Modal Management
    async function loadTablesModalData() {
        try {
            modalTablesGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 30px;">
                    <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
                    <p style="margin-top: 10px;">Loading tables status...</p>
                </div>`;

            const res = await fetch("/api/pos/tables");
            const data = await res.json();

            if (res.ok && data.success) {
                modalTablesGrid.innerHTML = "";
                if (headerTablesLabel) {
                    headerTablesLabel.textContent = `Tables (${data.occupied_count}/12)`;
                }

                data.tables.forEach(t => {
                    const isOcc = t.status === "OCCUPIED";
                    const isCurrent = orderMode === "DINING" && selectedTableNumber === t.table_number;
                    const card = document.createElement("div");
                    card.className = `modal-table-card ${isOcc ? "occupied" : "vacant"} ${isCurrent ? "selected" : ""}`;
                    card.innerHTML = `
                        <div class="modal-table-card-num"><i class="fa-solid fa-chair"></i> Table ${t.table_number}</div>
                        <div class="modal-table-card-status">${isOcc ? "● Occupied" : "● Vacant"}</div>
                        <div class="modal-table-card-items">${isOcc ? `${t.items_count} items (${t.elapsed_minutes}m)` : "Ready"}</div>
                        <div class="modal-table-card-total">${isOcc ? formatMoney(t.total_amount) : "₹0.00"}</div>
                    `;
                    card.addEventListener("click", () => {
                        selectTable(t.table_number);
                    });
                    modalTablesGrid.appendChild(card);
                });
            }
        } catch (e) {
            console.error("Error loading tables:", e);
            modalTablesGrid.innerHTML = `<div style="grid-column:1/-1; color:var(--brand-crimson); text-align:center;">Failed to load tables.</div>`;
        }
    }

    function openTablesModal() {
        loadTablesModalData();
        if (tablesModal) tablesModal.classList.add("active");
    }

    function closeTablesModal() {
        if (tablesModal) tablesModal.classList.remove("active");
    }

    if (btnOpenTablesModal) btnOpenTablesModal.addEventListener("click", openTablesModal);
    if (btnChangeTable) btnChangeTable.addEventListener("click", openTablesModal);
    if (btnCloseTablesModal) btnCloseTablesModal.addEventListener("click", closeTablesModal);
    if (btnDismissTablesModal) btnDismissTablesModal.addEventListener("click", closeTablesModal);

    // Save Table Tab (Incremental Dining Order)
    async function saveDiningTableTab() {
        if (cart.length === 0) {
            showToast("Cart is empty. Add dishes to Table tab first.", "error");
            return;
        }

        btnSaveTableTab.disabled = true;
        btnSaveTabText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

        try {
            const payload = {
                table_number: selectedTableNumber,
                items: cart.map(i => ({
                    menu_item_id: i.item_id,
                    name: i.name,
                    unit_price: i.unit_price,
                    quantity: i.quantity
                }))
            };

            const res = await fetch("/api/pos/tables/save-tab", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.success) {
                currentTableOrder = data.bill;
                showToast(`Table ${selectedTableNumber} tab saved! (${data.bill.items_count} items)`, "success");
                cartTableStatusPill.textContent = `Running Tab (${formatMoney(data.bill.total_amount)})`;
                cartTableStatusPill.style.background = "rgba(245, 158, 11, 0.25)";
                cartTableStatusPill.style.color = "#fbbf24";
                loadTablesModalData();
            } else {
                showToast(data.error || "Failed to save table tab", "error");
            }
        } catch (err) {
            console.error("Save tab error:", err);
            showToast("Network error saving table tab", "error");
        } finally {
            btnSaveTableTab.disabled = false;
            btnSaveTabText.innerHTML = '<i class="fa-solid fa-plus-circle"></i> Save / Add to Table';
        }
    }

    if (btnSaveTableTab) {
        btnSaveTableTab.addEventListener("click", saveDiningTableTab);
    }

    // Settle Dining Table Tab (Final Checkout & Receipt)
    async function settleDiningTableTab() {
        if (cart.length === 0) {
            showToast("Cart is empty. Nothing to settle.", "error");
            return;
        }

        const netTotal = getNetTotal();
        btnSettleTableTab.disabled = true;
        btnSettleTabText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Settling...';

        try {
            const payload = {
                table_number: selectedTableNumber,
                items: cart.map(i => ({
                    menu_item_id: i.item_id,
                    name: i.name,
                    unit_price: i.unit_price,
                    quantity: i.quantity
                })),
                discount: discountAmount,
                payment_mode: paymentMode,
                received_amount: paymentMode === "CASH" ? (parseFloat(cashReceivedInput.value) || netTotal) : netTotal
            };

            const res = await fetch("/api/pos/tables/settle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.success) {
                currentReceiptBill = data.bill;
                showToast(`Table ${selectedTableNumber} settled! (#${data.bill.bill_number}) Sent to Printer`, "success");

                // Clear Table cart state
                cart = [];
                discountAmount = 0;
                if (cartDiscountInput) cartDiscountInput.value = 0;
                if (cashReceivedInput) cashReceivedInput.value = "";
                currentTableOrder = null;
                cartTableStatusPill.textContent = "Vacant / Settled";
                cartTableStatusPill.style.background = "rgba(16, 185, 129, 0.2)";
                cartTableStatusPill.style.color = "#059669";
                updateCartUI();
                loadTablesModalData();

            } else {
                showToast(data.error || "Failed to settle table", "error");
            }
        } catch (err) {
            console.error("Settle error:", err);
            showToast("Network error settling table", "error");
        } finally {
            btnSettleTableTab.disabled = false;
            btnSettleTabText.innerHTML = '<i class="fa-solid fa-check-double"></i> Settle &amp; Print Bill';
        }
    }

    if (btnSettleTableTab) {
        btnSettleTableTab.addEventListener("click", settleDiningTableTab);
    }

    // Walk-in Checkout Order Submission
    async function submitOrder() {
        if (orderMode === "DINING") {
            settleDiningTableTab();
            return;
        }

        if (cart.length === 0) {
            showToast("Cart is empty. Add dishes first.", "error");
            return;
        }

        const netTotal = getNetTotal();
        const walkinTableVal = walkinTableSelect ? walkinTableSelect.value : "";
        const payload = {
            order_type: "WALK_IN",
            table_number: null,
            notes: walkinTableVal || "Walk-in Counter",
            items: cart.map(i => ({
                menu_item_id: i.item_id,
                name: i.name,
                unit_price: i.unit_price,
                quantity: i.quantity
            })),
            discount: discountAmount,
            payment_mode: paymentMode,
            received_amount: paymentMode === "CASH" ? (parseFloat(cashReceivedInput.value) || netTotal) : netTotal
        };

        btnCheckout.disabled = true;
        btnCheckoutText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';

        try {
            const res = await fetch("/api/pos/checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok && data.success) {
                currentReceiptBill = data.bill;
                showToast(`Order #${data.bill.bill_number} placed! Sent to Display Screen & Printer`, "success");
                
                // If on mobile, close drawer
                if (cartPane) cartPane.classList.remove("mobile-open");

                // Clear current cart for next customer
                cart = [];
                discountAmount = 0;
                if (cartDiscountInput) cartDiscountInput.value = 0;
                if (cashReceivedInput) cashReceivedInput.value = "";
                if (walkinTableSelect) walkinTableSelect.value = "";
                updateCartUI();

            } else {
                showToast(data.error || "Failed to process order", "error");
            }
        } catch (err) {
            console.error("Checkout error:", err);
            showToast("Network error while submitting order", "error");
        } finally {
            btnCheckout.disabled = false;
            updateCartUI();
        }
    }

    btnCheckout.addEventListener("click", submitOrder);

    // Thermal Receipt Rendering
    function renderThermalReceipt(bill) {
        currentReceiptBill = bill;
        const isDining = bill.order_type === "DINING" || (bill.table_number && bill.table_number > 0);
        const rcptTableEl = document.getElementById("rcpt-table-no");
        if (rcptTableEl) {
            const tableLabel = isDining ? `TABLE: Table ${bill.table_number}` : (bill.notes ? `TABLE: ${bill.notes}` : "TABLE: Walk-in Counter");
            rcptTableEl.textContent = tableLabel;
        }
        const rcptOrderTypeEl = document.getElementById("rcpt-order-type");
        if (rcptOrderTypeEl) {
            rcptOrderTypeEl.textContent = `Type: ${bill.order_type || (isDining ? 'DINING' : 'WALK-IN')}`;
        }


        document.getElementById("rcpt-bill-no").textContent = `Bill: ${bill.bill_number}`;
        document.getElementById("rcpt-date").textContent = bill.created_at || new Date().toLocaleString();
        document.getElementById("rcpt-cashier").textContent = `Staff: ${bill.cashier_role || "Cashier"}`;
        document.getElementById("rcpt-mode").textContent = `Mode: ${bill.payment_mode}`;

        const tbody = document.getElementById("rcpt-items-body");
        tbody.innerHTML = "";

        if (bill.items) {
            bill.items.forEach(item => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="col-item">${item.item_name}</td>
                    <td class="col-qty">${item.quantity}</td>
                    <td class="col-rate">${item.unit_price}</td>
                    <td class="col-amt">${item.total_price.toFixed(2)}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        document.getElementById("rcpt-subtotal").textContent = formatMoney(bill.subtotal);
        
        const discRow = document.getElementById("rcpt-discount-row");
        if (bill.discount > 0) {
            discRow.style.display = "flex";
            document.getElementById("rcpt-discount").textContent = `-${formatMoney(bill.discount)}`;
        } else {
            discRow.style.display = "none";
        }

        document.getElementById("rcpt-total").textContent = formatMoney(bill.total_amount);

        const tenderRow = document.getElementById("rcpt-tender-row");
        const changeRow = document.getElementById("rcpt-change-row");

        if (bill.payment_mode === "CASH" && bill.received_amount) {
            tenderRow.style.display = "flex";
            changeRow.style.display = "flex";
            document.getElementById("rcpt-tendered").textContent = formatMoney(bill.received_amount);
            document.getElementById("rcpt-change").textContent = formatMoney(bill.change_amount || 0);
        } else {
            tenderRow.style.display = "none";
            changeRow.style.display = "none";
        }

        document.getElementById("rcpt-barcode-text").textContent = bill.bill_number;
    }

    function openReceiptModal() {
        receiptModal.classList.add("active");
    }

    function closeReceiptModal() {
        receiptModal.classList.remove("active");
    }

    btnCloseReceipt.addEventListener("click", closeReceiptModal);
    btnDismissReceipt.addEventListener("click", closeReceiptModal);
    btnPrintReceipt.addEventListener("click", () => {
        window.print();
    });

    if (btnBtDirectPrint) {
        btnBtDirectPrint.addEventListener("click", async () => {
            if (!currentReceiptBill) {
                showToast("No active receipt data found.", "error");
                return;
            }
            if (!window.MitrayaBluetoothPrinter) {
                showToast("Bluetooth module not loaded.", "error");
                return;
            }
            if (!window.MitrayaBluetoothPrinter.isConnected()) {
                showToast("Connecting to Bluetooth Printer...", "info");
                try {
                    await window.MitrayaBluetoothPrinter.connect();
                } catch (e) {
                    if (e.name !== "NotFoundError") {
                        showToast("Could not connect to Bluetooth Printer.", "error");
                    }
                    return;
                }
            }
            try {
                btnBtDirectPrint.disabled = true;
                btnBtDirectPrint.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Printing...';
                await window.MitrayaBluetoothPrinter.printReceipt(currentReceiptBill);
                showToast("Printed via Bluetooth Thermal Printer!", "success");
            } catch (err) {
                showToast("Error printing to Bluetooth printer: " + err.message, "error");
            } finally {
                btnBtDirectPrint.disabled = false;
                btnBtDirectPrint.innerHTML = '<i class="fa-brands fa-bluetooth"></i> Print (BT)';
            }
        });
    }

    // Recent Bills Drawer & Reprint Logic
    async function loadRecentBills() {
        try {
            const res = await fetch("/api/pos/bills/recent?limit=30");
            const data = await res.json();

            if (res.ok && data.success) {
                recentBillsTbody.innerHTML = "";
                if (!data.bills || data.bills.length === 0) {
                    recentBillsTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:30px;">No POS bills created today yet.</td></tr>`;
                    return;
                }

                data.bills.forEach(b => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${b.bill_number}</strong></td>
                        <td>${b.created_at ? b.created_at.split(" ")[1] + " " + (b.created_at.split(" ")[2] || "") : "-"}</td>
                        <td>${b.items_count} items</td>
                        <td><span class="badge-tag ${b.payment_mode.toLowerCase()}">${b.payment_mode}</span></td>
                        <td><strong style="color:var(--accent-emerald); font-family:'JetBrains Mono'">${formatMoney(b.total_amount)}</strong></td>
                        <td>
                            <button type="button" class="nav-link-btn btn-reprint" data-bill-id="${b.id}" style="padding: 4px 10px; font-size: 11px;">
                                <i class="fa-solid fa-print"></i> Reprint
                            </button>
                        </td>
                    `;
                    tr.querySelector(".btn-reprint").addEventListener("click", async () => {
                        await reprintBill(b.id);
                    });
                    recentBillsTbody.appendChild(tr);
                });
            }
        } catch (err) {
            console.error("Error fetching recent bills:", err);
            showToast("Failed to fetch recent bills", "error");
        }
    }

    async function reprintBill(billId) {
        try {
            const res = await fetch(`/api/pos/bills/${billId}`);
            const data = await res.json();
            if (res.ok && data.success) {
                currentReceiptBill = data.bill;
                renderThermalReceipt(data.bill);
                closeRecentBillsModal();
                openReceiptModal();
            } else {
                showToast("Failed to load bill details", "error");
            }
        } catch (err) {
            showToast("Network error reprinting bill", "error");
        }
    }

    function openRecentBillsModal() {
        loadRecentBills();
        recentBillsModal.classList.add("active");
    }

    function closeRecentBillsModal() {
        recentBillsModal.classList.remove("active");
    }

    btnOpenRecent.addEventListener("click", openRecentBillsModal);
    btnCloseRecent.addEventListener("click", closeRecentBillsModal);
    btnCloseRecentFooter.addEventListener("click", closeRecentBillsModal);

    // Bluetooth Printer Manager Setup
    function initBluetoothPrinterUI() {
        if (!window.MitrayaBluetoothPrinter) return;

        const bt = window.MitrayaBluetoothPrinter;

        function updateBTUI(info) {
            if (info.connected) {
                if (btnBtPrinter) {
                    btnBtPrinter.className = "bt-status-btn connected";
                    if (btBtnLabel) btBtnLabel.textContent = `BT: ${info.deviceName || "Connected"}`;
                }
                if (btModalStatusDot) {
                    btModalStatusDot.className = "bt-status-dot connected";
                }
                if (btModalStatusText) {
                    btModalStatusText.textContent = "Connected & Ready";
                }
                if (btModalDeviceName) {
                    btModalDeviceName.textContent = info.deviceName || "Thermal Printer";
                }
                if (btnBtConnect) btnBtConnect.style.display = "none";
                if (btnBtDisconnect) btnBtDisconnect.style.display = "inline-flex";
            } else if (info.status === "connecting") {
                if (btnBtPrinter) {
                    btnBtPrinter.className = "bt-status-btn connecting";
                    if (btBtnLabel) btBtnLabel.textContent = "BT Connecting...";
                }
                if (btModalStatusDot) btModalStatusDot.className = "bt-status-dot connecting";
                if (btModalStatusText) btModalStatusText.textContent = "Pairing / Connecting...";
            } else {
                if (btnBtPrinter) {
                    btnBtPrinter.className = "bt-status-btn";
                    if (btBtnLabel) btBtnLabel.textContent = "BT Printer";
                }
                if (btModalStatusDot) btModalStatusDot.className = "bt-status-dot disconnected";
                if (btModalStatusText) btModalStatusText.textContent = "Disconnected";
                if (btModalDeviceName) btModalDeviceName.textContent = "No Printer Connected";
                if (btnBtConnect) btnBtConnect.style.display = "inline-flex";
                if (btnBtDisconnect) btnBtDisconnect.style.display = "none";
            }
        }

        bt.onStatusChange(updateBTUI);

        // Initial setup
        if (btAutoprintToggle) {
            btAutoprintToggle.checked = bt.isAutoPrintEnabled();
            btAutoprintToggle.addEventListener("change", () => {
                bt.setAutoPrintEnabled(btAutoprintToggle.checked);
                showToast(`Bluetooth Auto-print ${btAutoprintToggle.checked ? "Enabled" : "Disabled"}`);
            });
        }

        if (btPaperWidthSelect) {
            btPaperWidthSelect.value = bt.paperWidth.toString();
            btPaperWidthSelect.addEventListener("change", () => {
                bt.setPaperWidth(parseInt(btPaperWidthSelect.value, 10));
                showToast(`Paper width set to ${btPaperWidthSelect.value}mm`);
            });
        }

        if (btnBtPrinter && btPrinterModal) {
            btnBtPrinter.addEventListener("click", () => btPrinterModal.classList.add("active"));
        }
        if (btnCloseBtModal && btPrinterModal) {
            btnCloseBtModal.addEventListener("click", () => btPrinterModal.classList.remove("active"));
        }
        if (btnDismissBtModal && btPrinterModal) {
            btnDismissBtModal.addEventListener("click", () => btPrinterModal.classList.remove("active"));
        }

        if (btnBtConnect) {
            btnBtConnect.addEventListener("click", async () => {
                try {
                    await bt.connect();
                    showToast(`Connected to ${bt.getDeviceName() || "Bluetooth Printer"}!`, "success");
                } catch (err) {
                    if (err.name !== "NotFoundError") {
                        showToast(err.message || "Failed to connect Bluetooth printer", "error");
                    }
                }
            });
        }

        if (btnBtDisconnect) {
            btnBtDisconnect.addEventListener("click", async () => {
                await bt.disconnect();
                showToast("Bluetooth printer disconnected.");
            });
        }

        if (btnBtTestPrint) {
            btnBtTestPrint.addEventListener("click", async () => {
                if (!bt.isConnected()) {
                    showToast("Please connect to a Bluetooth printer first.", "error");
                    return;
                }
                try {
                    btnBtTestPrint.disabled = true;
                    btnBtTestPrint.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Printing Test...';
                    await bt.printTestReceipt();
                    showToast("Test receipt sent to printer!", "success");
                } catch (e) {
                    showToast("Test print failed: " + e.message, "error");
                } finally {
                    btnBtTestPrint.disabled = false;
                    btnBtTestPrint.innerHTML = '<i class="fa-solid fa-receipt"></i> Test Print';
                }
            });
        }
    }

    // Shortcuts Modal
    if (btnOpenShortcuts && shortcutsModal) {
        btnOpenShortcuts.addEventListener("click", () => shortcutsModal.classList.add("active"));
        btnCloseShortcuts.addEventListener("click", () => shortcutsModal.classList.remove("active"));
        btnDismissShortcuts.addEventListener("click", () => shortcutsModal.classList.remove("active"));
    }

    // Logout
    btnLogout.addEventListener("click", async () => {
        try {
            await fetch("/api/logout", { method: "POST" });
            window.location.href = "/login";
        } catch (e) {
            window.location.href = "/login";
        }
    });

    // Comprehensive Keyboard Shortcuts (Laptop / Desktop POS)
    document.addEventListener("keydown", (e) => {
        // F2 or '/' to focus search
        if (e.key === "F2" || (e.key === "/" && document.activeElement !== searchInput && document.activeElement !== cashReceivedInput && document.activeElement !== cartDiscountInput)) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
            return;
        }

        // F4 to focus Cash Tender
        if (e.key === "F4") {
            e.preventDefault();
            setPaymentMode("CASH");
            cashReceivedInput.focus();
            cashReceivedInput.select();
            return;
        }

        // F7 to focus Discount
        if (e.key === "F7" || (e.altKey && (e.key === "d" || e.key === "D"))) {
            e.preventDefault();
            cartDiscountInput.focus();
            cartDiscountInput.select();
            return;
        }

        // F8 to cycle payment modes
        if (e.key === "F8") {
            e.preventDefault();
            if (paymentMode === "CASH") setPaymentMode("UPI");
            else if (paymentMode === "UPI") setPaymentMode("CARD");
            else setPaymentMode("CASH");
            showToast(`Mode: ${paymentMode}`, "success");
            return;
        }

        // Alt + 1/2/3 for direct payment mode selection
        if (e.altKey && e.key === "1") {
            e.preventDefault();
            setPaymentMode("CASH");
            showToast("Mode: CASH", "success");
            return;
        }
        if (e.altKey && e.key === "2") {
            e.preventDefault();
            setPaymentMode("UPI");
            showToast("Mode: UPI", "success");
            return;
        }
        if (e.altKey && e.key === "3") {
            e.preventDefault();
            setPaymentMode("CARD");
            showToast("Mode: CARD", "success");
            return;
        }

        // Ctrl + Enter or F9 to Charge & Print
        if ((e.ctrlKey && e.key === "Enter") || e.key === "F9") {
            e.preventDefault();
            if (cart.length > 0) {
                submitOrder();
            } else {
                showToast("Cart is empty", "error");
            }
            return;
        }

        // F3 or Alt + R for Recent Bills
        if (e.key === "F3" || (e.altKey && (e.key === "r" || e.key === "R"))) {
            e.preventDefault();
            openRecentBillsModal();
            return;
        }

        // F10 to Clear Cart
        if (e.key === "F10") {
            e.preventDefault();
            clearCart();
            return;
        }

        // Escape closes all modals and mobile drawer
        if (e.key === "Escape") {
            closeReceiptModal();
            closeRecentBillsModal();
            if (shortcutsModal) shortcutsModal.classList.remove("active");
            if (cartPane) cartPane.classList.remove("mobile-open");
        }
    });

    // Mobile Sidebar Drawer Controls (for Admin)
    const adminSidebar = document.getElementById("admin-mobile-sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const btnSidebarToggle = document.getElementById("btn-sidebar-toggle");
    const btnSidebarClose = document.getElementById("btn-sidebar-close");
    const btnSidebarLogout = document.getElementById("btn-sidebar-logout");

    function openSidebar() {
        if (adminSidebar) adminSidebar.classList.add("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        if (adminSidebar) adminSidebar.classList.remove("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
        document.body.style.overflow = "";
    }

    if (btnSidebarToggle) btnSidebarToggle.addEventListener("click", openSidebar);
    if (btnSidebarClose) btnSidebarClose.addEventListener("click", closeSidebar);
    if (sidebarBackdrop) sidebarBackdrop.addEventListener("click", closeSidebar);

    if (btnSidebarLogout) {
        btnSidebarLogout.addEventListener("click", async () => {
            try {
                await fetch("/api/logout", { method: "POST" });
                window.location.href = "/login";
            } catch (e) {
                window.location.href = "/login";
            }
        });
    }

    // Initialize
    function init() {
        loadCatalog();
        updateCartUI();
        initBluetoothPrinterUI();
        loadTablesModalData();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();

