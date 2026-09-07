"""
Hotel Mitraya - Local Hardware Print Bridge & Real-Time Thermal Spooler
=======================================================================
Runs on the Cashier Laptop connected to the physical USB Thermal Printer (HOIN HOP-H58).
Seamlessly connects to either:
1. Local POS Server (http://localhost:5055)
2. Cloud Render/Neon POS Server (https://your-app.onrender.com)

Features:
- Auto-identifies connected USB Thermal Printers (HOIN HOP-H58 / ESC/POS)
- Real-time polling with sub-second response for incoming bills & KOTs
- Zero-click direct hardware printing via Windows Raw Spooler
- Automatic reconnection and robust error recovery
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' package required. Run: pip install requests")
    sys.exit(1)

# Import local printer modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from printer.manager import PrinterDetector, PrinterManager
from printer.formatter import ReceiptFormatter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MitrayaPrintBridge")


def get_server_base_url():
    """Determine the active server URL from env or fallback to localhost."""
    url = os.environ.get("MITRAYA_SERVER_URL") or os.environ.get("SERVER_URL")
    if not url:
        # Check command line arguments
        if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
            url = sys.argv[1]
        else:
            url = "https://hotel-mitraya-pos-java.onrender.com"
    return url.rstrip("/")


def main():
    base_url = get_server_base_url()
    logger.info("==================================================================")
    logger.info("   HOTEL MITRAYA - HARDWARE THERMAL PRINT BRIDGE (PROD)           ")
    logger.info("==================================================================")
    logger.info(f"Target POS Server : {base_url}")

    # 1. Detect Connected Printer
    thermal_info = PrinterDetector.identify_thermal_printer()
    printer_name = thermal_info.get("name", "HOIN HOP-H58")
    paper_width = thermal_info.get("paper_width", 58)

    logger.info(f"Connected Printer : {printer_name} ({paper_width}mm Thermal)")
    logger.info("Status            : ACTIVE & LISTENING FOR PRINT JOBS")
    logger.info("------------------------------------------------------------------")

    # Send startup confirmation print
    try:
        hello_bill = {
            "bill_number": "BRIDGE-INIT",
            "order_type": "STARTUP_CHECK",
            "table_label": "Counter Station",
            "cashier_role": "Print Bridge",
            "payment_mode": "SYSTEM_READY",
            "items": [
                {"item_name": "HOTEL MITRAYA PRINT BRIDGE", "quantity": 1, "unit_price": 0.0, "total_price": 0.0},
                {"item_name": "Printer: " + printer_name, "quantity": 1, "unit_price": 0.0, "total_price": 0.0},
                {"item_name": "Mode: Real-Time Auto-Spool", "quantity": 1, "unit_price": 0.0, "total_price": 0.0}
            ],
            "subtotal": 0.0,
            "discount": 0.0,
            "total_amount": 0.0
        }
        raw_hello = ReceiptFormatter.format_escpos_bytes(hello_bill, paper_width=paper_width, footer_text="Hardware Print Bridge Online")
        ok, msg = PrinterManager._send_raw_to_windows_printer(printer_name, raw_hello, "Mitraya Bridge Init")
        if ok:
            logger.info("✅ Startup confirmation slip sent to printer successfully.")
    except Exception as e:
        logger.warning(f"Startup check warning: {e}")

    # 2. Main Polling Loop
    last_event_id = 0
    consecutive_errors = 0

    try:
        # Initialize initial max id from server
        init_res = requests.get(f"{base_url}/api/display/live-orders?since_id=0&limit=1", timeout=5)
        if init_res.status_code == 200:
            last_event_id = init_res.json().get("max_id", 0)
            logger.info(f"Initial sync synchronized at Event ID: {last_event_id}")
    except Exception as e:
        logger.warning(f"Initial sync warning: {e} - Will retry on next tick")

    while True:
        try:
            url = f"{base_url}/api/display/live-orders?since_id={last_event_id}&limit=5"
            res = requests.get(url, timeout=4)

            if res.status_code == 200:
                consecutive_errors = 0
                data = res.json()
                new_bills = data.get("new_bills", [])
                max_id = data.get("max_id", last_event_id)

                if new_bills:
                    logger.info(f"⚡ Received {len(new_bills)} new bill(s) to print!")
                    for bill in new_bills:
                        bill_no = bill.get("bill_number", "N/A")
                        table = bill.get("table_label") or f"Table {bill.get('table_number', 'N/A')}"
                        total = bill.get("total_amount", 0.0)
                        logger.info(f"🖨️ Printing Bill #{bill_no} [{table}] - Rs.{total:.2f}")

                        # Format & Spool to Hardware
                        raw_bytes = ReceiptFormatter.format_escpos_bytes(
                            bill,
                            paper_width=paper_width,
                            header_title="HOTEL MITRAYA",
                            footer_text="Thank You! Visit Again."
                        )
                        ok, msg = PrinterManager._send_raw_to_windows_printer(printer_name, raw_bytes, f"Bill-{bill_no}")
                        if ok:
                            logger.info(f"✅ Successfully printed Bill #{bill_no}")
                        else:
                            logger.error(f"❌ Print failed for Bill #{bill_no}: {msg}")

                if max_id > last_event_id:
                    last_event_id = max_id

            time.sleep(1.0)

        except requests.exceptions.ConnectionError:
            consecutive_errors += 1
            if consecutive_errors % 10 == 1:
                logger.warning(f"Connecting to {base_url}... (Retrying in background)")
            time.sleep(2.0)
        except KeyboardInterrupt:
            logger.info("\n🛑 Hotel Mitraya Print Bridge stopped by user.")
            break
        except Exception as e:
            logger.error(f"Bridge loop error: {e}")
            time.sleep(2.0)


if __name__ == "__main__":
    main()
