"""
Authentication & Authorization Utilities
=========================================
Provides PIN hashing, verification, and role-based route guards.
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


def login_required(f):
    """Ensure user is logged in (either Admin or Cashier)."""
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

        role = session.get("role", "admin")  # default admin for legacy session
        if role != "admin":
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Access denied. Admin privileges required.",
                    "forbidden": True
                }), 403
            return redirect(url_for("pos.pos_view"))
        return f(*args, **kwargs)
    return decorated_function


def cashier_or_admin_required(f):
    """Ensure current user is authenticated as either Cashier or Admin."""
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
