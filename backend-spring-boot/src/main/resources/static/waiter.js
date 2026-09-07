/**
 * Hotel Mitraya - Waiter Mobile POS & Ordering Client
 * ====================================================
 * Coordinates table selection, fast menu browsing, order placement,
 * active order editing (adding/removing items), and live table tracking.
 */

(function () {
    "use strict";

    // State
    let selectedTable = 1;
    let tablesData = [];
    let catalog = [];
    let allMenuItems = [];
    let cart = {}; // key: menu_item_id -> { item, quantity, notes }
    let editCart = []; // array of { menu_item_id, item_name, unit_price, quantity, item_notes }
    let activeCategory = "all";
    let activeOrders = [];
    let pollTimer = null;
    let currentEditTableNo = null;

    // DOM Elements
    const tablesGrid = document.getElementById("tables-grid-container");
    const selectedTableLabel = document.getElementById("selected-table-label");
    const searchInput = document.getElementById("menu-search-input");
    const categoriesPills = document.getElementById("categories-pill-container");
    const menuList = document.getElementById("menu-items-list");
    const floatingCartBar = document.getElementById("floating-cart-bar");
    const floatingCartTotal = document.getElementById("floating-cart-total");
    const floatingCartCount = document.getElementById("floating-cart-count");
    const btnOpenCartModal = document.getElementById("btn-open-cart-modal");
    const cartModalOverlay = document.getElementById("cart-modal-overlay");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const cartReviewList = document.getElementById("cart-items-review-list");
    const modalCartTotal = document.getElementById("modal-cart-total");
    const modalTableTitle = document.getElementById("modal-table-title");
    const orderCustomerNameInput = document.getElementById("order-customer-name");
    const btnConfirmSubmitOrder = document.getElementById("btn-confirm-submit-order");

    const activeTableContextBar = document.getElementById("active-table-context-bar");
    const ctxTableBadge = document.getElementById("ctx-table-badge");
    const btnCtxEditOrder = document.getElementById("btn-ctx-edit-order");

    // Edit Modal Elements
    const editModalOverlay = document.getElementById("edit-modal-overlay");
    const editModalTitle = document.getElementById("edit-modal-title");
    const btnCloseEditModal = document.getElementById("btn-close-edit-modal");
    const editItemsList = document.getElementById("edit-items-list");
    const editModalTotal = document.getElementById("edit-modal-total");
    const btnSaveOrderEdits = document.getElementById("btn-save-order-edits");
    const btnAddMoreToEdit = document.getElementById("btn-add-more-to-edit");

    // Navigation Tabs
    const btnTabMenu = document.getElementById("btn-tab-menu");
    const btnTabTracker = document.getElementById("btn-tab-tracker");
    const viewMenuSection = document.getElementById("view-menu-section");
    const viewTrackerSection = document.getElementById("view-tracker-section");
    const ordersFeedContainer = document.getElementById("orders-feed-container");
    const activeOrdersBadge = document.getElementById("active-orders-count-badge");
    const btnRefreshOrders = document.getElementById("btn-refresh-orders");

    // Initialize
    async function init() {
        setupEventListeners();
        await Promise.all([loadTables(), loadMenu()]);
        startLivePolling();
    }

    function setupEventListeners() {
        // Tab Switcher
        btnTabMenu.addEventListener("click", () => switchTab("menu"));
        btnTabTracker.addEventListener("click", () => switchTab("tracker"));

        // Search
        searchInput.addEventListener("input", () => renderMenuItems());

        // Create Order Modal Controls
        btnOpenCartModal.addEventListener("click", openCartModal);
        btnCloseModal.addEventListener("click", closeCartModal);
        cartModalOverlay.addEventListener("click", (e) => {
            if (e.target === cartModalOverlay) closeCartModal();
        });

        // Edit Order Modal Controls
        if (btnCloseEditModal) {
            btnCloseEditModal.addEventListener("click", closeEditModal);
        }
        if (editModalOverlay) {
            editModalOverlay.addEventListener("click", (e) => {
                if (e.target === editModalOverlay) closeEditModal();
            });
        }
        if (btnCtxEditOrder) {
            btnCtxEditOrder.addEventListener("click", () => openEditOrderForTable(selectedTable));
        }
        if (btnSaveOrderEdits) {
            btnSaveOrderEdits.addEventListener("click", saveOrderEdits);
        }
        if (btnAddMoreToEdit) {
            btnAddMoreToEdit.addEventListener("click", () => {
                closeEditModal();
                switchTab("menu");
            });
        }

        // Submit New Order
        btnConfirmSubmitOrder.addEventListener("click", submitOrder);

        // Refresh Orders
        if (btnRefreshOrders) {
            btnRefreshOrders.addEventListener("click", () => {
                loadTables();
                loadMyActiveOrders();
            });
        }
    }

    function switchTab(tab) {
        if (tab === "menu") {
            btnTabMenu.classList.add("active");
            btnTabTracker.classList.remove("active");
            viewMenuSection.style.display = "block";
            viewTrackerSection.style.display = "none";
            updateFloatingCart();
        } else {
            btnTabTracker.classList.add("active");
            btnTabMenu.classList.remove("active");
            viewMenuSection.style.display = "none";
            viewTrackerSection.style.display = "block";
            floatingCartBar.style.display = "none";
            loadMyActiveOrders();
        }
    }

    // 1. Fetch & Render Tables
    async function loadTables() {
        try {
            const res = await fetch("/api/waiter/tables");
            const data = await res.json();
            if (data.success && data.tables) {
                tablesData = data.tables;
                renderTables(data.tables);
                updateTableContext();
                if (activeOrdersBadge) {
                    activeOrdersBadge.textContent = data.occupied_count || 0;
                    activeOrdersBadge.style.display = (data.occupied_count > 0) ? "inline-block" : "none";
                }
            }
        } catch (e) {
            console.error("Error loading tables:", e);
        }
    }

    function renderTables(tables) {
        tablesGrid.innerHTML = "";
        tables.forEach(t => {
            const isOccupied = t.status === "OCCUPIED";
            const isSelected = t.table_number === selectedTable;
            const chip = document.createElement("div");
            chip.className = `table-chip ${isOccupied ? "occupied" : ""} ${isSelected ? "selected" : ""}`;
            chip.innerHTML = `
                <span class="t-no">T-${t.table_number}</span>
                <span class="t-status">${isOccupied ? "Active" : "Vacant"}</span>
            `;
            chip.addEventListener("click", () => {
                selectTable(t.table_number);
            });
            tablesGrid.appendChild(chip);
        });
        updateTableLabel();
    }

    function selectTable(tableNo) {
        selectedTable = tableNo;
        document.querySelectorAll(".table-chip").forEach(el => el.classList.remove("selected"));
        const chips = document.querySelectorAll(".table-chip");
        if (chips[tableNo - 1]) {
            chips[tableNo - 1].classList.add("selected");
        }
        updateTableLabel();
        updateTableContext();
        if (navigator.vibrate) navigator.vibrate(20);
    }

    function updateTableLabel() {
        if (selectedTableLabel) {
            selectedTableLabel.textContent = `Table: T-${selectedTable}`;
        }
        if (modalTableTitle) {
            modalTableTitle.innerHTML = `<i class="fa-solid fa-chair"></i> Order for Table ${selectedTable}`;
        }
    }

    function updateTableContext() {
        const tableObj = tablesData.find(t => t.table_number === selectedTable);
        if (tableObj && tableObj.status === "OCCUPIED" && activeTableContextBar) {
            ctxTableBadge.textContent = `Table ${selectedTable}`;
            activeTableContextBar.style.display = "flex";
        } else if (activeTableContextBar) {
            activeTableContextBar.style.display = "none";
        }
    }

    // 2. Fetch & Render Menu Catalog
    async function loadMenu() {
        try {
            const res = await fetch("/api/waiter/menu");
            const data = await res.json();
            if (data.success && data.categories) {
                catalog = data.categories;
                allMenuItems = [];
                catalog.forEach(cat => {
                    (cat.items || []).forEach(itm => {
                        allMenuItems.push({ ...itm, category_name: cat.name });
                    });
                });
                renderCategoryPills();
                renderMenuItems();
            }
        } catch (e) {
            console.error("Error loading menu:", e);
        }
    }

    function renderCategoryPills() {
        categoriesPills.innerHTML = '<button type="button" class="cat-pill active" data-cat-id="all">All Dishes</button>';
        catalog.forEach(cat => {
            const pill = document.createElement("button");
            pill.type = "button";
            pill.className = "cat-pill";
            pill.setAttribute("data-cat-id", cat.id);
            pill.textContent = cat.name;
            pill.addEventListener("click", () => {
                document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                activeCategory = cat.id.toString();
                renderMenuItems();
            });
            categoriesPills.appendChild(pill);
        });

        categoriesPills.querySelector('[data-cat-id="all"]').addEventListener("click", (e) => {
            document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
            e.currentTarget.classList.add("active");
            activeCategory = "all";
            renderMenuItems();
        });
    }

    function renderMenuItems() {
        const query = (searchInput.value || "").trim().toLowerCase();
        menuList.innerHTML = "";

        let filtered = allMenuItems;

        if (activeCategory !== "all") {
            filtered = filtered.filter(i => (i.category_id || 0).toString() === activeCategory);
        }

        if (query) {
            filtered = filtered.filter(i =>
                i.name.toLowerCase().includes(query) ||
                (i.code && i.code.toLowerCase().includes(query)) ||
                (i.category_name && i.category_name.toLowerCase().includes(query))
            );
        }

        if (filtered.length === 0) {
            menuList.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-bowl-rice"></i>
                    <p>No dishes found for "${query}"</p>
                </div>
            `;
            return;
        }

        filtered.forEach(item => {
            const currentQty = cart[item.id] ? cart[item.id].quantity : 0;
            const card = document.createElement("div");
            card.className = "menu-card";
            card.innerHTML = `
                <div class="item-info">
                    <div class="item-name">${item.name}</div>
                    <div class="item-meta">
                        <span class="item-price">Rs.${Number(item.price).toFixed(2)}</span>
                        ${item.code ? `<span class="item-code">${item.code}</span>` : ""}
                    </div>
                </div>
                <div class="item-actions" id="action-box-${item.id}">
                    ${renderQtyControl(item, currentQty)}
                </div>
            `;
            menuList.appendChild(card);
        });

        attachQtyListeners();
    }

    function renderQtyControl(item, qty) {
        if (qty === 0) {
            return `<button type="button" class="btn-qty btn-add-initial" data-item-id="${item.id}"><i class="fa-solid fa-plus"></i> Add</button>`;
        }
        return `
            <div class="qty-control">
                <button type="button" class="btn-qty btn-minus" data-item-id="${item.id}">-</button>
                <span class="qty-val">${qty}</span>
                <button type="button" class="btn-qty btn-plus" data-item-id="${item.id}">+</button>
            </div>
        `;
    }

    function attachQtyListeners() {
        document.querySelectorAll(".btn-add-initial").forEach(btn => {
            btn.addEventListener("click", () => {
                const itemId = parseInt(btn.getAttribute("data-item-id"), 10);
                const item = allMenuItems.find(i => i.id === itemId);
                if (item) {
                    cart[itemId] = { item, quantity: 1, notes: "" };
                    updateItemUI(itemId);
                    updateFloatingCart();
                }
            });
        });

        document.querySelectorAll(".btn-plus").forEach(btn => {
            btn.addEventListener("click", () => {
                const itemId = parseInt(btn.getAttribute("data-item-id"), 10);
                if (cart[itemId]) {
                    cart[itemId].quantity += 1;
                    updateItemUI(itemId);
                    updateFloatingCart();
                }
            });
        });

        document.querySelectorAll(".btn-minus").forEach(btn => {
            btn.addEventListener("click", () => {
                const itemId = parseInt(btn.getAttribute("data-item-id"), 10);
                if (cart[itemId]) {
                    cart[itemId].quantity -= 1;
                    if (cart[itemId].quantity <= 0) {
                        delete cart[itemId];
                    }
                    updateItemUI(itemId);
                    updateFloatingCart();
                }
            });
        });
    }

    function updateItemUI(itemId) {
        const box = document.getElementById(`action-box-${itemId}`);
        const item = allMenuItems.find(i => i.id === itemId);
        if (box && item) {
            const currentQty = cart[itemId] ? cart[itemId].quantity : 0;
            box.innerHTML = renderQtyControl(item, currentQty);
            attachQtyListeners();
        }
    }

    // 3. Floating Cart & Create Order Modal
    function updateFloatingCart() {
        const itemIds = Object.keys(cart);
        let totalQty = 0;
        let totalAmount = 0.0;

        itemIds.forEach(id => {
            const entry = cart[id];
            totalQty += entry.quantity;
            totalAmount += entry.quantity * entry.item.price;
        });

        if (totalQty > 0 && viewMenuSection.style.display !== "none") {
            floatingCartTotal.textContent = `Rs.${totalAmount.toFixed(2)}`;
            floatingCartCount.textContent = `${totalQty} item${totalQty > 1 ? "s" : ""} for Table ${selectedTable}`;
            floatingCartBar.style.display = "flex";
        } else {
            floatingCartBar.style.display = "none";
        }
    }

    function openCartModal() {
        const itemIds = Object.keys(cart);
        if (itemIds.length === 0) return;

        cartReviewList.innerHTML = "";
        let totalAmount = 0.0;

        itemIds.forEach(id => {
            const entry = cart[id];
            const lineTotal = entry.quantity * entry.item.price;
            totalAmount += lineTotal;

            const row = document.createElement("div");
            row.className = "cart-item-row";
            row.innerHTML = `
                <div class="cart-item-main">
                    <div>
                        <div style="font-size:14px; font-weight:800; color:var(--text-main);">${entry.item.name}</div>
                        <div style="font-size:12px; color:var(--text-muted); font-family:'JetBrains Mono',monospace;">
                            ${entry.quantity} x Rs.${entry.item.price.toFixed(0)} = Rs.${lineTotal.toFixed(2)}
                        </div>
                    </div>
                    <div class="qty-control">
                        <button type="button" class="btn-qty modal-minus" data-id="${id}">-</button>
                        <span class="qty-val">${entry.quantity}</span>
                        <button type="button" class="btn-qty modal-plus" data-id="${id}">+</button>
                    </div>
                </div>
                <input type="text" class="item-notes-input" placeholder="Cooking note (e.g. Less spicy, Extra crispy)..." value="${entry.notes || ""}" data-id="${id}">
            `;
            cartReviewList.appendChild(row);
        });

        cartReviewList.querySelectorAll(".item-notes-input").forEach(input => {
            input.addEventListener("input", (e) => {
                const id = e.target.getAttribute("data-id");
                if (cart[id]) {
                    cart[id].notes = e.target.value.trim();
                }
            });
        });

        cartReviewList.querySelectorAll(".modal-plus").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                if (cart[id]) {
                    cart[id].quantity += 1;
                    openCartModal();
                    updateItemUI(parseInt(id, 10));
                    updateFloatingCart();
                }
            });
        });

        cartReviewList.querySelectorAll(".modal-minus").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                if (cart[id]) {
                    cart[id].quantity -= 1;
                    if (cart[id].quantity <= 0) {
                        delete cart[id];
                    }
                    if (Object.keys(cart).length === 0) {
                        closeCartModal();
                    } else {
                        openCartModal();
                    }
                    updateItemUI(parseInt(id, 10));
                    updateFloatingCart();
                }
            });
        });

        modalCartTotal.textContent = `Rs.${totalAmount.toFixed(2)}`;
        cartModalOverlay.style.display = "flex";
    }

    function closeCartModal() {
        cartModalOverlay.style.display = "none";
    }

    // 4. Submit New Order
    async function submitOrder() {
        const itemIds = Object.keys(cart);
        if (itemIds.length === 0) return;

        btnConfirmSubmitOrder.disabled = true;
        btnConfirmSubmitOrder.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending to Kitchen...';

        const orderItemsPayload = itemIds.map(id => ({
            menu_item_id: parseInt(id, 10),
            name: cart[id].item.name,
            unit_price: cart[id].item.price,
            quantity: cart[id].quantity,
            item_notes: cart[id].notes || ""
        }));

        const payload = {
            table_number: selectedTable,
            order_type: "DINING",
            customer_name: (orderCustomerNameInput.value || "").trim(),
            source: "WAITER",
            items: orderItemsPayload
        };

        try {
            const res = await fetch("/api/orders", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (res.ok && data.success) {
                cart = {};
                orderCustomerNameInput.value = "";
                closeCartModal();
                renderMenuItems();
                updateFloatingCart();
                await loadTables();
                switchTab("tracker");
                alert(`Order for Table ${selectedTable} has been sent to Counter & Kitchen!`);
            } else {
                alert(data.error || "Failed to submit order. Please try again.");
            }
        } catch (err) {
            alert("Network error while submitting order.");
        } finally {
            btnConfirmSubmitOrder.disabled = false;
            btnConfirmSubmitOrder.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Order to Kitchen';
        }
    }

    // 5. Edit Active Order Workflow (Add / Remove items)
    async function openEditOrderForTable(tableNo) {
        currentEditTableNo = tableNo;
        try {
            const res = await fetch(`/api/waiter/tables/${tableNo}/order`);
            const data = await res.json();

            if (data.success && data.order) {
                const ord = data.order;
                editCart = (ord.items || []).map(itm => ({
                    menu_item_id: itm.menu_item_id,
                    name: itm.item_name,
                    unit_price: itm.unit_price,
                    quantity: itm.quantity,
                    item_notes: itm.item_notes || ""
                }));

                // Also merge any items currently staged in local cart
                Object.keys(cart).forEach(id => {
                    const cItm = cart[id];
                    const existing = editCart.find(e => e.menu_item_id === parseInt(id, 10));
                    if (existing) {
                        existing.quantity += cItm.quantity;
                    } else {
                        editCart.push({
                            menu_item_id: parseInt(id, 10),
                            name: cItm.item.name,
                            unit_price: cItm.item.price,
                            quantity: cItm.quantity,
                            item_notes: cItm.notes || ""
                        });
                    }
                });

                renderEditOrderModal(ord);
            } else {
                alert(`No active order found on Table ${tableNo}`);
            }
        } catch (e) {
            console.error("Error opening edit modal:", e);
            alert("Could not load table order for editing.");
        }
    }

    function renderEditOrderModal(order) {
        if (!editModalOverlay) return;

        editModalTitle.innerHTML = `<i class="fa-solid fa-pen-to-square"></i> Edit Table ${order.table_number || currentEditTableNo}`;
        editItemsList.innerHTML = "";

        if (editCart.length === 0) {
            editItemsList.innerHTML = `
                <div class="empty-state" style="padding: 20px;">
                    <p style="color:var(--brand-crimson); font-weight:700;">No items remaining! Saving will cancel this order.</p>
                </div>
            `;
            editModalTotal.textContent = "Rs.0.00";
            editModalOverlay.style.display = "flex";
            return;
        }

        let totalAmount = 0.0;

        editCart.forEach((entry, idx) => {
            const lineTotal = entry.quantity * entry.unit_price;
            totalAmount += lineTotal;

            const row = document.createElement("div");
            row.className = "cart-item-row";
            row.innerHTML = `
                <div class="cart-item-main">
                    <div>
                        <div style="font-size:14px; font-weight:800; color:var(--text-main);">${entry.name}</div>
                        <div style="font-size:12px; color:var(--text-muted); font-family:'JetBrains Mono',monospace;">
                            ${entry.quantity} x Rs.${entry.unit_price.toFixed(0)} = Rs.${lineTotal.toFixed(2)}
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div class="qty-control">
                            <button type="button" class="btn-qty edit-minus" data-idx="${idx}">-</button>
                            <span class="qty-val">${entry.quantity}</span>
                            <button type="button" class="btn-qty edit-plus" data-idx="${idx}">+</button>
                        </div>
                        <button type="button" class="btn-qty edit-delete" data-idx="${idx}" style="background:#fee2e2; color:var(--brand-crimson); border-radius:6px;" title="Remove dish">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
                <input type="text" class="item-notes-input edit-note-input" placeholder="Cooking note..." value="${entry.item_notes || ""}" data-idx="${idx}">
            `;
            editItemsList.appendChild(row);
        });

        // Notes change
        editItemsList.querySelectorAll(".edit-note-input").forEach(input => {
            input.addEventListener("input", (e) => {
                const idx = parseInt(e.target.getAttribute("data-idx"), 10);
                if (editCart[idx]) {
                    editCart[idx].item_notes = e.target.value.trim();
                }
            });
        });

        // Plus
        editItemsList.querySelectorAll(".edit-plus").forEach(btn => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.getAttribute("data-idx"), 10);
                if (editCart[idx]) {
                    editCart[idx].quantity += 1;
                    renderEditOrderModal(order);
                }
            });
        });

        // Minus
        editItemsList.querySelectorAll(".edit-minus").forEach(btn => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.getAttribute("data-idx"), 10);
                if (editCart[idx]) {
                    editCart[idx].quantity -= 1;
                    if (editCart[idx].quantity <= 0) {
                        editCart.splice(idx, 1);
                    }
                    renderEditOrderModal(order);
                }
            });
        });

        // Delete
        editItemsList.querySelectorAll(".edit-delete").forEach(btn => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.getAttribute("data-idx"), 10);
                if (editCart[idx]) {
                    editCart.splice(idx, 1);
                    renderEditOrderModal(order);
                }
            });
        });

        editModalTotal.textContent = `Rs.${totalAmount.toFixed(2)}`;
        editModalOverlay.style.display = "flex";
    }

    function closeEditModal() {
        if (editModalOverlay) {
            editModalOverlay.style.display = "none";
        }
    }

    async function saveOrderEdits() {
        if (!currentEditTableNo) return;

        btnSaveOrderEdits.disabled = true;
        btnSaveOrderEdits.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

        const payload = {
            items: editCart.map(e => ({
                menu_item_id: e.menu_item_id,
                name: e.name,
                unit_price: e.unit_price,
                quantity: e.quantity,
                item_notes: e.item_notes || ""
            }))
        };

        try {
            const res = await fetch(`/api/waiter/tables/${currentEditTableNo}/order`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (res.ok && data.success) {
                cart = {}; // Clear any staged items
                closeEditModal();
                renderMenuItems();
                updateFloatingCart();
                await loadTables();
                switchTab("tracker");
                alert(data.message || `Table ${currentEditTableNo} order updated!`);
            } else {
                alert(data.error || "Failed to update order.");
            }
        } catch (e) {
            alert("Network error while saving edits.");
        } finally {
            btnSaveOrderEdits.disabled = false;
            btnSaveOrderEdits.innerHTML = '<i class="fa-solid fa-check"></i> Save Changes to Order';
        }
    }

    // 6. Active Orders Tracker Feed
    async function loadMyActiveOrders() {
        try {
            const res = await fetch("/api/waiter/orders/my-active");
            const data = await res.json();
            if (data.success && data.orders) {
                activeOrders = data.orders;
                renderOrdersFeed(activeOrders);
                if (activeOrdersBadge) {
                    activeOrdersBadge.textContent = activeOrders.length;
                    activeOrdersBadge.style.display = activeOrders.length > 0 ? "inline-block" : "none";
                }
            }
        } catch (e) {
            console.error("Error loading active orders:", e);
        }
    }

    function renderOrdersFeed(orders) {
        ordersFeedContainer.innerHTML = "";
        if (orders.length === 0) {
            ordersFeedContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-clipboard-check"></i>
                    <p>No active dining tables at the moment.</p>
                </div>
            `;
            return;
        }

        orders.forEach(ord => {
            const card = document.createElement("div");
            card.className = "order-card";
            const itemsText = (ord.items || []).map(i => `${i.quantity}x ${i.item_name}${i.item_notes ? ` (${i.item_notes})` : ""}`).join(", ");

            card.innerHTML = `
                <div class="order-card-header">
                    <div>
                        <span class="order-id-tag">#${ord.order_number}</span>
                        <span style="font-size:13px; font-weight:800; color:var(--brand-blue); margin-left:8px;">${ord.table_label}</span>
                    </div>
                    <button type="button" class="btn-edit-active-order btn-feed-edit" data-table="${ord.table_number}">
                        <i class="fa-solid fa-pen-to-square"></i> Edit Dishes
                    </button>
                </div>
                <div class="order-card-items">
                    <strong>Dishes:</strong> ${itemsText || "No items"}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--text-muted); border-top:1px solid var(--border-light); padding-top:8px;">
                    <span><i class="fa-regular fa-clock"></i> Placed: ${ord.created_at_time || "Now"}</span>
                    <strong style="color:var(--brand-navy); font-family:'JetBrains Mono',monospace; font-size:14px;">Rs.${Number(ord.total_amount).toFixed(2)}</strong>
                </div>
            `;
            ordersFeedContainer.appendChild(card);
        });

        ordersFeedContainer.querySelectorAll(".btn-feed-edit").forEach(btn => {
            btn.addEventListener("click", () => {
                const tableNo = parseInt(btn.getAttribute("data-table"), 10);
                if (tableNo) openEditOrderForTable(tableNo);
            });
        });
    }

    // 7. Live Polling Loop
    function startLivePolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async () => {
            await loadTables();
            if (viewTrackerSection && viewTrackerSection.style.display !== "none") {
                await loadMyActiveOrders();
            }
        }, 3500);
    }

    // Bootstrap
    window.addEventListener("DOMContentLoaded", init);

})();
