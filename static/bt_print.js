/**
 * Hotel Mitraya - Web Bluetooth Thermal Receipt Printer Driver
 * =============================================================
 * Provides direct ESC/POS thermal printing over Web Bluetooth (BLE).
 * Supports standard 58mm and 80mm POS Bluetooth thermal receipt printers.
 */

(function (window) {
    "use strict";

    // Known Bluetooth Printer Service UUIDs (Standard ESC/POS BLE Profiles)
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
            return this.device ? (this.device.name || "Bluetooth Printer") : null;
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
                throw new Error("Web Bluetooth is not supported in this browser. Please use Chrome, Edge, or Bluefy.");
            }

            if (this.isConnected()) {
                return true;
            }

            this.isConnecting = true;
            this._notifyStatus("connecting");

            try {
                // Request Bluetooth Device with printer service filters
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
                    throw new Error("No writable printing characteristic found on selected Bluetooth device.");
                }

                this.characteristic = foundChar;
                this.isConnecting = false;
                this._notifyStatus("connected");
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
         * Write raw binary buffer to Bluetooth characteristic in chunks (512 bytes).
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
                // Small pause between chunks to avoid buffer overflow on receipt printer
                await new Promise(resolve => setTimeout(resolve, 20));
            }
        }

        /**
         * Encodes receipt data into ESC/POS binary bytecode.
         */
        encodeReceipt(bill) {
            const encoder = new TextEncoder();
            const cols = this.paperWidth === 58 ? 32 : 42;
            const bytes = [];

            const append = (...arr) => bytes.push(...arr);
            const appendLine = (text = "") => bytes.push(...encoder.encode(text + "\n"));

            // ESC @ : Initialize printer
            append(0x1B, 0x40);

            // ESC a 1 : Center alignment
            append(0x1B, 0x61, 0x01);

            // GS ! 0x11 : Double width & double height for Main Title
            append(0x1D, 0x21, 0x11);
            // ESC E 1 : Bold ON
            append(0x1B, 0x45, 0x01);
            appendLine("HOTEL MITRAYA");

            // Normal font
            append(0x1D, 0x21, 0x00);
            append(0x1B, 0x45, 0x00);
            appendLine("Pure Veg Restaurant & Caterers");
            appendLine("Dharmaraj chowk Nr. Honda Showroom");
            appendLine("Akurdi, Pune - 411035");
            appendLine("Ph: +91 9158691003");
            appendLine("FSSAI Lic: 21525037001433");

            // ESC a 0 : Left alignment
            append(0x1B, 0x61, 0x00);

            const divider = "-".repeat(cols);
            appendLine(divider);

            // Meta Info: Bill No, Date, Cashier, Mode
            const billNo = `Bill: ${bill.bill_number || "POS-000000"}`;
            const dateStr = bill.created_at || new Date().toLocaleString("en-IN");
            appendLine(this._padBetween(billNo, dateStr, cols));

            const cashier = `Staff: ${bill.cashier_role || "Staff"}`;
            const mode = `Mode: ${bill.payment_mode || "CASH"}`;
            appendLine(this._padBetween(cashier, mode, cols));

            appendLine(divider);

            // Table Header: Item | Qty | Rate | Amt
            if (cols === 32) {
                appendLine("Item            Qty Rate   Amt");
            } else {
                appendLine("Item                     Qty   Rate     Amt");
            }
            appendLine(divider);

            // Item Rows
            const items = bill.items || [];
            items.forEach(i => {
                const name = i.item_name || i.name || "Item";
                const qty = String(i.quantity || 1);
                const rate = Number(i.unit_price || 0).toFixed(0);
                const amt = Number(i.total_price || (i.quantity * i.unit_price) || 0).toFixed(2);

                if (cols === 32) {
                    // 32-col layout (14 item, 4 qty, 5 rate, 7 amt)
                    const itemPart = name.padEnd(14).substring(0, 14);
                    const qtyPart = qty.padStart(3);
                    const ratePart = rate.padStart(5);
                    const amtPart = amt.padStart(8);
                    appendLine(`${itemPart} ${qtyPart} ${ratePart} ${amtPart}`);
                    if (name.length > 14) {
                        appendLine(`  ${name.substring(14)}`);
                    }
                } else {
                    // 42-col layout (20 item, 5 qty, 7 rate, 8 amt)
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

            // Discount if applicable
            if (bill.discount && Number(bill.discount) > 0) {
                const discStr = `-Rs.${Number(bill.discount).toFixed(2)}`;
                appendLine(this._padBetween("Discount:", discStr, cols));
            }

            appendLine(divider);

            // Grand Total (Bold & slightly enlarged)
            append(0x1B, 0x45, 0x01); // Bold ON
            append(0x1D, 0x21, 0x01); // Double height
            const totalStr = `Rs.${Number(bill.total_amount || 0).toFixed(2)}`;
            appendLine(this._padBetween("TOTAL:", totalStr, cols));
            append(0x1D, 0x21, 0x00); // Normal text
            append(0x1B, 0x45, 0x00); // Bold OFF

            appendLine(divider);

            // Cash Tendered & Change (if Cash)
            if (bill.payment_mode === "CASH" && bill.received_amount) {
                const recStr = `Rs.${Number(bill.received_amount).toFixed(2)}`;
                appendLine(this._padBetween("Cash Tendered:", recStr, cols));

                const change = Math.max(0, Number(bill.received_amount) - Number(bill.total_amount));
                const chgStr = `Rs.${change.toFixed(2)}`;
                appendLine(this._padBetween("Change Due:", chgStr, cols));
                appendLine(divider);
            }

            // Center Align for Footer
            append(0x1B, 0x61, 0x01);
            appendLine(`* ${bill.bill_number || "POS-RECEIPT"} *`);
            appendLine("Thank You! Visit Again.");
            appendLine("Have a Delicious Day!");

            // Feed 4 lines & cut
            appendLine("\n\n\n");
            // GS V 66 0 : Cut paper
            append(0x1D, 0x56, 0x42, 0x00);

            return bytes;
        }

        _padBetween(left, right, maxLen) {
            const spaces = Math.max(1, maxLen - left.length - right.length);
            return left + " ".repeat(spaces) + right;
        }

        async printReceipt(bill) {
            const bytes = this.encodeReceipt(bill);
            await this.writeBytes(bytes);
        }

        async printTestReceipt() {
            const testBill = {
                bill_number: "TEST-0001",
                created_at: new Date().toLocaleString("en-IN"),
                cashier_role: "Admin/Tester",
                payment_mode: "CASH",
                items: [
                    { item_name: "Special Chai", quantity: 2, unit_price: 20, total_price: 40 },
                    { item_name: "Masala Dosa", quantity: 1, unit_price: 90, total_price: 90 },
                    { item_name: "Filter Coffee", quantity: 1, unit_price: 30, total_price: 30 }
                ],
                subtotal: 160.00,
                discount: 0.00,
                total_amount: 160.00,
                received_amount: 200.00
            };
            await this.printReceipt(testBill);
        }
    }

    // Expose global instance
    window.MitrayaBluetoothPrinter = new BluetoothPrinterDriver();

})(window);
