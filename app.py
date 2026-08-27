"""
Hotel Mitraya - Bill Generation Web Application Server
======================================================
Provides responsive mobile & desktop web UI, REST APIs for PDF bill creation,
and dedicated management for the `/bills` folder.
"""

import os
import re
import glob
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, abort, session, redirect, url_for
from flask_cors import CORS
from generate_bill_docx import generate_bill_pdf, sanitize_filename

import tempfile
from database.db import init_db
from auth.routes import auth_bp
from admin.routes import admin_bp
from pos.routes import pos_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# In serverless environments like Vercel, use /tmp for writing files
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    BILLS_DIR = os.path.join(tempfile.gettempdir(), "bills")
else:
    BILLS_DIR = os.path.join(BASE_DIR, "bills")
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.docx")

os.makedirs(BILLS_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "hotel-mitraya-secure-billing-key-2026-auth-pin")
app.permanent_session_lifetime = timedelta(days=30)
CORS(app)

# Initialize Relational Database & Seed Data for Quick POS & Users
init_db()

# Register Blueprints for Modular POS Architecture
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(pos_bp)

# Hardcoded Access PIN (can also be overridden in Vercel Environment variables as APP_PIN)
APP_PIN = str(os.environ.get("APP_PIN", "2005")).strip()


@app.before_request
def require_auth():
    # Public routes allowed without PIN
    public_endpoints = {"login", "api_login", "health", "static", "auth.login_api"}
    if request.endpoint in public_endpoints:
        return None
    if request.path.startswith("/static/") or request.path == "/favicon.ico":
        return None

    # Check if user session is authenticated
    if not session.get("authenticated"):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "Authentication required. Please unlock with your PIN.",
                "auth_required": True
            }), 401
        return redirect(url_for("login"))

    # Role-based restriction: Cashier cannot access Admin routes or bulk billing
    role = session.get("role", "admin")
    if role == "cashier":
        if request.path.startswith("/admin") or request.path.startswith("/api/admin"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Access denied. Admin privileges required.", "forbidden": True}), 403
            return redirect(url_for("pos.pos_view"))


@app.route("/login", methods=["GET"])
def login():
    if session.get("authenticated"):
        role = session.get("role", "admin")
        if role == "cashier":
            return redirect(url_for("pos.pos_view"))
        return redirect(url_for("admin_bp.admin_dashboard_view"))
    return render_template("login.html")


@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_from_directory("static", "logo.png", mimetype="image/png")


@app.route("/bulk", methods=["GET"])
def bulk_billing():
    """Bulk / Institution Billing Route (Existing Unchanged System)."""
    return render_template("index.html")




@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/logout", methods=["POST", "GET"])
def api_logout():
    session.clear()
    return jsonify({
        "success": True,
        "message": "Logged out successfully",
        "redirect": "/login"
    })


def get_bill_metadata(filename: str):
    filepath = os.path.join(BILLS_DIR, filename)
    if not os.path.isfile(filepath):
        return None
    stat = os.stat(filepath)
    mtime = datetime.fromtimestamp(stat.st_mtime)
    
    # Try parsing Customer Name and Bill No from filename: <Customer>_<BillNo>.pdf
    name_no_ext = os.path.splitext(filename)[0]
    parts = name_no_ext.rsplit("_", 1)
    if len(parts) == 2:
        customer_display = parts[0].replace("_", " ")
        bill_no_display = parts[1]
    else:
        customer_display = name_no_ext.replace("_", " ")
        bill_no_display = "N/A"

    return {
        "filename": filename,
        "customer_name": customer_display,
        "bill_no": bill_no_display,
        "size_bytes": stat.st_size,
        "size_kb": round(stat.st_size / 1024, 1),
        "created_at": mtime.strftime("%d/%m/%Y %I:%M %p"),
        "timestamp": stat.st_mtime,
        "download_url": f"/api/bills/download/{filename}",
        "preview_url": f"/api/bills/preview/{filename}",
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "bills_count": len([f for f in os.listdir(BILLS_DIR) if f.lower().endswith(".pdf")]),
        "template_exists": os.path.exists(TEMPLATE_PATH)
    })


@app.route("/api/bills/generate", methods=["POST"])
def api_generate_bill():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        customer_name = str(data.get("customer_name", "")).strip()
        bill_no = str(data.get("bill_no", "")).strip()
        created_on = str(data.get("created_on", "")).strip()
        bill_date = str(data.get("bill_date", "")).strip()
        items = data.get("items", [])

        if not customer_name:
            return jsonify({"success": False, "error": "Customer name is required"}), 400
        if not bill_no:
            return jsonify({"success": False, "error": "Bill number is required"}), 400
        if not items or len(items) == 0:
            return jsonify({"success": False, "error": "At least one item is required"}), 400

        # Validate item entries
        sanitized_items = []
        for idx, itm in enumerate(items):
            iname = str(itm.get("name", "")).strip()
            if not iname:
                return jsonify({"success": False, "error": f"Item #{idx+1} has an empty name"}), 400
            try:
                iqty = float(itm.get("qty", 1))
                irate = float(itm.get("rate", 0))
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": f"Invalid Qty or Rate for item '{iname}'"}), 400
            sanitized_items.append({"name": iname, "qty": iqty, "rate": irate})

        # Set default dates if missing
        now = datetime.now()
        if not created_on:
            created_on = now.strftime("%d/%m/%Y %I:%M %p")
        if not bill_date:
            bill_date = now.strftime("%d/%m/%Y")

        discount = float(data.get("discount", 0) or 0)
        txn_mode = str(data.get("txn_mode", "CASH")).strip().upper() or "CASH"
        received_raw = data.get("received_amount", "")
        received_amount = float(received_raw) if (received_raw is not None and str(received_raw).strip() != "") else None

        payload = {
            "customer_name": customer_name,
            "bill_no": bill_no,
            "created_on": created_on,
            "bill_date": bill_date,
            "items": sanitized_items,
            "discount": discount,
            "txn_mode": txn_mode,
            "received_amount": received_amount
        }

        # Generate the PDF bill into /bills
        result = generate_bill_pdf(payload, template_path=TEMPLATE_PATH, bills_dir=BILLS_DIR)
        meta = get_bill_metadata(result["filename"])

        # Read and include base64 PDF for instant client download on serverless platforms like Vercel
        try:
            import base64
            with open(result["filepath"], "rb") as f:
                pdf_bytes = f.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            meta["pdf_base64"] = pdf_b64
            meta["pdf_data_url"] = f"data:application/pdf;base64,{pdf_b64}"
        except Exception as b64_err:
            print(f"[WARN] Base64 encode error: {b64_err}")

        return jsonify({
            "success": True,
            "message": f"Bill #{bill_no} successfully generated as PDF!",
            "bill": meta
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bills", methods=["GET"])
def api_list_bills():
    try:
        search_query = request.args.get("q", "").strip().lower()
        files = [f for f in os.listdir(BILLS_DIR) if f.lower().endswith(".pdf") and not f.startswith(".")]
        
        bills = []
        for fname in files:
            meta = get_bill_metadata(fname)
            if meta:
                if search_query:
                    if (search_query in meta["customer_name"].lower() or 
                        search_query in meta["bill_no"].lower() or 
                        search_query in meta["filename"].lower()):
                        bills.append(meta)
                else:
                    bills.append(meta)

        # Sort newest first
        bills.sort(key=lambda b: b["timestamp"], reverse=True)
        return jsonify({"success": True, "count": len(bills), "bills": bills})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bills/download/<path:filename>", methods=["GET"])
def api_download_bill(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BILLS_DIR, safe_name)
    if not os.path.isfile(filepath):
        # Ephemeral container fallback
        name_no_ext = os.path.splitext(safe_name)[0]
        parts = name_no_ext.rsplit("_", 1)
        if len(parts) == 2:
            cust = parts[0].replace("_", " ")
            bno = parts[1]
            try:
                generate_bill_pdf({
                    "customer_name": cust,
                    "bill_no": bno,
                    "bill_date": datetime.now().strftime("%d/%m/%Y"),
                    "items": [{"name": "Restaurant / Hospitality Services", "qty": 1, "rate": 0}]
                }, bills_dir=BILLS_DIR)
            except Exception:
                pass

    if not os.path.isfile(filepath):
        abort(404, description="Bill PDF not found on this serverless instance")
    return send_from_directory(
        BILLS_DIR,
        safe_name,
        as_attachment=True,
        download_name=safe_name,
        mimetype="application/pdf"
    )


@app.route("/api/bills/preview/<path:filename>", methods=["GET"])
def api_preview_bill(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BILLS_DIR, safe_name)
    if not os.path.isfile(filepath):
        # Ephemeral container fallback
        name_no_ext = os.path.splitext(safe_name)[0]
        parts = name_no_ext.rsplit("_", 1)
        if len(parts) == 2:
            cust = parts[0].replace("_", " ")
            bno = parts[1]
            try:
                generate_bill_pdf({
                    "customer_name": cust,
                    "bill_no": bno,
                    "bill_date": datetime.now().strftime("%d/%m/%Y"),
                    "items": [{"name": "Restaurant / Hospitality Services", "qty": 1, "rate": 0}]
                }, bills_dir=BILLS_DIR)
            except Exception:
                pass

    if not os.path.isfile(filepath):
        abort(404, description="Bill PDF not found on this serverless instance")
    return send_from_directory(
        BILLS_DIR,
        safe_name,
        as_attachment=False,
        mimetype="application/pdf"
    )


@app.route("/api/bills/<path:filename>", methods=["DELETE"])
def api_delete_bill(filename):
    try:
        safe_name = os.path.basename(filename)
        filepath = os.path.join(BILLS_DIR, safe_name)
        if not os.path.isfile(filepath):
            return jsonify({"success": False, "error": "Bill not found"}), 404
        os.remove(filepath)
        return jsonify({"success": True, "message": f"Bill '{safe_name}' deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/next-bill-no", methods=["GET"])
def api_next_bill_no():
    """Look at existing bills and suggest the next numeric bill number."""
    try:
        files = [f for f in os.listdir(BILLS_DIR) if f.lower().endswith(".pdf")]
        max_no = 1000
        for f in files:
            name_no_ext = os.path.splitext(f)[0]
            parts = name_no_ext.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                max_no = max(max_no, int(parts[1]))
        return jsonify({"success": True, "next_bill_no": str(max_no + 1)})
    except Exception:
        return jsonify({"success": True, "next_bill_no": "1001"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Hotel Mitraya Bill Generator running at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


