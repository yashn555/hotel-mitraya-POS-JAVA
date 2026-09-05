"""
Authentication & Authorization Utilities for Hotel Mitraya
===========================================================
Provides PIN hashing, verification, client metadata extraction,
and granular role-based route guards for ADMIN, CASHIER, and WAITER.
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash


def hash_pin(pin: str) -> str:
    """Securely hash a numeric PIN."""
    return generate_password_hash(str(pin).strip())


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify numeric PIN against stored hash."""
    if not pin or not pin_hash:
        return False
    return check_password_hash(pin_hash, str(pin).strip())


def get_client_ip() -> str:
    """Extract real client IP address even if behind a proxy/load balancer."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP").strip()
    return request.remote_addr or "127.0.0.1"


def get_current_user_context():
    """Returns a dictionary with current session user context for audit logging."""
    return {
        "user_id": session.get("user_id"),
        "username": session.get("username", session.get("role", "anonymous")),
        "role": session.get("role", "anonymous"),
        "name": session.get("user_name", "Staff"),
        "ip_address": get_client_ip()
    }


def login_required(f):
    """Ensure user is logged in with any valid role (Admin, Cashier, Waiter)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please unlock with your PIN.",
                    "auth_required": True
                }), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Ensure current user is authenticated as an Admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please log in as Admin.",
                    "auth_required": True
                }), 401
            return redirect(url_for("login"))

        role = session.get("role", "admin")
        if role != "admin":
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Access denied. Admin privileges required.",
                    "forbidden": True
                }), 403
            if role == "cashier":
                return redirect(url_for("pos.pos_view"))
            return redirect(url_for("waiter.waiter_view"))
        return f(*args, **kwargs)
    return decorated_function


def cashier_or_admin_required(f):
    """Ensure current user is authenticated as either Cashier or Admin (Counter operations)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please log in.",
                    "auth_required": True
                }), 401
            return redirect(url_for("login"))

        role = session.get("role", "admin")
        if role not in ["admin", "cashier"]:
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Access denied. Counter or Admin privileges required.",
                    "forbidden": True
                }), 403
            return redirect(url_for("waiter.waiter_view"))
        return f(*args, **kwargs)
    return decorated_function


def waiter_or_staff_required(f):
    """Ensure user is logged in as Waiter, Cashier, or Admin (e.g. for placing orders)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please log in.",
                    "auth_required": True
                }), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Generic decorator to restrict access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("authenticated"):
                if request.path.startswith("/api/"):
                    return jsonify({
                        "success": False,
                        "error": "Authentication required.",
                        "auth_required": True
                    }), 401
                return redirect(url_for("login"))

            role = session.get("role", "")
            if role not in allowed_roles:
                if request.path.startswith("/api/"):
                    return jsonify({
                        "success": False,
                        "error": f"Access denied. Requires one of: {', '.join(allowed_roles)}",
                        "forbidden": True
                    }), 403
                if role == "admin":
                    return redirect(url_for("admin.admin_dashboard_view"))
                if role == "cashier":
                    return redirect(url_for("pos.pos_view"))
                return redirect(url_for("waiter.waiter_view"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
