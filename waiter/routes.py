"""
Waiter Mobile Ordering Routes & Controller
==========================================
Provides lightweight mobile-optimized endpoints for floor waiters to:
- Browse digital menu & dish availability
- Select Tables 1 to 12
- Place new orders for dining tables
- Edit active orders (add items, remove items, change quantities, edit notes)
- Track active table orders in real time
"""

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from database.db import get_db, record_audit_log
from database.models import Category, MenuItem, Order, OrderItem, DiningTable
from auth.utils import waiter_or_staff_required, get_current_user_context

waiter_bp = Blueprint("waiter", __name__, template_folder="templates")


@waiter_bp.route("/waiter", methods=["GET"])
@waiter_or_staff_required
def waiter_view():
    """Renders the mobile-first Waiter App interface."""
    return render_template(
        "waiter.html",
        user_name=session.get("user_name", "Waiter"),
        user_role=session.get("role", "waiter")
    )


@waiter_bp.route("/api/waiter/menu", methods=["GET"])
@waiter_or_staff_required
def get_waiter_menu():
    """Retrieve active food categories and available dishes."""
    try:
        with get_db() as db:
            categories = (
                db.query(Category)
                .filter_by(is_active=True)
                .order_by(Category.display_order.asc(), Category.name.asc())
                .all()
            )

            catalog = []
            for cat in categories:
                available_items = [
                    item.to_dict()
                    for item in cat.items
                    if item.is_available
                ]
                available_items.sort(key=lambda x: (x["display_order"], x["name"]))
                catalog.append({
                    "id": cat.id,
                    "name": cat.name,
                    "display_order": cat.display_order,
                    "items": available_items
                })

            # Include uncategorized items if any
            uncategorized = (
                db.query(MenuItem)
                .filter(MenuItem.category_id.is_(None), MenuItem.is_available == True)
                .order_by(MenuItem.display_order.asc(), MenuItem.name.asc())
                .all()
            )
            if uncategorized:
                catalog.append({
                    "id": 0,
                    "name": "General Dishes",
                    "display_order": 999,
                    "items": [i.to_dict() for i in uncategorized]
                })

            return jsonify({
                "success": True,
                "categories": catalog
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@waiter_bp.route("/api/waiter/tables", methods=["GET"])
@waiter_or_staff_required
def get_waiter_tables():
    """Return live status of all 12 tables and their active orders."""
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
                active_ord = order_by_table.get(t_num)
                if active_ord:
                    elapsed_min = int((datetime.now() - active_ord.created_at).total_seconds() / 60) if active_ord.created_at else 0
                    tables.append({
                        "table_number": t_num,
                        "status": "OCCUPIED",
                        "order_id": active_ord.id,
                        "order_number": active_ord.order_number,
                        "order_status": active_ord.status,
                        "customer_name": active_ord.customer_name or "",
                        "notes": active_ord.notes or "",
                        "items_count": len(active_ord.items) if active_ord.items else 0,
                        "total_amount": float(active_ord.total_amount),
                        "created_by": active_ord.created_by_name,
                        "created_at_time": active_ord.created_at.strftime("%I:%M %p") if active_ord.created_at else None,
                        "elapsed_minutes": elapsed_min,
                        "items": [i.to_dict() for i in active_ord.items] if active_ord.items else []
                    })
                else:
                    tables.append({
                        "table_number": t_num,
                        "status": "VACANT",
                        "order_id": None,
                        "order_number": None,
                        "order_status": "VACANT",
                        "customer_name": "",
                        "notes": "",
                        "items_count": 0,
                        "total_amount": 0.0,
                        "created_by": None,
                        "created_at_time": None,
                        "elapsed_minutes": 0,
                        "items": []
                    })

            return jsonify({
                "success": True,
                "total_tables": 12,
                "occupied_count": len(active_orders),
                "vacant_count": 12 - len(active_orders),
                "tables": tables
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@waiter_bp.route("/api/waiter/tables/<int:table_no>/order", methods=["GET"])
@waiter_or_staff_required
def get_table_order_details(table_no):
    """Retrieve full active order details for a specific table so the waiter can edit it."""
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
            if not order:
                return jsonify({
                    "success": True,
                    "table_number": table_no,
                    "status": "VACANT",
                    "order": None
                })

            return jsonify({
                "success": True,
                "table_number": table_no,
                "status": "OCCUPIED",
                "order": order.to_dict()
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@waiter_bp.route("/api/waiter/tables/<int:table_no>/order", methods=["PUT"])
@waiter_or_staff_required
def update_table_order(table_no):
    """
    Directly update the active order on Table `table_no`:
    Add items, remove items, adjust quantities, update notes.
    """
    try:
        data = request.get_json(force=True)
        cart_items = data.get("items", [])
        notes = data.get("notes")
        customer_name = data.get("customer_name")
        ctx = get_current_user_context()

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
            if not order:
                return jsonify({"success": False, "error": f"No active order found on Table {table_no}"}), 404

            # If cart_items is empty, cancel order and free table
            if not cart_items or len(cart_items) == 0:
                order.status = "CANCELLED"
                order.notes = (order.notes or "") + " [All items removed by waiter]"
                d_tbl = db.query(DiningTable).filter_by(table_number=table_no).first()
                if d_tbl:
                    d_tbl.status = "VACANT"
                    d_tbl.current_order_id = None
                db.flush()
                return jsonify({
                    "success": True,
                    "message": f"Table {table_no} order cancelled and table freed.",
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
                return jsonify({"success": False, "error": "No valid items in update"}), 400

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
                action="EDIT_TABLE_ORDER",
                entity="ORDER",
                entity_id=str(order.id),
                details=f"Waiter updated Table {table_no} order ({len(new_db_items)} items, Total: Rs.{subtotal})",
                **ctx
            )

            return jsonify({
                "success": True,
                "message": f"Table {table_no} order updated! ({len(new_db_items)} items, Rs.{subtotal:.2f})",
                "order": order.to_dict()
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@waiter_bp.route("/api/waiter/orders/my-active", methods=["GET"])
@waiter_or_staff_required
def get_my_active_orders():
    """Fetch all active dining orders for live tracking by floor staff."""
    try:
        with get_db() as db:
            orders = (
                db.query(Order)
                .filter(
                    Order.order_type == "DINING",
                    Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])
                )
                .order_by(Order.table_number.asc(), Order.id.desc())
                .all()
            )
            return jsonify({
                "success": True,
                "count": len(orders),
                "orders": [o.to_dict() for o in orders]
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
