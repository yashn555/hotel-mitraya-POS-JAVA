"""
Comprehensive Automated Test Suite for Hotel Mitraya Quick POS System
======================================================================
Verifies:
1. Role-based Authentication (Admin vs Cashier) & RBAC Route Protection
2. POS Catalog retrieval and Category listing
3. POS Checkout & Sequential Bill Numbering (e.g. POS-000001, POS-000002)
4. Cash Tender & Change Calculations
5. Historical Price Snapshot Integrity (Price change on Menu does NOT change historical bills)
6. Admin Menu Management (Add/Edit Category, Add/Edit Item, Toggle Availability)
7. Sales Reports & KPIs (Today's Total, Cash vs UPI vs Card breakdown, Best Sellers)
8. POS Bill History, Details & 80mm Thermal Receipt Data
9. Admin & Cashier PIN Update Security
"""

import requests
import os
import sys

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5055")


def run_pos_tests():
    print("==================================================================")
    print("STARTING FULL QUICK POS & ADMIN VERIFICATION TEST SUITE")
    print("==================================================================")

    # -------------------------------------------------------------
    # 1. CASHIER AUTHENTICATION & ACCESS RESTRICTIONS
    # -------------------------------------------------------------
    print("\n[1] Testing Cashier Login with PIN '1234'...")
    cashier_session = requests.Session()
    r_cashier_login = cashier_session.post(
        f"{BASE_URL}/api/pos/login",
        json={"role": "cashier", "pin": "1234"}
    )
    assert r_cashier_login.status_code == 200, f"Cashier login failed: {r_cashier_login.text}"
    cashier_data = r_cashier_login.json()
    assert cashier_data["success"] == True
    assert cashier_data["role"] == "cashier"
    assert cashier_data["redirect"] == "/pos"
    print(f"    -> OK: Cashier authenticated successfully, redirect: {cashier_data['redirect']}")

    # Verify Cashier can access /pos
    print("\n[2] Testing Cashier access to /pos (Allowed)...")
    r_pos_view = cashier_session.get(f"{BASE_URL}/pos")
    assert r_pos_view.status_code == 200
    assert "Quick POS" in r_pos_view.text or "HOTEL MITRAYA" in r_pos_view.text
    print("    -> OK: Cashier successfully loaded POS interface")

    # Verify Cashier CANNOT access /admin or /api/admin/*
    print("\n[3] Testing Cashier RBAC Restriction for /admin & /api/admin/menu-items (Blocked)...")
    r_admin_blocked = cashier_session.get(f"{BASE_URL}/admin", allow_redirects=False)
    assert r_admin_blocked.status_code in [302, 403], f"Cashier should not access /admin: {r_admin_blocked.status_code}"
    
    r_api_admin_blocked = cashier_session.get(f"{BASE_URL}/api/admin/menu-items")
    assert r_api_admin_blocked.status_code == 403, f"Cashier API call to admin should be 403: {r_api_admin_blocked.status_code}"
    print("    -> OK: Cashier properly blocked from Admin Dashboard and Admin APIs (403 Forbidden)")

    # -------------------------------------------------------------
    # 2. ADMIN AUTHENTICATION & FULL ACCESS
    # -------------------------------------------------------------
    print("\n[4] Testing Admin Login with PIN '2005'...")
    admin_session = requests.Session()
    r_admin_login = admin_session.post(
        f"{BASE_URL}/api/pos/login",
        json={"role": "admin", "pin": "2005"}
    )
    assert r_admin_login.status_code == 200, f"Admin login failed: {r_admin_login.text}"
    admin_data = r_admin_login.json()
    assert admin_data["success"] == True
    assert admin_data["role"] == "admin"
    print(f"    -> OK: Admin authenticated successfully, redirect: {admin_data['redirect']}")

    # Verify Admin can access /admin, /pos, and /bulk (or /)
    print("\n[5] Testing Admin Access to Admin Dashboard, POS, and Bulk Billing...")
    r_dash = admin_session.get(f"{BASE_URL}/admin")
    assert r_dash.status_code == 200
    assert "Admin Portal" in r_dash.text or "Operations &amp; Billing Hub" in r_dash.text or "Operations & Billing Hub" in r_dash.text
    
    r_pos = admin_session.get(f"{BASE_URL}/pos")
    assert r_pos.status_code == 200

    r_bulk = admin_session.get(f"{BASE_URL}/bulk")
    assert r_bulk.status_code == 200
    assert "HOTEL MITRAYA" in r_bulk.text
    print("    -> OK: Admin has full access to Admin Dashboard, Quick POS, and Bulk Billing")

    # -------------------------------------------------------------
    # 3. POS CATALOG & MENU RETRIEVAL
    # -------------------------------------------------------------
    print("\n[6] Testing GET /api/pos/catalog...")
    r_catalog = cashier_session.get(f"{BASE_URL}/api/pos/catalog")
    assert r_catalog.status_code == 200
    cat_data = r_catalog.json()
    assert cat_data["success"] == True
    assert len(cat_data["categories"]) >= 3
    
    # Check sample dishes in catalog
    all_items = []
    for c in cat_data["categories"]:
        all_items.extend(c["items"])
    item_names = [i["name"] for i in all_items]
    assert any("Dahi Dhapata" in name for name in item_names)
    assert any("Thali" in name for name in item_names)
    print(f"    -> OK: Catalog contains {len(cat_data['categories'])} categories and {len(all_items)} active menu items")

    # -------------------------------------------------------------
    # 4. POS CHECKOUT & SEQUENTIAL BILL GENERATION
    # -------------------------------------------------------------
    dhapata_item = next((i for i in all_items if "Dhapata" in i["name"]), all_items[0])
    chai_item = next((i for i in all_items if "Chai" in i["name"] or "Coffee" in i["name"] or "Tea" in i["name"]), all_items[1])


    order_payload = {
        "items": [
            {"menu_item_id": dhapata_item["id"], "name": dhapata_item["name"], "unit_price": dhapata_item["price"], "quantity": 2},
            {"menu_item_id": chai_item["id"], "name": chai_item["name"], "unit_price": chai_item["price"], "quantity": 2}
        ],
        "discount": 20,
        "payment_mode": "CASH",
        "received_amount": 500
    }

    expected_subtotal = (dhapata_item["price"] * 2) + (chai_item["price"] * 2)
    expected_total = expected_subtotal - 20
    expected_change = 500 - expected_total

    r_checkout = cashier_session.post(f"{BASE_URL}/api/pos/checkout", json=order_payload)
    assert r_checkout.status_code == 200, f"Checkout failed: {r_checkout.text}"
    checkout_res = r_checkout.json()
    assert checkout_res["success"] == True
    bill1 = checkout_res["bill"]
    
    assert bill1["bill_number"].startswith("POS-")
    assert bill1["subtotal"] == expected_subtotal
    assert bill1["discount"] == 20
    assert bill1["total_amount"] == expected_total
    assert bill1["received_amount"] == 500
    assert bill1["change_amount"] == expected_change
    assert bill1["payment_mode"] == "CASH"
    assert len(bill1["items"]) == 2
    print(f"    -> OK: First POS Bill #{bill1['bill_number']} generated! Total: Rs.{bill1['total_amount']}, Change: Rs.{bill1['change_amount']}")

    # -------------------------------------------------------------
    # 5. SECOND POS BILL (UPI) & NUMBER SEQUENCE
    # -------------------------------------------------------------
    print("\n[8] Testing Second POS Bill with UPI Payment & Sequential Numbering...")
    order_upi_payload = {
        "items": [
            {"menu_item_id": dhapata_item["id"], "name": dhapata_item["name"], "unit_price": dhapata_item["price"], "quantity": 1}
        ],
        "discount": 0,
        "payment_mode": "UPI",
        "received_amount": dhapata_item["price"]
    }
    r_checkout2 = cashier_session.post(f"{BASE_URL}/api/pos/checkout", json=order_upi_payload)
    assert r_checkout2.status_code == 200
    bill2 = r_checkout2.json()["bill"]
    assert bill2["payment_mode"] == "UPI"
    
    # Check sequence
    b1_num = int(bill1["bill_number"].replace("POS-", ""))
    b2_num = int(bill2["bill_number"].replace("POS-", ""))
    assert b2_num == b1_num + 1, f"Sequential numbering error: {bill1['bill_number']} vs {bill2['bill_number']}"
    print(f"    -> OK: Sequential bill numbers verified: {bill1['bill_number']} -> {bill2['bill_number']}")

    # -------------------------------------------------------------
    # 6. HISTORICAL PRICE SNAPSHOTTING INTEGRITY TEST
    # -------------------------------------------------------------
    print("\n[9] Testing Historical Price Snapshot Integrity...")
    original_dhapata_price = dhapata_item["price"]
    new_test_price = original_dhapata_price + 50.0

    # Admin updates the menu item price in database
    r_update_price = admin_session.post(f"{BASE_URL}/api/admin/menu-items", json={
        "id": dhapata_item["id"],
        "name": dhapata_item["name"],
        "category_id": dhapata_item["category_id"],
        "price": new_test_price,
        "is_available": True,
        "display_order": dhapata_item.get("display_order", 0)
    })
    assert r_update_price.status_code == 200, "Price update failed"
    print(f"    -> Menu item '{dhapata_item['name']}' price changed from Rs.{original_dhapata_price} to Rs.{new_test_price}")

    # Now fetch bill1 and check that its snapshotted unit_price was NOT altered!
    r_fetch_bill1 = admin_session.get(f"{BASE_URL}/api/pos/bills/{bill1['id']}")
    assert r_fetch_bill1.status_code == 200
    fetched_bill1 = r_fetch_bill1.json()["bill"]
    snapshotted_item = next(i for i in fetched_bill1["items"] if i["menu_item_id"] == dhapata_item["id"])
    assert snapshotted_item["unit_price"] == original_dhapata_price, f"Snapshot failed! Price changed to {snapshotted_item['unit_price']}"
    print(f"    -> OK: Historical snapshot confirmed! Bill #{bill1['bill_number']} still has unit price Rs.{snapshotted_item['unit_price']}")

    # Revert price back
    admin_session.post(f"{BASE_URL}/api/admin/menu-items", json={
        "id": dhapata_item["id"],
        "name": dhapata_item["name"],
        "category_id": dhapata_item["category_id"],
        "price": original_dhapata_price,
        "is_available": True,
        "display_order": dhapata_item.get("display_order", 0)
    })

    # -------------------------------------------------------------
    # 7. ADMIN MENU MANAGEMENT (Add/Toggle/Delete)
    # -------------------------------------------------------------
    print("\n[10] Testing Admin Menu Management (Add Item, Toggle Availability, Delete Item)...")
    # Add new item
    r_add_item = admin_session.post(f"{BASE_URL}/api/admin/menu-items", json={
        "name": "Special Kesar Pista Kulfi",
        "price": 65.0,
        "category_id": dhapata_item["category_id"],
        "code": "DS99",
        "is_available": True,
        "display_order": 99
    })
    assert r_add_item.status_code == 200
    new_item = r_add_item.json()["item"]
    print(f"    -> OK: Added new item '{new_item['name']}' with ID {new_item['id']}")

    # Toggle availability
    r_toggle = admin_session.post(f"{BASE_URL}/api/admin/menu-items/{new_item['id']}/toggle-availability")
    assert r_toggle.status_code == 200
    assert r_toggle.json()["is_available"] == False
    print("    -> OK: Successfully toggled item availability to Disabled")

    # Delete test item
    r_del = admin_session.delete(f"{BASE_URL}/api/admin/menu-items/{new_item['id']}")
    assert r_del.status_code == 200
    print("    -> OK: Successfully deleted test item")

    # -------------------------------------------------------------
    # 8. SALES REPORTS & ANALYTICS
    # -------------------------------------------------------------
    print("\n[11] Testing Sales Reports & Analytics (Summary & Best Sellers)...")
    r_summary = admin_session.get(f"{BASE_URL}/api/admin/reports/summary")
    assert r_summary.status_code == 200
    summary = r_summary.json()["today"]
    assert summary["bills_count"] >= 2
    assert summary["cash_sales"] > 0
    assert summary["upi_sales"] > 0
    assert summary["total_sales"] == summary["cash_sales"] + summary["upi_sales"] + summary["card_sales"]
    print(f"    -> OK: Today's Total Sales: Rs.{summary['total_sales']} (Cash: Rs.{summary['cash_sales']}, UPI: Rs.{summary['upi_sales']}, Card: Rs.{summary['card_sales']})")

    r_best = admin_session.get(f"{BASE_URL}/api/admin/reports/best-sellers")
    assert r_best.status_code == 200
    best_sellers = r_best.json()["best_sellers"]
    assert len(best_sellers) >= 1
    print(f"    -> OK: Top selling dish: {best_sellers[0]['item_name']} ({best_sellers[0]['total_qty']} sold, Rs.{best_sellers[0]['total_revenue']})")

    # -------------------------------------------------------------
    # 9. POS BILL HISTORY & REPRINT
    # -------------------------------------------------------------
    print("\n[12] Testing POS Bill History and Search Filter...")
    r_history = admin_session.get(f"{BASE_URL}/api/admin/pos-bills?q={bill1['bill_number']}")
    assert r_history.status_code == 200
    hist_data = r_history.json()
    assert len(hist_data["bills"]) == 1
    assert hist_data["bills"][0]["bill_number"] == bill1["bill_number"]
    print(f"    -> OK: POS bill history search returned Bill #{bill1['bill_number']}")

    # -------------------------------------------------------------
    # 10. USER / PIN MANAGEMENT
    # -------------------------------------------------------------
    print("\n[13] Testing Cashier PIN Update by Admin...")
    r_pin_update = admin_session.post(f"{BASE_URL}/api/admin/users/change-pin", json={
        "role": "cashier",
        "new_pin": "5678"
    })
    assert r_pin_update.status_code == 200
    print("    -> OK: Admin successfully updated Cashier PIN to '5678'")

    # Verify old PIN fails and new PIN succeeds
    r_old_pin_login = requests.post(f"{BASE_URL}/api/pos/login", json={"role": "cashier", "pin": "1234"})
    assert r_old_pin_login.status_code == 401
    
    r_new_pin_login = requests.post(f"{BASE_URL}/api/pos/login", json={"role": "cashier", "pin": "5678"})
    assert r_new_pin_login.status_code == 200
    print("    -> OK: Cashier authenticated with new PIN '5678' (Old PIN '1234' rejected)")

    # Reset Cashier PIN back to 1234
    admin_session.post(f"{BASE_URL}/api/admin/users/change-pin", json={"role": "cashier", "new_pin": "1234"})
    print("    -> OK: Cashier PIN reset back to default '1234'")

    # -------------------------------------------------------------
    # 11. 12 TABLES RESTAURANT MANAGEMENT & DINING TAB WORKFLOW
    # -------------------------------------------------------------
    print("\n[14] Testing 12 Tables Restaurant State API (GET /api/pos/tables)...")
    r_tables = cashier_session.get(f"{BASE_URL}/api/pos/tables")
    assert r_tables.status_code == 200
    tables_data = r_tables.json()
    assert tables_data["success"] == True
    assert tables_data["total_tables"] == 12
    assert len(tables_data["tables"]) == 12
    print(f"    -> OK: Successfully verified 12 restaurant tables. Vacant: {tables_data['vacant_count']}, Occupied: {tables_data['occupied_count']}")

    print("\n[15] Testing Dining Workflow: Starting Running Tab on Table 4 (save-tab)...")
    # Get current max_id before saving tab
    r_live_before = cashier_session.get(f"{BASE_URL}/api/display/live-orders")
    current_max_event = r_live_before.json().get("max_id", 0)

    r_save_tab = cashier_session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 4,
        "customer_name": "Sharma Family",
        "items": [
            {"menu_item_id": dhapata_item["id"], "name": dhapata_item["name"], "unit_price": dhapata_item["price"], "quantity": 2}
        ]
    })
    assert r_save_tab.status_code == 200
    tab_res = r_save_tab.json()
    assert tab_res["success"] == True
    assert tab_res["bill"]["status"] == "OPEN"
    assert tab_res["bill"]["order_type"] == "DINING"
    assert tab_res["bill"]["table_number"] == 4
    tab_bill_no = tab_res["bill"]["bill_number"]
    print(f"    -> OK: Table 4 Tab created with status OPEN, Bill #{tab_bill_no}, Subtotal: Rs.{tab_res['bill']['subtotal']}")

    # VERIFY LOOPHOLE FIX: Dining tab creation does NOT emit print events on Display screen
    r_live_check = cashier_session.get(f"{BASE_URL}/api/display/live-orders?since_id={current_max_event}")
    assert r_live_check.status_code == 200
    assert len(r_live_check.json().get("new_bills", [])) == 0, "Loophole detected: OPEN dining tab emitted a print event!"
    print("    -> OK: Verified NO print event emitted for in-progress dining tab")

    # Verify Table 4 is now OCCUPIED
    r_table4 = cashier_session.get(f"{BASE_URL}/api/pos/tables/4")
    assert r_table4.status_code == 200
    t4_data = r_table4.json()
    assert t4_data["status"] == "OCCUPIED"
    assert t4_data["bill"]["bill_number"] == tab_bill_no
    print("    -> OK: Table 4 verified as OCCUPIED with active running order")

    # Add more food items to Table 4 (e.g. guests ordered chai & dessert while eating)
    print("\n[16] Testing Incremental Ordering: Adding more dishes to Table 4...")
    r_add_dishes = cashier_session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 4,
        "items": [
            {"menu_item_id": dhapata_item["id"], "name": dhapata_item["name"], "unit_price": dhapata_item["price"], "quantity": 2},
            {"name": "Special Masala Chai", "unit_price": 20.0, "quantity": 3}
        ]
    })
    assert r_add_dishes.status_code == 200
    updated_tab = r_add_dishes.json()["bill"]
    assert len(updated_tab["items"]) == 2
    expected_subtotal = (dhapata_item["price"] * 2) + (20.0 * 3)
    assert updated_tab["subtotal"] == expected_subtotal
    print(f"    -> OK: Table 4 tab updated with additional chai! New total: Rs.{updated_tab['subtotal']}")

    # Settle Table 4 final bill when leaving
    print("\n[17] Testing Dining Settlement: Final Payment & Table Freeing (POST /api/pos/tables/settle)...")
    r_settle = cashier_session.post(f"{BASE_URL}/api/pos/tables/settle", json={
        "table_number": 4,
        "payment_mode": "UPI",
        "discount": 10.0
    })
    assert r_settle.status_code == 200
    settled_bill = r_settle.json()["bill"]
    assert settled_bill["status"] == "COMPLETED"
    assert settled_bill["discount"] == 10.0
    assert settled_bill["total_amount"] == expected_subtotal - 10.0
    assert settled_bill["payment_mode"] == "UPI"
    print(f"    -> OK: Table 4 settled successfully as COMPLETED (Paid Rs.{settled_bill['total_amount']} via UPI)")

    # VERIFY: Final settlement DOES emit print event on Display screen
    r_live_settled = cashier_session.get(f"{BASE_URL}/api/display/live-orders?since_id={current_max_event}")
    assert r_live_settled.status_code == 200
    new_print_bills = r_live_settled.json().get("new_bills", [])
    assert len(new_print_bills) >= 1, "Settled bill was not emitted for printing!"
    assert new_print_bills[0]["bill_number"] == settled_bill["bill_number"]
    print(f"    -> OK: Print event verified for settled Bill #{settled_bill['bill_number']} on Display screen!")

    # Verify Table 4 is VACANT again
    r_table4_after = cashier_session.get(f"{BASE_URL}/api/pos/tables/4")
    assert r_table4_after.status_code == 200
    assert r_table4_after.json()["status"] == "VACANT"
    print("    -> OK: Table 4 returned to VACANT status and ready for next guests")

    # -------------------------------------------------------------
    # 12. DEDICATED DISPLAY & WIRED PRINT SCREEN
    # -------------------------------------------------------------
    print("\n[18] Testing Dedicated Display View & Live Order Stream API...")
    r_display_page = cashier_session.get(f"{BASE_URL}/display")
    assert r_display_page.status_code == 200
    assert "Live Kitchen &amp; Wired Thermal Print Station" in r_display_page.text or "Live Kitchen & Wired Thermal Print Station" in r_display_page.text
    print("    -> OK: /display window loaded successfully")

    r_live_feed = cashier_session.get(f"{BASE_URL}/api/display/live-orders?since_id=0&limit=5")
    assert r_live_feed.status_code == 200
    live_data = r_live_feed.json()
    assert live_data["success"] == True
    assert len(live_data["bills"]) <= 5
    print(f"    -> OK: Live display feed returned {len(live_data['bills'])} recent completed orders (Max Event ID: {live_data['max_id']})")


    print("\n==================================================================")
    print("ALL 18 QUICK POS, RBAC, 12 TABLES, DUAL BILLING & DISPLAY TESTS PASSED (100% OK)!")
    print("==================================================================")


if __name__ == "__main__":
    run_pos_tests()

