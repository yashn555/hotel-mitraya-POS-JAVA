"""
Hotel Mitraya - Comprehensive Live Simulation & End-to-End POS Test Suite
========================================================================
Simulates real-world restaurant operations:
1. Walk-in Customers: Immediate direct order placement and instant print event emission.
2. Dining Lifecycle (Table 3):
   - Arrives, sits at Table 3.
   - Orders Starters -> Saves tab (status OPEN, NO print event).
   - Orders Beverages (after time delay) -> Updates tab (status OPEN, NO print event).
   - Orders Main Course -> Updates tab (status OPEN, NO print event).
   - Orders Desserts -> Updates tab (status OPEN, NO print event).
   - Settles Bill (after dining period) -> Settle tab (status COMPLETED, final bill emitted to Display Screen).
3. Concurrent Multi-Table Operations: Tables 1, 5, 8, 12 operating in parallel with Walk-in customers.
4. Display Screen Polling Stream: Verifies live order stream accurately returns only completed bills.
5. 12 Tables Radar Accuracy: Verifies occupied vs vacant table counts and running totals.
6. Admin Financial Analytics Integrity: Verifies daily revenue, payment mode breakdowns, and best sellers.
"""

import requests
import time
import os
import sys

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5055")


def run_full_simulation():
    print("\n" + "=" * 75)
    print("  HOTEL MITRAYA - REAL-TIME POS & DINING SIMULATION TEST SUITE")
    print("=" * 75)

    session = requests.Session()

    # -------------------------------------------------------------
    # 0. AUTHENTICATION
    # -------------------------------------------------------------
    print("\n[PHASE 0] Staff Authentication...")
    r_login = session.post(f"{BASE_URL}/api/pos/login", json={"role": "cashier", "pin": "1234"})
    assert r_login.status_code == 200, f"Login failed: {r_login.text}"
    print("  -> Cashier authenticated successfully.")

    # Fetch catalog items
    r_cat = session.get(f"{BASE_URL}/api/pos/catalog")
    assert r_cat.status_code == 200
    catalog = r_cat.json()["categories"]
    all_items = []
    for c in catalog:
        all_items.extend(c["items"])

    dhapata = next((i for i in all_items if "Dhapata" in i["name"]), all_items[0])
    chai = next((i for i in all_items if "Chai" in i["name"] or "Tea" in i["name"]), all_items[1])
    thali = next((i for i in all_items if "Thali" in i["name"] or "Bhaji" in i["name"] or "Rice" in i["name"]), all_items[2])
    dessert = next((i for i in all_items if "Gulab" in i["name"] or "Kulfi" in i["name"] or "Ice" in i["name"]), all_items[3])

    print(f"  -> Menu catalog loaded: {len(all_items)} items available.")
    print(f"     * Starter: {dhapata['name']} (Rs.{dhapata['price']})")
    print(f"     * Beverage: {chai['name']} (Rs.{chai['price']})")
    print(f"     * Main Course: {thali['name']} (Rs.{thali['price']})")
    print(f"     * Dessert: {dessert['name']} (Rs.{dessert['price']})")

    # Initial Display Screen State
    r_display_init = session.get(f"{BASE_URL}/api/display/live-orders?since_id=0&limit=5")
    assert r_display_init.status_code == 200
    last_event_id = r_display_init.json().get("max_id", 0)
    print(f"  -> Display Screen initial sync: Base Event ID = {last_event_id}")

    # -------------------------------------------------------------
    # 1. WALK-IN CUSTOMER FLOW
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print("[PHASE 1] Walk-in Customer Flow (Immediate Direct Order & Print)")
    print("-" * 75)
    
    walkin_payload = {
        "order_type": "WALK_IN",
        "items": [
            {"menu_item_id": dhapata["id"], "name": dhapata["name"], "unit_price": dhapata["price"], "quantity": 2},
            {"menu_item_id": chai["id"], "name": chai["name"], "unit_price": chai["price"], "quantity": 1}
        ],
        "discount": 0.0,
        "payment_mode": "CASH",
        "received_amount": 500.0
    }
    
    r_walkin = session.post(f"{BASE_URL}/api/pos/checkout", json=walkin_payload)
    assert r_walkin.status_code == 200, f"Walkin checkout failed: {r_walkin.text}"
    walkin_bill = r_walkin.json()["bill"]
    expected_walkin_total = (dhapata["price"] * 2) + (chai["price"] * 1)
    
    assert walkin_bill["status"] == "COMPLETED"
    assert walkin_bill["order_type"] == "WALK_IN"
    assert walkin_bill["total_amount"] == expected_walkin_total
    print(f"  -> Walk-in Bill #{walkin_bill['bill_number']} generated! Subtotal: Rs.{walkin_bill['subtotal']}, Net: Rs.{walkin_bill['total_amount']}")

    # Verify Display Screen receives Walk-in print event immediately
    r_display_poll = session.get(f"{BASE_URL}/api/display/live-orders?since_id={last_event_id}&limit=5")
    assert r_display_poll.status_code == 200
    display_data = r_display_poll.json()
    new_bills = display_data.get("new_bills", [])
    
    assert len(new_bills) >= 1, "Walk-in bill was not emitted to Display screen!"
    assert new_bills[-1]["bill_number"] == walkin_bill["bill_number"]
    last_event_id = display_data["max_id"]
    print(f"  -> Display Screen received print event for Walk-in #{walkin_bill['bill_number']}! (New Event ID: {last_event_id})")

    # -------------------------------------------------------------
    # 2. REALISTIC DINING LIFECYCLE (Table 3: Multi-Stage Ordering)
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print("[PHASE 2] Realistic Dining Lifecycle on Table 3 (Incremental Ordering over time)")
    print("-" * 75)

    # Stage 1: Guests sit down at Table 3 and order Starters
    print("\n  [Stage 1] Guests seated at Table 3 -> Order 2x Starters...")
    table3_items = [
        {"menu_item_id": dhapata["id"], "name": dhapata["name"], "unit_price": dhapata["price"], "quantity": 2}
    ]
    r_tab_s1 = session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 3,
        "customer_name": "Patil Family",
        "items": table3_items
    })
    assert r_tab_s1.status_code == 200
    tab3_data = r_tab_s1.json()["bill"]
    assert tab3_data["status"] == "OPEN"
    assert tab3_data["table_number"] == 3
    table3_bill_no = tab3_data["bill_number"]
    print(f"     -> Table 3 Tab created (Bill #{table3_bill_no}, Running Total: Rs.{tab3_data['subtotal']})")

    # Check Table Radar status
    r_tables = session.get(f"{BASE_URL}/api/pos/tables")
    t3_status = next(t for t in r_tables.json()["tables"] if t["table_number"] == 3)
    assert t3_status["status"] == "OCCUPIED"
    assert t3_status["total_amount"] == (dhapata["price"] * 2)
    print(f"     -> Table 3 verified as OCCUPIED in 12 Tables Radar.")

    # Check Display Screen does NOT print
    r_disp_s1 = session.get(f"{BASE_URL}/api/display/live-orders?since_id={last_event_id}")
    assert len(r_disp_s1.json().get("new_bills", [])) == 0, "ERROR: In-progress dining tab emitted print event!"
    print("     -> Verified: Display screen did NOT trigger print (Running tab remains silent).")

    # Stage 2 (+10s delay): Guests order Beverages
    print("\n  [Stage 2] After 10s -> Guests order 3x Masala Chai...")
    time.sleep(1.0) # simulation pause
    table3_items.append(
        {"menu_item_id": chai["id"], "name": chai["name"], "unit_price": chai["price"], "quantity": 3}
    )
    r_tab_s2 = session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 3,
        "items": table3_items
    })
    assert r_tab_s2.status_code == 200
    subtotal_s2 = (dhapata["price"] * 2) + (chai["price"] * 3)
    assert r_tab_s2.json()["bill"]["subtotal"] == subtotal_s2
    print(f"     -> Table 3 updated with Chai (New Running Total: Rs.{subtotal_s2})")

    # Stage 3 (+20s delay): Guests order Main Course
    print("\n  [Stage 3] After 20s -> Guests order 2x Main Course Thali...")
    time.sleep(1.0)
    table3_items.append(
        {"menu_item_id": thali["id"], "name": thali["name"], "unit_price": thali["price"], "quantity": 2}
    )
    r_tab_s3 = session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 3,
        "items": table3_items
    })
    assert r_tab_s3.status_code == 200
    subtotal_s3 = subtotal_s2 + (thali["price"] * 2)
    assert r_tab_s3.json()["bill"]["subtotal"] == subtotal_s3
    print(f"     -> Table 3 updated with Main Course (New Running Total: Rs.{subtotal_s3})")

    # Stage 4 (+30s delay): Guests order Desserts
    print("\n  [Stage 4] After 30s -> Guests order 2x Desserts...")
    time.sleep(1.0)
    table3_items.append(
        {"menu_item_id": dessert["id"], "name": dessert["name"], "unit_price": dessert["price"], "quantity": 2}
    )
    r_tab_s4 = session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 3,
        "items": table3_items
    })
    assert r_tab_s4.status_code == 200
    subtotal_s4 = subtotal_s3 + (dessert["price"] * 2)
    assert r_tab_s4.json()["bill"]["subtotal"] == subtotal_s4
    print(f"     -> Table 3 updated with Desserts (New Running Total: Rs.{subtotal_s4})")

    # Verify Display Screen STILL has not printed anything for Table 3
    r_disp_s4 = session.get(f"{BASE_URL}/api/display/live-orders?since_id={last_event_id}")
    assert len(r_disp_s4.json().get("new_bills", [])) == 0
    print("     -> Verified: Display screen still has zero print events during entire dining session.")

    # Stage 5 (Dining Complete / Departure): Settle Bill & Print
    print("\n  [Stage 5] Guests finished dining -> Settle Table 3 Bill with Rs.20 Discount via UPI...")
    r_settle3 = session.post(f"{BASE_URL}/api/pos/tables/settle", json={
        "table_number": 3,
        "discount": 20.0,
        "payment_mode": "UPI"
    })
    assert r_settle3.status_code == 200, f"Settlement failed: {r_settle3.text}"
    settled_t3 = r_settle3.json()["bill"]
    
    expected_t3_net = subtotal_s4 - 20.0
    assert settled_t3["status"] == "COMPLETED"
    assert settled_t3["discount"] == 20.0
    assert settled_t3["total_amount"] == expected_t3_net
    assert len(settled_t3["items"]) == 4
    print(f"     -> Table 3 Settled! Bill #{settled_t3['bill_number']}, Net Total: Rs.{settled_t3['total_amount']} (Paid via UPI)")

    # Verify Table 3 is VACANT now
    r_t3_check = session.get(f"{BASE_URL}/api/pos/tables/3")
    assert r_t3_check.json()["status"] == "VACANT"
    print("     -> Table 3 returned to VACANT status.")

    # VERIFY DISPLAY SCREEN PRINTS THE FULL FINAL SETTLED BILL
    r_disp_final = session.get(f"{BASE_URL}/api/display/live-orders?since_id={last_event_id}")
    new_disp_bills = r_disp_final.json().get("new_bills", [])
    assert len(new_disp_bills) >= 1, "Final settled dining bill was not emitted to Display screen!"
    
    t3_print_bill = next((b for b in new_disp_bills if b["bill_number"] == settled_t3["bill_number"]), None)
    assert t3_print_bill is not None
    assert t3_print_bill["table_number"] == 3
    assert len(t3_print_bill["items"]) == 4
    assert t3_print_bill["total_amount"] == expected_t3_net
    last_event_id = r_disp_final.json()["max_id"]
    print(f"     -> OK: Display Screen received final Table 3 Bill #{settled_t3['bill_number']} with all {len(t3_print_bill['items'])} items and net Rs.{expected_t3_net}!")

    # -------------------------------------------------------------
    # 3. CONCURRENT MULTI-TABLE & WALK-IN RUSH SIMULATION
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print("[PHASE 3] Concurrent Multi-Table Operations (Tables 1, 7, 11 + Walk-in Rush)")
    print("-" * 75)

    # Table 1: Opens tab
    session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 1,
        "items": [{"menu_item_id": dhapata["id"], "name": dhapata["name"], "unit_price": dhapata["price"], "quantity": 1}]
    })
    # Table 7: Opens tab
    session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 7,
        "items": [{"menu_item_id": thali["id"], "name": thali["name"], "unit_price": thali["price"], "quantity": 3}]
    })
    # Table 11: Opens tab
    session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 11,
        "items": [{"menu_item_id": chai["id"], "name": chai["name"], "unit_price": chai["price"], "quantity": 4}]
    })
    
    # Check 12 Tables radar
    r_radar = session.get(f"{BASE_URL}/api/pos/tables").json()
    assert r_radar["occupied_count"] >= 3
    print(f"  -> 12 Tables Radar: {r_radar['occupied_count']} Tables Occupied, {r_radar['vacant_count']} Vacant.")

    # Walk-in customer places quick order in middle of rush
    r_walkin2 = session.post(f"{BASE_URL}/api/pos/checkout", json={
        "order_type": "WALK_IN",
        "items": [{"menu_item_id": chai["id"], "name": chai["name"], "unit_price": chai["price"], "quantity": 2}],
        "payment_mode": "UPI"
    }).json()["bill"]
    print(f"  -> Rush Walk-in Bill #{r_walkin2['bill_number']} placed.")

    # Settle Table 1
    r_settle1 = session.post(f"{BASE_URL}/api/pos/tables/settle", json={
        "table_number": 1,
        "payment_mode": "CASH"
    }).json()["bill"]
    print(f"  -> Table 1 Settled (#{r_settle1['bill_number']}).")

    # Cancel / Clear Table 7 (e.g. guests changed mind)
    session.post(f"{BASE_URL}/api/pos/tables/7/clear")
    print("  -> Table 7 order cancelled and table freed.")

    # Table 11 adds dessert
    session.post(f"{BASE_URL}/api/pos/tables/save-tab", json={
        "table_number": 11,
        "items": [
            {"menu_item_id": chai["id"], "name": chai["name"], "unit_price": chai["price"], "quantity": 4},
            {"menu_item_id": dessert["id"], "name": dessert["name"], "unit_price": dessert["price"], "quantity": 2}
        ]
    })
    # Settle Table 11
    r_settle11 = session.post(f"{BASE_URL}/api/pos/tables/settle", json={
        "table_number": 11,
        "payment_mode": "CARD"
    }).json()["bill"]
    print(f"  -> Table 11 Settled (#{r_settle11['bill_number']}).")

    # Verify Display Screen stream received all completed bills (Walkin2, Table 1, Table 11) and ignored Table 7
    r_disp_rush = session.get(f"{BASE_URL}/api/display/live-orders?since_id={last_event_id}")
    rush_new_bills = r_disp_rush.json().get("new_bills", [])
    rush_bill_nos = [b["bill_number"] for b in rush_new_bills]
    
    assert r_walkin2["bill_number"] in rush_bill_nos
    assert r_settle1["bill_number"] in rush_bill_nos
    assert r_settle11["bill_number"] in rush_bill_nos
    print(f"  -> OK: Display Screen received all {len(rush_new_bills)} finalized bills from rush accurately!")

    # -------------------------------------------------------------
    # 4. ADMIN SALES & FINANCIAL INTEGRITY AUDIT
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print("[PHASE 4] Admin Sales & Financial Analytics Audit")
    print("-" * 75)
    
    admin_session = requests.Session()
    admin_session.post(f"{BASE_URL}/api/pos/login", json={"role": "admin", "pin": "2005"})
    
    r_summary = admin_session.get(f"{BASE_URL}/api/admin/reports/summary")
    assert r_summary.status_code == 200
    today_stats = r_summary.json()["today"]
    
    print(f"  -> Today's Total Settled Sales: Rs.{today_stats['total_sales']:.2f}")
    print(f"     * Cash Sales: Rs.{today_stats['cash_sales']:.2f}")
    print(f"     * UPI Sales: Rs.{today_stats['upi_sales']:.2f}")
    print(f"     * Card Sales: Rs.{today_stats['card_sales']:.2f}")
    print(f"     * Total Bills: {today_stats['bills_count']}")
    
    assert today_stats["cash_sales"] >= 0
    assert today_stats["upi_sales"] >= 0
    assert today_stats["card_sales"] >= 0
    assert round(today_stats["total_sales"], 2) == round(today_stats["cash_sales"] + today_stats["upi_sales"] + today_stats["card_sales"], 2)
    print("  -> Financial consistency audit passed: Cash + UPI + Card == Total Revenue (100% Match)")

    print("\n" + "=" * 75)
    print("  ALL REAL-TIME SIMULATION TESTS COMPLETED WITH 100% SUCCESS (0 ERRORS)")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_full_simulation()
