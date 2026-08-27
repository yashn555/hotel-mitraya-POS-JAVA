"""
Quick POS Billing Routes & Controller
=====================================
Provides high-speed walk-in restaurant checkout, item catalog retrieval,
sequential bill generation (e.g., POS-000001), and 80mm thermal receipt printing.
"""

from datetime import datetime, date
from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import func
from database.db import get_db
from database.models import Category, MenuItem, PosBill, PosBillItem, User
from auth.utils import cashier_or_admin_required

pos_bp = Blueprint("pos", __name__, template_folder="templates")


def generate_next_pos_bill_number(db_session) -> str:
    """Generate sequential POS bill numbers formatted as POS-000001."""
    last_bill = (
        db_session.query(PosBill)
        .order_by(PosBill.id.desc())
        .first()
    )
    if not last_bill or not last_bill.bill_number:
        return "POS-000001"

    # Extract numeric part
    try:
        raw_num = last_bill.bill_number.replace("POS-", "")
        next_num = int(raw_num) + 1
        return f"POS-{next_num:06d}"
    except Exception:
        total_count = db_session.query(PosBill).count()
        return f"POS-{total_count + 1:06d}"


@pos_bp.route("/pos", methods=["GET"])
@cashier_or_admin_required
def pos_view():
    return render_template(
        "pos.html",
        user_role=session.get("role", "cashier"),
        user_name=session.get("user_name", "Staff")
    )


@pos_bp.route("/api/pos/catalog", methods=["GET"])
@cashier_or_admin_required
def get_pos_catalog():
    """Return active categories and available food items for POS screen."""
    try:
        with get_db() as db:
            categories = (
                db.query(Category)
                .filter_by(is_active=True)
                .order_by(Category.display_order.asc(), Category.name.asc())
                .all()
            )

            result = []
            for cat in categories:
                items = [
                    item.to_dict()
                    for item in cat.items
                    if item.is_available
                ]
                # Sort items by display order
                items.sort(key=lambda x: (x["display_order"], x["name"]))
                result.append({
                    "id": cat.id,
                    "name": cat.name,
                    "display_order": cat.display_order,
                    "items": items
                })

            # Also return unassigned active items if any
            uncategorized_items = (
                db.query(MenuItem)
                .filter(MenuItem.category_id.is_(None), MenuItem.is_available == True)
                .order_by(MenuItem.display_order.asc(), MenuItem.name.asc())
                .all()
            )
            if uncategorized_items:
                result.append({
                    "id": 0,
                    "name": "General / Others",
                    "display_order": 999,
                    "items": [item.to_dict() for item in uncategorized_items]
                })

            return jsonify({"success": True, "categories": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/checkout", methods=["POST"])
@cashier_or_admin_required
def pos_checkout():
    """
    Process walk-in POS checkout:
    Creates PosBill, captures item name & unit price snapshot, calculates totals/change.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No order payload provided"}), 400

        cart_items = data.get("items", [])
        if not cart_items or len(cart_items) == 0:
            return jsonify({"success": False, "error": "Cart is empty. Please add items to bill."}), 400

        payment_mode = str(data.get("payment_mode", "CASH")).strip().upper()
        if payment_mode not in ["CASH", "UPI", "CARD"]:
            payment_mode = "CASH"

        discount = float(data.get("discount", 0) or 0)
        received_raw = data.get("received_amount")
        received_amount = float(received_raw) if (received_raw is not None and str(received_raw).strip() != "") else None

        with get_db() as db:
            bill_number = generate_next_pos_bill_number(db)
            
            subtotal = 0.0
            db_bill_items = []

            for entry in cart_items:
                item_id = entry.get("menu_item_id")
                qty = float(entry.get("quantity", 1))
                if qty <= 0:
                    continue

                # Fetch master item to guarantee current price snapshot
                name = str(entry.get("name", "")).strip()
                unit_price = float(entry.get("unit_price", 0))

                if item_id:
                    m_item = db.query(MenuItem).filter_by(id=item_id).first()
                    if m_item:
                        name = m_item.name
                        unit_price = float(m_item.price)

                line_total = round(qty * unit_price, 2)
                subtotal += line_total

                db_item = PosBillItem(
                    menu_item_id=item_id,
                    item_name=name,
                    unit_price=unit_price,
                    quantity=qty,
                    total_price=line_total
                )
                db_bill_items.append(db_item)

            if not db_bill_items:
                return jsonify({"success": False, "error": "Invalid items in cart"}), 400

            subtotal = round(subtotal, 2)
            discount = min(discount, subtotal)
            total_amount = max(0.0, round(subtotal - discount, 2))

            # Change calculation for CASH
            change_amount = None
            if payment_mode == "CASH":
                if received_amount is None:
                    received_amount = total_amount
                change_amount = max(0.0, round(received_amount - total_amount, 2))

            current_role = session.get("role", "cashier")

            bill = PosBill(
                bill_number=bill_number,
                subtotal=subtotal,
                discount=discount,
                total_amount=total_amount,
                payment_mode=payment_mode,
                received_amount=received_amount,
                change_amount=change_amount,
                cashier_role=current_role,
                status="COMPLETED",
                created_at=datetime.now()
            )
            bill.items = db_bill_items

            db.add(bill)
            db.flush()

            bill_data = bill.to_dict()

            return jsonify({
                "success": True,
                "message": f"Bill #{bill.bill_number} generated successfully!",
                "bill": bill_data
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/bills/recent", methods=["GET"])
@cashier_or_admin_required
def get_recent_pos_bills():
    """Fetch recent POS bills for today for quick reprint drawer."""
    try:
        with get_db() as db:
            limit = int(request.args.get("limit", 25))
            bills = (
                db.query(PosBill)
                .order_by(PosBill.id.desc())
                .limit(limit)
                .all()
            )
            return jsonify({
                "success": True,
                "bills": [b.to_dict() for b in bills]
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/bills/<bill_identifier>", methods=["GET"])
@cashier_or_admin_required
def get_pos_bill_details(bill_identifier):
    """Retrieve full bill details by ID or Bill Number for reprinting."""
    try:
        with get_db() as db:
            if bill_identifier.isdigit():
                bill = db.query(PosBill).filter_by(id=int(bill_identifier)).first()
            else:
                bill = db.query(PosBill).filter_by(bill_number=bill_identifier).first()

            if not bill:
                return jsonify({"success": False, "error": "POS Bill not found"}), 404

            return jsonify({
                "success": True,
                "bill": bill.to_dict()
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
