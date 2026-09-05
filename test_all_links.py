"""
Hotel Mitraya - Complete Links & Security Verification Script
=============================================================
Tests all internal URLs, navigation links, PWA files, and role-based permissions.
"""

import requests
import os

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5055")


def verify_all_system_links():
    print("\n" + "=" * 70)
    print("  VERIFYING ALL SYSTEM LINKS, PAGES, APIS & PWA ASSETS")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. PUBLIC ASSETS & PWA FILES
    # -------------------------------------------------------------
    print("\n[1] Verifying Static & PWA Assets...")
    static_endpoints = [
        "/static/manifest.json",
        "/static/sw.js",
        "/static/pwa.js",
        "/static/logo.png",
        "/static/pos.css",
        "/static/pos.js",
        "/static/display.js",
        "/static/style.css",
        "/static/receipt.css",
        "/api/health"
    ]
    for ep in static_endpoints:
        r = requests.get(f"{BASE_URL}{ep}")
        assert r.status_code == 200, f"Failed static endpoint: {ep} ({r.status_code})"
        print(f"  -> {ep.ljust(30)} [200 OK] ({len(r.content)} bytes)")

    # -------------------------------------------------------------
    # 2. UNAUTHENTICATED ACCESS GUARDS
    # -------------------------------------------------------------
    print("\n[2] Verifying Security Guards for Unauthenticated Requests...")
    protected_pages = ["/", "/pos", "/display", "/admin", "/admin/menu", "/admin/reports"]
    for page in protected_pages:
        r = requests.get(f"{BASE_URL}{page}", allow_redirects=False)
        assert r.status_code in [302, 401], f"Page {page} not protected: status {r.status_code}"
        print(f"  -> {page.ljust(30)} [302 Redirected to Login / Protected]")

    protected_apis = ["/api/pos/tables", "/api/display/live-orders", "/api/admin/reports/summary", "/api/bills"]
    for api in protected_apis:
        r = requests.get(f"{BASE_URL}{api}")
        assert r.status_code == 401, f"API {api} not returning 401: status {r.status_code}"
        print(f"  -> {api.ljust(30)} [401 Unauthorized Blocked]")

    # -------------------------------------------------------------
    # 3. CASHIER (WAITER) PERMISSIONS
    # -------------------------------------------------------------
    print("\n[3] Verifying Cashier Session (PIN 5678)...")
    cashier = requests.Session()
    r_login_c = cashier.post(f"{BASE_URL}/api/pos/login", json={"role": "cashier", "pin": "5678"})
    assert r_login_c.status_code == 200, "Cashier login failed"
    print("  -> Logged in as Cashier")

    # Allowed Cashier Pages & APIs
    cashier_allowed = [
        "/pos",
        "/display",
        "/pos/display",
        "/api/pos/catalog",
        "/api/pos/tables",
        "/api/display/live-orders"
    ]
    for url in cashier_allowed:
        r = cashier.get(f"{BASE_URL}{url}")
        assert r.status_code == 200, f"Cashier could not access allowed route: {url} ({r.status_code})"
        print(f"  -> Allowed: {url.ljust(25)} [200 OK]")

    # Blocked Admin Pages for Cashier
    cashier_blocked = ["/admin", "/admin/menu", "/admin/reports", "/api/admin/reports/summary", "/api/admin/menu-items"]
    for url in cashier_blocked:
        r = cashier.get(f"{BASE_URL}{url}", allow_redirects=False)
        assert r.status_code in [302, 403], f"Cashier accessed restricted route {url}!"
        print(f"  -> Blocked: {url.ljust(25)} [{r.status_code} Access Denied]")

    # -------------------------------------------------------------
    # 4. ADMIN FULL ACCESS PERMISSIONS
    # -------------------------------------------------------------
    print("\n[4] Verifying Admin Session (PIN 2005)...")
    admin = requests.Session()
    r_login_a = admin.post(f"{BASE_URL}/api/pos/login", json={"role": "admin", "pin": "2005"})
    assert r_login_a.status_code == 200, "Admin login failed"
    print("  -> Logged in as Admin")

    admin_urls = [
        "/admin",
        "/admin/menu",
        "/admin/reports",
        "/pos",
        "/display",
        "/",
        "/api/pos/catalog",
        "/api/pos/tables",
        "/api/display/live-orders",
        "/api/admin/menu-items",
        "/api/admin/categories",
        "/api/admin/reports/summary",
        "/api/admin/reports/best-sellers",
        "/api/admin/pos-bills",
        "/api/bills",
        "/api/next-bill-no"
    ]
    for url in admin_urls:
        r = admin.get(f"{BASE_URL}{url}")
        assert r.status_code == 200, f"Admin could not access route: {url} ({r.status_code})"
        print(f"  -> Admin Access: {url.ljust(30)} [200 OK]")

    print("\n" + "=" * 70)
    print("  ALL SYSTEM LINKS, ASSETS & SECURITY CONTROLS VERIFIED (100% OK)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    verify_all_system_links()
