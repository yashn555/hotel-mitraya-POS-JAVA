"""
Admin Management & Sales Analytics Controller
==============================================
Provides dashboard views and APIs for Menu Management, POS Bill History,
User/PIN Settings, and Sales Reports (Cash/UPI/Card & Best Sellers).
"""

from datetime import datetime, date, time
from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import func, desc
from database.db import get_db
from database.models import Category, MenuItem, PosBill, PosBillItem, User
from auth.utils import admin_required

admin_bp = Blueprint("admin", __name__, template_folder="templates")


# =========================================================================
# Page Views
# =========================================================================

@admin_bp.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard_view():
    return render_template(
        "admin_dashboard.html",
        user_name=session.get("user_name", "Admin")
    )


@admin_bp.route("/admin/menu", methods=["GET"])
@admin_required
def menu_management_view():
    return render_template(
        "menu_management.html",
        user_name=session.get("user_name", "Admin")
    )


@admin_bp.route("/admin/reports", methods=["GET"])
@admin_required
def sales_reports_view():
    return render_template(
        "sales_reports.html",
        user_name=session.get("user_name", "Admin")
    )


# =========================================================================
# Category Management APIs
# =========================================================================

@admin_bp.route("/api/admin/categories", methods=["GET"])
@admin_required
def list_categories_api():
    try:
        with get_db() as db:
            categories = (
                db.query(Category)
                .order_by(Category.display_order.asc(), Category.name.asc())
                .all()
            )
            return jsonify({
                "success": True,
                "categories": [c.to_dict() for c in categories]
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/categories", methods=["POST"])
@admin_required
def save_category_api():
    try:
        data = request.get_json(force=True)
        cat_id = data.get("id")
        name = str(data.get("name", "")).strip()
        display_order = int(data.get("display_order", 0))
        is_active = bool(data.get("is_active", True))

        if not name:
            return jsonify({"success": False, "error": "Category name is required"}), 400

        with get_db() as db:
            if cat_id:
                category = db.query(Category).filter_by(id=cat_id).first()
                if not category:
                    return jsonify({"success": False, "error": "Category not found"}), 404
                category.name = name
                category.display_order = display_order
                category.is_active = is_active
                msg = f"Category '{name}' updated successfully!"
            else:
                # Check duplicate
                existing = db.query(Category).filter(func.lower(Category.name) == name.lower()).first()
                if existing:
                    return jsonify({"success": False, "error": f"Category '{name}' already exists"}), 400

                category = Category(
                    name=name,
                    display_order=display_order,
                    is_active=is_active
                )
                db.add(category)
                msg = f"Category '{name}' created successfully!"

            db.flush()
            return jsonify({"success": True, "message": msg, "category": category.to_dict()})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/categories/<int:cat_id>", methods=["DELETE"])
@admin_required
def delete_category_api(cat_id):
    try:
        with get_db() as db:
            category = db.query(Category).filter_by(id=cat_id).first()
            if not category:
                return jsonify({"success": False, "error": "Category not found"}), 404
            
            db.delete(category)
            return jsonify({"success": True, "message": "Category deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================================
# Menu Item Management APIs
# =========================================================================

@admin_bp.route("/api/admin/menu-items", methods=["GET"])
@admin_required
def list_menu_items_api():
    try:
        with get_db() as db:
            category_id = request.args.get("category_id")
            query = db.query(MenuItem)
            if category_id:
                query = query.filter_by(category_id=int(category_id))

            items = query.order_by(MenuItem.display_order.asc(), MenuItem.name.asc()).all()
            return jsonify({
                "success": True,
                "items": [item.to_dict() for item in items]
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/menu-items", methods=["POST"])
@admin_required
def save_menu_item_api():
    try:
        data = request.get_json(force=True)
        item_id = data.get("id")
        name = str(data.get("name", "")).strip()
        price = float(data.get("price", 0))
        category_id = data.get("category_id")
        code = str(data.get("code", "")).strip() or None
        is_available = bool(data.get("is_available", True))
        display_order = int(data.get("display_order", 0))

        if not name:
            return jsonify({"success": False, "error": "Item name is required"}), 400
        if price < 0:
            return jsonify({"success": False, "error": "Price cannot be negative"}), 400

        with get_db() as db:
            if category_id:
                category_id = int(category_id)
                cat = db.query(Category).filter_by(id=category_id).first()
                if not cat:
                    category_id = None

            if item_id:
                item = db.query(MenuItem).filter_by(id=item_id).first()
                if not item:
                    return jsonify({"success": False, "error": "Menu item not found"}), 404
                item.name = name
                item.price = price
                item.category_id = category_id
                item.code = code
                item.is_available = is_available
                item.display_order = display_order
                msg = f"Item '{name}' updated successfully!"
            else:
                item = MenuItem(
                    name=name,
                    price=price,
                    category_id=category_id,
                    code=code,
                    is_available=is_available,
                    display_order=display_order
                )
                db.add(item)
                msg = f"Item '{name}' added successfully!"

            db.flush()
            return jsonify({"success": True, "message": msg, "item": item.to_dict()})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/menu-items/<int:item_id>/toggle-availability", methods=["POST"])
@admin_required
def toggle_item_availability_api(item_id):
    try:
        with get_db() as db:
            item = db.query(MenuItem).filter_by(id=item_id).first()
            if not item:
                return jsonify({"success": False, "error": "Menu item not found"}), 404
            item.is_available = not item.is_available
            db.flush()
            status_text = "Available" if item.is_available else "Disabled"
            return jsonify({
                "success": True,
                "message": f"Item '{item.name}' is now marked as {status_text}",
                "is_available": item.is_available
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/menu-items/<int:item_id>", methods=["DELETE"])
@admin_required
def delete_menu_item_api(item_id):
    try:
        with get_db() as db:
            item = db.query(MenuItem).filter_by(id=item_id).first()
            if not item:
                return jsonify({"success": False, "error": "Menu item not found"}), 404
            db.delete(item)
            return jsonify({"success": True, "message": "Item deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================================
# Sales Analytics & Reports APIs
# =========================================================================

@admin_bp.route("/api/admin/reports/summary", methods=["GET"])
@admin_required
def sales_summary_api():
    """Returns today's total sales, bills count, and payment method breakdown."""
    try:
        with get_db() as db:
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            # Query all COMPLETED bills for today
            today_bills = (
                db.query(PosBill)
                .filter(
                    PosBill.created_at >= today_start,
                    PosBill.created_at <= today_end,
                    PosBill.status == "COMPLETED"
                )
                .all()
            )

            total_sales = sum(b.total_amount for b in today_bills)
            bills_count = len(today_bills)
            cash_sales = sum(b.total_amount for b in today_bills if b.payment_mode == "CASH")
            upi_sales = sum(b.total_amount for b in today_bills if b.payment_mode == "UPI")
            card_sales = sum(b.total_amount for b in today_bills if b.payment_mode == "CARD")
            discount_given = sum(b.discount for b in today_bills)

            # All-time stats (COMPLETED bills only)
            all_time_bills = db.query(PosBill).filter(PosBill.status == "COMPLETED").count()
            all_time_revenue = db.query(func.coalesce(func.sum(PosBill.total_amount), 0.0)).filter(PosBill.status == "COMPLETED").scalar() or 0.0

            return jsonify({
                "success": True,
                "today": {
                    "total_sales": round(total_sales, 2),
                    "bills_count": bills_count,
                    "cash_sales": round(cash_sales, 2),
                    "upi_sales": round(upi_sales, 2),
                    "card_sales": round(card_sales, 2),
                    "discount_given": round(discount_given, 2),
                    "average_bill": round(total_sales / bills_count, 2) if bills_count > 0 else 0.0
                },
                "all_time": {
                    "total_bills": all_time_bills,
                    "total_revenue": round(float(all_time_revenue), 2)
                }
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/reports/best-sellers", methods=["GET"])
@admin_required
def best_sellers_api():
    """Top selling items ranked by quantity sold and total revenue from completed bills."""
    try:
        with get_db() as db:
            limit = int(request.args.get("limit", 10))
            
            # Query top items for completed bills only
            results = (
                db.query(
                    PosBillItem.item_name,
                    func.sum(PosBillItem.quantity).label("total_qty"),
                    func.sum(PosBillItem.total_price).label("total_revenue")
                )
                .join(PosBill, PosBillItem.pos_bill_id == PosBill.id)
                .filter(PosBill.status == "COMPLETED")
                .group_by(PosBillItem.item_name)
                .order_by(desc("total_qty"))
                .limit(limit)
                .all()
            )

            items = [
                {
                    "item_name": r[0],
                    "total_qty": int(r[1]) if r[1] is not None else 0,
                    "total_revenue": round(float(r[2]), 2) if r[2] is not None else 0.0
                }
                for r in results
            ]

            return jsonify({"success": True, "best_sellers": items})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/pos-bills", methods=["GET"])
@admin_required
def list_pos_bills_api():
    """Search and filter historical POS bills."""
    try:
        with get_db() as db:
            search_query = request.args.get("q", "").strip()
            payment_filter = request.args.get("payment_mode", "").strip().upper()
            date_filter = request.args.get("date", "").strip()  # YYYY-MM-DD
            status_filter = request.args.get("status", "COMPLETED").strip().upper()

            query = db.query(PosBill)
            if status_filter:
                query = query.filter(PosBill.status == status_filter)


            if search_query:
                query = query.filter(PosBill.bill_number.ilike(f"%{search_query}%"))
            if payment_filter in ["CASH", "UPI", "CARD"]:
                query = query.filter_by(payment_mode=payment_filter)
            if date_filter:
                try:
                    d = datetime.strptime(date_filter, "%Y-%m-%d").date()
                    d_start = datetime.combine(d, time.min)
                    d_end = datetime.combine(d, time.max)
                    query = query.filter(PosBill.created_at >= d_start, PosBill.created_at <= d_end)
                except ValueError:
                    pass

            bills = query.order_by(PosBill.id.desc()).limit(100).all()

            return jsonify({
                "success": True,
                "count": len(bills),
                "bills": [b.to_dict() for b in bills]
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
