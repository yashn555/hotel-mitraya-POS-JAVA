/**
 * Hotel Mitraya - Unified Hardware & Bluetooth Thermal Printer Manager
 * ====================================================================
 * Coordinates:
 * 1. Web Bluetooth (BLE) 58mm & 80mm ESC/POS Thermal Printing
 * 2. Welcome Slip Generation & Startup Diagnostics
 * 3. Server-side Thermal Spooler integration (Windows Driver & Network ESC/POS)
 * 4. Automatic connection status monitoring & event notifications
 */

(function (window) {
    "use strict";

    // Known Standard Bluetooth ESC/POS Service UUIDs
    const PRINTER_SERVICES = [
        "000018f0-0000-1000-8000-00805f9b34fb",
        "e7810a71-73ae-499d-8c15-faa9aef0c3f2",
        "49535343-fe7d-4ae5-8fa9-9fafd205e455",
        "0000e0ff-0000-1000-8000-00805f9b34fb",
        "0000ff00-0000-1000-8000-00805f9b34fb",
        "0000ffe0-0000-1000-8000-00805f9b34fb",
        "0000ae00-0000-1000-8000-00805f9b34fb",
        "0000ff80-0000-1000-8000-00805f9b34fb"
    ];

    class BluetoothPrinterDriver {
        constructor() {
            this.device = null;
            this.server = null;
            this.characteristic = null;
            this.statusListeners = [];
            this.autoPrint = localStorage.getItem("mitraya_bt_autoprint") !== "false";
            this.paperWidth = parseInt(localStorage.getItem("mitraya_bt_paper_width") || "80", 10);
            this.isConnecting = false;
        }

        isSupported() {
            return !!(navigator.bluetooth && navigator.bluetooth.requestDevice);
        }

        isConnected() {
            return !!(this.device && this.device.gatt && this.device.gatt.connected && this.characteristic);
        }

        getDeviceName() {
            return this.device ? (this.device.name || "Bluetooth Thermal Printer") : null;
        }

        isAutoPrintEnabled() {
            return this.autoPrint;
        }

        setAutoPrintEnabled(enabled) {
            this.autoPrint = !!enabled;
            localStorage.setItem("mitraya_bt_autoprint", this.autoPrint ? "true" : "false");
        }

        setPaperWidth(width) {
            this.paperWidth = width === 58 ? 58 : 80;
            localStorage.setItem("mitraya_bt_paper_width", this.paperWidth.toString());
        }

        getPaperWidth() {
            return this.paperWidth;
        }

        onStatusChange(callback) {
            if (typeof callback === "function") {
                this.statusListeners.push(callback);
            }
        }

        _notifyStatus(status, details = {}) {
            const data = {
                status, // 'connected', 'disconnected', 'connecting', 'error'
                connected: this.isConnected(),
                deviceName: this.getDeviceName(),
                paperWidth: this.paperWidth,
                ...details
            };
            this.statusListeners.forEach(cb => {
                try {
                    cb(data);
                } catch (e) {
                    console.error("BT Status callback error:", e);
                }
            });
        }

        async connect() {
            if (!this.isSupported()) {
                throw new Error("Web Bluetooth is not supported on this browser. Please use Chrome or Edge on Windows/Android.");
            }

            if (this.isConnected()) {
                return true;
            }

            this.isConnecting = true;
            this._notifyStatus("connecting");

            try {
                this.device = await navigator.bluetooth.requestDevice({
                    acceptAllDevices: true,
                    optionalServices: PRINTER_SERVICES
                });

                this.device.addEventListener("gattserverdisconnected", () => {
                    this.characteristic = null;
                    this.server = null;
                    this._notifyStatus("disconnected");
                });

                this.server = await this.device.gatt.connect();

                // Find primary service and writable characteristic
                let foundChar = null;
                const services = await this.server.getPrimaryServices();

                for (const service of services) {
                    const characteristics = await service.getCharacteristics();
                    for (const char of characteristics) {
                        if (char.properties.write || char.properties.writeWithoutResponse) {
                            foundChar = char;
                            break;
                        }
                    }
                    if (foundChar) break;
                }

                if (!foundChar) {
                    throw new Error("No writable printing characteristic found on selected Bluetooth printer.");
                }

                this.characteristic = foundChar;
                this.isConnecting = false;
                this._notifyStatus("connected");

                // Print Welcome slip on successful connection
                try {
                    await this.printWelcomeSlip();
                } catch (pe) {
                    console.warn("Welcome print failed:", pe);
                }

                return true;
            } catch (err) {
                this.isConnecting = false;
                this.characteristic = null;
                this.server = null;
                this._notifyStatus("error", { error: err.message });
                throw err;
            }
        }

        async disconnect() {
            if (this.device && this.device.gatt) {
                try {
                    await this.device.gatt.disconnect();
                } catch (e) {
                    console.warn("Error disconnecting GATT:", e);
                }
            }
            this.characteristic = null;
            this.server = null;
            this._notifyStatus("disconnected");
        }

        /**
         * Write raw binary buffer to Bluetooth characteristic in chunks.
         */
        async writeBytes(bytes) {
            if (!this.isConnected()) {
                throw new Error("Bluetooth printer is not connected.");
            }

            const chunkSize = 512;
            for (let i = 0; i < bytes.length; i += chunkSize) {
                const chunk = bytes.slice(i, i + chunkSize);
                const buffer = new Uint8Array(chunk);
                if (this.characteristic.properties.writeWithoutResponse) {
                    await this.characteristic.writeValueWithoutResponse(buffer);
                } else {
                    await this.characteristic.writeValue(buffer);
                }
                await new Promise(resolve => setTimeout(resolve, 20));
            }
        }

        _padBetween(left, right, maxLen) {
            const spaces = Math.max(1, maxLen - left.length - right.length);
            return left + " ".repeat(spaces) + right;
        }

        /**
         * Generates ESC/POS bytes for a Welcome Slip
         */
        encodeWelcomeSlip() {
            const encoder = new TextEncoder();
            const cols = this.paperWidth === 58 ? 32 : 42;
            const bytes = [];

            const append = (...arr) => bytes.push(...arr);
            const appendLine = (text = "") => bytes.push(...encoder.encode(text + "\n"));

            // ESC @ : Initialize
            append(0x1B, 0x40);
            // ESC a 1 : Center
            append(0x1B, 0x61, 0x01);

            // Double size bold header
            append(0x1D, 0x21, 0x11);
            append(0x1B, 0x45, 0x01);
            appendLine("HOTEL MITRAYA");

            // Normal text
            append(0x1D, 0x21, 0x00);
            append(0x1B, 0x45, 0x00);
            appendLine("Pure Veg Restaurant & Caterers");
            appendLine("Akurdi, Pune - 411035");

            const divider = "=".repeat(cols);
            appendLine(divider);

            // Double height title
            append(0x1D, 0x21, 0x01);
            append(0x1B, 0x45, 0x01);
            appendLine("PRINTER CONNECTED!");
            append(0x1D, 0x21, 0x00);
            append(0x1B, 0x45, 0x00);

            appendLine(divider);

            // Left align details
            append(0x1B, 0x61, 0x00);
            const nowStr = new Date().toLocaleString("en-IN");
            appendLine(`Date/Time: ${nowStr}`);
            appendLine(`Device   : ${this.getDeviceName() || "Bluetooth Thermal"}`);
            appendLine(`Width    : ${this.paperWidth}mm (${cols} cols)`);
            appendLine(`Status   : READY FOR BILLING`);

            appendLine("-".repeat(cols));

            // Center align footer
            append(0x1B, 0x61, 0x01);
            appendLine("WELCOME & HAVE A GREAT SHIFT!");
            appendLine("Fast Billing & Printing Active");

            // Feed & cut
            appendLine("\n\n\n");
            append(0x1D, 0x56, 0x42, 0x00);

            return bytes;
        }

        /**
         * Encodes a customer bill into ESC/POS binary bytecode.
         */
        encodeReceipt(bill) {
            const encoder = new TextEncoder();
            const cols = this.paperWidth === 58 ? 32 : 42;
            const bytes = [];

            const append = (...arr) => bytes.push(...arr);
            const appendLine = (text = "") => bytes.push(...encoder.encode(text + "\n"));

            // ESC @ : Initialize
            append(0x1B, 0x40);
            // ESC a 1 : Center
            append(0x1B, 0x61, 0x01);

            // Brand Title
            append(0x1D, 0x21, 0x11);
            append(0x1B, 0x45, 0x01);
            appendLine("HOTEL MITRAYA");

            // Normal text
            append(0x1D, 0x21, 0x00);
            append(0x1B, 0x45, 0x00);
            appendLine("Pure Veg Restaurant & Caterers");
            appendLine("Dharmaraj chowk Nr. Honda Showroom");
            appendLine("Akurdi, Pune - 411035");
            appendLine("Ph: +91 9158691003");
            appendLine("FSSAI Lic: 21525037001433");

            // Left align
            append(0x1B, 0x61, 0x00);
            const divider = "-".repeat(cols);
            appendLine(divider);

            // Bill metadata
            const billNo = `Bill: ${bill.bill_number || "POS-000000"}`;
            const dateStr = bill.created_at || new Date().toLocaleString("en-IN");
            appendLine(this._padBetween(billNo, dateStr, cols));

            const tableLabel = bill.table_number ? `Table: ${bill.table_number}` : (bill.order_type === "DINING" ? "Dining" : "Walk-in");
            const mode = `Mode: ${bill.payment_mode || "CASH"}`;
            appendLine(this._padBetween(tableLabel, mode, cols));

            if (bill.customer_name) {
                appendLine(`Guest: ${bill.customer_name}`);
            }

            appendLine(divider);

            // Items table header
            if (cols === 32) {
                appendLine("Item            Qty Rate   Amt");
            } else {
                appendLine("Item                     Qty   Rate     Amt");
            }
            appendLine(divider);

            // Items rows
            const items = bill.items || [];
            items.forEach(i => {
                const name = i.item_name || i.name || "Item";
                const qty = String(i.quantity || 1);
                const rate = Number(i.unit_price || 0).toFixed(0);
                const amt = Number(i.total_price || (i.quantity * i.unit_price) || 0).toFixed(2);

                if (cols === 32) {
                    const itemPart = name.padEnd(14).substring(0, 14);
                    const qtyPart = qty.padStart(3);
                    const ratePart = rate.padStart(5);
                    const amtPart = amt.padStart(8);
                    appendLine(`${itemPart} ${qtyPart} ${ratePart} ${amtPart}`);
                    if (name.length > 14) {
                        appendLine(`  ${name.substring(14)}`);
                    }
                } else {
                    const itemPart = name.padEnd(20).substring(0, 20);
                    const qtyPart = qty.padStart(5);
                    const ratePart = rate.padStart(7);
                    const amtPart = amt.padStart(8);
                    appendLine(`${itemPart} ${qtyPart} ${ratePart} ${amtPart}`);
                    if (name.length > 20) {
                        appendLine(`  ${name.substring(20)}`);
                    }
                }
            });

            appendLine(divider);

            // Subtotal
            const subtotalStr = `Rs.${Number(bill.subtotal || 0).toFixed(2)}`;
            appendLine(this._padBetween("Sub Total:", subtotalStr, cols));

            // Discount
            if (bill.discount && Number(bill.discount) > 0) {
                const discStr = `-Rs.${Number(bill.discount).toFixed(2)}`;
                appendLine(this._padBetween("Discount:", discStr, cols));
            }

            appendLine(divider);

            // Grand Total
            append(0x1B, 0x45, 0x01); // Bold ON
            append(0x1D, 0x21, 0x01); // Double height
            const totalStr = `Rs.${Number(bill.total_amount || 0).toFixed(2)}`;
            appendLine(this._padBetween("TOTAL:", totalStr, cols));
            append(0x1D, 0x21, 0x00); // Normal text
            append(0x1B, 0x45, 0x00); // Bold OFF

            appendLine(divider);

            // Cash Tendered & Change
            if (bill.payment_mode === "CASH" && bill.received_amount) {
                const recStr = `Rs.${Number(bill.received_amount).toFixed(2)}`;
                appendLine(this._padBetween("Cash Tendered:", recStr, cols));

                const change = Math.max(0, Number(bill.received_amount) - Number(bill.total_amount));
                const chgStr = `Rs.${change.toFixed(2)}`;
                appendLine(this._padBetween("Change Due:", chgStr, cols));
                appendLine(divider);
            }

            // Footer
            append(0x1B, 0x61, 0x01);
            appendLine(`* ${bill.bill_number || "POS-RECEIPT"} *`);
            appendLine("Thank You! Visit Again.");
            appendLine("Have a Delicious Day!");

            // Feed & cut
            appendLine("\n\n\n");
            append(0x1D, 0x56, 0x42, 0x00);

            return bytes;
        }

        async printReceipt(bill) {
            const bytes = this.encodeReceipt(bill);
            await this.writeBytes(bytes);
        }

        async printWelcomeSlip() {
            const bytes = this.encodeWelcomeSlip();
            await this.writeBytes(bytes);
        }

        async printTestReceipt() {
            const testBill = {
                bill_number: "TEST-0001",
                created_at: new Date().toLocaleString("en-IN"),
                cashier_role: "Staff",
                payment_mode: "CASH",
                items: [
                    { item_name: "Special Masala Chai", quantity: 2, unit_price: 20, total_price: 40 },
                    { item_name: "Dahi Dhapata Plate", quantity: 1, unit_price: 130, total_price: 130 },
                    { item_name: "Special Veg Thali", quantity: 1, unit_price: 160, total_price: 160 }
                ],
                subtotal: 330.00,
                discount: 10.00,
                total_amount: 320.00,
                received_amount: 500.00
            };
            await this.printReceipt(testBill);
        }
    }

    // Expose global instance
    window.MitrayaBluetoothPrinter = new BluetoothPrinterDriver();

})(window);
