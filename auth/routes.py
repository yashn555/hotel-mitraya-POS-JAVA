"""
Authentication & User Management Routes for Hotel Mitraya
==========================================================
Handles multi-role authentication (Admin, Cashier, Waiter),
PIN verification, session lifecycle, staff management, and audit tracking.
"""

import os
from flask import Blueprint, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash
from database.db import get_db, record_audit_log
from database.models import User
from auth.utils import verify_pin, admin_required, login_required, get_client_ip, get_current_user_context

APP_PIN = str(os.environ.get("APP_PIN", "2005")).strip()

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/pos/login", methods=["POST"])
@auth_bp.route("/api/auth/login", methods=["POST"])
@auth_bp.route("/api/login", methods=["POST"])
def login_api():
    try:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        entered_pin = str(data.get("pin", "")).strip()
        requested_role = str(data.get("role", "")).strip().lower()
        client_ip = get_client_ip()

        if not entered_pin:
            return jsonify({"success": False, "error": "Please enter your security PIN"}), 400

        with get_db() as db:
            user = None
            
            # 1. If specific role requested
            if requested_role in ["admin", "cashier", "waiter"]:
                user = db.query(User).filter_by(role=requested_role, is_active=True).first()
                if user and (verify_pin(entered_pin, user.pin_hash) or entered_pin == APP_PIN):
                    pass # Valid
                else:
                    user = None
            
            # 2. If no role specified or not matched, match any active user by PIN
            if not user:
                users = db.query(User).filter_by(is_active=True).all()
                for u in users:
                    if verify_pin(entered_pin, u.pin_hash):
                        user = u
                        break
            
            # 3. Master fallback to Admin if entered_pin matches APP_PIN
            if not user and entered_pin == APP_PIN:
                user = db.query(User).filter_by(role="admin", is_active=True).first()

            if not user:
                record_audit_log(
                    db,
                    action="LOGIN_FAILED",
                    entity="USER",
                    details=f"Failed login attempt (role requested: {requested_role or 'any'})",
                    ip_address=client_ip
                )
                return jsonify({
                    "success": False,
                    "error": f"Incorrect {requested_role.capitalize() + ' ' if requested_role else ''}PIN. Access denied."
                }), 401

            if not user or not user.is_active:
                return jsonify({"success": False, "error": "User account is disabled or invalid"}), 401

            # Establish Session
            session.permanent = True
            session["authenticated"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["user_name"] = user.name

            # Determine Default Landing Route
            if user.role == "admin":
                redirect_target = "/admin"
            elif user.role == "cashier":
                redirect_target = "/pos"
            elif user.role == "waiter":
                redirect_target = "/waiter"
            else:
                redirect_target = "/pos"

            # Check next parameter with security overrides
            next_url = request.args.get("next") or (data.get("next") if isinstance(data, dict) else None)
            if next_url and next_url.startswith("/"):
                if user.role == "cashier" and next_url.startswith("/admin"):
                    redirect_target = "/pos"
                elif user.role == "waiter" and (next_url.startswith("/admin") or next_url.startswith("/pos")):
                    redirect_target = "/waiter"
                else:
                    redirect_target = next_url

            # Audit Log Successful Login
            record_audit_log(
                db,
                action="LOGIN_SUCCESS",
                entity="USER",
                entity_id=str(user.id),
                details=f"User {user.username} ({user.role}) logged in",
                user_id=user.id,
                username=user.username,
                role=user.role,
                ip_address=client_ip
            )

            return jsonify({
                "success": True,
                "role": user.role,
                "name": user.name,
                "user_id": user.id,
                "username": user.username,
                "message": f"Welcome {user.name}! Access granted.",
                "redirect": redirect_target
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/auth/me", methods=["GET"])
@auth_bp.route("/api/pos/me", methods=["GET"])
def current_user_api():
    if not session.get("authenticated"):
        return jsonify({"authenticated": False, "role": None, "name": None, "user_id": None})
    return jsonify({
        "authenticated": True,
        "role": session.get("role", "admin"),
        "name": session.get("user_name", "Staff"),
        "username": session.get("username", session.get("role")),
        "user_id": session.get("user_id")
    })


@auth_bp.route("/api/auth/logout", methods=["POST", "GET"])
@auth_bp.route("/api/pos/logout", methods=["POST", "GET"])
@auth_bp.route("/api/logout", methods=["POST", "GET"])
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout_api():
    session.clear()
    if request.path == "/logout":
        return redirect(url_for("login"))
    return jsonify({
        "success": True,
        "message": "Logged out successfully",
        "redirect": "/login"
    })


# =========================================================================
# Staff & User Management APIs (Admin Only)
# =========================================================================

@auth_bp.route("/api/admin/users", methods=["GET"])
@admin_required
def list_users_api():
    try:
        with get_db() as db:
            users = db.query(User).order_by(User.role.asc(), User.id.asc()).all()
            return jsonify({
                "success": True,
                "users": [u.to_dict() for u in users]
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/admin/users", methods=["POST"])
@admin_required
def save_user_api():
    try:
        data = request.get_json(force=True)
        user_id = data.get("id")
        username = str(data.get("username", "")).strip().lower()
        role = str(data.get("role", "waiter")).strip().lower()
        name = str(data.get("name", "")).strip() or "Staff"
        pin = str(data.get("pin", "")).strip()
        is_active = bool(data.get("is_active", True))
        ctx = get_current_user_context()

        if role not in ["admin", "cashier", "waiter"]:
            return jsonify({"success": False, "error": "Invalid role. Must be 'admin', 'cashier', or 'waiter'."}), 400

        with get_db() as db:
            if user_id:
                user = db.query(User).filter_by(id=int(user_id)).first()
                if not user:
                    return jsonify({"success": False, "error": "User not found"}), 404
                
                if pin:
                    if len(pin) < 4 or not pin.isdigit():
                        return jsonify({"success": False, "error": "PIN must be at least 4 digits long and numeric."}), 400
                    user.pin_hash = generate_password_hash(pin)

                user.name = name
                user.role = role
                user.is_active = is_active
                msg = f"User '{user.username}' updated successfully!"

                record_audit_log(
                    db,
                    action="USER_UPDATE",
                    entity="USER",
                    entity_id=str(user.id),
                    details=f"Admin updated user {user.username} (Role: {role}, Active: {is_active})",
                    **ctx
                )
            else:
                if not username:
                    return jsonify({"success": False, "error": "Username is required"}), 400
                if not pin or len(pin) < 4 or not pin.isdigit():
                    return jsonify({"success": False, "error": "Initial PIN must be at least 4 digits long and numeric."}), 400

                existing = db.query(User).filter_by(username=username).first()
                if existing:
                    return jsonify({"success": False, "error": f"Username '{username}' already exists"}), 400

                user = User(
                    username=username,
                    role=role,
                    name=name,
                    pin_hash=generate_password_hash(pin),
                    is_active=is_active
                )
                db.add(user)
                db.flush()
                msg = f"Staff user '{username}' ({role.capitalize()}) created successfully!"

                record_audit_log(
                    db,
                    action="USER_CREATE",
                    entity="USER",
                    entity_id=str(user.id),
                    details=f"Admin created staff user {username} ({role})",
                    **ctx
                )

            db.flush()
            return jsonify({"success": True, "message": msg, "user": user.to_dict()})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/admin/users/change-pin", methods=["POST"])
@admin_required
def change_pin_api():
    try:
        data = request.get_json(force=True)
        target_role = str(data.get("role", "")).strip().lower()
        new_pin = str(data.get("new_pin", "")).strip()
        user_id = data.get("user_id")
        ctx = get_current_user_context()

        if not new_pin or len(new_pin) < 4 or not new_pin.isdigit():
            return jsonify({"success": False, "error": "PIN must be at least 4 digits long and numeric."}), 400

        with get_db() as db:
            user = None
            if user_id:
                try:
                    user = db.query(User).filter_by(id=int(user_id)).first()
                except (ValueError, TypeError):
                    pass
            if not user and target_role in ["admin", "cashier", "waiter"]:
                user = db.query(User).filter_by(role=target_role).first()

            if not user:
                if target_role in ["admin", "cashier", "waiter"]:
                    display_names = {"admin": "Admin", "cashier": "POS Cashier", "waiter": "Floor Waiter"}
                    user = User(
                        username=target_role,
                        role=target_role,
                        name=display_names.get(target_role, "Staff"),
                        pin_hash=generate_password_hash(new_pin)
                    )
                    db.add(user)
                    db.flush()
                else:
                    return jsonify({"success": False, "error": "User not found"}), 404
            else:
                user.pin_hash = generate_password_hash(new_pin)

            db.flush()
            user_name = user.name
            user_role = user.role

            record_audit_log(
                db,
                action="PIN_UPDATE",
                entity="USER",
                entity_id=str(user.id),
                details=f"PIN updated for user {user.username} ({user.role})",
                **ctx
            )

        return jsonify({
            "success": True,
            "message": f"Successfully updated PIN for {user_name} ({user_role.capitalize()})!"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user_api(user_id):
    try:
        ctx = get_current_user_context()
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            if user.username == "admin" or user.id == session.get("user_id"):
                return jsonify({"success": False, "error": "Cannot delete primary administrator account"}), 400

            username = user.username
            db.delete(user)

            record_audit_log(
                db,
                action="USER_DELETE",
                entity="USER",
                entity_id=str(user_id),
                details=f"Deleted user account: {username}",
                **ctx
            )

            return jsonify({"success": True, "message": f"User '{username}' deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
