"""
FormulaBase Nexus - Sample PDF Invoice Template Generator
Generates professional vector PDF templates for SARA and LMN brands
using ReportLab. These are the templates that the SmartPDFInvoiceEngine
will overlay real invoice data onto.
"""
import os
import sys

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pts


def draw_rounded_rect(c, x, y, w, h, radius=8, fill_color=None, stroke_color=None, stroke_width=1):
    """Draw a rounded rectangle."""
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    p = c.beginPath()
    p.roundRect(x, y, w, h, radius)
    if fill_color and stroke_color:
        c.drawPath(p, fill=1, stroke=1)
    elif fill_color:
        c.drawPath(p, fill=1, stroke=0)
    elif stroke_color:
        c.drawPath(p, fill=0, stroke=1)


def draw_gradient_header(c, x, y, w, h, color_start, color_end, steps=30):
    """Simulate gradient with multiple rectangles."""
    r1, g1, b1 = color_start
    r2, g2, b2 = color_end
    step_h = h / steps
    for i in range(steps):
        t = i / steps
        r = r1 + (r2 - r1) * t
        g = g1 + (g2 - g1) * t
        b = b1 + (b2 - b1) * t
        c.setFillColorRGB(r, g, b)
        c.rect(x, y + (steps - 1 - i) * step_h, w, step_h + 0.5, fill=1, stroke=0)


def generate_sara_template(output_path: str):
    """
    Generate SARA Natural Soap Invoice Template
    Theme: White + Lush Emerald Green
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("SARA Natural Soap - Invoice Template")

    # Colors
    emerald_dark = HexColor("#059669")
    emerald_mid = HexColor("#10B981")
    emerald_light = HexColor("#34D399")
    emerald_pale = HexColor("#ECFDF5")
    emerald_border = HexColor("#A7F3D0")
    emerald_deep = HexColor("#064E3B")
    dark_text = HexColor("#0F172A")
    mid_text = HexColor("#475569")
    light_border = HexColor("#E2E8F0")
    white_color = HexColor("#FFFFFF")

    # ── GRADIENT HEADER BAND ─────────────────────────────────────
    # Green gradient header (top 130pts)
    header_h = 130
    draw_gradient_header(
        c, 0, PAGE_H - header_h, PAGE_W, header_h,
        (0x05/255, 0x96/255, 0x69/255),  # #059669
        (0x34/255, 0xD3/255, 0x99/255),  # #34D399
    )

    # Decorative circle in header (top right)
    c.setFillColor(HexColor("#FFFFFF20"))
    c.circle(PAGE_W - 40, PAGE_H - 30, 80, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF15"))
    c.circle(PAGE_W - 80, PAGE_H - 70, 50, fill=1, stroke=0)

    # Brand Name
    c.setFillColor(white_color)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(28, PAGE_H - 45, "SARA")
    c.setFont("Helvetica", 12)
    c.drawString(28, PAGE_H - 62, "NATURAL SOAP")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#D1FAE5"))
    c.drawString(28, PAGE_H - 76, "Pure. Natural. Radiant.")

    # Company info in header
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#A7F3D0"))
    c.drawRightString(PAGE_W - 28, PAGE_H - 42, "Formula Base OEM Services Myanmar")
    c.drawRightString(PAGE_W - 28, PAGE_H - 54, "No. 42, Industrial Zone, Hlaing Thar Yar, Yangon")
    c.drawRightString(PAGE_W - 28, PAGE_H - 66, "Tel: 09-111-222-333  |  Email: sara@formulabase.mm")

    # INVOICE label
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(white_color)
    c.drawRightString(PAGE_W - 28, PAGE_H - 95, "INVOICE")

    # Invoice meta box (right side of header)
    meta_x = PAGE_W - 180
    meta_y = PAGE_H - 125
    meta_w = 155
    meta_h = 26

    # Invoice No field
    c.setFillColor(HexColor("#064E3B"))
    draw_rounded_rect(c, meta_x, meta_y, meta_w, meta_h, radius=4, fill_color=HexColor("#064E3B"))
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#6EE7B7"))
    c.drawString(meta_x + 8, meta_y + 16, "INVOICE NO")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(white_color)
    c.drawString(meta_x + 8, meta_y + 5, "<<INVOICE_NO>>")

    # ── INVOICE INFO SECTION ──────────────────────────────────────
    info_y = PAGE_H - 155

    # Left: Customer info block
    c.setFillColor(emerald_pale)
    draw_rounded_rect(c, 22, info_y - 55, 250, 68, radius=6, fill_color=emerald_pale, stroke_color=emerald_border, stroke_width=0.5)

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(emerald_mid)
    c.drawString(32, info_y - 10, "BILL TO")

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(32, info_y - 22, "Customer:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark_text)
    c.drawString(90, info_y - 22, "<<CUST_NAME>>")

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(32, info_y - 35, "Phone:")
    c.drawString(90, info_y - 35, "<<CUST_PHONE>>")

    c.drawString(32, info_y - 48, "Address:")
    c.drawString(90, info_y - 48, "<<CUST_ADDRESS>>")

    # Right: Date and Payment info
    c.setFillColor(emerald_pale)
    draw_rounded_rect(c, 288, info_y - 55, 282, 68, radius=6, fill_color=emerald_pale, stroke_color=emerald_border, stroke_width=0.5)

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(298, info_y - 10, "Invoice Date:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark_text)
    c.drawString(390, info_y - 10, "<<INVOICE_DATE>>")

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(298, info_y - 25, "Payment Method:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark_text)
    c.drawString(390, info_y - 25, "<<PAYMENT_METHOD>>")

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(298, info_y - 40, "Remarks:")
    c.drawString(390, info_y - 40, "<<REMARKS>>")

    # ── ITEMS TABLE ───────────────────────────────────────────────
    table_top = info_y - 70
    table_x = 22

    # Table header
    draw_rounded_rect(c, table_x, table_top - 20, PAGE_W - 44, 22,
                      radius=4, fill_color=emerald_dark)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(white_color)
    c.drawCentredString(table_x + 20, table_top - 13, "#")
    c.drawString(table_x + 50, table_top - 13, "PRODUCT / DESCRIPTION")
    c.drawCentredString(table_x + 295, table_top - 13, "QTY")
    c.drawCentredString(table_x + 340, table_top - 13, "FOC")
    c.drawRightString(table_x + 415, table_top - 13, "UNIT PRICE")
    c.drawRightString(PAGE_W - 44 + table_x, table_top - 13, "AMOUNT")

    # Table rows (14 rows with alternating bg)
    row_h = 22
    row_y = table_top - 22
    for i in range(14):
        if i % 2 == 0:
            c.setFillColor(white_color)
        else:
            c.setFillColor(emerald_pale)
        c.rect(table_x, row_y - row_h, PAGE_W - 44, row_h, fill=1, stroke=0)

        # Row separator
        c.setStrokeColor(emerald_border)
        c.setLineWidth(0.3)
        c.line(table_x, row_y - row_h, PAGE_W - 22, row_y - row_h)

        # Column separators (subtle)
        c.setStrokeColor(HexColor("#E5E7EB"))
        c.setLineWidth(0.2)
        for sep_x in [table_x + 275, table_x + 315, table_x + 390]:
            c.line(sep_x, row_y, sep_x, row_y - row_h)

        row_y -= row_h

    # Table border
    c.setStrokeColor(emerald_border)
    c.setLineWidth(0.5)
    c.rect(table_x, row_y, PAGE_W - 44, table_top - row_y - row_h + 22, stroke=1, fill=0)

    # ── TOTALS SECTION ────────────────────────────────────────────
    totals_y = row_y - 8
    totals_x = PAGE_W - 210

    c.setFillColor(emerald_pale)
    draw_rounded_rect(c, totals_x - 10, totals_y - 115, 195, 118,
                      radius=6, fill_color=emerald_pale, stroke_color=emerald_border, stroke_width=0.5)

    def draw_total_row(label, tag, y, bold=False, accent=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        color = emerald_deep if accent else mid_text
        c.setFont("Helvetica", 8)
        c.setFillColor(color)
        c.drawString(totals_x, y, label)
        c.setFont(font, 9 if accent else 8)
        c.setFillColor(dark_text if not accent else emerald_deep)
        c.drawRightString(PAGE_W - 30, y, tag)
        if not accent:
            c.setStrokeColor(light_border)
            c.setLineWidth(0.3)
            c.line(totals_x, y - 4, PAGE_W - 28, y - 4)

    draw_total_row("Subtotal",     "<<SUB_TOTAL>>",    totals_y - 15)
    draw_total_row("Discount",     "<<DISCOUNT_AMT>>", totals_y - 30)
    draw_total_row("Delivery Fee", "<<DELIVERY_FEE>>", totals_y - 45)
    draw_total_row("Tax (CT 5%)",  "<<TAX_AMOUNT>>",   totals_y - 60)

    # Grand Total highlight
    c.setFillColor(emerald_dark)
    draw_rounded_rect(c, totals_x - 10, totals_y - 90, 195, 26,
                      radius=4, fill_color=emerald_dark)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(white_color)
    c.drawString(totals_x, totals_y - 80, "GRAND TOTAL")
    c.drawRightString(PAGE_W - 30, totals_y - 80, "<<GRAND_TOTAL>>")

    draw_total_row("Amount Paid",  "<<PAID_AMOUNT>>",  totals_y - 100, bold=True)
    draw_total_row("Balance Due",  "<<BALANCE_DUE>>",  totals_y - 112, bold=True, accent=True)

    # ── FOOTER ────────────────────────────────────────────────────
    footer_y = 40
    c.setFillColor(emerald_pale)
    c.rect(0, 0, PAGE_W, footer_y + 10, fill=1, stroke=0)
    c.setStrokeColor(emerald_border)
    c.setLineWidth(0.5)
    c.line(0, footer_y + 10, PAGE_W, footer_y + 10)

    c.setFont("Helvetica", 7.5)
    c.setFillColor(emerald_mid)
    c.drawCentredString(PAGE_W / 2, footer_y - 5, "Thank you for choosing SARA Natural Soap! ✦ Genuine Products. Natural Ingredients. Your Skin Deserves the Best.")
    c.setFillColor(mid_text)
    c.setFont("Helvetica", 7)
    c.drawCentredString(PAGE_W / 2, footer_y - 17, "Formula Base OEM Services Myanmar  |  www.formulabase.mm  |  09-111-222-333")

    c.save()
    print(f"✅ SARA Invoice Template generated: {output_path}")
    return output_path


def generate_lmn_template(output_path: str):
    """
    Generate LMN Vitamin C Soap Invoice Template
    Theme: White + Radiant Citrus Orange/Amber
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("LMN Vitamin C Soap - Invoice Template")

    # Colors
    orange_dark = HexColor("#EA580C")
    orange_mid = HexColor("#F97316")
    amber_light = HexColor("#FBBF24")
    orange_pale = HexColor("#FFF7ED")
    orange_border = HexColor("#FED7AA")
    orange_deep = HexColor("#7C2D12")
    dark_text = HexColor("#0F172A")
    mid_text = HexColor("#78350F")
    light_border = HexColor("#FEE2E2")
    white_color = HexColor("#FFFFFF")

    # ── GRADIENT HEADER (diagonal stripe pattern feel) ────────────
    header_h = 135
    draw_gradient_header(
        c, 0, PAGE_H - header_h, PAGE_W, header_h,
        (0xEA/255, 0x58/255, 0x0C/255),  # #EA580C
        (0xFB/255, 0xBF/255, 0x24/255),  # #FBBF24
    )

    # Decorative circles
    c.setFillColor(HexColor("#FFFFFF18"))
    c.circle(PAGE_W - 50, PAGE_H - 40, 90, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF12"))
    c.circle(60, PAGE_H - 10, 60, fill=1, stroke=0)

    # Brand Name
    c.setFillColor(white_color)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(28, PAGE_H - 48, "LMN")
    c.setFont("Helvetica", 11)
    c.drawString(28, PAGE_H - 63, "VITAMIN C SOAP")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#FEF3C7"))
    c.drawString(28, PAGE_H - 77, "Bright. Fresh. Glowing.")

    # Company info
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#FDE68A"))
    c.drawRightString(PAGE_W - 28, PAGE_H - 44, "Formula Base OEM Services Myanmar")
    c.drawRightString(PAGE_W - 28, PAGE_H - 56, "No. 42, Industrial Zone, Hlaing Thar Yar, Yangon")
    c.drawRightString(PAGE_W - 28, PAGE_H - 68, "Tel: 09-444-555-666  |  Email: lmn@formulabase.mm")

    # INVOICE label
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(white_color)
    c.drawRightString(PAGE_W - 28, PAGE_H - 100, "INVOICE")

    # Invoice No box
    meta_x = PAGE_W - 185
    meta_y = PAGE_H - 128
    c.setFillColor(HexColor("#7C2D12"))
    draw_rounded_rect(c, meta_x, meta_y, 160, 26, radius=4, fill_color=HexColor("#7C2D12"))
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#FCD34D"))
    c.drawString(meta_x + 8, meta_y + 17, "INVOICE NO")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(white_color)
    c.drawString(meta_x + 8, meta_y + 5, "<<INVOICE_NO>>")

    # ── CUSTOMER & DATE INFO ──────────────────────────────────────
    info_y = PAGE_H - 158

    # Customer block
    c.setFillColor(orange_pale)
    draw_rounded_rect(c, 22, info_y - 58, 252, 70, radius=6, fill_color=orange_pale, stroke_color=orange_border, stroke_width=0.5)

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(orange_mid)
    c.drawString(32, info_y - 10, "BILL TO")

    def lmn_info_row(label, tag, y):
        c.setFont("Helvetica", 8)
        c.setFillColor(mid_text)
        c.drawString(32, y, label)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(dark_text)
        c.drawString(90, y, tag)

    lmn_info_row("Customer:", "<<CUST_NAME>>",    info_y - 23)
    lmn_info_row("Phone:",    "<<CUST_PHONE>>",   info_y - 37)
    lmn_info_row("Address:",  "<<CUST_ADDRESS>>", info_y - 51)

    # Right block
    c.setFillColor(orange_pale)
    draw_rounded_rect(c, 288, info_y - 58, 282, 70, radius=6, fill_color=orange_pale, stroke_color=orange_border, stroke_width=0.5)
    lmn_info_row2_x = 298
    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(lmn_info_row2_x, info_y - 12, "Invoice Date:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark_text)
    c.drawString(lmn_info_row2_x + 90, info_y - 12, "<<INVOICE_DATE>>")

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(lmn_info_row2_x, info_y - 27, "Payment:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark_text)
    c.drawString(lmn_info_row2_x + 90, info_y - 27, "<<PAYMENT_METHOD>>")

    c.setFont("Helvetica", 8)
    c.setFillColor(mid_text)
    c.drawString(lmn_info_row2_x, info_y - 42, "Remarks:")
    c.drawString(lmn_info_row2_x + 90, info_y - 42, "<<REMARKS>>")

    # ── ITEMS TABLE ───────────────────────────────────────────────
    table_top = info_y - 73
    table_x = 22

    # Header
    draw_rounded_rect(c, table_x, table_top - 22, PAGE_W - 44, 24, radius=4, fill_color=orange_dark)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(white_color)
    c.drawCentredString(table_x + 20, table_top - 14, "#")
    c.drawString(table_x + 48, table_top - 14, "PRODUCT / DESCRIPTION")
    c.drawCentredString(table_x + 293, table_top - 14, "QTY")
    c.drawCentredString(table_x + 338, table_top - 14, "FOC")
    c.drawRightString(table_x + 413, table_top - 14, "UNIT PRICE")
    c.drawRightString(PAGE_W - 44 + table_x, table_top - 14, "AMOUNT")

    # Table rows
    row_h = 22
    row_y = table_top - 22
    for i in range(14):
        c.setFillColor(white_color if i % 2 == 0 else orange_pale)
        c.rect(table_x, row_y - row_h, PAGE_W - 44, row_h, fill=1, stroke=0)
        c.setStrokeColor(orange_border)
        c.setLineWidth(0.3)
        c.line(table_x, row_y - row_h, PAGE_W - 22, row_y - row_h)
        row_y -= row_h

    c.setStrokeColor(orange_border)
    c.setLineWidth(0.5)
    c.rect(table_x, row_y, PAGE_W - 44, table_top - row_y - row_h + 24, stroke=1, fill=0)

    # ── TOTALS ────────────────────────────────────────────────────
    totals_y = row_y - 8
    totals_x = PAGE_W - 210

    c.setFillColor(orange_pale)
    draw_rounded_rect(c, totals_x - 10, totals_y - 118, 197, 120,
                      radius=6, fill_color=orange_pale, stroke_color=orange_border, stroke_width=0.5)

    def lmn_total_row(label, tag, y, bold=False, accent=False):
        c.setFont("Helvetica", 8)
        c.setFillColor(mid_text)
        c.drawString(totals_x, y, label)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 9 if accent else 8)
        c.setFillColor(orange_deep if accent else dark_text)
        c.drawRightString(PAGE_W - 30, y, tag)
        if not accent:
            c.setStrokeColor(light_border)
            c.setLineWidth(0.3)
            c.line(totals_x, y - 4, PAGE_W - 28, y - 4)

    lmn_total_row("Subtotal",     "<<SUB_TOTAL>>",    totals_y - 15)
    lmn_total_row("Discount",     "<<DISCOUNT_AMT>>", totals_y - 30)
    lmn_total_row("Delivery Fee", "<<DELIVERY_FEE>>", totals_y - 45)
    lmn_total_row("Tax (CT 5%)",  "<<TAX_AMOUNT>>",   totals_y - 60)

    # Grand Total
    c.setFillColor(orange_dark)
    draw_rounded_rect(c, totals_x - 10, totals_y - 90, 197, 27, radius=4, fill_color=orange_dark)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(white_color)
    c.drawString(totals_x, totals_y - 80, "GRAND TOTAL")
    c.drawRightString(PAGE_W - 30, totals_y - 80, "<<GRAND_TOTAL>>")

    lmn_total_row("Amount Paid", "<<PAID_AMOUNT>>", totals_y - 102, bold=True)
    lmn_total_row("Balance Due", "<<BALANCE_DUE>>", totals_y - 115, bold=True, accent=True)

    # ── FOOTER ────────────────────────────────────────────────────
    c.setFillColor(orange_pale)
    c.rect(0, 0, PAGE_W, 50, fill=1, stroke=0)
    c.setStrokeColor(orange_border)
    c.setLineWidth(0.5)
    c.line(0, 50, PAGE_W, 50)

    # Vitamin C icon decoration
    c.setFillColor(orange_mid)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(PAGE_W / 2, 35, "Thank you for choosing LMN Vitamin C Soap!")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(mid_text)
    c.drawCentredString(PAGE_W / 2, 22, "Brightening Naturally · Rich in Vitamin C · Dermatologist Tested")
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#9A3412"))
    c.drawCentredString(PAGE_W / 2, 10, "Formula Base OEM Services Myanmar  |  09-444-555-666  |  www.formulabase.mm")

    c.save()
    print(f"✅ LMN Invoice Template generated: {output_path}")
    return output_path


if __name__ == "__main__":
    # Create output directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(script_dir, "backend", "modules", "pdf_invoice_engine", "templates")
    os.makedirs(templates_dir, exist_ok=True)

    sara_path = os.path.join(templates_dir, "SARA_Invoice_Template.pdf")
    lmn_path  = os.path.join(templates_dir, "LMN_Invoice_Template.pdf")

    generate_sara_template(sara_path)
    generate_lmn_template(lmn_path)

    print(f"\n🎨 Both PDF templates generated!")
    print(f"   SARA: {sara_path}")
    print(f"   LMN:  {lmn_path}")
