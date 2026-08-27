"""
Hotel Mitraya - Bill Generator (Word / DOCX to PDF)
====================================================
Works by:
  1. Copying the original template.docx
  2. Finding the item-row in the table (the row with {itemno})
  3. Duplicating that row once per item, filling values
  4. Replacing every remaining {placeholder} in the document
  5. Generating DOCX and converting to PDF
  6. Saving the PDF in the dedicated `/bills` folder with format:
     <Customer_Name>_<Bill_No>.pdf

Usage:
  - Web Server: imported by app.py
  - CLI: python generate_bill_docx.py --cli
  - GUI: python generate_bill_docx.py
"""

import copy
import os
import shutil
import zipfile
import re
import sys
import subprocess
from datetime import datetime
from lxml import etree

try:
    from num2words import num2words as _n2w
    def amount_to_words(amount: float) -> str:
        rupees = int(amount)
        paise  = round((amount - rupees) * 100)
        text   = _n2w(rupees, lang="en_IN").title()
        if paise:
            text += f" And {_n2w(paise, lang='en_IN').title()} Paise"
        return f"Rupees {text} Only"
except ImportError:
    def amount_to_words(amount: float) -> str:
        return f"Rupees {amount:.2f} Only"


# ─── XML helpers ─────────────────────────────────────────────────────────────

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def w(tag):
    return f"{{{W_NS}}}{tag}"

def get_full_text(element) -> str:
    """Return concatenated text of all <w:t> descendants."""
    return "".join(
        t.text or ""
        for t in element.iter(w("t"))
    )

def set_run_text(run_el, text: str):
    """Replace the text in a <w:r> element (first <w:t>, clear others)."""
    t_els = list(run_el.iter(w("t")))
    if t_els:
        t_els[0].text = text
        t_els[0].set(
            "{http://www.w3.org/XML/1998/namespace}space", "preserve"
        )
        for extra in t_els[1:]:
            extra.getparent().remove(extra)
    else:
        t_el = etree.SubElement(run_el, w("t"))
        t_el.text = text
        t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

def replace_in_element(element, replacements: dict):
    """
    Replace {placeholder} occurrences in all <w:t> inside `element`.
    Handles runs where the placeholder text is split across adjacent <w:t>
    by working on the paragraph level.
    """
    for para in element.iter(w("p")):
        full = get_full_text(para)
        changed = False
        new_text = full
        for ph, val in replacements.items():
            if ph in new_text:
                new_text = new_text.replace(ph, str(val))
                changed = True
        if not changed:
            continue
        runs = list(para.iter(w("r")))
        if not runs:
            continue
        set_run_text(runs[0], new_text)
        for r in runs[1:]:
            for t in r.iter(w("t")):
                t.text = ""


# ─── Filename Sanitization Helper ─────────────────────────────────────────────

def sanitize_filename(name: str, fallback: str = "bill") -> str:
    """Clean string to be safely used as filename on Windows/Linux/macOS."""
    if not name:
        return fallback
    clean = re.sub(r'[\\/*?:"<>|]', "", str(name))
    clean = re.sub(r'\s+', "_", clean.strip())
    clean = re.sub(r'_+', "_", clean)
    return clean.strip("._") or fallback


# ─── Core Generator ──────────────────────────────────────────────────────────

def generate_bill_docx(data: dict, output_path: str, template_path: str = None) -> str:
    """
    Fill the Hotel Mitraya Word template with `data` and save to `output_path`.
    """
    if template_path is None:
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "template.docx"
        )
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Work on a temp copy so we never touch the master template
    tmp_docx = output_path + ".tmp_work.docx"
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    shutil.copy2(template_path, tmp_docx)

    # ── Unzip -> manipulate XML -> rezip ────────────────────────────────────
    work_dir = output_path + "_workdir"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    with zipfile.ZipFile(tmp_docx, "r") as z:
        z.extractall(work_dir)

    doc_xml_path = os.path.join(work_dir, "word", "document.xml")
    tree = etree.parse(doc_xml_path)
    root = tree.getroot()

    # ── Compute values ─────────────────────────────────────────────────────
    items           = data.get("items", [])
    discount        = float(data.get("discount", 0) or 0)
    grand_total     = sum(float(i["qty"]) * float(i["rate"]) for i in items)
    after_discount  = grand_total - discount
    received_raw    = data.get("received_amount", "")
    received_amount = float(received_raw) if (received_raw is not None and str(received_raw).strip() != "") else after_discount

    def fmt_num(n):
        """Show as integer if whole number, else 2 dp."""
        return str(int(n)) if n == int(n) else f"{n:.2f}"

    # ── Find the items table and item-template row ─────────────────────────
    tables = root.findall(f".//{w('tbl')}")
    item_table = None
    template_row = None

    for tbl in tables:
        rows = tbl.findall(w("tr"))
        for row in rows:
            if "{itemno}" in get_full_text(row):
                item_table   = tbl
                template_row = row
                break
        if item_table is not None:
            break

    if item_table is None or template_row is None:
        raise RuntimeError("Could not find item-template row ({itemno}) in template.")

    # ── Duplicate row once per item, fill values ───────────────────────────
    for i, item in enumerate(items):
        qty   = float(item["qty"])
        rate  = float(item["rate"])
        total = qty * rate

        new_row = copy.deepcopy(template_row)
        replace_in_element(new_row, {
            "{itemno}":    str(i + 1),
            "{item name}": item.get("name", ""),
            "{qty}":       fmt_num(qty),
            "{rate}":      fmt_num(rate),
            "{total}":     fmt_num(total),
        })
        template_row.addprevious(new_row)

    # Remove the blank template row
    item_table.remove(template_row)

    # ── Fill {grandtotal} in the Total row ────────────────────────────────
    replace_in_element(item_table, {"{grandtotal}": fmt_num(grand_total)})

    # ── Fill all other placeholders in the whole document ─────────────────
    global_replacements = {
        "{Customer Name}":        data.get("customer_name", ""),
        "{ bill no}":             str(data.get("bill_no", "")),
        "{date and time}":        data.get("created_on", ""),
        "{date}":                 data.get("bill_date", ""),
        "{amount in words}":      amount_to_words(after_discount),
        "{discount}":             fmt_num(discount),
        "{after discount total}": fmt_num(after_discount),
        "{received amt}":         fmt_num(received_amount),
    }
    replace_in_element(root, global_replacements)

    # ── Serialise back ────────────────────────────────────────────────────
    tree.write(doc_xml_path, xml_declaration=True,
               encoding="UTF-8", standalone=True)

    # Repack as docx (zip)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for fpath in sorted(
            os.path.join(dp, f)
            for dp, _, files in os.walk(work_dir)
            for f in files
        ):
            arcname = os.path.relpath(fpath, work_dir)
            zout.write(fpath, arcname)

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(tmp_docx):
        os.remove(tmp_docx)
        
    print(f"[OK] Bill DOCX saved -> {output_path}")
    return output_path


# ─── PDF Conversion Engine ───────────────────────────────────────────────────

def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> str:
    """
    Convert DOCX to PDF using LibreOffice (Linux/Docker/Cloud) or MS Word COM (Windows).
    """
    docx_path = os.path.abspath(docx_path)
    pdf_path = os.path.abspath(pdf_path)
    pdf_dir = os.path.dirname(pdf_path)
    os.makedirs(pdf_dir, exist_ok=True)

    # 1. Check for LibreOffice / soffice CLI (Standard on Linux servers / Docker containers)
    soffice_cmd = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice_cmd:
        try:
            cmd = [
                soffice_cmd,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", pdf_dir,
                docx_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            # LibreOffice outputs with same basename + .pdf in outdir
            expected_lo_pdf = os.path.join(pdf_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
            if os.path.exists(expected_lo_pdf):
                if expected_lo_pdf != pdf_path:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    shutil.move(expected_lo_pdf, pdf_path)
                return pdf_path
        except Exception as e:
            print(f"[WARN] LibreOffice conversion error: {e}")

    # 2. Windows MS Word Automation via COM
    if sys.platform == "win32":
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            try:
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = False
                doc = word.Documents.Open(docx_path)
                # 17 represents wdFormatPDF
                doc.SaveAs(pdf_path, FileFormat=17)
                doc.Close(SaveChanges=0)
                word.Quit()
                if os.path.exists(pdf_path):
                    return pdf_path
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            print(f"[WARN] Windows Word COM conversion failed: {e}")

    # 3. docx2pdf library fallback
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        print(f"[WARN] docx2pdf library fallback failed: {e}")

    if os.path.exists(pdf_path):
        return pdf_path

    raise RuntimeError("PDF Conversion failed. Please ensure MS Word (Windows) or LibreOffice is installed.")

# ─── Pure Python PDF Generator (Serverless / Cloud Native) ────────────────────

def generate_bill_pdf_reportlab(data: dict, pdf_path: str) -> str:
    """
    Generate pixel-perfect Hotel Mitraya invoice PDF using ReportLab.
    Works natively on Linux/AWS Lambda/Vercel without needing LibreOffice or MS Word.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=25,
        bottomMargin=25
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'HotelTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#991b1b'),
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'HotelSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155'),
        alignment=TA_CENTER
    )
    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )
    normal_val = ParagraphStyle(
        'NormalVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )
    table_header = ParagraphStyle(
        'THeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    cell_left = ParagraphStyle(
        'CellLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_LEFT
    )
    cell_center = ParagraphStyle(
        'CellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_CENTER
    )
    cell_right = ParagraphStyle(
        'CellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_RIGHT
    )
    
    story = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, 'static', 'logo.png')
    logo_img = None
    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=65, height=65)
        except Exception:
            logo_img = None
            
    header_text = [
        Paragraph('<b>HOTEL MITRAYA</b>', title_style),
        Paragraph('Dharmaraj chowk Nr. Honda Showroom, Akurdi, Pune, 411035', subtitle_style),
        Paragraph('<b>Contact:</b> +91 9158691003 &nbsp;|&nbsp; <b>FSSAI No.:</b> 21525037001433', subtitle_style),
        Paragraph('<b>Bank Details:</b> A/c Holder - HOTEL MITRAYA &nbsp;|&nbsp; A/c No - 169402000001218 &nbsp;|&nbsp; IFSC - IOBA0001694', subtitle_style),
    ]
    
    if logo_img:
        header_table = Table([[logo_img, header_text]], colWidths=[75, 460])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
        ]))
        story.append(header_table)
    else:
        for p in header_text:
            story.append(p)
            
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#991b1b'), spaceAfter=10))
    
    # Invoice Meta Bar
    customer_name = str(data.get('customer_name', 'Valued Customer')).strip()
    bill_no = str(data.get('bill_no', '1001')).strip()
    created_on = str(data.get('created_on', '')).strip()
    bill_date = str(data.get('bill_date', '')).strip()
    txn_mode = str(data.get('txn_mode', 'CASH')).strip().upper() or "CASH"
    
    meta_data = [
        [
            Paragraph('<b>Billed To:</b>', bold_label),
            Paragraph(f'<b>{customer_name}</b>', bold_label),
            Paragraph('<b>Invoice No:</b>', bold_label),
            Paragraph(f'#{bill_no}', normal_val)
        ],
        [
            Paragraph('<b>Payment Mode:</b>', bold_label),
            Paragraph(txn_mode, normal_val),
            Paragraph('<b>Bill Date:</b>', bold_label),
            Paragraph(bill_date, normal_val)
        ],
        [
            Paragraph('', bold_label),
            Paragraph('', normal_val),
            Paragraph('<b>Created On:</b>', bold_label),
            Paragraph(created_on, normal_val)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[90, 240, 85, 120])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))
    
    # Items Table
    items = data.get('items', [])
    discount = float(data.get('discount', 0) or 0)
    grand_total = sum(float(i['qty']) * float(i['rate']) for i in items)
    after_discount = grand_total - discount
    received_raw = data.get('received_amount', '')
    received_amount = float(received_raw) if (received_raw is not None and str(received_raw).strip() != '') else after_discount

    def fmt_num(n):
        return f'{n:,.2f}'

    table_rows = [
        [
            Paragraph('#', table_header),
            Paragraph('ITEM DESCRIPTION', table_header),
            Paragraph('QTY', table_header),
            Paragraph('RATE (₹)', table_header),
            Paragraph('TOTAL (₹)', table_header)
        ]
    ]
    
    for idx, itm in enumerate(items):
        iqty = float(itm.get('qty', 1))
        irate = float(itm.get('rate', 0))
        itot = iqty * irate
        table_rows.append([
            Paragraph(str(idx + 1), cell_center),
            Paragraph(str(itm.get('name', '')), cell_left),
            Paragraph(str(int(iqty) if iqty == int(iqty) else f'{iqty:.2f}'), cell_center),
            Paragraph(fmt_num(irate), cell_right),
            Paragraph(fmt_num(itot), cell_right)
        ])
        
    # Subtotal row
    table_rows.append([
        Paragraph('', cell_center),
        Paragraph('<b>Subtotal</b>', cell_left),
        Paragraph('', cell_center),
        Paragraph('', cell_right),
        Paragraph(f'<b>₹{fmt_num(grand_total)}</b>', cell_right)
    ])
    
    items_table = Table(table_rows, colWidths=[30, 275, 55, 85, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))
    
    # Bottom Summary & Amount in words
    amt_words = amount_to_words(after_discount)
    words_para = [
        Paragraph('<b>Amount in Words:</b>', bold_label),
        Spacer(1, 4),
        Paragraph(f'<i>{amt_words}</i>', normal_val),
        Spacer(1, 10),
        Paragraph('<b>Terms & Conditions:</b>', bold_label),
        Paragraph('1. Subject to Pune Jurisdiction.<br/>2. Payment is due as per agreed terms.', subtitle_style)
    ]
    
    summary_rows = [
        [Paragraph('Sub Total:', bold_label), Paragraph(f'₹{fmt_num(grand_total)}', cell_right)],
        [Paragraph('Discount:', bold_label), Paragraph(f'₹{fmt_num(discount)}', cell_right)],
        [Paragraph('<b>TOTAL AMOUNT:</b>', bold_label), Paragraph(f'<b>₹{fmt_num(after_discount)}</b>', cell_right)],
        [Paragraph('Received Amount:', bold_label), Paragraph(f'₹{fmt_num(received_amount)}', cell_right)],
    ]
    summary_table = Table(summary_rows, colWidths=[110, 90])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#fee2e2')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    
    bottom_table = Table([[words_para, summary_table]], colWidths=[325, 210])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(bottom_table)
    story.append(Spacer(1, 20))
    
    # Signatures
    sig_data = [
        [
            Paragraph('Customer Signature', subtitle_style),
            Paragraph('For <b>HOTEL MITRAYA</b><br/><br/><br/>Authorized Signatory', subtitle_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 265])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM')
    ]))
    story.append(sig_table)
    
    doc.build(story)
    return pdf_path


# ─── High-Level Bill PDF Generator ──────────────────────────────────────────

def generate_bill_pdf(data: dict, template_path: str = None, bills_dir: str = None) -> dict:
    """
    Generate high-quality Hotel Mitraya PDF bill and store in dedicated `/bills` folder
    with naming convention: <Customer_Name>_<Bill_No>.pdf.

    Uses ReportLab for instant, 100% reliable serverless PDF creation on Vercel/Cloud.
    Returns dict with file metadata and absolute/relative paths.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if bills_dir is None:
        if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            import tempfile
            bills_dir = os.path.join(tempfile.gettempdir(), "bills")
        else:
            bills_dir = os.path.join(base_dir, "bills")
    os.makedirs(bills_dir, exist_ok=True)

    customer_name = str(data.get("customer_name", "Customer")).strip()
    bill_no = str(data.get("bill_no", "001")).strip()

    safe_cust = sanitize_filename(customer_name, "Customer")
    safe_bill = sanitize_filename(bill_no, "001")

    base_name = f"{safe_cust}_{safe_bill}"
    pdf_filename = f"{base_name}.pdf"
    pdf_path = os.path.join(bills_dir, pdf_filename)

    # Primary: Fast, clean, serverless pure-Python ReportLab PDF generation
    try:
        generate_bill_pdf_reportlab(data, pdf_path)
    except Exception as e:
        print(f"[WARN] ReportLab generation error: {e}. Attempting docx fallback...")
        temp_docx_path = os.path.join(bills_dir, f".temp_{base_name}.docx")
        generate_bill_docx(data, temp_docx_path, template_path)
        convert_docx_to_pdf(temp_docx_path, pdf_path)
        if os.path.exists(temp_docx_path):
            try:
                os.remove(temp_docx_path)
            except Exception:
                pass

    print(f"[OK] Final Bill PDF saved -> {pdf_path}")
    return {
        "filename": pdf_filename,
        "filepath": pdf_path,
        "relpath": os.path.relpath(pdf_path, base_dir),
        "size_bytes": os.path.getsize(pdf_path),
        "customer_name": customer_name,
        "bill_no": bill_no
    }


# ─── Legacy Desktop GUI (Tkinter) ────────────────────────────────────────────

def run_gui(template_path: str):
    import tkinter as tk
    from tkinter import ttk, messagebox

    class BillingApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Hotel Mitraya — Bill Generator (PDF)")
            self.geometry("860x700")
            self.configure(bg="#1A3A5C")
            self.resizable(True, True)
            self.item_rows = []
            self._build_ui()

        def _build_ui(self):
            bar = tk.Frame(self, bg="#B22222", pady=10)
            bar.pack(fill="x")
            tk.Label(bar, text="🍽 Hotel Mitraya",
                     font=("Helvetica", 18, "bold"),
                     bg="#B22222", fg="white").pack()
            tk.Label(bar, text="Bill Generation System — PDF Output",
                     font=("Helvetica", 9), bg="#B22222", fg="#FFC0C0").pack()

            outer = tk.Frame(self, bg="#1A3A5C")
            outer.pack(fill="both", expand=True, padx=12, pady=10)

            canvas = tk.Canvas(outer, bg="#1A3A5C", highlightthickness=0)
            sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            self.sf = tk.Frame(canvas, bg="#1A3A5C")
            self.sf.bind("<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=self.sf, anchor="nw")
            canvas.configure(yscrollcommand=sb.set)
            canvas.bind_all("<MouseWheel>",
                lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
            sb.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            self._build_form(self.sf)

        def _card(self, parent, title):
            f = tk.LabelFrame(parent, text=f"  {title}  ",
                              font=("Helvetica", 10, "bold"),
                              bg="#E8F4FD", fg="#1A3A5C",
                              relief="groove", bd=2, padx=10, pady=8)
            f.pack(fill="x", padx=4, pady=6)
            return f

        def _field(self, parent, label, row, col=0, width=30, default=""):
            tk.Label(parent, text=label, bg="#E8F4FD", fg="#1A3A5C",
                     font=("Helvetica", 9, "bold"), anchor="w").grid(
                row=row, column=col*2, padx=(4,2), pady=4, sticky="w")
            var = tk.StringVar(value=str(default))
            ttk.Entry(parent, textvariable=var, width=width).grid(
                row=row, column=col*2+1, padx=(0,12), pady=4, sticky="ew")
            return var

        def _build_form(self, parent):
            now = datetime.now()

            c1 = self._card(parent, "📄 Invoice Details")
            c1.columnconfigure((1,3), weight=1)
            self.v_customer  = self._field(c1, "Customer Name",  0, 0, 30)
            self.v_billno    = self._field(c1, "Bill No",         0, 1, 12, "1230")
            self.v_created   = self._field(c1, "Created On",      1, 0, 28,
                                           now.strftime("%d/%m/%Y %I:%M %p"))
            self.v_billdate  = self._field(c1, "Bill Date",       1, 1, 16,
                                           now.strftime("%d/%m/%Y"))

            self.items_card = self._card(parent, "🍱 Items")
            self._item_header()
            self._add_item()

            btn_row = tk.Frame(self.items_card, bg="#E8F4FD")
            btn_row.pack(fill="x", pady=(4,0))
            tk.Button(btn_row, text="➕ Add Item", command=self._add_item,
                      bg="#007ACC", fg="white",
                      font=("Helvetica", 9, "bold"),
                      relief="flat", padx=10, pady=4).pack(side="left", padx=4)
            tk.Button(btn_row, text="➖ Remove Last", command=self._remove_item,
                      bg="#B22222", fg="white",
                      font=("Helvetica", 9, "bold"),
                      relief="flat", padx=10, pady=4).pack(side="left", padx=4)

            c3 = self._card(parent, "💰 Payment Details")
            c3.columnconfigure((1,3), weight=1)
            self.v_discount  = self._field(c3, "Discount (RS)", 0, 0, 12, "0")
            self.v_txnmode   = self._field(c3, "Txn Mode",      0, 1, 12, "CASH")
            self.v_received  = self._field(c3, "Received Amt",  1, 0, 16, "")
            tk.Label(c3, text="(blank = auto-fills grand total)",
                     bg="#E8F4FD", fg="grey", font=("Helvetica", 8)).grid(
                row=1, column=1, sticky="w", padx=4)

            tk.Button(parent, text="🖨 GENERATE PDF BILL",
                      command=self._generate,
                      bg="#1A3A5C", fg="white",
                      font=("Helvetica", 13, "bold"),
                      relief="flat", padx=20, pady=12).pack(pady=14)

            self.status = tk.StringVar(value="Ready. Output will be saved in /bills folder.")
            tk.Label(parent, textvariable=self.status,
                     bg="#1A3A5C", fg="#90EE90",
                     font=("Helvetica", 9)).pack(pady=(0,8))

        def _item_header(self):
            hdr = tk.Frame(self.items_card, bg="#1A3A5C")
            hdr.pack(fill="x", padx=4, pady=(0,2))
            for txt, w_ in [("# ", 3), ("Item Name", 34), ("Qty", 10), ("Rate ₹", 12)]:
                tk.Label(hdr, text=txt, bg="#1A3A5C", fg="white",
                         font=("Helvetica", 9, "bold"),
                         width=w_, anchor="w").pack(side="left", padx=2)

        def _add_item(self):
            rf = tk.Frame(self.items_card, bg="#E8F4FD")
            rf.pack(fill="x", padx=4, pady=1)
            idx = len(self.item_rows) + 1
            tk.Label(rf, text=f"{idx}.", bg="#E8F4FD", width=3,
                     font=("Helvetica", 9)).pack(side="left", padx=2)
            nv, qv, rv = tk.StringVar(), tk.StringVar(), tk.StringVar()
            ttk.Entry(rf, textvariable=nv, width=34).pack(side="left", padx=2)
            ttk.Entry(rf, textvariable=qv, width=10).pack(side="left", padx=2)
            ttk.Entry(rf, textvariable=rv, width=12).pack(side="left", padx=2)
            self.item_rows.append({"frame": rf, "name": nv, "qty": qv, "rate": rv})

        def _remove_item(self):
            if self.item_rows:
                self.item_rows.pop()["frame"].destroy()

        def _generate(self):
            try:
                items = []
                for row in self.item_rows:
                    name = row["name"].get().strip()
                    qty  = row["qty"].get().strip()
                    rate = row["rate"].get().strip()
                    if not name and not qty and not rate:
                        continue
                    if not name:
                        messagebox.showerror("Validation", "Item name is empty.")
                        return
                    try:
                        q, r = float(qty), float(rate)
                    except ValueError:
                        messagebox.showerror("Validation",
                            f"Invalid Qty/Rate for '{name}'.")
                        return
                    items.append({"name": name, "qty": q, "rate": r})

                if not items:
                    messagebox.showerror("Validation", "Add at least one item.")
                    return

                discount    = float(self.v_discount.get().strip() or 0)
                grand_total = sum(float(i["qty"]) * float(i["rate"]) for i in items)
                after_disc  = grand_total - discount
                recv_raw    = self.v_received.get().strip()
                received    = float(recv_raw) if recv_raw else after_disc

                data = {
                    "customer_name":    self.v_customer.get().strip(),
                    "bill_no":          self.v_billno.get().strip(),
                    "created_on":       self.v_created.get().strip(),
                    "bill_date":        self.v_billdate.get().strip(),
                    "items":            items,
                    "discount":         discount,
                    "txn_mode":         self.v_txnmode.get().strip() or "CASH",
                    "received_amount":  received,
                }

                res = generate_bill_pdf(data, template_path)
                out = res["filepath"]

                self.status.set(f"Saved PDF: {res['filename']}")
                if messagebox.askyesno("Done", f"Bill PDF saved in /bills folder:\n{out}\n\nOpen now?"):
                    try:
                        os.startfile(out)
                    except Exception:
                        pass

            except Exception as exc:
                messagebox.showerror("Error", str(exc))
                self.status.set(f"Error: {exc}")

    BillingApp().mainloop()


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "template.docx"
    )

    if "--cli" in sys.argv:
        data = {
            "customer_name":   "Buona Vita Hospitality Services LLP",
            "bill_no":         "1229",
            "created_on":      "24/02/2026 11:37 AM",
            "bill_date":       "24/02/2026",
            "items": [
                {"name": "Dahi Dhapata & Biryani plate", "qty": 150, "rate": 130},
                {"name": "Mineral Water Bottle", "qty": 50, "rate": 20}
            ],
            "discount":        500,
            "txn_mode":        "CASH",
            "received_amount": 20000,
        }
        res = generate_bill_pdf(data, template_path)
        print(f"[CLI SUCCESS] Generated: {res}")
    else:
        run_gui(template_path)
