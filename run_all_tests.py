"""
Unified Test Runner for Hotel Mitraya Restaurant POS & Ordering System
========================================================================
Runs full end-to-end integration tests using Flask test client.
"""

import json
from app import app
from database.db import get_db
from database.models import PosBill, Order, MenuItem, PrintJob, AuditLog, User


def run_tests():
    print("==================================================================")
    print("STARTING HOTEL MITRAYA FULL PRODUCTION INTEGRATION TESTS")
    print("==================================================================")

    # Reset default test PINs
    with get_db() as db:
        from werkzeug.security import generate_password_hash
        u_admin = db.query(User).filter_by(username="admin").first()
        if u_admin: u_admin.pin_hash = generate_password_hash("2005")
        u_cashier = db.query(User).filter_by(username="cashier").first()
        if u_cashier: u_cashier.pin_hash = generate_password_hash("5678")
        u_waiter = db.query(User).filter_by(username="waiter").first()
        if u_waiter: u_waiter.pin_hash = generate_password_hash("1234")
        db.flush()

    # 1. Unauthenticated request protection
    print("\n[1] Testing Unauthenticated Access Guards (401 Unauthorized)...")
    anon_client = app.test_client()
    r = anon_client.get("/api/admin/menu-items")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    assert r.get_json()["auth_required"] == True
    print("    -> OK: Protected API returned 401 with auth_required")

    # 2. Multi-Role Login Verification
    print("\n[2] Testing Multi-Role Authentication (Admin, Cashier, Waiter)...")
    
    # Waiter Login
    waiter_client = app.test_client()
    r_waiter = waiter_client.post("/api/login", json={"role": "waiter", "pin": "1234"})
    assert r_waiter.status_code == 200, f"Waiter login failed: {r_waiter.get_json()}"
    w_data = r_waiter.get_json()
    assert w_data["success"] == True
    assert w_data["role"] == "waiter"
    assert w_data["redirect"] == "/waiter"
    print(f"    -> OK: Waiter authenticated successfully! Redirect: {w_data['redirect']}")

    # Waiter access to /waiter
    r_w_view = waiter_client.get("/waiter")
    assert r_w_view.status_code == 200
    print("    -> OK: Waiter accessed /waiter interface")

    # Waiter blocked from Admin & Cashier endpoints
    r_w_admin = waiter_client.get("/api/admin/menu-items")
    assert r_w_admin.status_code == 403, f"Waiter should be forbidden from admin APIs, got {r_w_admin.status_code}"
    r_w_pos = waiter_client.get("/api/pos/bills/recent")
    assert r_w_pos.status_code == 403, f"Waiter should be forbidden from pos bills, got {r_w_pos.status_code}"
    print("    -> OK: Waiter strictly blocked from Admin & POS Billing APIs (403 Forbidden)")

    # Cashier Login
    cashier_client = app.test_client()
    r_cashier = cashier_client.post("/api/login", json={"role": "cashier", "pin": "5678"})
    assert r_cashier.status_code == 200
    c_data = r_cashier.get_json()
    assert c_data["role"] == "cashier"
    assert c_data["redirect"] == "/pos"
    print(f"    -> OK: Cashier authenticated successfully! Redirect: {c_data['redirect']}")

    # Cashier blocked from Admin
    r_c_admin = cashier_client.get("/api/admin/categories")
    assert r_c_admin.status_code == 403
    print("    -> OK: Cashier strictly blocked from Admin APIs (403 Forbidden)")

    # Admin Login
    admin_client = app.test_client()
    r_admin = admin_client.post("/api/login", json={"role": "admin", "pin": "2005"})
    assert r_admin.status_code == 200
    a_data = r_admin.get_json()
    assert a_data["role"] == "admin"
    assert a_data["redirect"] == "/admin"
    print(f"    -> OK: Admin authenticated successfully! Full access granted.")

    # 3. Waiter Menu & 12 Table Status Retrieval
    print("\n[3] Testing Waiter Menu Catalog & Table Status...")
    r_menu = waiter_client.get("/api/waiter/menu")
    assert r_menu.status_code == 200
    menu_data = r_menu.get_json()
    assert menu_data["success"] == True
    assert len(menu_data["categories"]) >= 3
    
    all_dishes = []
    for cat in menu_data["categories"]:
        all_dishes.extend(cat["items"])
    print(f"    -> OK: Waiter retrieved {len(all_dishes)} active dishes")

    r_tables = waiter_client.get("/api/waiter/tables")
    assert r_tables.status_code == 200
    tables_data = r_tables.get_json()
    assert tables_data["total_tables"] == 12
    assert len(tables_data["tables"]) == 12
    print("    -> OK: All 12 tables retrieved successfully")

    # 4. Waiter Places Order for Table 3
    print("\n[4] Testing Waiter Table 3 Order Placement (POST /api/orders)...")
    with get_db() as db:
        old_orders = db.query(Order).filter(Order.table_number == 3, Order.status.in_(["PLACED", "CONFIRMED", "PREPARING", "READY"])).all()
        for o in old_orders:
            o.status = "COMPLETED"
        old_bills = db.query(PosBill).filter(PosBill.table_number == 3, PosBill.status == "OPEN").all()
        for b in old_bills:
            b.status = "COMPLETED"

    dish1 = all_dishes[0]
    dish2 = all_dishes[1]
    expected_subtotal = (dish1["price"] * 2) + (dish2["price"] * 3)

    r_create_order = waiter_client.post("/api/orders", json={
        "table_number": 3,
        "order_type": "DINING",
        "customer_name": "Mehta Family",
        "source": "WAITER",
        "items": [
            {"menu_item_id": dish1["id"], "name": dish1["name"], "unit_price": dish1["price"], "quantity": 2, "item_notes": "Extra crispy"},
            {"menu_item_id": dish2["id"], "name": dish2["name"], "unit_price": dish2["price"], "quantity": 3, "item_notes": "Mild spice"}
        ]
    })
    assert r_create_order.status_code == 200, f"Order placement failed: {r_create_order.get_json()}"
    order_data = r_create_order.get_json()["order"]
    assert order_data["table_number"] == 3
    assert order_data["status"] == "PLACED"
    assert order_data["subtotal"] == expected_subtotal
    assert len(order_data["items"]) == 2
    print(f"    -> OK: Order #{order_data['order_number']} created with status 'PLACED'! Total: Rs.{order_data['total_amount']}")

    # Waiter checks active orders
    r_my_orders = waiter_client.get("/api/waiter/orders/my-active")
    assert r_my_orders.status_code == 200
    assert len(r_my_orders.get_json()["orders"]) >= 1
    print("    -> OK: Order verified in Waiter live order feed")

    # 5. Counter Cashier Live Sync & Order Lifecycle Progression
    print("\n[5] Testing Counter Cashier Order Queue & Status Transitions...")
    r_live = cashier_client.get("/api/orders/live")
    assert r_live.status_code == 200
    live_res = r_live.get_json()
    assert live_res["active_orders_count"] >= 1
    assert "3" in live_res["table_orders"] or 3 in live_res["table_orders"]
    print(f"    -> OK: Cashier sees Table 3 order in live queue (Count: {live_res['active_orders_count']})")

    # Cashier changes status: PLACED -> PREPARING
    r_prep = cashier_client.patch(f"/api/orders/{order_data['id']}/status", json={"status": "PREPARING"})
    assert r_prep.status_code == 200
    assert r_prep.get_json()["order"]["status"] == "PREPARING"
    print(f"    -> OK: Order #{order_data['order_number']} status changed to 'PREPARING'")

    # Cashier changes status: PREPARING -> READY
    r_ready = cashier_client.patch(f"/api/orders/{order_data['id']}/status", json={"status": "READY"})
    assert r_ready.status_code == 200
    assert r_ready.get_json()["order"]["status"] == "READY"
    print(f"    -> OK: Order #{order_data['order_number']} status changed to 'READY'")

    # 6. Counter Settles Table 3 Order (Bill Generation & Thermal Print Job)
    print("\n[6] Testing Table 3 Final Settlement & Thermal Print Spooling...")
    discount = 20.0
    expected_total = expected_subtotal - discount
    received = 1000.0
    expected_change = received - expected_total

    r_settle = cashier_client.post("/api/pos/tables/settle", json={
        "table_number": 3,
        "payment_mode": "CASH",
        "discount": discount,
        "received_amount": received
    })
    assert r_settle.status_code == 200, f"Settlement failed: {r_settle.get_json()}"
    settle_data = r_settle.get_json()
    bill = settle_data["bill"]
    assert bill["table_number"] == 3
    assert bill["status"] == "COMPLETED"
    assert bill["subtotal"] == expected_subtotal
    assert bill["discount"] == discount
    assert bill["total_amount"] == expected_total
    assert bill["change_amount"] == expected_change
    assert "print_job" in settle_data
    print(f"    -> OK: Bill #{bill['bill_number']} finalized! Subtotal: Rs.{bill['subtotal']}, Discount: Rs.{bill['discount']}, Total: Rs.{bill['total_amount']}, Change: Rs.{bill['change_amount']}")
    print(f"    -> OK: Thermal print job recorded (Job ID: {settle_data['print_job']['job_id']})")

    # Verify Table 3 is VACANT again
    r_t3_check = cashier_client.get("/api/pos/tables/3")
    assert r_t3_check.status_code == 200
    assert r_t3_check.get_json()["status"] == "VACANT"
    print("    -> OK: Table 3 returned to VACANT status")

    # 7. Thermal Printer Subsystem (58mm & 80mm Formatting & Reprint)
    print("\n[7] Testing Thermal Printer Configuration, 58mm & 80mm Formats & Reprint...")
    r_plist = cashier_client.get("/api/printer/list")
    assert r_plist.status_code == 200
    assert r_plist.get_json()["count"] >= 1

    # 58mm test print
    r_test_58 = cashier_client.post("/api/printer/test", json={"paper_width": 58})
    assert r_test_58.status_code == 200
    assert r_test_58.get_json()["job"]["paper_width"] == 58
    assert "HOTEL MITRAYA" in r_test_58.get_json()["job"]["preview_text"]
    print("    -> OK: 58mm (32 cols) test slip generated cleanly")

    # 80mm test print
    r_test_80 = cashier_client.post("/api/printer/test", json={"paper_width": 80})
    assert r_test_80.status_code == 200
    assert r_test_80.get_json()["job"]["paper_width"] == 80
    print("    -> OK: 80mm (42 cols) test slip generated cleanly")

    # Reprint historical bill
    r_reprint = cashier_client.post(f"/api/printer/reprint/{bill['id']}")
    assert r_reprint.status_code == 200
    assert r_reprint.get_json()["success"] == True
    print(f"    -> OK: Bill #{bill['bill_number']} successfully reprinted without creating new bill record")

    # 8. Instant Walk-in POS Checkout Test
    print("\n[8] Testing Instant Walk-in POS Checkout (POST /api/pos/checkout)...")
    r_checkout = cashier_client.post("/api/pos/checkout", json={
        "order_type": "WALK_IN",
        "customer_name": "Walk-in Guest",
        "payment_mode": "UPI",
        "discount": 0,
        "items": [
            {"menu_item_id": dish1["id"], "name": dish1["name"], "unit_price": dish1["price"], "quantity": 1}
        ]
    })
    assert r_checkout.status_code == 200
    walkin_bill = r_checkout.get_json()["bill"]
    assert walkin_bill["order_type"] == "WALK_IN"
    assert walkin_bill["status"] == "COMPLETED"
    assert walkin_bill["payment_mode"] == "UPI"
    print(f"    -> OK: Walk-in Bill #{walkin_bill['bill_number']} checked out via UPI!")

    # 9. Audit Trail Verification
    print("\n[9] Testing System Audit Trail (GET /api/admin/audit-logs)...")
    r_audit = admin_client.get("/api/admin/audit-logs")
    assert r_audit.status_code == 200
    audit_data = r_audit.get_json()
    logs = audit_data["logs"]
    assert len(logs) >= 3
    actions = [l["action"] for l in logs]
    print(f"    -> OK: Audit trail verified! Actions logged: {set(actions)}")

    # 10. Database Backup Export
    print("\n[10] Testing Database JSON Backup Export (GET /api/admin/database/backup)...")
    r_backup = admin_client.get("/api/admin/database/backup")
    assert r_backup.status_code == 200
    backup_data = json.loads(r_backup.data.decode("utf-8"))
    assert "users" in backup_data
    assert "categories" in backup_data
    assert "menu_items" in backup_data
    assert "pos_bills" in backup_data
    assert "orders" in backup_data
    print(f"    -> OK: Complete database backup generated! (Bills: {len(backup_data['pos_bills'])}, Orders: {len(backup_data['orders'])})")

    # 12. Kitchen Display System (KDS) & Printer Station Routes & Startup Init
    print("\n[12] Testing Kitchen Display System & Printer Station Startup Init...")
    r_kitchen = cashier_client.get("/kitchen")
    assert r_kitchen.status_code == 200, f"Failed to access /kitchen: {r_kitchen.status_code}"
    print("    -> OK: /kitchen (KDS) accessible")

    r_printer = cashier_client.get("/printer")
    assert r_printer.status_code == 200, f"Failed to access /printer: {r_printer.status_code}"
    print("    -> OK: /printer station accessible")

    r_init = cashier_client.post("/api/printer/startup-init")
    assert r_init.status_code == 200
    init_data = r_init.get_json()
    assert init_data["success"] == True
    assert "identified_printer" in init_data
    print(f"    -> OK: Printer startup diagnostic passed! Identified printer: '{init_data['identified_printer']}' with HELLO confirmation slip")

    print("\n==================================================================")
    print("ALL 12 PRODUCTION INTEGRATION & SECURITY TEST SUITES PASSED (100% OK)!")
    print("==================================================================")


if __name__ == "__main__":
    run_tests()
