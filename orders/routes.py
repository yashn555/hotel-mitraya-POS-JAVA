"""
Unified Order Management Controller & API Routes
=================================================
Manages end-to-end lifecycle for restaurant dining & walk-in orders.
Provides robust order placement, editing (adding/removing items),
kitchen display feed, and live cashier synchronization.
"""

from datetime import datetime, date, time
from flask import Blueprint, request, jsonify, session, render_template
from sqlalchemy import func, desc
from database.db import get_db, record_audit_log
from database.models import Order, OrderItem, MenuItem, PosBill, PosBillItem, PrintEvent, DiningTable
from auth.utils import login_required, waiter_or_staff_required, cashier_or_admin_required, admin_required, get_current_user_context

orders_bp = Blueprint("orders", __name__)


def generate_next_order_number(db_session) -> str:
    """Generate sequential order number formatted as ORD-YYYYMMDD-001 or ORD-000001."""
    today_prefix = datetime.now().strftime("ORD-%Y%m%d-")
    last_order = (
        db_session.query(Order)
        .filter(Order.order_number.like(f"{today_prefix}%"))
        .order_by(Order.id.desc())
        .first()
    )
    if not last_order or not last_order.order_number:
        return f"{today_prefix}001"

    try:
        raw_num = last_order.order_number.split("-")[-1]
        next_num = int(raw_num) + 1
        return f"{today_prefix}{next_num:03d}"
    except Exception:
        count = db_session.query(Order).count()
        return f"{today_prefix}{count + 1:03d}"


@orders_bp.route("/kitchen", methods=["GET"])
@orders_bp.route("/kds", methods=["GET"])
def kitchen_view():
    """Simple, dedicated Kitchen Display Screen showing orders with menu items & table numbers."""
    return render_template(
        "kitchen.html",
        user_role=session.get("role", "staff"),
        user_name=session.get("user_name", "Kitchen Staff")
    )


@orders_bp.route("/api/orders/kitchen", methods=["GET"])
def kitchen_orders_api():
    """
    Lightweight, clean endpoint for Kitchen Screen:
    Returns active orders with Table Number / Walk-in reference, Items, Quantities, and Notes.
    """
    try:
        with get_db() as db:
            active_orders = (
                db.query(Order)
                .filter(Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"]))
                .order_by(Order.id.asc())
                .all()
            )

            tickets = []
            for o in active_orders:
                elapsed_min = int((datetime.now() - o.created_at).total_seconds() / 60) if o.created_at else 0
                items_list = [
                    {
                        "item_name": itm.item_name,
                        "quantity": itm.quantity,
                        "notes": itm.item_notes or ""
                    }
                    for itm in (o.items or [])
                ]
                tickets.append({
                    "id": o.id,
                    "order_number": o.order_number,
                    "table_number": o.table_number,
                    "table_label": f"Table {o.table_number}" if o.table_number else (f"Walk-in ({o.customer_name})" if o.customer_name else "Walk-in"),
                    "customer_name": o.customer_name or "",
                    "notes": o.notes or "",
                    "created_at_time": o.created_at.strftime("%I:%M %p") if o.created_at else "",
                    "elapsed_minutes": elapsed_min,
                    "items": items_list
                })

            return jsonify({
                "success": True,
                "server_time": datetime.now().strftime("%I:%M:%S %p"),
                "count": len(tickets),
                "orders": tickets
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/api/orders", methods=["POST"])
@waiter_or_staff_required
def create_order_api():
    """
    Create a new dining or walk-in order.
    Calculates prices server-side. If an active dining order exists for the table, appends items.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No order payload provided"}), 400

        cart_items = data.get("items", [])
        if not cart_items or len(cart_items) == 0:
            return jsonify({"success": False, "error": "Cannot place empty order. Please select items."}), 400

        order_type = str(data.get("order_type", "DINING")).strip().upper()
        if order_type not in ["DINING", "WALK_IN", "TAKEAWAY"]:
            order_type = "DINING"

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
        source = str(data.get("source", session.get("role", "WAITER"))).strip().upper()

        user_id = session.get("user_id")
        user_role = session.get("role", "waiter")
        user_name = session.get("user_name", "Staff")
        ctx = get_current_user_context()

        with get_db() as db:
            # If active order exists on this table, append items to it
            if table_number and order_type == "DINING":
                existing_active = (
                    db.query(Order)
                    .filter(
                        Order.table_number == table_number,
                        Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])
                    )
                    .first()
                )
                if existing_active:
                    return append_items_to_existing_order(db, existing_active, cart_items, notes, ctx)

            order_number = generate_next_order_number(db)
            subtotal = 0.0
            order_items_list = []

            for entry in cart_items:
                item_id = entry.get("menu_item_id") or entry.get("id")
                qty = float(entry.get("quantity", 1))
                if qty <= 0:
                    continue

                item_notes = str(entry.get("item_notes", entry.get("notes", ""))).strip() or None
                name = str(entry.get("name", entry.get("item_name", ""))).strip()
                unit_price = float(entry.get("unit_price", entry.get("price", 0)))

                if item_id:
                    m_item = db.query(MenuItem).filter_by(id=int(item_id)).first()
                    if m_item:
                        name = m_item.name
                        unit_price = float(m_item.price)

                line_total = round(qty * unit_price, 2)
                subtotal += line_total

                db_item = OrderItem(
                    menu_item_id=int(item_id) if item_id else None,
                    item_name=name,
                    unit_price=unit_price,
                    quantity=qty,
                    item_notes=item_notes,
                    total_price=line_total
                )
                order_items_list.append(db_item)

            if not order_items_list:
                return jsonify({"success": False, "error": "No valid items to place order"}), 400

            subtotal = round(subtotal, 2)

            order = Order(
                order_number=order_number,
                source=source,
                order_type=order_type,
                table_number=table_number,
                customer_name=customer_name,
                notes=notes,
                status="PLACED",
                subtotal=subtotal,
                total_amount=subtotal,
                created_by_user_id=user_id,
                created_by_role=user_role,
                created_by_name=user_name,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            order.items = order_items_list

            db.add(order)
            db.flush()

            if table_number and order_type == "DINING":
                d_tbl = db.query(DiningTable).filter_by(table_number=table_number).first()
                if d_tbl:
                    d_tbl.status = "OCCUPIED"
                    d_tbl.current_order_id = order.id
                db.flush()

            record_audit_log(
                db,
                action="CREATE_ORDER",
                entity="ORDER",
                entity_id=str(order.id),
                details=f"Created Order #{order.order_number} ({order.table_label}, {len(order_items_list)} items, Total: Rs.{subtotal})",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Order #{order.order_number} placed successfully!",
                "order": order.to_dict()
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


def append_items_to_existing_order(db, existing_order: Order, new_items: list, new_notes: str, ctx: dict):
    """Helper to incrementally add dishes to an active table order."""
    subtotal = float(existing_order.subtotal or 0.0)
    added_count = 0

    for entry in new_items:
        item_id = entry.get("menu_item_id") or entry.get("id")
        qty = float(entry.get("quantity", 1))
        if qty <= 0:
            continue

        item_notes = str(entry.get("item_notes", entry.get("notes", ""))).strip() or None
        name = str(entry.get("name", entry.get("item_name", ""))).strip()
        unit_price = float(entry.get("unit_price", entry.get("price", 0)))

        if item_id:
            m_item = db.query(MenuItem).filter_by(id=int(item_id)).first()
            if m_item:
                name = m_item.name
                unit_price = float(m_item.price)

        line_total = round(qty * unit_price, 2)
        subtotal += line_total

        existing_item = None
        for itm in existing_order.items:
            if itm.menu_item_id == (int(item_id) if item_id else None) and itm.item_name == name and itm.item_notes == item_notes:
                existing_item = itm
                break

        if existing_item:
            existing_item.quantity += qty
            existing_item.total_price = round(existing_item.quantity * existing_item.unit_price, 2)
        else:
            db_item = OrderItem(
                order_id=existing_order.id,
                menu_item_id=int(item_id) if item_id else None,
                item_name=name,
                unit_price=unit_price,
                quantity=qty,
                item_notes=item_notes,
                total_price=line_total
            )
            existing_order.items.append(db_item)
        added_count += 1

    if new_notes and new_notes not in (existing_order.notes or ""):
        existing_order.notes = f"{existing_order.notes}; {new_notes}" if existing_order.notes else new_notes

    existing_order.subtotal = round(subtotal, 2)
    existing_order.total_amount = round(subtotal, 2)
    existing_order.updated_at = datetime.now()

    db.flush()

    record_audit_log(
        db,
        action="UPDATE_ORDER_ITEMS",
        entity="ORDER",
        entity_id=str(existing_order.id),
        details=f"Added {added_count} items to Order #{existing_order.order_number} (New Total: Rs.{existing_order.total_amount})",
        **ctx
    )

    return jsonify({
        "success": True,
        "message": f"Added {added_count} items to existing Order #{existing_order.order_number}!",
        "order": existing_order.to_dict()
    })


@orders_bp.route("/api/orders/<int:order_id>", methods=["PUT"])
@waiter_or_staff_required
def update_order_items_api(order_id):
    """
    Full editing of an active order's items (Add / Remove / Modify quantity / Notes).
    Used by Floor Waiters when dining customers want to add or remove dishes.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No update payload provided"}), 400

        cart_items = data.get("items", [])
        notes = data.get("notes")
        customer_name = data.get("customer_name")
        ctx = get_current_user_context()

        with get_db() as db:
            order = db.query(Order).filter_by(id=order_id).first()
            if not order:
                return jsonify({"success": False, "error": "Order not found"}), 404

            if order.status in ["COMPLETED", "CANCELLED"]:
                return jsonify({"success": False, "error": f"Cannot edit an order that is already {order.status}"}), 400

            # If cart_items is empty, waiter removed all items -> cancel order
            if not cart_items or len(cart_items) == 0:
                order.status = "CANCELLED"
                order.notes = (order.notes or "") + " [All items removed by waiter]"
                if order.table_number:
                    d_tbl = db.query(DiningTable).filter_by(table_number=order.table_number).first()
                    if d_tbl:
                        d_tbl.status = "VACANT"
                        d_tbl.current_order_id = None
                db.flush()
                return jsonify({
                    "success": True,
                    "message": f"All items removed. Order #{order.order_number} cancelled and table freed.",
                    "order": order.to_dict()
                })

            # Replace items
            order.items.clear()
            db.flush()

            subtotal = 0.0
            new_db_items = []

            for entry in cart_items:
                item_id = entry.get("menu_item_id") or entry.get("id")
                qty = float(entry.get("quantity", 1))
                if qty <= 0:
                    continue

                item_notes = str(entry.get("item_notes", entry.get("notes", ""))).strip() or None
                name = str(entry.get("name", entry.get("item_name", ""))).strip()
                unit_price = float(entry.get("unit_price", entry.get("price", 0)))

                if item_id:
                    m_item = db.query(MenuItem).filter_by(id=int(item_id)).first()
                    if m_item:
                        name = m_item.name
                        unit_price = float(m_item.price)

                line_total = round(qty * unit_price, 2)
                subtotal += line_total

                db_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=int(item_id) if item_id else None,
                    item_name=name,
                    unit_price=unit_price,
                    quantity=qty,
                    item_notes=item_notes,
                    total_price=line_total
                )
                new_db_items.append(db_item)

            if not new_db_items:
                return jsonify({"success": False, "error": "No valid items in update payload"}), 400

            subtotal = round(subtotal, 2)
            order.items = new_db_items
            order.subtotal = subtotal
            order.total_amount = subtotal
            if notes is not None:
                order.notes = str(notes).strip()
            if customer_name is not None:
                order.customer_name = str(customer_name).strip()
            order.updated_at = datetime.now()

            db.flush()

            record_audit_log(
                db,
                action="EDIT_ORDER",
                entity="ORDER",
                entity_id=str(order.id),
                details=f"Waiter updated Order #{order.order_number} ({len(new_db_items)} items, Total: Rs.{subtotal})",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Order #{order.order_number} updated successfully! ({len(new_db_items)} items, Rs.{subtotal:.2f})",
                "order": order.to_dict()
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/api/orders", methods=["GET"])
@waiter_or_staff_required
def list_orders_api():
    """List orders with optional filters by status, table, role, and date."""
    try:
        status_filter = request.args.get("status", "").strip().upper()
        table_filter = request.args.get("table_number")
        limit = int(request.args.get("limit", 50))
        my_orders_only = request.args.get("my_orders", "").lower() in ["true", "1"]

        with get_db() as db:
            query = db.query(Order)

            if my_orders_only and session.get("user_id"):
                query = query.filter(Order.created_by_user_id == session.get("user_id"))

            if status_filter:
                if "," in status_filter:
                    statuses = [s.strip() for s in status_filter.split(",")]
                    query = query.filter(Order.status.in_(statuses))
                else:
                    query = query.filter_by(status=status_filter)

            if table_filter:
                try:
                    query = query.filter_by(table_number=int(table_filter))
                except ValueError:
                    pass

            orders = query.order_by(Order.id.desc()).limit(limit).all()

            return jsonify({
                "success": True,
                "count": len(orders),
                "orders": [o.to_dict() for o in orders]
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/api/orders/<int:order_id>", methods=["GET"])
@waiter_or_staff_required
def get_order_api(order_id):
    """Retrieve details for a specific order."""
    try:
        with get_db() as db:
            order = db.query(Order).filter_by(id=order_id).first()
            if not order:
                return jsonify({"success": False, "error": "Order not found"}), 404
            return jsonify({
                "success": True,
                "order": order.to_dict()
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/api/orders/<int:order_id>/status", methods=["PATCH", "POST"])
@cashier_or_admin_required
def update_order_status_api(order_id):
    """Update order lifecycle status."""
    try:
        data = request.get_json(force=True)
        new_status = str(data.get("status", "")).strip().upper()
        ctx = get_current_user_context()

        valid_statuses = ["PLACED", "CONFIRMED", "PREPARING", "READY", "COMPLETED", "CANCELLED"]
        if new_status not in valid_statuses:
            return jsonify({"success": False, "error": f"Invalid status: {new_status}"}), 400

        with get_db() as db:
            order = db.query(Order).filter_by(id=order_id).first()
            if not order:
                return jsonify({"success": False, "error": "Order not found"}), 404

            order.status = new_status
            order.updated_at = datetime.now()
            db.flush()

            record_audit_log(
                db,
                action="STATUS_CHANGE",
                entity="ORDER",
                entity_id=str(order.id),
                details=f"Order #{order.order_number} status changed to {new_status}",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Order #{order.order_number} is now {new_status}",
                "order": order.to_dict()
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/api/orders/<int:order_id>/cancel", methods=["POST"])
@waiter_or_staff_required
def cancel_order_api(order_id):
    """Cancel an active order."""
    try:
        data = request.get_json(silent=True) or {}
        reason = str(data.get("reason", "Cancelled by Staff")).strip()
        ctx = get_current_user_context()

        with get_db() as db:
            order = db.query(Order).filter_by(id=order_id).first()
            if not order:
                return jsonify({"success": False, "error": "Order not found"}), 404

            order.status = "CANCELLED"
            order.notes = f"{order.notes}; CANCELLED: {reason}" if order.notes else f"CANCELLED: {reason}"
            order.updated_at = datetime.now()

            if order.table_number:
                d_tbl = db.query(DiningTable).filter_by(table_number=order.table_number).first()
                if d_tbl and d_tbl.current_order_id == order.id:
                    d_tbl.status = "VACANT"
                    d_tbl.current_order_id = None

            db.flush()

            record_audit_log(
                db,
                action="ORDER_CANCELLED",
                entity="ORDER",
                entity_id=str(order.id),
                details=f"Order #{order.order_number} cancelled. Reason: {reason}",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Order #{order.order_number} cancelled successfully.",
                "order": order.to_dict()
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/api/orders/live", methods=["GET"])
@waiter_or_staff_required
def live_orders_sync_api():
    """
    High-speed synchronization endpoint for Counter & Waiter screens:
    Returns active orders summary and open dining table count.
    """
    try:
        with get_db() as db:
            active_orders = (
                db.query(Order)
                .filter(Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"]))
                .order_by(Order.id.asc())
                .all()
            )

            table_orders = {}
            for ord_obj in active_orders:
                if ord_obj.table_number:
                    table_orders[ord_obj.table_number] = ord_obj.to_dict()

            return jsonify({
                "success": True,
                "server_time": datetime.now().strftime("%I:%M:%S %p"),
                "active_orders_count": len(active_orders),
                "active_orders": [o.to_dict() for o in active_orders],
                "table_orders": table_orders
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
