"""
Comprehensive Role & Workflow Validation Tests
==============================================
Validates the simplified system architecture:
1. Admin: PINs, Reports, Menu, Bulk Billing
2. Cashier: Walk-in instant checkout (with auto-print) & Dining Active Table settlement
3. Waiter: Place order for Table, Edit active order (add & remove dishes), view tracker
4. Kitchen: Simple read-only ticket feed with table numbers, dishes, quantities, notes
"""

import os
import unittest
from app import app
from database.db import get_db
from database.models import User, Order, PosBill, DiningTable, MenuItem

class TestRolesAndWorkflows(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_admin_role_access(self):
        """Verify Admin login and admin-only endpoints."""
        # Login with Admin PIN
        res = self.client.post("/api/auth/login", json={"pin": "2005", "role": "admin"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["role"], "admin")

        # Admin can access admin modules
        r_menu = self.client.get("/admin/menu")
        self.assertEqual(r_menu.status_code, 200)

        r_reports = self.client.get("/admin/reports")
        self.assertEqual(r_reports.status_code, 200)

        r_summary = self.client.get("/api/admin/reports/summary")
        self.assertEqual(r_summary.status_code, 200)
        self.assertTrue(r_summary.get_json()["success"])

        # Admin can access bulk billing
        r_bulk = self.client.get("/bulk")
        self.assertEqual(r_bulk.status_code, 200)

    def test_02_walkin_customer_flow(self):
        """Verify Cashier Walk-in instant checkout with auto-print."""
        # Login as Cashier
        res = self.client.post("/api/auth/login", json={"pin": "2005", "role": "cashier"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["role"], "cashier")

        # Get menu items
        r_cat = self.client.get("/api/pos/catalog")
        self.assertEqual(r_cat.status_code, 200)
        categories = r_cat.get_json()["categories"]
        self.assertTrue(len(categories) > 0)
        first_item = categories[0]["items"][0]

        # Instant Walk-in checkout
        checkout_payload = {
            "order_type": "WALK_IN",
            "items": [
                {"menu_item_id": first_item["id"], "name": first_item["name"], "unit_price": first_item["price"], "quantity": 2}
            ],
            "discount": 0,
            "payment_mode": "CASH",
            "received_amount": first_item["price"] * 2
        }
        r_chk = self.client.post("/api/pos/checkout", json=checkout_payload)
        self.assertEqual(r_chk.status_code, 200)
        data = r_chk.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["auto_print"])
        self.assertEqual(data["bill"]["order_type"], "WALK_IN")
        self.assertEqual(data["bill"]["total_amount"], first_item["price"] * 2)

    def test_03_dining_customer_flow_and_waiter_editing(self):
        """
        Verify Dining customer flow:
        1. Waiter places order for Table 6
        2. Waiter edits active order on Table 6 (adds dish, removes dish)
        3. Cashier sees Table 6 in Active Orders
        4. Customer is done dining -> Cashier settles bill via UPI -> Table 6 freed
        """
        # 1. Login as Waiter
        res_w = self.client.post("/api/auth/login", json={"pin": "2005", "role": "waiter"})
        self.assertEqual(res_w.status_code, 200)

        # Get available dishes
        r_menu = self.client.get("/api/waiter/menu")
        self.assertEqual(r_menu.status_code, 200)
        cats = r_menu.get_json()["categories"]
        item1 = cats[0]["items"][0]
        item2 = cats[0]["items"][1] if len(cats[0]["items"]) > 1 else cats[0]["items"][0]

        # Place initial order on Table 6
        order_payload = {
            "table_number": 6,
            "order_type": "DINING",
            "source": "WAITER",
            "customer_name": "Table 6 Guests",
            "items": [
                {"menu_item_id": item1["id"], "name": item1["name"], "unit_price": item1["price"], "quantity": 2, "item_notes": "Less spicy"}
            ]
        }
        r_ord = self.client.post("/api/orders", json=order_payload)
        self.assertEqual(r_ord.status_code, 200)
        ord_data = r_ord.get_json()["order"]
        self.assertEqual(ord_data["table_number"], 6)
        self.assertEqual(ord_data["status"], "PLACED")
        self.assertEqual(len(ord_data["items"]), 1)

        # 2. Waiter edits active order: adds item2, updates item1 quantity to 1
        edit_payload = {
            "items": [
                {"menu_item_id": item1["id"], "name": item1["name"], "unit_price": item1["price"], "quantity": 1, "item_notes": "Less spicy"},
                {"menu_item_id": item2["id"], "name": item2["name"], "unit_price": item2["price"], "quantity": 3, "item_notes": "Extra hot"}
            ]
        }
        r_edit = self.client.put("/api/waiter/tables/6/order", json=edit_payload)
        self.assertEqual(r_edit.status_code, 200)
        edited_ord = r_edit.get_json()["order"]
        self.assertEqual(len(edited_ord["items"]), 2)
        expected_total = (item1["price"] * 1) + (item2["price"] * 3)
        self.assertEqual(edited_ord["total_amount"], expected_total)

        # 3. Cashier logs in and checks Active Tables
        res_c = self.client.post("/api/auth/login", json={"pin": "2005", "role": "cashier"})
        self.assertEqual(res_c.status_code, 200)

        r_tables = self.client.get("/api/pos/tables")
        self.assertEqual(r_tables.status_code, 200)
        tables_res = r_tables.get_json()["tables"]
        t6 = next(t for t in tables_res if t["table_number"] == 6)
        self.assertEqual(t6["status"], "OCCUPIED")
        self.assertEqual(t6["items_count"], 2)
        self.assertEqual(t6["total_amount"], expected_total)

        # 4. Cashier settles Table 6 bill
        settle_payload = {
            "table_number": 6,
            "payment_mode": "UPI",
            "discount": 10.0
        }
        r_settle = self.client.post("/api/pos/tables/settle", json=settle_payload)
        self.assertEqual(r_settle.status_code, 200)
        settle_data = r_settle.get_json()
        self.assertTrue(settle_data["success"])
        self.assertTrue(settle_data["auto_print"])
        self.assertEqual(settle_data["bill"]["payment_mode"], "UPI")
        self.assertEqual(settle_data["bill"]["total_amount"], expected_total - 10.0)

        # Verify Table 6 is now VACANT
        r_tables_after = self.client.get("/api/pos/tables")
        tables_after = r_tables_after.get_json()["tables"]
        t6_after = next(t for t in tables_after if t["table_number"] == 6)
        self.assertEqual(t6_after["status"], "VACANT")

    def test_04_kitchen_screen_read_only(self):
        """Verify Kitchen Screen API returns pure active orders."""
        r_kitch = self.client.get("/api/orders/kitchen")
        self.assertEqual(r_kitch.status_code, 200)
        data = r_kitch.get_json()
        self.assertTrue(data["success"])
        self.assertIn("orders", data)
        self.assertIn("server_time", data)

    def test_05_role_security_guards(self):
        """Verify role-based boundary enforcement."""
        # Waiter login
        self.client.post("/api/auth/login", json={"pin": "2005", "role": "waiter"})
        r_admin = self.client.get("/admin")
        self.assertEqual(r_admin.status_code, 302) # Redirect to /waiter

        r_pos = self.client.get("/pos")
        self.assertEqual(r_pos.status_code, 302) # Redirect to /waiter

        # Cashier login
        self.client.post("/api/auth/login", json={"pin": "2005", "role": "cashier"})
        r_admin2 = self.client.get("/admin")
        self.assertEqual(r_admin2.status_code, 302) # Redirect to /pos

if __name__ == "__main__":
    unittest.main()
