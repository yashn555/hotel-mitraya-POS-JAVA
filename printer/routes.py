"""
Printer API Routes & Hardware Configuration Controller
======================================================
Provides endpoints for printer detection, test prints, receipt dispatch,
reprinting, job status tracking, and thermal printer settings.
"""

from flask import Blueprint, request, jsonify, session
from database.db import get_db, record_audit_log
from database.models import PosBill, PrintJob, PrinterConfigModel
from auth.utils import cashier_or_admin_required, admin_required, get_current_user_context
from printer.manager import PrinterManager, PrinterDetector
from printer.formatter import ReceiptFormatter

printer_bp = Blueprint("printer", __name__)


@printer_bp.route("/printer", methods=["GET"])
@cashier_or_admin_required
def printer_station_view():
    """Hardware Print Station & Live Order Display."""
    from flask import render_template
    return render_template(
        "display.html",
        user_role=session.get("role", "cashier"),
        user_name=session.get("user_name", "Staff")
    )


@printer_bp.route("/api/printer/startup-init", methods=["POST", "GET"])
@cashier_or_admin_required
def startup_printer_init_api():
    """
    Performs startup printer diagnostic:
    1. Identifies all wired and connected system printers.
    2. Identifies the active thermal printer (e.g. 58mm/80mm, ESC/POS, Windows spooler).
    3. Prints a Hello startup confirmation slip.
    4. Returns identified printer status to the station UI.
    """
    try:
        printers = PrinterDetector.list_system_printers()
        detected_name = None
        for p in printers:
            name = p.get("name", "")
            low = name.lower()
            if any(k in low for k in ["pos", "thermal", "receipt", "58", "80", "xp-", "tvs", "epson", "citizen", "star", "hprt", "xprinter"]):
                detected_name = name
                break
        
        if not detected_name and printers:
            # Fall back to default printer or first
            default_p = next((p["name"] for p in printers if p.get("is_default")), None)
            detected_name = default_p or printers[0].get("name", "Windows Spooler")

        with get_db() as db:
            active_cfg = PrinterManager.get_active_config(db)
            paper_width = active_cfg.get("paper_width", 80)
            
            # Create startup confirmation payload
            hello_payload = {
                "bill_number": "INIT-001",
                "order_type": "STARTUP_CONFIRMATION",
                "table_label": "Wired Printer Ready",
                "cashier_role": session.get("user_name", "System"),
                "payment_mode": "READY",
                "items": [
                    {"item_name": "HELLO — HOTEL MITRAYA", "quantity": 1, "unit_price": 0.0, "total_price": 0.0},
                    {"item_name": f"Station: {detected_name or 'Default'}", "quantity": 1, "unit_price": 0.0, "total_price": 0.0},
                    {"item_name": "Status: ONLINE & READY", "quantity": 1, "unit_price": 0.0, "total_price": 0.0}
                ],
                "subtotal": 0.0,
                "discount": 0.0,
                "total_amount": 0.0
            }

            custom_cfg = dict(active_cfg)
            if detected_name:
                custom_cfg["printer_name"] = detected_name

            print_job = PrinterManager.dispatch_print_job(
                db,
                bill_data=hello_payload,
                job_type="STARTUP_HELLO",
                custom_config=custom_cfg
            )

            return jsonify({
                "success": True,
                "message": f"Printer '{detected_name or 'Default'}' identified and initialized with confirmation print!",
                "identified_printer": detected_name or "Standard Spooler",
                "total_printers_detected": len(printers),
                "printers": printers,
                "paper_width": paper_width,
                "print_job": print_job
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/list", methods=["GET"])
@cashier_or_admin_required
def list_printers_api():
    """List all detected system printers and virtual ESC/POS devices."""
    try:
        printers = PrinterDetector.list_system_printers()
        return jsonify({
            "success": True,
            "count": len(printers),
            "printers": printers
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/status", methods=["GET"])
@cashier_or_admin_required
def printer_status_api():
    """Retrieve current thermal printer configuration and status."""
    try:
        hw_info = PrinterDetector.identify_thermal_printer()
        with get_db() as db:
            config = PrinterManager.get_active_config(db)
            recent_jobs_count = db.query(PrintJob).count()
            failed_jobs_count = db.query(PrintJob).filter_by(status="FAILED").count()

            return jsonify({
                "success": True,
                "connected": hw_info["connected"],
                "identified_printer": hw_info["name"],
                "paper_width": hw_info["paper_width"],
                "columns": hw_info["columns"],
                "config": config,
                "stats": {
                    "total_jobs": recent_jobs_count,
                    "failed_jobs": failed_jobs_count
                }
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/config", methods=["POST"])
@cashier_or_admin_required
def update_printer_config_api():
    """Save or update default thermal printer settings (58mm/80mm, connection type, network IP)."""
    try:
        data = request.get_json(force=True)
        name = str(data.get("name", "Counter Thermal Printer")).strip()
        conn_type = str(data.get("connection_type", "WINDOWS_DRIVER")).strip().upper()
        paper_width = int(data.get("paper_width", 80))
        if paper_width not in [58, 80]:
            paper_width = 80
        printer_name = str(data.get("printer_name", "")).strip()
        ip_addr = str(data.get("ip_address", "")).strip()
        port = int(data.get("port", 9100))
        cut_enabled = bool(data.get("cut_enabled", True))
        header_title = str(data.get("header_title", "HOTEL MITRAYA")).strip()
        footer_text = str(data.get("footer_text", "Thank You! Visit Again.")).strip()
        ctx = get_current_user_context()

        with get_db() as db:
            cfg = db.query(PrinterConfigModel).filter_by(is_default=True).first()
            if not cfg:
                cfg = PrinterConfigModel(is_default=True)
                db.add(cfg)

            cfg.name = name
            cfg.connection_type = conn_type
            cfg.paper_width = paper_width
            cfg.printer_name = printer_name
            cfg.ip_address = ip_addr
            cfg.port = port
            cfg.cut_enabled = cut_enabled
            cfg.header_title = header_title
            cfg.footer_text = footer_text

            db.flush()

            record_audit_log(
                db,
                action="PRINTER_CONFIG_UPDATE",
                entity="PRINTER",
                entity_id=str(cfg.id),
                details=f"Updated printer configuration: {conn_type}, {paper_width}mm ({printer_name or ip_addr})",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": "Printer configuration updated successfully!",
                "config": cfg.to_dict()
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/test", methods=["POST"])
@cashier_or_admin_required
def test_print_api():
    """Print an alignment and diagnostic slip for 58mm or 80mm."""
    try:
        data = request.get_json(silent=True) or {}
        paper_width = int(data.get("paper_width", 80))
        if paper_width not in [58, 80]:
            paper_width = 80

        with get_db() as db:
            active_cfg = PrinterManager.get_active_config(db)
            custom_cfg = dict(active_cfg)
            custom_cfg["paper_width"] = paper_width
            if "printer_name" in data:
                custom_cfg["printer_name"] = data["printer_name"]
            if "connection_type" in data:
                custom_cfg["connection_type"] = data["connection_type"]

            test_payload = {
                "bill_number": "TEST-001",
                "order_type": "TEST_PRINT",
                "table_label": f"Test {paper_width}mm Slip",
                "cashier_role": session.get("user_name", "Staff"),
                "payment_mode": "CASH",
                "items": [
                    {"item_name": "Special Dahi Dhapata", "quantity": 2, "unit_price": 110.0, "total_price": 220.0},
                    {"item_name": "Masala Chai", "quantity": 3, "unit_price": 20.0, "total_price": 60.0},
                    {"item_name": "Special Veg Thali", "quantity": 1, "unit_price": 160.0, "total_price": 160.0}
                ],
                "subtotal": 440.0,
                "discount": 20.0,
                "total_amount": 420.0,
                "received_amount": 500.0,
                "change_amount": 80.0
            }

            res = PrinterManager.dispatch_print_job(
                db,
                bill_data=test_payload,
                job_type="TEST_SLIP",
                custom_config=custom_cfg
            )

            return jsonify({
                "success": True,
                "message": f"Test print dispatched ({paper_width}mm)!",
                "job": res
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/reprint/<int:bill_id>", methods=["POST"])
@cashier_or_admin_required
def reprint_bill_api(bill_id):
    """Reprint a historical bill by ID."""
    try:
        ctx = get_current_user_context()
        with get_db() as db:
            res = PrinterManager.reprint_bill(db, bill_id=bill_id, user_context=ctx)
            if not res.get("success"):
                return jsonify(res), 400
            return jsonify({
                "success": True,
                "message": f"Reprint job #{res.get('job_id')} dispatched successfully!",
                "result": res
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/jobs", methods=["GET"])
@cashier_or_admin_required
def list_print_jobs_api():
    """Retrieve recent thermal print jobs with status, width, and error details."""
    try:
        with get_db() as db:
            limit = int(request.args.get("limit", 30))
            jobs = db.query(PrintJob).order_by(PrintJob.id.desc()).limit(limit).all()
            return jsonify({
                "success": True,
                "jobs": [j.to_dict() for j in jobs]
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@printer_bp.route("/api/printer/jobs/<int:job_id>/retry", methods=["POST"])
@cashier_or_admin_required
def retry_job_api(job_id):
    """Retry a failed print job."""
    try:
        with get_db() as db:
            res = PrinterManager.retry_print_job(db, job_id=job_id)
            if not res.get("success"):
                return jsonify(res), 400
            return jsonify({
                "success": True,
                "message": f"Print job #{job_id} retried!",
                "result": res
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
