/**
 * HOTEL MITRAYA — SMART BILL GENERATOR FRONTEND CONTROLLER
 * Responsive, Mobile-first Web Application for PDF Bill Generation & Management
 */

(function () {
    "use strict";

    // ─── State Management ──────────────────────────────────────────────────
    const state = {
        items: [
            { id: 1, name: "Dahi Dhapata & Biryani plate", qty: 150, rate: 130 }
        ],
        nextItemId: 2,
        currentGeneratedBill: null,
        presets: [
            { name: "Dahi Dhapata & Biryani plate", rate: 130 },
            { name: "Special Veg Thali", rate: 160 },
            { name: "Chicken Biryani Plate", rate: 180 },
            { name: "Paneer Butter Masala", rate: 150 },
            { name: "Butter Roti", rate: 20 },
            { name: "Mineral Water Bottle (1L)", rate: 20 },
            { name: "Cold Drink (Can)", rate: 40 },
            { name: "Special Tea / Coffee", rate: 25 },
        ]
    };

    // ─── DOM References ────────────────────────────────────────────────────
    const elements = {
        // Form inputs
        customerName: document.getElementById("customer_name"),
        billNo: document.getElementById("bill_no"),
        billDate: document.getElementById("bill_date"),
        createdOn: document.getElementById("created_on"),
        discount: document.getElementById("discount"),
        txnMode: document.getElementById("txn_mode"),
        receivedAmount: document.getElementById("received_amount"),
        itemsContainer: document.getElementById("items-container"),
        itemsCounter: document.getElementById("items-counter"),

        // Action buttons
        btnAutoBillNo: document.getElementById("btn-auto-bill-no"),
        btnSetToday: document.getElementById("btn-set-today"),
        btnSetNow: document.getElementById("btn-set-now"),
        btnAddItem: document.getElementById("btn-add-item"),
        btnAddItemBottom: document.getElementById("btn-add-item-bottom"),
        btnQuickPresets: document.getElementById("btn-quick-presets"),
        quickPresetsBox: document.getElementById("quick-presets-box"),
        presetTagsContainer: document.getElementById("preset-tags-container"),
        btnResetForm: document.getElementById("btn-reset-form"),
        btnGenerateBill: document.getElementById("btn-generate-bill"),
        btnGenerateBillSidebar: document.getElementById("btn-generate-bill-sidebar"),
        btnGenerateBillMobile: document.getElementById("btn-generate-bill-mobile"),

        // Live preview elements
        previewCustomer: document.getElementById("preview-customer"),
        previewBillNo: document.getElementById("preview-billno"),
        previewDate: document.getElementById("preview-date"),
        previewItemsList: document.getElementById("preview-items-list"),
        previewSubtotal: document.getElementById("preview-subtotal"),
        previewDiscount: document.getElementById("preview-discount"),
        previewGrandtotal: document.getElementById("preview-grandtotal"),
        previewReceived: document.getElementById("preview-received"),
        previewAmountWords: document.getElementById("preview-amount-words"),
        mobileGrandTotal: document.getElementById("mobile-grand-total"),

        // Modals & Drawers
        modalSuccess: document.getElementById("modal-success"),
        btnCloseSuccessModal: document.getElementById("btn-close-success-modal"),
        btnNewBillAfterSuccess: document.getElementById("btn-new-bill-after-success"),
        successBillTitle: document.getElementById("success-bill-title"),
        successBillPath: document.getElementById("success-bill-path"),
        successBillSize: document.getElementById("success-bill-size"),
        successBillTime: document.getElementById("success-bill-time"),
        pdfPreviewFrame: document.getElementById("pdf-preview-frame"),
        btnDownloadPdf: document.getElementById("btn-download-pdf"),
        btnViewPdf: document.getElementById("btn-view-pdf"),
        btnShareBill: document.getElementById("btn-share-bill"),

        drawerHistory: document.getElementById("drawer-history"),
        btnOpenHistory: document.getElementById("btn-open-history"),
        btnCloseHistory: document.getElementById("btn-close-history"),
        historySearchInput: document.getElementById("history-search-input"),
        btnRefreshHistory: document.getElementById("btn-refresh-history"),
        historyListContainer: document.getElementById("history-list-container"),
        billsCountBadge: document.getElementById("bills-count-badge"),

        // Theme, Auth & Overlays
        btnThemeToggle: document.getElementById("btn-theme-toggle"),
        btnLogout: document.getElementById("btn-logout"),
        loadingOverlay: document.getElementById("loading-overlay"),
        toastContainer: document.getElementById("toast-container")
    };

    // ─── Helpers: Date & Time ──────────────────────────────────────────────
    function getFormattedToday() {
        const now = new Date();
        const dd = String(now.getDate()).padStart(2, "0");
        const mm = String(now.getMonth() + 1).padStart(2, "0");
        const yyyy = now.getFullYear();
        return `${dd}/${mm}/${yyyy}`;
    }

    function getFormattedNow() {
        const now = new Date();
        const dateStr = getFormattedToday();
        let hours = now.getHours();
        const minutes = String(now.getMinutes()).padStart(2, "0");
        const ampm = hours >= 12 ? "PM" : "AM";
        hours = hours % 12;
        hours = hours ? hours : 12;
        const hrStr = String(hours).padStart(2, "0");
        return `${dateStr} ${hrStr}:${minutes} ${ampm}`;
    }

    // ─── Helpers: Currency in Words (Indian System) ─────────────────────────
    function numberToWordsINR(amount) {
        const num = Math.floor(Math.abs(Number(amount) || 0));
        const paise = Math.round((Math.abs(Number(amount) || 0) - num) * 100);

        if (num === 0 && paise === 0) return "Rupees Zero Only";

        const units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
        const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

        function convertBelowThousand(n) {
            let str = "";
            if (n >= 100) {
                str += units[Math.floor(n / 100)] + " Hundred ";
                n %= 100;
            }
            if (n >= 20) {
                str += tens[Math.floor(n / 10)] + " ";
                n %= 10;
            }
            if (n > 0) {
                str += units[n] + " ";
            }
            return str.trim();
        }

        let words = "";
        let crore = Math.floor(num / 10000000);
        let remainder = num % 10000000;
        let lakh = Math.floor(remainder / 100000);
        remainder = remainder % 100000;
        let thousand = Math.floor(remainder / 1000);
        let hundredAndBelow = remainder % 1000;

        if (crore > 0) words += convertBelowThousand(crore) + " Crore ";
        if (lakh > 0) words += convertBelowThousand(lakh) + " Lakh ";
        if (thousand > 0) words += convertBelowThousand(thousand) + " Thousand ";
        if (hundredAndBelow > 0) words += convertBelowThousand(hundredAndBelow) + " ";

        words = words.trim();
        let result = words ? `Rupees ${words}` : "Rupees Zero";

        if (paise > 0) {
            result += ` And ${convertBelowThousand(paise)} Paise`;
        }

        return result + " Only";
    }

    function formatINR(val) {
        const n = Number(val) || 0;
        return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // ─── Toast Alerts ──────────────────────────────────────────────────────
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-circle-exclamation";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(20px)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // ─── Theme Toggle ──────────────────────────────────────────────────────
    function initTheme() {
        const saved = localStorage.getItem("hm_theme") || "light";
        document.documentElement.setAttribute("data-theme", saved);
        updateThemeIcon(saved);

        elements.btnThemeToggle.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", next);
            localStorage.setItem("hm_theme", next);
            updateThemeIcon(next);
        });
    }

    function updateThemeIcon(theme) {
        const icon = elements.btnThemeToggle.querySelector("i");
        if (theme === "dark") {
            icon.className = "fa-solid fa-sun";
            elements.btnThemeToggle.title = "Switch to Light Mode";
        } else {
            icon.className = "fa-solid fa-moon";
            elements.btnThemeToggle.title = "Switch to Dark Mode";
        }
    }

    // ─── Presets Rendering ─────────────────────────────────────────────────
    function initPresets() {
        elements.presetTagsContainer.innerHTML = "";
        state.presets.forEach(p => {
            const tag = document.createElement("button");
            tag.type = "button";
            tag.className = "preset-tag";
            tag.innerHTML = `<span>${p.name}</span><span class="preset-price">₹${p.rate}</span>`;
            tag.addEventListener("click", () => {
                addItem(p.name, 1, p.rate);
                showToast(`Added '${p.name}' to bill`, "info");
            });
            elements.presetTagsContainer.appendChild(tag);
        });

        elements.btnQuickPresets.addEventListener("click", () => {
            elements.quickPresetsBox.classList.toggle("hidden");
        });
    }

    // ─── Item List Management ──────────────────────────────────────────────
    function renderItems() {
        elements.itemsContainer.innerHTML = "";
        state.items.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "item-row";
            row.dataset.id = item.id;

            const total = (Number(item.qty) || 0) * (Number(item.rate) || 0);

            row.innerHTML = `
                <div class="item-index-badge">${index + 1}</div>
                
                <input type="text" class="form-control item-input-name" 
                       placeholder="Item description" value="${item.name || ''}" 
                       data-field="name" autocomplete="off" required>
                
                <input type="number" step="any" min="0" class="form-control item-input-qty font-mono" 
                       placeholder="Qty" value="${item.qty !== undefined ? item.qty : 1}" 
                       data-field="qty" required>
                
                <input type="number" step="any" min="0" class="form-control item-input-rate font-mono" 
                       placeholder="Rate" value="${item.rate !== undefined ? item.rate : 0}" 
                       data-field="rate" required>
                
                <div class="item-total-badge">${formatINR(total)}</div>
                
                <button type="button" class="btn-item-delete" title="Remove item">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;

            // Row input event listeners
            row.querySelectorAll("input").forEach(input => {
                input.addEventListener("input", (e) => {
                    const field = e.target.dataset.field;
                    item[field] = e.target.value;
                    
                    if (field === "qty" || field === "rate") {
                        const newTotal = (Number(item.qty) || 0) * (Number(item.rate) || 0);
                        row.querySelector(".item-total-badge").textContent = formatINR(newTotal);
                    }
                    updateCalculations();
                });
            });

            // Row delete button
            row.querySelector(".btn-item-delete").addEventListener("click", () => {
                if (state.items.length <= 1) {
                    showToast("Bill must have at least one item", "error");
                    return;
                }
                state.items = state.items.filter(i => i.id !== item.id);
                renderItems();
                updateCalculations();
            });

            elements.itemsContainer.appendChild(row);
        });

        elements.itemsCounter.textContent = `${state.items.length} ${state.items.length === 1 ? "Item" : "Items"}`;
        updateCalculations();
    }

    function addItem(name = "", qty = 1, rate = 0) {
        state.items.push({
            id: state.nextItemId++,
            name: name,
            qty: qty,
            rate: rate
        });
        renderItems();
        // Focus name on new row
        const rows = elements.itemsContainer.querySelectorAll(".item-row");
        const lastRow = rows[rows.length - 1];
        if (lastRow && !name) {
            lastRow.querySelector(".item-input-name").focus();
        }
    }

    // ─── Live Calculations & Real-Time Preview ──────────────────────────────
    function updateCalculations() {
        let subtotal = 0;
        state.items.forEach(i => {
            const q = Number(i.qty) || 0;
            const r = Number(i.rate) || 0;
            subtotal += (q * r);
        });

        const discount = Number(elements.discount.value) || 0;
        const grandTotal = Math.max(0, subtotal - discount);

        const recVal = elements.receivedAmount.value.trim();
        const received = recVal !== "" ? Number(recVal) || 0 : grandTotal;

        // Update live receipt values
        elements.previewCustomer.textContent = elements.customerName.value.trim() || "—";
        elements.previewBillNo.textContent = elements.billNo.value.trim() || "—";
        elements.previewDate.textContent = elements.billDate.value.trim() || getFormattedToday();

        elements.previewSubtotal.textContent = formatINR(subtotal);
        elements.previewDiscount.textContent = "-" + formatINR(discount);
        elements.previewGrandtotal.textContent = formatINR(grandTotal);
        elements.previewReceived.textContent = formatINR(received);
        elements.previewAmountWords.textContent = numberToWordsINR(grandTotal);
        elements.mobileGrandTotal.textContent = formatINR(grandTotal);

        // Update live items summary in receipt card
        elements.previewItemsList.innerHTML = "";
        state.items.forEach(i => {
            const q = Number(i.qty) || 0;
            const r = Number(i.rate) || 0;
            const t = q * r;
            const line = document.createElement("div");
            line.className = "receipt-item-line";
            line.innerHTML = `
                <span class="receipt-item-desc">${i.name || "Item"} (x${q})</span>
                <span class="receipt-item-amt">${formatINR(t)}</span>
            `;
            elements.previewItemsList.appendChild(line);
        });
    }

    // ─── Auto Next Bill Number ─────────────────────────────────────────────
    async function fetchNextBillNo() {
        try {
            const res = await fetch("/api/next-bill-no");
            const data = await res.json();
            if (data.success && data.next_bill_no) {
                elements.billNo.value = data.next_bill_no;
                updateCalculations();
            }
        } catch (e) {
            console.error("Error fetching next bill no:", e);
        }
    }

    // ─── Generate Bill (POST /api/bills/generate) ───────────────────────────
    async function handleGenerateBill() {
        const customerName = elements.customerName.value.trim();
        const billNo = elements.billNo.value.trim();
        const billDate = elements.billDate.value.trim() || getFormattedToday();
        const createdOn = elements.createdOn.value.trim() || getFormattedNow();
        const discount = Number(elements.discount.value) || 0;
        const txnMode = elements.txnMode.value;
        const receivedRaw = elements.receivedAmount.value.trim();
        const receivedAmount = receivedRaw !== "" ? Number(receivedRaw) : null;

        // Validation
        if (!customerName) {
            showToast("Please enter Customer / Company Name", "error");
            elements.customerName.focus();
            return;
        }
        if (!billNo) {
            showToast("Please enter Bill Number", "error");
            elements.billNo.focus();
            return;
        }

        const validItems = [];
        for (let i = 0; i < state.items.length; i++) {
            const itm = state.items[i];
            const name = (itm.name || "").trim();
            const qty = Number(itm.qty);
            const rate = Number(itm.rate);
            if (!name) {
                showToast(`Item #${i + 1} description is empty`, "error");
                return;
            }
            if (isNaN(qty) || qty <= 0) {
                showToast(`Item '${name}' has invalid quantity`, "error");
                return;
            }
            if (isNaN(rate) || rate < 0) {
                showToast(`Item '${name}' has invalid rate`, "error");
                return;
            }
            validItems.push({ name, qty, rate });
        }

        if (validItems.length === 0) {
            showToast("Add at least one item to generate bill", "error");
            return;
        }

        // Show loading state
        elements.loadingOverlay.classList.remove("hidden");

        const payload = {
            customer_name: customerName,
            bill_no: billNo,
            created_on: createdOn,
            bill_date: billDate,
            items: validItems,
            discount: discount,
            txn_mode: txnMode,
            received_amount: receivedAmount
        };

        try {
            const response = await fetch("/api/bills/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            elements.loadingOverlay.classList.add("hidden");

            if (!result.success) {
                showToast(result.error || "Failed to generate bill", "error");
                return;
            }

            state.currentGeneratedBill = result.bill;
            showSuccessModal(result.bill);
            fetchSavedBillsCount();
            showToast("PDF Bill generated and saved in /bills!", "success");

        } catch (err) {
            elements.loadingOverlay.classList.add("hidden");
            console.error(err);
            showToast("Network or Server error while generating PDF", "error");
        }
    }

    // ─── Helpers: Base64 & Local Storage ───────────────────────────────────
    function b64toBlob(b64Data, contentType = "application/pdf", sliceSize = 512) {
        try {
            const byteCharacters = atob(b64Data);
            const byteArrays = [];
            for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
                const slice = byteCharacters.slice(offset, offset + sliceSize);
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {
                    byteNumbers[i] = slice.charCodeAt(i);
                }
                byteArrays.push(new Uint8Array(byteNumbers));
            }
            return new Blob(byteArrays, { type: contentType });
        } catch (e) {
            console.error("Base64 to Blob error:", e);
            return null;
        }
    }

    function saveBillLocally(bill) {
        try {
            const existing = getLocalBills();
            const filtered = existing.filter(b => b.filename !== bill.filename);
            filtered.unshift(bill);
            // Keep up to 50 recent bills in local storage
            localStorage.setItem("mitraya_saved_bills", JSON.stringify(filtered.slice(0, 50)));
        } catch (e) {
            console.warn("Could not save bill locally:", e);
        }
    }

    function getLocalBills() {
        try {
            const raw = localStorage.getItem("mitraya_saved_bills");
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function downloadPdfBlob(bill) {
        let url = bill._blobUrl;
        if (!url && bill.pdf_base64) {
            const blob = b64toBlob(bill.pdf_base64);
            if (blob) {
                url = URL.createObjectURL(blob);
                bill._blobUrl = url;
                bill._blob = blob;
            }
        }
        if (!url) {
            url = bill.download_url;
        }

        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = bill.filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
        }, 100);
    }

    // ─── Success Modal & Preview ───────────────────────────────────────────
    function showSuccessModal(bill) {
        // Convert Base64 to Blob if available
        if (bill.pdf_base64) {
            const blob = b64toBlob(bill.pdf_base64);
            if (blob) {
                bill._blob = blob;
                bill._blobUrl = URL.createObjectURL(blob);
            }
            saveBillLocally(bill);
        }

        elements.successBillTitle.textContent = bill.filename;
        elements.successBillSize.textContent = `${bill.size_kb} KB`;
        elements.successBillTime.textContent = bill.created_at || "Just now";

        const effectiveUrl = bill._blobUrl || bill.download_url;
        const previewUrl = bill._blobUrl || bill.preview_url;

        // Download button click handler
        elements.btnDownloadPdf.href = effectiveUrl;
        elements.btnDownloadPdf.setAttribute("download", bill.filename);
        elements.btnDownloadPdf.onclick = (e) => {
            e.preventDefault();
            downloadPdfBlob(bill);
            showToast(`Downloading ${bill.filename}`, "info");
        };

        // Preview Frame
        elements.btnViewPdf.href = previewUrl;
        elements.btnViewPdf.onclick = (e) => {
            if (bill._blobUrl) {
                e.preventDefault();
                window.open(bill._blobUrl, "_blank");
            }
        };
        elements.pdfPreviewFrame.src = previewUrl;

        // Setup WhatsApp PDF Share Handler
        const grandTotalText = elements.previewGrandtotal.textContent;
        const shareMsg = `*Hotel Mitraya — Bill Invoice*\nCustomer: ${bill.customer_name}\nBill No: #${bill.bill_no}\nAmount: ${grandTotalText}\nThank you for your business!`;

        elements.btnShareBill.onclick = async () => {
            // Priority 1: Direct PDF file attachment on mobile devices via Web Share API
            if (bill._blob && navigator.share && navigator.canShare) {
                try {
                    const file = new File([bill._blob], bill.filename, { type: "application/pdf" });
                    if (navigator.canShare({ files: [file] })) {
                        await navigator.share({
                            files: [file],
                            title: `Bill #${bill.bill_no} - Hotel Mitraya`,
                            text: shareMsg
                        });
                        showToast("Shared PDF Bill successfully!", "success");
                        return;
                    }
                } catch (err) {
                    if (err.name === "AbortError") return;
                    console.warn("Native file share fallback:", err);
                }
            }

            // Priority 2: Fallback for desktop / unsupported browsers
            // Download the PDF automatically so the user has the file, then open WhatsApp chat
            downloadPdfBlob(bill);
            showToast("Downloaded PDF file! Opening WhatsApp...", "info");
            setTimeout(() => {
                window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(shareMsg)}`, "_blank");
            }, 300);
        };

        elements.modalSuccess.classList.remove("hidden");
    }

    // ─── History Drawer & Saved Bills Management ───────────────────────────
    async function loadSavedBills(query = "") {
        elements.historyListContainer.innerHTML = `
            <div class="loading-state">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <span>Loading saved bills...</span>
            </div>
        `;

        try {
            const url = query ? `/api/bills?q=${encodeURIComponent(query)}` : "/api/bills";
            let serverBills = [];
            try {
                const res = await fetch(url);
                if (res.ok) {
                    const data = await res.json();
                    if (data.success && data.bills) {
                        serverBills = data.bills;
                    }
                }
            } catch (err) {
                console.warn("Could not fetch server bills:", err);
            }

            // Merge server bills with client local storage bills
            const localBills = getLocalBills();
            const mergedMap = new Map();

            serverBills.forEach(b => mergedMap.set(b.filename, b));
            localBills.forEach(b => {
                if (!mergedMap.has(b.filename)) {
                    mergedMap.set(b.filename, b);
                } else if (b.pdf_base64 && !mergedMap.get(b.filename).pdf_base64) {
                    // Enrich server bill with local base64
                    mergedMap.get(b.filename).pdf_base64 = b.pdf_base64;
                }
            });

            let allBills = Array.from(mergedMap.values());
            if (query) {
                const q = query.toLowerCase();
                allBills = allBills.filter(b => 
                    (b.customer_name && b.customer_name.toLowerCase().includes(q)) ||
                    (b.bill_no && b.bill_no.toLowerCase().includes(q)) ||
                    (b.filename && b.filename.toLowerCase().includes(q))
                );
            }

            // Sort newest first
            allBills.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

            elements.billsCountBadge.textContent = allBills.length;

            if (allBills.length === 0) {
                elements.historyListContainer.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-regular fa-folder-open" style="font-size: 2rem;"></i>
                        <p>No saved PDF bills found</p>
                    </div>
                `;
                return;
            }

            elements.historyListContainer.innerHTML = "";
            allBills.forEach(b => {
                const card = document.createElement("div");
                card.className = "history-card";
                card.innerHTML = `
                    <div class="history-header-row">
                        <div class="history-cust">${b.customer_name}</div>
                        <div class="history-billno">#${b.bill_no}</div>
                    </div>
                    <div class="history-meta">
                        <span><i class="fa-regular fa-clock"></i> ${b.created_at}</span>
                        <span><i class="fa-solid fa-file-pdf"></i> ${b.size_kb} KB</span>
                    </div>
                    <div class="history-actions">
                        <button type="button" class="btn-history-action btn-history-download" title="Download PDF">
                            <i class="fa-solid fa-download"></i> Download
                        </button>
                        <button type="button" class="btn-history-action btn-history-preview" title="View PDF">
                            <i class="fa-solid fa-eye"></i> View
                        </button>
                        <button type="button" class="btn-history-action btn-history-delete" data-filename="${b.filename}" title="Delete Bill">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                `;

                // Download event
                card.querySelector(".btn-history-download").addEventListener("click", () => {
                    downloadPdfBlob(b);
                    showToast(`Downloading ${b.filename}`, "info");
                });

                // Preview event
                card.querySelector(".btn-history-preview").addEventListener("click", () => {
                    if (b.pdf_base64) {
                        const blob = b64toBlob(b.pdf_base64);
                        if (blob) {
                            window.open(URL.createObjectURL(blob), "_blank");
                            return;
                        }
                    }
                    window.open(b.preview_url || b.download_url, "_blank");
                });

                // Delete bill event
                card.querySelector(".btn-history-delete").addEventListener("click", async (e) => {
                    const fname = e.currentTarget.dataset.filename;
                    if (confirm(`Are you sure you want to delete '${fname}'?`)) {
                        await deleteBill(fname);
                    }
                });

                elements.historyListContainer.appendChild(card);
            });

        } catch (e) {
            console.error(e);
            elements.historyListContainer.innerHTML = `<div class="empty-state">Failed to load bills</div>`;
        }
    }

    async function deleteBill(filename) {
        try {
            // Remove from local storage
            const local = getLocalBills().filter(b => b.filename !== filename);
            localStorage.setItem("mitraya_saved_bills", JSON.stringify(local));

            try {
                await fetch(`/api/bills/${encodeURIComponent(filename)}`, { method: "DELETE" });
            } catch (e) {}

            showToast(`Deleted ${filename}`, "info");
            loadSavedBills(elements.historySearchInput.value.trim());
            fetchSavedBillsCount();
        } catch (e) {
            showToast("Error deleting bill", "error");
        }
    }

    async function fetchSavedBillsCount() {
        try {
            const res = await fetch("/api/bills");
            const data = await res.json();
            if (data.success) {
                elements.billsCountBadge.textContent = data.count || 0;
            }
        } catch (e) {}
    }

    // ─── Reset Form ────────────────────────────────────────────────────────
    function resetForm() {
        elements.customerName.value = "";
        elements.discount.value = "0";
        elements.receivedAmount.value = "";
        elements.txnMode.value = "CASH";
        elements.billDate.value = getFormattedToday();
        elements.createdOn.value = getFormattedNow();
        state.items = [
            { id: 1, name: "Dahi Dhapata & Biryani plate", qty: 150, rate: 130 }
        ];
        state.nextItemId = 2;
        renderItems();
        fetchNextBillNo();
        showToast("Form reset to initial state", "info");
    }

    // ─── Event Listeners Initialization ────────────────────────────────────
    function initEvents() {
        // Preset Date/Time handlers
        elements.btnSetToday.addEventListener("click", () => {
            elements.billDate.value = getFormattedToday();
            updateCalculations();
        });
        elements.btnSetNow.addEventListener("click", () => {
            elements.createdOn.value = getFormattedNow();
            updateCalculations();
        });
        elements.btnAutoBillNo.addEventListener("click", fetchNextBillNo);

        // Input recalculation triggers
        elements.customerName.addEventListener("input", updateCalculations);
        elements.billNo.addEventListener("input", updateCalculations);
        elements.billDate.addEventListener("input", updateCalculations);
        elements.discount.addEventListener("input", updateCalculations);
        elements.receivedAmount.addEventListener("input", updateCalculations);
        elements.txnMode.addEventListener("change", updateCalculations);

        // Add item buttons
        elements.btnAddItem.addEventListener("click", () => addItem());
        elements.btnAddItemBottom.addEventListener("click", () => addItem());

        // Generate bill buttons (Desktop main, Sidebar, and Mobile bottom bar)
        elements.btnGenerateBill.addEventListener("click", handleGenerateBill);
        elements.btnGenerateBillSidebar.addEventListener("click", handleGenerateBill);
        elements.btnGenerateBillMobile.addEventListener("click", handleGenerateBill);

        // Reset
        elements.btnResetForm.addEventListener("click", () => {
            if (confirm("Reset bill form and clear all entries?")) {
                resetForm();
            }
        });

        // Success Modal Close & New Bill
        elements.btnCloseSuccessModal.addEventListener("click", () => {
            elements.modalSuccess.classList.add("hidden");
        });
        elements.btnNewBillAfterSuccess.addEventListener("click", () => {
            elements.modalSuccess.classList.add("hidden");
            resetForm();
        });

        // History Drawer Open/Close
        elements.btnOpenHistory.addEventListener("click", () => {
            elements.drawerHistory.classList.remove("hidden");
            loadSavedBills();
        });
        elements.btnCloseHistory.addEventListener("click", () => {
            elements.drawerHistory.classList.add("hidden");
        });
        elements.btnRefreshHistory.addEventListener("click", () => {
            loadSavedBills(elements.historySearchInput.value.trim());
        });
        elements.historySearchInput.addEventListener("input", (e) => {
            loadSavedBills(e.target.value.trim());
        });

        // Close on background click
        elements.modalSuccess.addEventListener("click", (e) => {
            if (e.target === elements.modalSuccess) {
                elements.modalSuccess.classList.add("hidden");
            }
        });
        elements.drawerHistory.addEventListener("click", (e) => {
            if (e.target === elements.drawerHistory) {
                elements.drawerHistory.classList.add("hidden");
            }
        });

        // Logout / Lock System
        if (elements.btnLogout) {
            elements.btnLogout.addEventListener("click", async () => {
                if (confirm("Lock billing system and logout?")) {
                    try {
                        await fetch("/api/logout", { method: "POST" });
                    } catch (e) {}
                    window.location.href = "/login";
                }
            });
        }
    }

    // ─── App Bootstrap ─────────────────────────────────────────────────────
    function init() {
        initTheme();
        initPresets();
        initEvents();

        // Default initial values
        elements.billDate.value = getFormattedToday();
        elements.createdOn.value = getFormattedNow();
        elements.customerName.value = "Buona Vita Hospitality Services LLP";

        renderItems();
        fetchNextBillNo();
        fetchSavedBillsCount();
    }

    document.addEventListener("DOMContentLoaded", init);
})();
