"""
Automated Test Suite for Hotel Mitraya Web Bill Generation System & PIN Security
"""

import requests
import os
import sys

PORT = os.environ.get("PORT", "5056")
BASE_URL = os.environ.get("BASE_URL", f"http://127.0.0.1:{PORT}")

def run_tests():
    print("=== STARTING FULL END-TO-END VERIFICATION WITH PIN AUTH ===")
    
    # 1. Health Check (Public endpoint)
    print("\n[1] Testing GET /api/health (Public endpoint)...")
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    health_data = r.json()
    print(f"    -> OK: {health_data}")
    assert health_data["status"] == "healthy"
    assert health_data["template_exists"] == True

    # 2. Static Assets (Public)
    print("\n[2] Testing GET /static/style.css & /static/app.js...")
    rcss = requests.get(f"{BASE_URL}/static/style.css")
    assert rcss.status_code == 200, "style.css missing"
    print(f"    -> OK: CSS verified ({len(rcss.text)} bytes)")

    rjs = requests.get(f"{BASE_URL}/static/app.js")
    assert rjs.status_code == 200, "app.js missing"
    print(f"    -> OK: JS verified ({len(rjs.text)} bytes)")

    # 3. Dedicated Login Page
    print("\n[3] Testing GET /login...")
    rlogin = requests.get(f"{BASE_URL}/login")
    assert rlogin.status_code == 200, f"Login page failed: {rlogin.status_code}"
    assert "Secured Billing System" in rlogin.text or "HOTEL MITRAYA" in rlogin.text
    print(f"    -> OK: Login page served ({len(rlogin.text)} bytes)")

    # 4. Security Verification: Unauthenticated Access Rejection
    print("\n[4] Testing Security Protection for Unauthenticated Requests...")
    # Unauthenticated GET / should redirect to /login
    r_unauth_index = requests.get(f"{BASE_URL}/", allow_redirects=False)
    assert r_unauth_index.status_code in [302, 401], f"Unauth index should redirect or deny: {r_unauth_index.status_code}"
    print(f"    -> OK: Unauthenticated index redirected with status {r_unauth_index.status_code}")

    # Unauthenticated API calls should return 401
    r_unauth_api = requests.get(f"{BASE_URL}/api/bills")
    assert r_unauth_api.status_code == 401, f"Unauth API should return 401, got {r_unauth_api.status_code}"
    assert r_unauth_api.json().get("auth_required") == True
    print(f"    -> OK: Unauthenticated API call blocked with 401 Unauthorized")

    # 5. PIN Verification: Wrong PIN Rejection
    print("\n[5] Testing PIN Verification with WRONG PIN ('1234')...")
    r_wrong = requests.post(f"{BASE_URL}/api/login", json={"pin": "1234"})
    assert r_wrong.status_code == 401, f"Wrong PIN should return 401, got {r_wrong.status_code}"
    assert r_wrong.json().get("success") == False
    print(f"    -> OK: Wrong PIN rejected properly ({r_wrong.json().get('error')})")

    # 6. PIN Verification: Correct PIN Login ('2005')
    print("\n[6] Testing PIN Verification with CORRECT PIN ('2005')...")
    session = requests.Session()
    r_login = session.post(f"{BASE_URL}/api/login", json={"pin": "2005"})
    assert r_login.status_code == 200, f"Login failed: {r_login.text}"
    login_data = r_login.json()
    assert login_data.get("success") == True
    print(f"    -> OK: Authenticated successfully: {login_data.get('message')}")

    # 7. Authenticated Dashboard Access
    print("\n[7] Testing GET / with Authenticated Session...")
    r_auth_index = session.get(f"{BASE_URL}/")
    assert r_auth_index.status_code == 200
    assert "HOTEL MITRAYA" in r_auth_index.text
    assert "btn-logout" in r_auth_index.text
    print(f"    -> OK: Main dashboard accessible with session cookie")

    # 8. Next Bill Number API
    print("\n[8] Testing GET /api/next-bill-no (Authenticated)...")
    r = session.get(f"{BASE_URL}/api/next-bill-no")
    assert r.status_code == 200
    next_no = r.json().get("next_bill_no")
    print(f"    -> OK: Next bill number suggested: {next_no}")

    # 9. Generate PDF Bill
    print("\n[9] Testing POST /api/bills/generate (Authenticated)...")
    bill_data = {
        "customer_name": "Royal Palms Banquets & Caterers",
        "bill_no": next_no,
        "created_on": "27/08/2026 05:00 PM",
        "bill_date": "27/08/2026",
        "items": [
            {"name": "Dahi Dhapata & Biryani plate", "qty": 100, "rate": 130},
            {"name": "Special Veg Thali", "qty": 50, "rate": 160},
            {"name": "Mineral Water Bottle (1L)", "qty": 150, "rate": 20}
        ],
        "discount": 500,
        "txn_mode": "UPI",
        "received_amount": 23500
    }
    r = session.post(f"{BASE_URL}/api/bills/generate", json=bill_data)
    assert r.status_code == 200, f"Generate bill failed: {r.text}"
    gen_result = r.json()
    assert gen_result["success"] == True
    bill_meta = gen_result["bill"]
    assert bill_meta.get("pdf_base64"), "pdf_base64 missing in response"
    print(f"    -> OK: Bill generated with base64 PDF: {bill_meta['filename']} ({bill_meta['size_kb']} KB)")

    # 10. List & Search Saved Bills
    print("\n[10] Testing GET /api/bills and Search...")
    r_list = session.get(f"{BASE_URL}/api/bills")
    assert r_list.status_code == 200
    assert len(r_list.json()["bills"]) >= 1

    r_search = session.get(f"{BASE_URL}/api/bills?q=Royal")
    assert r_search.status_code == 200
    assert len(r_search.json()["bills"]) >= 1
    print(f"    -> OK: Listed & searched saved bills successfully")

    # 11. Download & Preview PDF
    print("\n[11] Testing Download and Inline Preview...")
    r_dl = session.get(f"{BASE_URL}/api/bills/download/{bill_meta['filename']}")
    assert r_dl.status_code == 200
    assert r_dl.headers.get("Content-Type") == "application/pdf"

    r_prev = session.get(f"{BASE_URL}/api/bills/preview/{bill_meta['filename']}")
    assert r_prev.status_code == 200
    assert r_prev.headers.get("Content-Type") == "application/pdf"
    print(f"    -> OK: Download and Preview PDF verified")

    # 12. Logout & Re-lock Protection Verification
    print("\n[12] Testing Logout & Session Termination...")
    r_logout = session.post(f"{BASE_URL}/api/logout")
    assert r_logout.status_code == 200
    assert r_logout.json().get("success") == True

    # Now verify that subsequent API calls are blocked
    r_after_logout = session.get(f"{BASE_URL}/api/bills")
    assert r_after_logout.status_code == 401, f"Expected 401 after logout, got {r_after_logout.status_code}"
    print(f"    -> OK: Session terminated properly, subsequent requests blocked (401)")

    print("\n==================================================================")
    print("ALL 12 PIN SECURITY & BILLING TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()

