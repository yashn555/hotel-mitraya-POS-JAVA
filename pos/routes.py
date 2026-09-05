"""
Quick POS Billing Routes & Counter Operations Controller
=========================================================
Serves the Billing Counter & Thermal Printing Point:
1. Walk-in Customer: Fast menu checkout with automatic thermal receipt printing.
2. Dining Active Orders: Live view of Tables 1-12 with Waiter-placed orders,
   one-click settlement (Cash/UPI/Card/Discount), receipt printing, and table release.
3. Recent Bills History & Instant Reprint Drawer.
"""

from datetime import datetime, date, time
from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import func
from database.db import get_db, record_audit_log
from database.models import Category, MenuItem, PosBill, PosBillItem, PrintEvent, Order, OrderItem, DiningTable
from auth.utils import cashier_or_admin_required, login_required, get_current_user_context
from printer.manager import PrinterManager

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
    """Renders the Cashier Counter POS interface."""
    return render_template(
        "pos.html",
        user_role=session.get("role", "cashier"),
        user_name=session.get("user_name", "Staff")
    )


@pos_bp.route("/api/pos/catalog", methods=["GET"])
@login_required
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
                items.sort(key=lambda x: (x["display_order"], x["name"]))
                result.append({
                    "id": cat.id,
                    "name": cat.name,
                    "display_order": cat.display_order,
                    "items": items
                })

            uncategorized_items = (
                db.query(MenuItem)
                .filter(MenuItem.category_id.is_(None), MenuItem.is_available == True)
                .order_by(MenuItem.display_order.asc(), MenuItem.name.asc())
                .all()
            )
            if uncategorized_items:
                result.append({
                    "id": 0,
                    "name": "General Dishes",
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
    """Polling endpoint for the Dedicated Display Screen connected to the wired printer."""
    try:
        since_id = int(request.args.get("since_id", 0))
        limit = int(request.args.get("limit", 5))

        with get_db() as db:
            max_event_id = db.query(func.coalesce(func.max(PrintEvent.id), 0)).scalar() or 0

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

            recent_completed = (
                db.query(PosBill)
                .filter(PosBill.status == "COMPLETED")
                .order_by(PosBill.id.desc())
                .limit(limit)
                .all()
            )

            active_tabs_count = (
                db.query(func.count(Order.id))
                .filter(Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"]))
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
    Get live status for all 12 tables and their active waiter-placed orders.
    """
    try:
        with get_db() as db:
            active_orders = (
                db.query(Order)
                .filter(
                    Order.order_type == "DINING",
                    Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])
                )
                .all()
            )
            order_by_table = {o.table_number: o for o in active_orders if o.table_number}

            tables = []
            for t_num in range(1, 13):
                active_o = order_by_table.get(t_num)
                if active_o:
                    elapsed_min = int((datetime.now() - active_o.created_at).total_seconds() / 60) if active_o.created_at else 0
                    order_dict = {
                        "id": active_o.id,
                        "order_id": active_o.id,
                        "order_number": active_o.order_number,
                        "table_number": t_num,
                        "customer_name": active_o.customer_name or "",
                        "notes": active_o.notes or "",
                        "items_count": len(active_o.items) if active_o.items else 0,
                        "subtotal": float(active_o.subtotal),
                        "total_amount": float(active_o.total_amount),
                        "created_by": active_o.created_by_name,
                        "created_at": active_o.created_at.strftime("%I:%M %p") if active_o.created_at else None,
                        "elapsed_minutes": elapsed_min,
                        "order_status": active_o.status,
                        "items": [i.to_dict() for i in active_o.items] if active_o.items else []
                    }
                    table_entry = dict(order_dict)
                    table_entry["status"] = "OCCUPIED"
                    table_entry["active_order"] = order_dict
                    table_entry["active_bill"] = order_dict
                    tables.append(table_entry)
                else:
                    tables.append({
                        "table_number": t_num,
                        "status": "VACANT",
                        "order_id": None,
                        "order_number": None,
                        "customer_name": "",
                        "notes": "",
                        "items_count": 0,
                        "subtotal": 0.0,
                        "total_amount": 0.0,
                        "created_by": None,
                        "created_at": None,
                        "elapsed_minutes": 0,
                        "order_status": "VACANT",
                        "items": []
                    })

            occupied_count = len(order_by_table)

            return jsonify({
                "success": True,
                "total_tables": 12,
                "occupied_count": occupied_count,
                "vacant_count": 12 - occupied_count,
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
            order = (
                db.query(Order)
                .filter(
                    Order.table_number == table_no,
                    Order.order_type == "DINING",
                    Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])
                )
                .first()
            )
            if order:
                order_dict = order.to_dict()
                order_dict["bill_number"] = order.order_number
                order_dict["payment_mode"] = "CASH"
                order_dict["discount"] = 0.0
                return jsonify({
                    "success": True,
                    "table_number": table_no,
                    "status": "OCCUPIED",
                    "order": order_dict,
                    "bill": order_dict
                })

            return jsonify({
                "success": True,
                "table_number": table_no,
                "status": "VACANT",
                "order": None,
                "bill": None
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/checkout", methods=["POST"])
@cashier_or_admin_required
def pos_checkout():
    """
    Direct Walk-in Counter instant POS checkout:
    Creates PosBill, computes server-side price snapshot, marks COMPLETED,
    creates PrintJob, dispatches to thermal printer, and returns bill for instant auto-print.
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
        ctx = get_current_user_context()

        with get_db() as db:
            bill_number = generate_next_pos_bill_number(db)
            subtotal = 0.0
            db_bill_items = []

            for entry in cart_items:
                item_id = entry.get("menu_item_id") or entry.get("id")
                qty = float(entry.get("quantity", 1))
                if qty <= 0:
                    continue

                name = str(entry.get("name", entry.get("item_name", ""))).strip()
                unit_price = float(entry.get("unit_price", entry.get("price", 0)))

                if item_id:
                    m_item = db.query(MenuItem).filter_by(id=int(item_id)).first()
                    if m_item:
                        name = m_item.name
                        unit_price = float(m_item.price)

                line_total = round(qty * unit_price, 2)
                subtotal += line_total

                db_item = PosBillItem(
                    menu_item_id=int(item_id) if item_id else None,
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

            change_amount = None
            if payment_mode == "CASH":
                if received_amount is None:
                    received_amount = total_amount
                change_amount = max(0.0, round(received_amount - total_amount, 2))

            current_cashier = session.get("user_name", session.get("role", "cashier"))

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
                cashier_role=current_cashier,
                status="COMPLETED",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            bill.items = db_bill_items

            db.add(bill)
            db.flush()

            # Record print event for display station
            print_event = PrintEvent(
                pos_bill_id=bill.id,
                event_type="FINAL_BILL",
                created_at=datetime.now()
            )
            db.add(print_event)
            db.flush()

            bill_data = bill.to_dict()

            # Dispatch Thermal Print Job
            print_res = PrinterManager.dispatch_print_job(
                db,
                bill_data=bill_data,
                pos_bill_id=bill.id,
                job_type="FINAL_BILL"
            )

            record_audit_log(
                db,
                action="POS_CHECKOUT",
                entity="BILL",
                entity_id=str(bill.id),
                details=f"Walk-in Checkout: Bill #{bill.bill_number}, Total: Rs.{total_amount} via {payment_mode}",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Bill #{bill.bill_number} generated successfully!",
                "bill": bill_data,
                "print_job": print_res,
                "auto_print": True
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/tables/settle", methods=["POST"])
@cashier_or_admin_required
def settle_table_tab():
    """
    Settle & finalize running table order:
    Calculates final discount, payment mode, change, marks PosBill & Order status as 'COMPLETED',
    creates PrintJob, dispatches to printer, and frees Table (1 to 12).
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No settlement payload provided"}), 400

        try:
            table_no = int(data.get("table_number", 0))
        except (ValueError, TypeError):
            table_no = 0

        payment_mode = str(data.get("payment_mode", "CASH")).strip().upper()
        if payment_mode not in ["CASH", "UPI", "CARD"]:
            payment_mode = "CASH"

        discount = float(data.get("discount", 0) or 0)
        received_raw = data.get("received_amount")
        received_amount = float(received_raw) if (received_raw is not None and str(received_raw).strip() != "") else None
        ctx = get_current_user_context()

        with get_db() as db:
            # Find active Order for this table
            order = None
            if table_no > 0:
                order = db.query(Order).filter(
                    Order.table_number == table_no,
                    Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])
                ).first()

            if not order and data.get("order_id"):
                order = db.query(Order).filter_by(id=int(data.get("order_id"))).first()

            if not order:
                return jsonify({"success": False, "error": f"No active dining order found for Table {table_no}"}), 404

            # Create completed PosBill from the order
            bill_number = generate_next_pos_bill_number(db)
            subtotal = float(order.subtotal or 0.0)
            discount = min(discount, subtotal)
            total_amount = max(0.0, round(subtotal - discount, 2))

            change_amount = None
            if payment_mode == "CASH":
                if received_amount is None:
                    received_amount = total_amount
                change_amount = max(0.0, round(received_amount - total_amount, 2))

            current_cashier = session.get("user_name", session.get("role", "cashier"))

            bill = PosBill(
                bill_number=bill_number,
                order_type="DINING",
                table_number=order.table_number,
                customer_name=order.customer_name,
                notes=order.notes,
                subtotal=subtotal,
                discount=discount,
                total_amount=total_amount,
                payment_mode=payment_mode,
                received_amount=received_amount,
                change_amount=change_amount,
                cashier_role=current_cashier,
                status="COMPLETED",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            for ord_item in order.items:
                bill.items.append(PosBillItem(
                    pos_bill_id=bill.id,
                    menu_item_id=ord_item.menu_item_id,
                    item_name=ord_item.item_name,
                    unit_price=ord_item.unit_price,
                    quantity=ord_item.quantity,
                    total_price=ord_item.total_price
                ))

            db.add(bill)
            db.flush()

            # Mark order as completed
            order.status = "COMPLETED"
            order.bill_id = bill.id
            order.updated_at = datetime.now()

            # Free Table
            if order.table_number:
                d_tbl = db.query(DiningTable).filter_by(table_number=order.table_number).first()
                if d_tbl:
                    d_tbl.status = "VACANT"
                    d_tbl.current_order_id = None

            # Record print event for display station
            print_event = PrintEvent(
                pos_bill_id=bill.id,
                event_type="FINAL_BILL",
                created_at=datetime.now()
            )
            db.add(print_event)
            db.flush()

            bill_data = bill.to_dict()

            # Dispatch Thermal Print Job
            print_res = PrinterManager.dispatch_print_job(
                db,
                bill_data=bill_data,
                pos_bill_id=bill.id,
                job_type="FINAL_BILL"
            )

            record_audit_log(
                db,
                action="SETTLE_BILL",
                entity="BILL",
                entity_id=str(bill.id),
                details=f"Table {order.table_number} settled: Bill #{bill.bill_number}, Total: Rs.{total_amount} via {payment_mode}",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Table {order.table_number} Bill #{bill.bill_number} settled successfully!",
                "bill": bill_data,
                "print_job": print_res,
                "auto_print": True
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@pos_bp.route("/api/pos/tables/<int:table_no>/clear", methods=["POST"])
@cashier_or_admin_required
def clear_table_tab(table_no):
    """Void / cancel an active running table order and free the table."""
    try:
        ctx = get_current_user_context()
        with get_db() as db:
            orders = (
                db.query(Order)
                .filter(
                    Order.table_number == table_no,
                    Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])
                )
                .all()
            )

            if not orders:
                return jsonify({"success": False, "error": f"No active order on Table {table_no}"}), 404

            for ord_obj in orders:
                ord_obj.status = "CANCELLED"
                ord_obj.updated_at = datetime.now()

            d_tbl = db.query(DiningTable).filter_by(table_number=table_no).first()
            if d_tbl:
                d_tbl.status = "VACANT"
                d_tbl.current_order_id = None

            db.flush()

            record_audit_log(
                db,
                action="CANCEL_TABLE_TAB",
                entity="TABLE",
                entity_id=str(table_no),
                details=f"Cancelled active order on Table {table_no}",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Table {table_no} order cancelled and table freed."
            })
    except Exception as e:
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
