"""
Hotel Mitraya - Thermal Printer Manager & Hardware Spooler
===========================================================
Provides:
1. Windows Installed Thermal Printer Detection & Spooling (via win32print / raw spooler)
2. Network Thermal Printer Direct Socket Spooling (IP:9100)
3. Decoupled Print Job Lifecycle (PRINT_PENDING, PRINTING, PRINTED, FAILED)
4. Robust Retry & Reprint Management without disrupting financial records
"""

import os
import sys
import socket
import subprocess
from datetime import datetime
from database.models import PosBill, PrintJob, PrinterConfigModel, Order
from database.db import record_audit_log
from printer.formatter import ReceiptFormatter

# Try importing win32print on Windows platforms
HAS_WIN32PRINT = False
if sys.platform == "win32":
    try:
        import win32print
        HAS_WIN32PRINT = True
    except ImportError:
        HAS_WIN32PRINT = False


class PrinterDetector:
    """Detects available physical and virtual printers on the host system."""

    @classmethod
    def list_system_printers(cls) -> list:
        printers = []
        
        # 1. Primary: Windows win32print API
        if HAS_WIN32PRINT:
            try:
                flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                enum_list = win32print.EnumPrinters(flags)
                default_p = win32print.GetDefaultPrinter() if hasattr(win32print, "GetDefaultPrinter") else ""
                for p in enum_list:
                    # p is a tuple: (flags, description, name, comment)
                    p_name = p[2]
                    printers.append({
                        "name": p_name,
                        "description": p[1] or p_name,
                        "is_default": (p_name == default_p),
                        "driver": "Windows Driver",
                        "status": "Ready"
                    })
                if printers:
                    return printers
            except Exception as e:
                print(f"[WARN] win32print enumeration failed: {e}")

        # 2. Secondary Windows Fallback: PowerShell Get-Printer
        if sys.platform == "win32":
            try:
                cmd = ["powershell", "-NoProfile", "-Command", "Get-Printer | Select-Object Name, Type, DriverName, PrinterStatus | ConvertTo-Json"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and res.stdout.strip():
                    import json
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        p_name = item.get("Name", "Unknown")
                        printers.append({
                            "name": p_name,
                            "description": item.get("DriverName", p_name),
                            "is_default": False,
                            "driver": item.get("DriverName", "Windows Driver"),
                            "status": item.get("PrinterStatus", "Ready")
                        })
                    if printers:
                        return printers
            except Exception as e:
                print(f"[WARN] PowerShell printer detection failed: {e}")

        # 3. Fallback standard virtual POS printers if none detected
        return []

    @classmethod
    def identify_thermal_printer(cls) -> dict:
        printers = cls.list_system_printers()
        thermal_keywords = ["hoin", "hop-", "pos", "thermal", "receipt", "58", "80", "xp-", "tvs", "epson", "citizen", "star", "hprt", "xprinter"]
        ignore_keywords = ["pdf", "onenote", "xps", "fax", "anydesk"]

        matched = None
        for p in printers:
            name = p.get("name", "")
            low = name.lower()
            if any(ign in low for ign in ignore_keywords):
                continue
            if any(k in low for k in thermal_keywords):
                matched = p
                break
        
        if not matched:
            # Fallback 1: Use Windows Default Printer
            for p in printers:
                name = p.get("name", "")
                low = name.lower()
                if p.get("is_default") and not any(ign in low for ign in ignore_keywords):
                    matched = p
                    break

        if not matched:
            # Fallback 2: Use any available physical printer
            for p in printers:
                name = p.get("name", "")
                low = name.lower()
                if not any(ign in low for ign in ignore_keywords):
                    matched = p
                    break

        if not matched and printers:
            matched = printers[0]

        if matched:
            name = matched["name"]
            low = name.lower()
            width = 58 if ("58" in low or "h58" in low or "32" in low or "2inch" in low) else 80
            return {
                "connected": True,
                "name": name,
                "paper_width": width,
                "columns": 32 if width == 58 else 42,
                "printer": matched
            }
        
        return {
            "connected": False,
            "name": "Default Printer",
            "paper_width": 80,
            "columns": 42,
            "printer": None
        }

    @classmethod
    def test_network_printer_connection(cls, ip_address: str, port: int = 9100, timeout: float = 2.0) -> dict:
        """Tests if a network ESC/POS thermal printer is reachable on IP:Port."""
        if not ip_address:
            return {"reachable": False, "error": "IP address not provided"}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip_address, int(port)))
            s.close()
            return {"reachable": True, "message": f"Successfully connected to thermal printer at {ip_address}:{port}"}
        except Exception as e:
            return {"reachable": False, "error": str(e)}


class PrinterManager:
    """Orchestrates thermal receipt printing, print jobs, and connection drivers."""

    @classmethod
    def get_active_config(cls, db_session) -> dict:
        """Fetch active printer config from database or return standard default."""
        config_obj = db_session.query(PrinterConfigModel).filter_by(is_default=True).first()
        if not config_obj:
            config_obj = db_session.query(PrinterConfigModel).first()
        if config_obj:
            return config_obj.to_dict()
        return {
            "id": None,
            "name": "Default Thermal Printer",
            "connection_type": "WINDOWS_DRIVER",
            "paper_width": 80,
            "printer_name": "",
            "ip_address": "",
            "port": 9100,
            "is_default": True,
            "cut_enabled": True,
            "header_title": "HOTEL MITRAYA",
            "footer_text": "Thank You! Visit Again."
        }

    @classmethod
    def _send_raw_to_windows_printer(cls, printer_name: str, raw_bytes: bytes, doc_name: str = "Hotel Mitraya Receipt") -> tuple[bool, str]:
        """Send raw ESC/POS binary bytecode directly to an identified Windows spooler queue."""
        if not HAS_WIN32PRINT:
            return False, "win32print is not available on this environment"
        try:
            detected = PrinterDetector.list_system_printers()
            names = [p.get("name") for p in detected if p.get("name")]
            
            p_name = None
            # 1. Exact match if specified
            if printer_name and printer_name in names:
                p_name = printer_name
            # 2. Case-insensitive / Substring match
            elif printer_name:
                for n in names:
                    if printer_name.lower() in n.lower():
                        p_name = n
                        break

            # 3. Identify thermal / POS / receipt printer from system list
            if not p_name:
                for n in names:
                    low = n.lower()
                    if any(k in low for k in ["pos", "thermal", "receipt", "58", "80", "xp-", "tvs", "epson", "citizen", "star", "hprt", "xprinter"]):
                        p_name = n
                        break

            # 4. Fallback to Windows default printer
            if not p_name and hasattr(win32print, "GetDefaultPrinter"):
                try:
                    p_name = win32print.GetDefaultPrinter()
                except Exception:
                    pass

            if not p_name:
                p_name = names[0] if names else None

            if not p_name:
                return False, "No ready Windows printer identified on system"

            h_printer = win32print.OpenPrinter(p_name)
            try:
                job_id = win32print.StartDocPrinter(h_printer, 1, (doc_name, None, "RAW"))
                try:
                    win32print.StartPagePrinter(h_printer)
                    win32print.WritePrinter(h_printer, raw_bytes)
                    win32print.EndPagePrinter(h_printer)
                finally:
                    win32print.EndDocPrinter(h_printer)
            finally:
                win32print.ClosePrinter(h_printer)
            return True, f"Printed successfully to identified printer: '{p_name}'"
        except Exception as e:
            return False, f"Windows print error on '{printer_name or 'Default'}': {str(e)}"


    @classmethod
    def _send_raw_to_network_printer(cls, ip_address: str, port: int, raw_bytes: bytes, timeout: float = 3.0) -> tuple[bool, str]:
        """Send raw ESC/POS binary bytecode to network thermal printer via TCP socket."""
        if not ip_address:
            return False, "Network IP address is required"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip_address, int(port)))
            s.sendall(raw_bytes)
            s.close()
            return True, f"Receipt sent to network printer at {ip_address}:{port}"
        except Exception as e:
            return False, f"Network print failed for {ip_address}:{port}: {str(e)}"

    @classmethod
    def dispatch_print_job(cls, db_session, bill_data: dict, pos_bill_id: int = None, order_id: int = None,
                           job_type: str = "FINAL_BILL", custom_config: dict = None) -> dict:
        """
        Dispatches a receipt to the configured thermal printer with job tracking.
        Guarantees that physical print errors will NEVER throw an unhandled exception or break billing.
        """
        config = custom_config or cls.get_active_config(db_session)
        paper_width = int(config.get("paper_width", 80))
        connection_type = str(config.get("connection_type", "WINDOWS_DRIVER")).upper()
        printer_name = str(config.get("printer_name", "")).strip()
        ip_addr = str(config.get("ip_address", "")).strip()
        port = int(config.get("port", 9100))
        cut_enabled = bool(config.get("cut_enabled", True))
        header_title = str(config.get("header_title", "HOTEL MITRAYA"))
        footer_text = str(config.get("footer_text", "Thank You! Visit Again."))

        # Dynamic Hardware Auto-Discovery & Auto-Adjustment
        identified = PrinterDetector.identify_thermal_printer()
        if identified.get("connected"):
            sys_names = [p.get("name") for p in PrinterDetector.list_system_printers()]
            if not printer_name or printer_name not in sys_names:
                printer_name = identified.get("name")
            if not custom_config or "paper_width" not in custom_config:
                paper_width = int(identified.get("paper_width", paper_width))

        # 1. Generate formatted plain text & ESC/POS binary bytecode
        plain_text_slip = ReceiptFormatter.format_plain_text(
            bill_data,
            paper_width=paper_width,
            header_title=header_title,
            footer_text=footer_text
        )
        escpos_bytes = ReceiptFormatter.format_escpos_bytes(
            bill_data,
            paper_width=paper_width,
            header_title=header_title,
            footer_text=footer_text,
            cut=cut_enabled
        )

        # 2. Record PrintJob record in DB
        job = PrintJob(
            pos_bill_id=pos_bill_id,
            order_id=order_id,
            job_type=job_type,
            printer_name=printer_name or ip_addr or "Thermal Receipt Printer",
            paper_width=paper_width,
            status="PRINTING",
            created_at=datetime.now()
        )
        db_session.add(job)
        db_session.flush()

        # 3. Attempt physical dispatch
        print_success = False
        error_msg = None

        if connection_type == "WINDOWS_DRIVER":
            if HAS_WIN32PRINT:
                success, msg = cls._send_raw_to_windows_printer(printer_name, escpos_bytes)
                if success:
                    print_success = True
                else:
                    error_msg = msg
            else:
                # Windows environment without win32print or non-Windows server
                print_success = True  # Spooled cleanly to preview / browser print
                error_msg = None

        elif connection_type == "NETWORK_RAW":
            success, msg = cls._send_raw_to_network_printer(ip_addr, port, escpos_bytes)
            if success:
                print_success = True
            else:
                error_msg = msg

        elif connection_type == "BROWSER_PRINT":
            # Browser print / Web Bluetooth client
            print_success = True

        else:
            print_success = True

        # 4. Finalize Job Status in DB
        if print_success:
            job.status = "PRINTED"
            job.printed_at = datetime.now()
            job.error_message = None
        else:
            job.status = "FAILED"
            job.error_message = error_msg

        db_session.flush()

        return {
            "success": True,
            "printed": print_success,
            "job_id": job.id,
            "status": job.status,
            "paper_width": paper_width,
            "error_message": error_msg,
            "preview_text": plain_text_slip
        }

    @classmethod
    def retry_print_job(cls, db_session, job_id: int) -> dict:
        """Retry a previously failed print job."""
        job = db_session.query(PrintJob).filter_by(id=job_id).first()
        if not job:
            return {"success": False, "error": "Print job not found"}

        bill_data = None
        if job.pos_bill:
            bill_data = job.pos_bill.to_dict()
        elif job.order_id:
            order = db_session.query(Order).filter_by(id=job.order_id).first()
            if order:
                bill_data = order.to_dict()

        if not bill_data:
            return {"success": False, "error": "No bill or order associated with this print job"}

        job.retry_count = (job.retry_count or 0) + 1
        res = cls.dispatch_print_job(
            db_session,
            bill_data=bill_data,
            pos_bill_id=job.pos_bill_id,
            order_id=job.order_id,
            job_type=job.job_type
        )
        return res

    @classmethod
    def reprint_bill(cls, db_session, bill_id: int, user_context: dict = None) -> dict:
        """Reprint a historical bill by ID."""
        bill = db_session.query(PosBill).filter_by(id=bill_id).first()
        if not bill:
            return {"success": False, "error": "Bill not found"}

        bill_data = bill.to_dict()
        res = cls.dispatch_print_job(
            db_session,
            bill_data=bill_data,
            pos_bill_id=bill.id,
            job_type="REPRINT"
        )

        record_audit_log(
            db_session,
            action="REPRINT_BILL",
            entity="BILL",
            entity_id=str(bill.id),
            details=f"Reprint requested for Bill #{bill.bill_number}",
            **(user_context or {})
        )

        return res
