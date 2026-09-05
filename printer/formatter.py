"""
Hotel Mitraya - Production Receipt Formatter
=============================================
Formats restaurant bill receipts, KOT slips, and test tickets for:
- 58mm Thermal Printers (32 character width)
- 80mm Thermal Printers (42-48 character width)

Generates:
1. Binary ESC/POS Bytecode for thermal print heads (alignment, bold, scaling, feed & paper cut)
2. Monospaced Plain Text Slips for preview, logging, and browser print fallback
"""

import math
from datetime import datetime


class ReceiptFormatter:
    """
    Receipt formatting engine for Hotel Mitraya.
    """

    @staticmethod
    def _pad_between(left: str, right: str, width: int) -> str:
        """Pads spaces between left and right text to fit exact line width."""
        left_str = str(left)
        right_str = str(right)
        spaces = max(1, width - len(left_str) - len(right_str))
        return left_str + (" " * spaces) + right_str

    @classmethod
    def format_plain_text(cls, bill_data: dict, paper_width: int = 80, header_title: str = "HOTEL MITRAYA", footer_text: str = "Thank You! Visit Again.") -> str:
        """
        Format bill data into structured plain text receipt for 58mm (32 cols) or 80mm (42 cols).
        """
        cols = 32 if paper_width == 58 else 42
        lines = []

        divider = "-" * cols
        double_divider = "=" * cols

        # 1. Header (Centered)
        lines.append(header_title.center(cols))
        lines.append("Pure Veg Restaurant & Caterers".center(cols))
        lines.append("Dharmaraj Chowk, Nr Honda Showroom".center(cols))
        lines.append("Akurdi, Pune - 411035".center(cols))
        lines.append("Ph: +91 9158691003 | FSSAI: 21525037001433".center(cols))
        lines.append(double_divider)

        # 2. Metadata: Bill No, Date/Time, Table, Staff, Payment Mode
        bill_no = f"Bill: {bill_data.get('bill_number', 'POS-000000')}"
        date_str = bill_data.get('created_at') or datetime.now().strftime("%d/%m/%Y %I:%M %p")
        lines.append(cls._pad_between(bill_no, date_str, cols))

        table_label = bill_data.get('table_label') or (f"Table {bill_data.get('table_number')}" if bill_data.get('table_number') else "Walk-in")
        order_type = bill_data.get('order_type', 'WALK_IN')
        lines.append(cls._pad_between(f"Type: {table_label}", f"Mode: {bill_data.get('payment_mode', 'CASH')}", cols))

        cashier_name = bill_data.get('cashier_role') or bill_data.get('cashier_name') or "Staff"
        cust_name = bill_data.get('customer_name')
        if cust_name:
            lines.append(cls._pad_between(f"Cust: {cust_name[:15]}", f"Staff: {cashier_name[:10]}", cols))
        else:
            lines.append(cls._pad_between(f"Staff: {cashier_name}", "", cols).strip())

        lines.append(divider)

        # 3. Itemized Table Header
        if cols == 32:
            # 32 columns layout: Item (14) | Qty (3) | Rate (5) | Amt (8)
            lines.append("Item            Qty  Rate   Amt")
            lines.append(divider)
        else:
            # 42 columns layout: Item (20) | Qty (5) | Rate (7) | Amt (8)
            lines.append("Item                     Qty    Rate    Amt")
            lines.append(divider)

        # 4. Item Rows
        items = bill_data.get("items", [])
        for itm in items:
            name = str(itm.get("item_name") or itm.get("name") or "Item").strip()
            qty = float(itm.get("quantity", 1))
            qty_str = f"{int(qty)}" if qty.is_integer() else f"{qty:.1f}"
            rate = float(itm.get("unit_price", 0))
            amt = float(itm.get("total_price", qty * rate))

            rate_str = f"{rate:.0f}"
            amt_str = f"{amt:.2f}"

            if cols == 32:
                item_col = name[:14].ljust(14)
                qty_col = qty_str.rjust(3)
                rate_col = rate_str.rjust(5)
                amt_col = amt_str.rjust(8)
                lines.append(f"{item_col} {qty_col} {rate_col} {amt_col}")
                if len(name) > 14:
                    lines.append(f"  {name[14:30]}")
            else:
                item_col = name[:20].ljust(20)
                qty_col = qty_str.rjust(5)
                rate_col = rate_str.rjust(7)
                amt_col = amt_str.rjust(8)
                lines.append(f"{item_col} {qty_col} {rate_col} {amt_col}")
                if len(name) > 20:
                    lines.append(f"  {name[20:40]}")

        lines.append(divider)

        # 5. Financial Summary
        subtotal = float(bill_data.get("subtotal", 0))
        discount = float(bill_data.get("discount", 0))
        total_amount = float(bill_data.get("total_amount", subtotal - discount))

        lines.append(cls._pad_between("Sub Total:", f"Rs.{subtotal:.2f}", cols))
        if discount > 0:
            lines.append(cls._pad_between("Discount:", f"-Rs.{discount:.2f}", cols))

        lines.append(double_divider)
        lines.append(cls._pad_between("GRAND TOTAL:", f"Rs.{total_amount:.2f}", cols))
        lines.append(double_divider)

        # 6. Cash Received & Change Due
        payment_mode = str(bill_data.get("payment_mode", "CASH")).upper()
        if payment_mode == "CASH" and bill_data.get("received_amount"):
            rec = float(bill_data.get("received_amount", total_amount))
            change = float(bill_data.get("change_amount", max(0, rec - total_amount)))
            lines.append(cls._pad_between("Cash Tendered:", f"Rs.{rec:.2f}", cols))
            lines.append(cls._pad_between("Change Due:", f"Rs.{change:.2f}", cols))
            lines.append(divider)

        # 7. Footer
        lines.append("")
        lines.append(f"* {bill_data.get('bill_number', 'POS-RECEIPT')} *".center(cols))
        lines.append(footer_text.center(cols))
        lines.append("Have a Delicious Day!".center(cols))
        lines.append("")

        return "\n".join(lines)

    @classmethod
    def format_escpos_bytes(cls, bill_data: dict, paper_width: int = 80, header_title: str = "HOTEL MITRAYA", footer_text: str = "Thank You! Visit Again.", cut: bool = True) -> bytes:
        """
        Encode bill data into raw ESC/POS binary bytecode.
        """
        cols = 32 if paper_width == 58 else 42
        bytes_out = bytearray()

        def append_raw(*b):
            bytes_out.extend(b)

        def append_text(text=""):
            # Encode with ASCII / CP437 fallback
            bytes_out.extend((text + "\n").encode("cp437", errors="replace"))

        # ESC @ : Initialize printer
        append_raw(0x1B, 0x40)

        # ESC a 1 : Center align
        append_raw(0x1B, 0x61, 0x01)

        # GS ! 0x11 : Double width & double height for Hotel Title
        append_raw(0x1D, 0x21, 0x11)
        # ESC E 1 : Bold ON
        append_raw(0x1B, 0x45, 0x01)
        append_text(header_title)

        # Reset font to normal
        append_raw(0x1D, 0x21, 0x00)
        append_raw(0x1B, 0x45, 0x00)
        append_text("Pure Veg Restaurant & Caterers")
        append_text("Dharmaraj Chowk, Nr Honda Showroom")
        append_text("Akurdi, Pune - 411035")
        append_text("Ph: +91 9158691003 | FSSAI: 21525037001433")

        # ESC a 0 : Left align
        append_raw(0x1B, 0x61, 0x00)

        divider = "-" * cols
        append_text(divider)

        # Metadata
        bill_no = f"Bill: {bill_data.get('bill_number', 'POS-000000')}"
        date_str = bill_data.get('created_at') or datetime.now().strftime("%d/%m/%Y %I:%M %p")
        append_text(cls._pad_between(bill_no, date_str, cols))

        table_label = bill_data.get('table_label') or (f"Table {bill_data.get('table_number')}" if bill_data.get('table_number') else "Walk-in")
        mode = f"Mode: {bill_data.get('payment_mode', 'CASH')}"
        append_text(cls._pad_between(f"Type: {table_label}", mode, cols))

        cashier_name = bill_data.get('cashier_role') or bill_data.get('cashier_name') or "Staff"
        cust_name = bill_data.get('customer_name')
        if cust_name:
            append_text(cls._pad_between(f"Cust: {cust_name[:15]}", f"Staff: {cashier_name[:10]}", cols))
        else:
            append_text(cls._pad_between(f"Staff: {cashier_name}", "", cols).strip())

        append_text(divider)

        # Item Header
        if cols == 32:
            append_text("Item            Qty  Rate   Amt")
        else:
            append_text("Item                     Qty    Rate    Amt")
        append_text(divider)

        # Items
        items = bill_data.get("items", [])
        for itm in items:
            name = str(itm.get("item_name") or itm.get("name") or "Item").strip()
            qty = float(itm.get("quantity", 1))
            qty_str = f"{int(qty)}" if qty.is_integer() else f"{qty:.1f}"
            rate = float(itm.get("unit_price", 0))
            amt = float(itm.get("total_price", qty * rate))

            rate_str = f"{rate:.0f}"
            amt_str = f"{amt:.2f}"

            if cols == 32:
                item_col = name[:14].ljust(14)
                qty_col = qty_str.rjust(3)
                rate_col = rate_str.rjust(5)
                amt_col = amt_str.rjust(8)
                append_text(f"{item_col} {qty_col} {rate_col} {amt_col}")
                if len(name) > 14:
                    append_text(f"  {name[14:30]}")
            else:
                item_col = name[:20].ljust(20)
                qty_col = qty_str.rjust(5)
                rate_col = rate_str.rjust(7)
                amt_col = amt_str.rjust(8)
                append_text(f"{item_col} {qty_col} {rate_col} {amt_col}")
                if len(name) > 20:
                    append_text(f"  {name[20:40]}")

        append_text(divider)

        # Totals
        subtotal = float(bill_data.get("subtotal", 0))
        discount = float(bill_data.get("discount", 0))
        total_amount = float(bill_data.get("total_amount", subtotal - discount))

        append_text(cls._pad_between("Sub Total:", f"Rs.{subtotal:.2f}", cols))
        if discount > 0:
            append_text(cls._pad_between("Discount:", f"-Rs.{discount:.2f}", cols))

        append_text(divider)

        # Bold & Double Height Total
        append_raw(0x1B, 0x45, 0x01)  # Bold ON
        append_raw(0x1D, 0x21, 0x01)  # Double Height
        append_text(cls._pad_between("TOTAL:", f"Rs.{total_amount:.2f}", cols))
        append_raw(0x1D, 0x21, 0x00)  # Normal font
        append_raw(0x1B, 0x45, 0x00)  # Bold OFF

        append_text(divider)

        # Cash Details
        payment_mode = str(bill_data.get("payment_mode", "CASH")).upper()
        if payment_mode == "CASH" and bill_data.get("received_amount"):
            rec = float(bill_data.get("received_amount", total_amount))
            change = float(bill_data.get("change_amount", max(0, rec - total_amount)))
            append_text(cls._pad_between("Cash Tendered:", f"Rs.{rec:.2f}", cols))
            append_text(cls._pad_between("Change Due:", f"Rs.{change:.2f}", cols))
            append_text(divider)

        # Footer (Centered)
        append_raw(0x1B, 0x61, 0x01)
        append_text(f"* {bill_data.get('bill_number', 'POS-RECEIPT')} *")
        append_text(footer_text)
        append_text("Have a Delicious Day!")

        # Paper feed & Partial Cut
        append_text("\n\n\n")
        if cut:
            # GS V 66 0 : Cut paper
            append_raw(0x1D, 0x56, 0x42, 0x00)

        return bytes(bytes_out)

    @classmethod
    def format_test_slip(cls, paper_width: int = 80, printer_name: str = "Thermal Printer") -> dict:
        """Generates alignment and diagnostic test pattern for 58mm/80mm."""
        cols = 32 if paper_width == 58 else 42
        test_data = {
            "bill_number": "TEST-001",
            "order_type": "TEST_PRINT",
            "table_label": "Diagnostic Slip",
            "cashier_role": "Admin",
            "payment_mode": "CASH",
            "created_at": datetime.now().strftime("%d/%m/%Y %I:%M:%S %p"),
            "items": [
                {"item_name": "Special Dahi Dhapata", "quantity": 2, "unit_price": 110.0, "total_price": 220.0},
                {"item_name": "Masala Chai", "quantity": 3, "unit_price": 20.0, "total_price": 60.0},
                {"item_name": "Special Veg Thali", "quantity": 1, "unit_price": 160.0, "total_price": 160.0}
            ],
            "subtotal": 440.0,
            "discount": 20.0,
            "total_amount": 420.0,
            "received_amount": 500.0,
            "change_amount": 80.0
        }
        text_slip = cls.format_plain_text(test_data, paper_width=paper_width, header_title="* HOTEL MITRAYA PRINTER TEST *", footer_text=f"Width: {paper_width}mm ({cols} cols) | {printer_name}")
        escpos_bytes = cls.format_escpos_bytes(test_data, paper_width=paper_width, header_title="* HOTEL MITRAYA PRINTER TEST *", footer_text=f"Width: {paper_width}mm ({cols} cols) | {printer_name}")
        return {
            "text": text_slip,
            "escpos_bytes": escpos_bytes,
            "paper_width": paper_width,
            "cols": cols
        }
