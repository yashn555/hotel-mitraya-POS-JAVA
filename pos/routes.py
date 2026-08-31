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
from database.models import Category, MenuItem, PosBill, PosBillItem, PrintEvent, User
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


@pos_bp.route("/display", methods=["GET"])
@pos_bp.route("/pos/display", methods=["GET"])
@cashier_or_admin_required
def display_view():
    """Dedicated Live Order & Wired Thermal Print Display Window."""
    return render_template(
        "display.html",
        user_role=session.get("role", "cashier"),
        user_name=session.get("user_name", "Staff")
    )


@pos_bp.route("/api/display/live-orders", methods=["GET"])
@cashier_or_admin_required
def get_live_display_orders():
    """
    Polling endpoint for the Dedicated Display Screen connected to the wired printer:
    Returns new final checkout print events (completed bills only) since `since_id` and active tables summary.
    Running dining tabs (status 'OPEN') do NOT trigger print events.
    """
    try:
        since_id = int(request.args.get("since_id", 0))
        limit = int(request.args.get("limit", 5))

        with get_db() as db:
            max_event_id = db.query(func.coalesce(func.max(PrintEvent.id), 0)).scalar() or 0

            # 1. Query new print events since since_id (only triggered on final checkout / table settlement)
            if since_id > 0:
                new_events = (
                    db.query(PrintEvent)
                    .filter(PrintEvent.id > since_id)
                    .order_by(PrintEvent.id.asc())
                    .all()
                )
                bill_ids = [evt.pos_bill_id for evt in new_events]
                bills_map = {b.id: b for b in db.query(PosBill).filter(PosBill.id.in_(bill_ids)).all()}
                new_bills = [bills_map[evt.pos_bill_id].to_dict() for evt in new_events if evt.pos_bill_id in bills_map]
            else:
                new_bills = []

            # 2. Get top 5 recent COMPLETED bills for the history feed
            recent_completed = (
                db.query(PosBill)
                .filter(PosBill.status == "COMPLETED")
                .order_by(PosBill.id.desc())
                .limit(limit)
                .all()
            )

            # 3. Active dining tables count
            active_tabs_count = (
                db.query(func.count(PosBill.id))
                .filter(PosBill.status == "OPEN", PosBill.order_type == "DINING")
                .scalar() or 0
            )

            return jsonify({
                "success": True,
                "server_time": datetime.now().strftime("%I:%M:%S %p"),
                "bills": [b.to_dict() for b in recent_completed],
                "new_bills": new_bills,
                "max_id": max_event_id,
                "active_tables_count": active_tabs_count
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@pos_bp.route("/api/pos/tables", methods=["GET"])
@cashier_or_admin_required
def get_pos_tables():
    """
    Get live status for all 12 tables:
    Returns Table 1 to Table 12 with status (vacant / occupied), running bill details, items count, total, elapsed time.
    """
    try:
        with get_db() as db:
            active_bills = (
                db.query(PosBill)
                .filter(PosBill.status == "OPEN", PosBill.order_type == "DINING")
                .all()
            )
            bill_by_table = {b.table_number: b for b in active_bills if b.table_number}

            tables = []
            for t_num in range(1, 13):
                active_b = bill_by_table.get(t_num)
                if active_b:
                    elapsed_min = int((datetime.now() - active_b.created_at).total_seconds() / 60) if active_b.created_at else 0
                    tables.append({
                        "table_number": t_num,
                        "status": "OCCUPIED",
                        "bill_id": active_b.id,
                        "bill_number": active_b.bill_number,
                        "customer_name": active_b.customer_name or "",
                        "items_count": len(active_b.items) if active_b.items else 0,
                        "subtotal": float(active_b.subtotal),
                        "total_amount": float(active_b.total_amount),
                        "created_at": active_b.created_at.strftime("%I:%M %p") if active_b.created_at else None,
                        "elapsed_minutes": elapsed_min
                    })
                else:
                    tables.append({
                        "table_number": t_num,
                        "status": "VACANT",
                        "bill_id": None,
                        "bill_number": None,
                        "customer_name": "",
                        "items_count": 0,
                        "subtotal": 0.0,
                        "total_amount": 0.0,
                        "created_at": None,
                        "elapsed_minutes": 0
                    })

            return jsonify({
                "success": True,
                "total_tables": 12,
                "occupied_count": len(active_bills),
                "vacant_count": 12 - len(active_bills),
                "tables": tables
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/tables/<int:table_no>", methods=["GET"])
@cashier_or_admin_required
def get_table_active_order(table_no):
    """Retrieve active running dining order for a specific table (1 to 12)."""
    if table_no < 1 or table_no > 12:
        return jsonify({"success": False, "error": "Table number must be between 1 and 12"}), 400

    try:
        with get_db() as db:
            bill = (
                db.query(PosBill)
                .filter(PosBill.table_number == table_no, PosBill.status == "OPEN", PosBill.order_type == "DINING")
                .first()
            )
            if not bill:
                return jsonify({
                    "success": True,
                    "table_number": table_no,
                    "status": "VACANT",
                    "bill": None
                })

            return jsonify({
                "success": True,
                "table_number": table_no,
                "status": "OCCUPIED",
                "bill": bill.to_dict()
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/tables/save-tab", methods=["POST"])
@cashier_or_admin_required
def save_table_tab():
    """
    Save or incrementally update running dining tab for Table X (1 to 12):
    Allows adding items one by one / gradually while customers are eating.
    Keeps status as 'OPEN'.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No table order payload provided"}), 400

        try:
            table_no = int(data.get("table_number", 0))
        except (ValueError, TypeError):
            table_no = 0

        if table_no < 1 or table_no > 12:
            return jsonify({"success": False, "error": "Valid table number (1-12) is required"}), 400

        cart_items = data.get("items", [])
        if not cart_items or len(cart_items) == 0:
            return jsonify({"success": False, "error": "Cannot save empty table tab. Add dishes first."}), 400

        customer_name = str(data.get("customer_name", "")).strip()
        notes = str(data.get("notes", "")).strip()
        current_role = session.get("role", "cashier")

        with get_db() as db:
            # Check if there is an existing OPEN bill on this table
            bill = (
                db.query(PosBill)
                .filter(PosBill.table_number == table_no, PosBill.status == "OPEN", PosBill.order_type == "DINING")
                .first()
            )

            if not bill:
                bill_number = generate_next_pos_bill_number(db)
                bill = PosBill(
                    bill_number=bill_number,
                    order_type="DINING",
                    table_number=table_no,
                    customer_name=customer_name,
                    notes=notes,
                    subtotal=0.0,
                    discount=0.0,
                    total_amount=0.0,
                    payment_mode="CASH",
                    cashier_role=current_role,
                    status="OPEN",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(bill)
                db.flush()
            else:
                # Update metadata
                if customer_name:
                    bill.customer_name = customer_name
                if notes:
                    bill.notes = notes
                bill.updated_at = datetime.now()
                # Clear existing items and replace with current cart state
                bill.items.clear()
                db.flush()

            subtotal = 0.0
            db_bill_items = []

            for entry in cart_items:
                item_id = entry.get("menu_item_id")
                qty = float(entry.get("quantity", 1))
                if qty <= 0:
                    continue

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
                    pos_bill_id=bill.id,
                    menu_item_id=item_id,
                    item_name=name,
                    unit_price=unit_price,
                    quantity=qty,
                    total_price=line_total
                )
                db_bill_items.append(db_item)

            if not db_bill_items:
                return jsonify({"success": False, "error": "No valid items to save"}), 400

            subtotal = round(subtotal, 2)
            bill.subtotal = subtotal
            bill.total_amount = subtotal
            bill.items = db_bill_items
            db.flush()

            bill_data = bill.to_dict()

            return jsonify({
                "success": True,
                "message": f"Table {table_no} tab saved successfully! ({len(db_bill_items)} items, Total: ₹{subtotal:.2f})",
                "bill": bill_data
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/tables/settle", methods=["POST"])
@cashier_or_admin_required
def settle_table_tab():
    """
    Settle & finalize running table order when customer leaves:
    Calculates final discount, payment mode, change, and marks PosBill status as 'COMPLETED',
    making Table vacant again.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No settlement payload provided"}), 400

        try:
            table_no = int(data.get("table_number", 0))
        except (ValueError, TypeError):
            table_no = 0

        bill_id = data.get("bill_id")
        payment_mode = str(data.get("payment_mode", "CASH")).strip().upper()
        if payment_mode not in ["CASH", "UPI", "CARD"]:
            payment_mode = "CASH"

        discount = float(data.get("discount", 0) or 0)
        received_raw = data.get("received_amount")
        received_amount = float(received_raw) if (received_raw is not None and str(received_raw).strip() != "") else None

        with get_db() as db:
            query = db.query(PosBill).filter(PosBill.status == "OPEN", PosBill.order_type == "DINING")
            if bill_id:
                bill = query.filter(PosBill.id == int(bill_id)).first()
            elif table_no > 0:
                bill = query.filter(PosBill.table_number == table_no).first()
            else:
                return jsonify({"success": False, "error": "Table number or Bill ID is required"}), 400

            if not bill:
                return jsonify({"success": False, "error": f"No active dining tab found for Table {table_no}"}), 404

            # If items payload is provided during settlement, update items
            cart_items = data.get("items")
            if cart_items and len(cart_items) > 0:
                bill.items.clear()
                db.flush()
                subtotal = 0.0
                for entry in cart_items:
                    item_id = entry.get("menu_item_id")
                    qty = float(entry.get("quantity", 1))
                    if qty <= 0:
                        continue
                    name = str(entry.get("name", "")).strip()
                    unit_price = float(entry.get("unit_price", 0))
                    if item_id:
                        m_item = db.query(MenuItem).filter_by(id=item_id).first()
                        if m_item:
                            name = m_item.name
                            unit_price = float(m_item.price)
                    line_total = round(qty * unit_price, 2)
                    subtotal += line_total
                    bill.items.append(PosBillItem(
                        pos_bill_id=bill.id,
                        menu_item_id=item_id,
                        item_name=name,
                        unit_price=unit_price,
                        quantity=qty,
                        total_price=line_total
                    ))
                bill.subtotal = round(subtotal, 2)

            subtotal = float(bill.subtotal or 0.0)
            discount = min(discount, subtotal)
            total_amount = max(0.0, round(subtotal - discount, 2))

            # Change calculation for CASH
            change_amount = None
            if payment_mode == "CASH":
                if received_amount is None:
                    received_amount = total_amount
                change_amount = max(0.0, round(received_amount - total_amount, 2))

            bill.discount = discount
            bill.total_amount = total_amount
            bill.payment_mode = payment_mode
            bill.received_amount = received_amount
            bill.change_amount = change_amount
            bill.status = "COMPLETED"
            bill.updated_at = datetime.now()

            # Record print event for the Display Screen & Wired Printer
            print_event = PrintEvent(
                pos_bill_id=bill.id,
                event_type="FINAL_BILL",
                created_at=datetime.now()
            )
            db.add(print_event)

            db.flush()
            bill_data = bill.to_dict()

            return jsonify({
                "success": True,
                "message": f"Table {bill.table_number} Bill #{bill.bill_number} settled successfully!",
                "bill": bill_data
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/tables/<int:table_no>/clear", methods=["POST"])
@cashier_or_admin_required
def clear_table_tab(table_no):
    """Void / cancel an active running table order."""
    try:
        with get_db() as db:
            bill = (
                db.query(PosBill)
                .filter(PosBill.table_number == table_no, PosBill.status == "OPEN", PosBill.order_type == "DINING")
                .first()
            )
            if not bill:
                return jsonify({"success": False, "error": f"No active order on Table {table_no}"}), 404

            bill.status = "CANCELLED"
            bill.updated_at = datetime.now()
            db.flush()

            return jsonify({
                "success": True,
                "message": f"Table {table_no} order cancelled and table freed."
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/checkout", methods=["POST"])
@cashier_or_admin_required
def pos_checkout():
    """
    Process Walk-in (or Direct Table) instant POS checkout:
    Creates PosBill, captures item name & unit price snapshot, calculates totals/change,
    marks as COMPLETED immediately and sends to Display Screen.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No order payload provided"}), 400

        cart_items = data.get("items", [])
        if not cart_items or len(cart_items) == 0:
            return jsonify({"success": False, "error": "Cart is empty. Please add items to bill."}), 400

        order_type = str(data.get("order_type", "WALK_IN")).strip().upper()
        if order_type not in ["WALK_IN", "DINING"]:
            order_type = "WALK_IN"

        table_number = data.get("table_number")
        if table_number:
            try:
                table_number = int(table_number)
                if table_number < 1 or table_number > 12:
                    table_number = None
            except (ValueError, TypeError):
                table_number = None

        customer_name = str(data.get("customer_name", "")).strip()
        notes = str(data.get("notes", "")).strip()

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
                order_type=order_type,
                table_number=table_number,
                customer_name=customer_name,
                notes=notes,
                subtotal=subtotal,
                discount=discount,
                total_amount=total_amount,
                payment_mode=payment_mode,
                received_amount=received_amount,
                change_amount=change_amount,
                cashier_role=current_role,
                status="COMPLETED",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            bill.items = db_bill_items

            db.add(bill)
            db.flush()

            # Record print event for the Display Screen & Wired Printer
            print_event = PrintEvent(
                pos_bill_id=bill.id,
                event_type="FINAL_BILL",
                created_at=datetime.now()
            )
            db.add(print_event)
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
    """Fetch recent completed POS bills for quick reprint drawer."""
    try:
        with get_db() as db:
            limit = int(request.args.get("limit", 25))
            bills = (
                db.query(PosBill)
                .filter(PosBill.status == "COMPLETED")
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

