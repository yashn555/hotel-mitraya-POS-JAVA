"""
Authentication Routes for Hotel Mitraya
========================================
Handles login, PIN verification for Admin and Cashier roles, and PIN management.
"""

import os
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash
from database.db import get_db
from database.models import User
from auth.utils import verify_pin, admin_required, cashier_or_admin_required

APP_PIN = str(os.environ.get("APP_PIN", "2005")).strip()

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/pos/login", methods=["POST"])
@auth_bp.route("/api/login", methods=["POST"])
def login_api():
    try:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        entered_pin = str(data.get("pin", "")).strip()
        requested_role = str(data.get("role", "")).strip().lower()

        if not entered_pin:
            return jsonify({"success": False, "error": "Please enter your security PIN"}), 400

        with get_db() as db:
            user = None
            if requested_role == "cashier":
                user = db.query(User).filter_by(role="cashier").first()
                if not user or not verify_pin(entered_pin, user.pin_hash):
                    return jsonify({
                        "success": False,
                        "error": "Incorrect Cashier PIN. Access denied."
                    }), 401
            else:
                # Default to Admin (for requested_role == 'admin' or legacy unstated role calls)
                user = db.query(User).filter_by(role="admin").first()
                if not user or not verify_pin(entered_pin, user.pin_hash):
                    # Check fallback for default admin legacy PIN '2005'
                    if entered_pin == APP_PIN:
                        if user:
                            user.pin_hash = generate_password_hash(APP_PIN)
                            db.flush()
                    else:
                        return jsonify({
                            "success": False,
                            "error": "Incorrect Admin PIN. Access denied." if requested_role == "admin" else "Incorrect PIN. Access denied."
                        }), 401

            if not user:
                return jsonify({"success": False, "error": "Invalid user account"}), 401

            # Establish Session
            session.permanent = True
            session["authenticated"] = True
            session["user_id"] = user.id
            session["role"] = user.role
            session["user_name"] = user.name

            redirect_target = "/admin" if user.role == "admin" else "/pos"
            
            # If request specified a return url
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                # If cashier tries to access admin route, override to /pos
                if user.role == "cashier" and next_url.startswith("/admin"):
                    redirect_target = "/pos"
                else:
                    redirect_target = next_url

            return jsonify({
                "success": True,
                "role": user.role,
                "name": user.name,
                "message": f"Welcome {user.name}! Access granted.",
                "redirect": redirect_target
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/pos/me", methods=["GET"])
def current_user_api():
    if not session.get("authenticated"):
        return jsonify({"authenticated": False, "role": None, "name": None})
    return jsonify({
        "authenticated": True,
        "role": session.get("role", "admin"),
        "name": session.get("user_name", "Staff"),
        "user_id": session.get("user_id")
    })


@auth_bp.route("/api/admin/users/change-pin", methods=["POST"])
@admin_required
def change_pin_api():
    try:
        data = request.get_json(force=True)
        target_role = str(data.get("role", "")).strip().lower()
        new_pin = str(data.get("new_pin", "")).strip()

        if target_role not in ["admin", "cashier"]:
            return jsonify({"success": False, "error": "Invalid role specified. Must be 'admin' or 'cashier'."}), 400

        if not new_pin or len(new_pin) < 4 or not new_pin.isdigit():
            return jsonify({"success": False, "error": "PIN must be at least 4 digits long and numeric."}), 400

        with get_db() as db:
            user = db.query(User).filter_by(role=target_role).first()
            if not user:
                user = User(
                    username=target_role,
                    role=target_role,
                    name="Admin" if target_role == "admin" else "POS Cashier",
                    pin_hash=generate_password_hash(new_pin)
                )
                db.add(user)
            else:
                user.pin_hash = generate_password_hash(new_pin)

            db.flush()

        return jsonify({
            "success": True,
            "message": f"Successfully updated PIN for {target_role.capitalize()}!"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
