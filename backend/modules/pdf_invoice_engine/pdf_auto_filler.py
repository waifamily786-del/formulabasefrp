"""
FormulaBase Nexus - Smart PDF Template Auto-Fill & Vector Overlay Engine
Implements all 3 filling modes:
  1. AI Layout & Label Auto-Detector (pdfplumber)
  2. <<TAG>> Placeholder Auto-Replace
  3. AcroForm Field Auto-Fill (pypdf)
"""
import io
import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# TAG PATTERNS: Supports both <<TAG>> and {{TAG}} formats
# ──────────────────────────────────────────────────────────────────
TAG_PATTERN = re.compile(r"<<([A-Z0-9_]+)>>|\{\{([A-Z0-9_]+)\}\}", re.IGNORECASE)

# Standard field label keywords for auto-detection
LABEL_MAP = {
    "invoice_no": ["invoice no", "inv no", "invoice #", "voucher no", "ဘောင်ချာအမှတ်", "<<invoice_no>>", "{{invoice_no}}"],
    "invoice_date": ["date", "invoice date", "နေ့စွဲ", "<<invoice_date>>", "{{invoice_date}}"],
    "customer_name": ["customer", "customer name", "name", "buyer", "bill to", "ဝယ်သူအမည်", "အမည်", "<<cust_name>>", "{{cust_name}}"],
    "customer_phone": ["phone", "tel", "mobile", "ဖုန်း", "<<cust_phone>>", "{{cust_phone}}"],
    "customer_address": ["address", "ship to", "လိပ်စာ", "<<cust_address>>", "{{cust_address}}"],
    "payment_method": ["payment", "payment method", "ငွေချေစနစ်", "<<payment_method>>", "{{payment_method}}"],
    "subtotal": ["subtotal", "sub total", "sub-total", "amount", "စုစုပေါင်း", "<<sub_total>>", "{{sub_total}}"],
    "discount": ["discount", "disc.", "လျှော့ငွေ", "<<discount_amt>>", "{{discount_amt}}"],
    "delivery_fee": ["delivery", "delivery fee", "shipping", "ပို့ဆောင်ခ", "<<delivery_fee>>", "{{delivery_fee}}"],
    "tax_amount": ["tax", "ct", "commercial tax", "vat", "<<tax_amount>>", "{{tax_amount}}"],
    "grand_total": ["grand total", "net total", "total due", "ကျသင့်ငွေ", "<<grand_total>>", "{{grand_total}}"],
    "paid_amount": ["paid", "paid amount", "amount paid", "ပေးငွေ", "<<paid_amount>>", "{{paid_amount}}"],
    "balance_due": ["balance", "due", "change", "balance due", "ကျန်ငွေ", "<<balance_due>>", "{{balance_due}}"],
    "remarks": ["remarks", "note", "notes", "မှတ်ချက်", "<<remarks>>", "{{remarks}}"],
}

# Default table column layout (standard A4 invoice)
DEFAULT_TABLE_CONFIG = {
    "start_y": 480.0,
    "row_height": 22.0,
    "font_size": 10,
    "max_rows": 12,
    "columns": {
        "no":         {"x": 55.0,  "align": "center"},
        "name":       {"x": 95.0,  "align": "left"},
        "qty":        {"x": 330.0, "align": "center"},
        "foc":        {"x": 380.0, "align": "center"},
        "unit_price": {"x": 450.0, "align": "right"},
        "line_total": {"x": 545.0, "align": "right"},
    },
}


class SmartPDFInvoiceEngine:
    """
    Production-ready Smart PDF Invoice Engine.
    - Takes any user-uploaded PDF invoice design (.pdf)
    - Auto-detects field coordinates via labels, table grids, or <<TAGS>>
    - Overlays POS invoice data directly onto original vector PDF
    - No Adobe InDesign or external design software required
    """

    def __init__(self, fonts_dir: Optional[str] = None):
        self.font_name = "Helvetica"
        self.myanmar_font_registered = False
        self._register_fonts(fonts_dir)

    def _register_fonts(self, fonts_dir: Optional[str]):
        """Register Myanmar Unicode and Inter fonts for ReportLab."""
        if not fonts_dir:
            return

        font_candidates = [
            ("MyanmarUnicode", "Pyidaungsu.ttf"),
            ("MyanmarUnicode", "NotoSansMyanmar-Regular.ttf"),
            ("MyanmarUnicode", "myanmar_unicode.ttf"),
        ]
        for font_name, filename in font_candidates:
            path = os.path.join(fonts_dir, filename)
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, path))
                    self.font_name = font_name
                    self.myanmar_font_registered = True
                    logger.info(f"Myanmar font registered: {path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to register font {path}: {e}")

        # Register Inter as fallback
        inter_path = os.path.join(fonts_dir, "Inter-Regular.ttf") if fonts_dir else None
        if inter_path and os.path.exists(inter_path):
            try:
                pdfmetrics.registerFont(TTFont("Inter", inter_path))
                if not self.myanmar_font_registered:
                    self.font_name = "Inter"
            except Exception as e:
                logger.warning(f"Failed to register Inter font: {e}")

    # ──────────────────────────────────────────────────────────────
    # AUTO-DETECTION METHODS
    # ──────────────────────────────────────────────────────────────

    def auto_detect_template_layout(self, pdf_template_path: str) -> Dict[str, Any]:
        """
        Automatically scans an uploaded PDF design to locate:
        - Header/footer field coordinates (Invoice No, Date, Customer, etc.)
        - Table start Y position and column layout
        - <<TAG>> placeholder positions for exact replacement
        - AcroForm fields if present
        """
        detected_fields = {}
        table_config = dict(DEFAULT_TABLE_CONFIG)

        try:
            with pdfplumber.open(pdf_template_path) as pdf:
                page = pdf.pages[0]
                page_width = float(page.width)
                page_height = float(page.height)
                words = page.extract_words(extra_attrs=["size", "fontname"])

                for w in words:
                    text_raw = w.get("text", "").strip()
                    text_lower = text_raw.lower()
                    if not text_lower:
                        continue

                    # Convert pdfplumber top-origin coords to ReportLab bottom-origin
                    pdf_x_label_end = float(w.get("x1", 0)) + 5.0
                    pdf_y = page_height - float(w.get("bottom", 0)) + 2.0

                    # Check if this word is a <<TAG>> placeholder
                    tag_match = TAG_PATTERN.match(text_raw)
                    if tag_match:
                        tag_name = (tag_match.group(1) or tag_match.group(2)).lower()
                        for field_key, keywords in LABEL_MAP.items():
                            norm_kws = [k.strip("<>{}").lower() for k in keywords if k.startswith(("<<", "{{"))]
                            if tag_name in norm_kws or any(tag_name == k for k in norm_kws):
                                detected_fields[field_key] = {
                                    "x": float(w.get("x0", 0)),
                                    "y": pdf_y,
                                    "font_size": int(float(w.get("size", 10))),
                                    "align": "right" if field_key in [
                                        "subtotal", "discount", "delivery_fee",
                                        "tax_amount", "grand_total", "paid_amount", "balance_due"
                                    ] else "left",
                                    "color": "#0F172A",
                                    "is_tag": True,
                                    "cover_rect": [
                                        float(w.get("x0", 0)) - 2,
                                        page_height - float(w.get("bottom", 0)) - 2,
                                        float(w.get("x1", 0)) - float(w.get("x0", 0)) + 4,
                                        float(w.get("bottom", 0)) - float(w.get("top", 0)) + 4,
                                    ],
                                }
                                break
                        continue

                    # Match against label keywords
                    for field_key, keywords in LABEL_MAP.items():
                        plain_kws = [k for k in keywords if not k.startswith(("<<", "{{"))]
                        if any(text_lower == kw or text_lower.startswith(kw) for kw in plain_kws):
                            if field_key not in detected_fields:
                                detected_fields[field_key] = {
                                    "x": pdf_x_label_end,
                                    "y": pdf_y,
                                    "font_size": max(8, int(float(w.get("size", 10)))),
                                    "align": "right" if field_key in [
                                        "subtotal", "discount", "delivery_fee",
                                        "tax_amount", "grand_total", "paid_amount", "balance_due"
                                    ] else "left",
                                    "color": "#0F172A",
                                    "is_tag": False,
                                    "cover_rect": None,
                                }
                            break

                    # Detect table header row (Item / Description / Particulars)
                    if text_lower in ["description", "particulars", "item", "items", "product",
                                      "product name", "အမျိုးအမည်", "ကုန်ပစ္စည်းအမည်"]:
                        table_config["start_y"] = (page_height - float(w.get("bottom", 0))) - 26.0

                    # Detect Qty column x-position
                    if text_lower in ["qty", "quantity", "pcs", "unit qty"]:
                        table_config["columns"]["qty"]["x"] = float(w.get("x0", 330.0))
                        table_config["columns"]["foc"]["x"] = float(w.get("x0", 330.0)) + 50.0

                    # Detect Price column
                    if text_lower in ["price", "unit price", "rate", "unit rate"]:
                        table_config["columns"]["unit_price"]["x"] = float(w.get("x1", 450.0))

                    # Detect Total column
                    if text_lower in ["total", "amount", "line total"]:
                        table_config["columns"]["line_total"]["x"] = float(w.get("x1", 545.0))

            # Also check for AcroForm fields
            acroform_fields = self._detect_acroform_fields(pdf_template_path)
            if acroform_fields:
                detected_fields["_acroform_fields"] = acroform_fields

            return {
                "page_width": page_width,
                "page_height": page_height,
                "fields": detected_fields,
                "table": table_config,
                "detection_summary": {
                    "fields_found": len(detected_fields),
                    "has_acroform": bool(acroform_fields),
                    "table_start_y": table_config["start_y"],
                },
            }
        except Exception as e:
            logger.error(f"Error detecting template layout: {e}")
            return {
                "page_width": 595.0,
                "page_height": 842.0,
                "fields": {},
                "table": DEFAULT_TABLE_CONFIG,
                "detection_summary": {"error": str(e)},
            }

    def _detect_acroform_fields(self, pdf_path: str) -> Dict[str, Any]:
        """Detect interactive PDF AcroForm fields."""
        try:
            reader = PdfReader(pdf_path)
            fields = reader.get_fields()
            if not fields:
                return {}
            return {name: {"type": str(field.get("/FT", ""))} for name, field in fields.items()}
        except Exception as e:
            logger.debug(f"AcroForm detection: {e}")
            return {}

    # ──────────────────────────────────────────────────────────────
    # MAIN FILL ENGINE
    # ──────────────────────────────────────────────────────────────

    def generate_filled_invoice_pdf(
        self,
        template_pdf_path: str,
        output_pdf_path: str,
        invoice_data: Dict[str, Any],
        items: List[Dict[str, Any]],
        mapping_config: Optional[Dict[str, Any]] = None,
        brand_accent_color: str = "#10B981",
    ) -> str:
        """
        Main method: Overlay invoice data onto the PDF template.

        Args:
            template_pdf_path: Path to the uploaded blank PDF template
            output_pdf_path: Where to save the filled invoice PDF
            invoice_data: Dict with all header/footer field values
            items: List of line item dicts {name, qty, foc, unit_price, line_total}
            mapping_config: Previously saved coordinate mapping (or None to auto-detect)
            brand_accent_color: Brand hex color for accents

        Returns:
            Absolute path to the generated PDF file
        """
        # Step 1: Auto-detect layout if no saved mapping
        if not mapping_config:
            logger.info("No mapping config provided - running auto-detection...")
            mapping_config = self.auto_detect_template_layout(template_pdf_path)

        # Step 2: Read the original template
        reader = PdfReader(template_pdf_path)
        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)

        # Step 3: Handle AcroForm fields if present
        writer = PdfWriter()
        writer.append(reader)

        acroform_fields = mapping_config.get("fields", {}).get("_acroform_fields", {})
        if acroform_fields:
            try:
                # Map our standard data to known AcroForm field names
                acro_data = self._map_to_acroform(invoice_data, items, acroform_fields)
                writer.update_page_form_field_values(writer.pages[0], acro_data)
                logger.info(f"AcroForm fields filled: {list(acro_data.keys())}")
            except Exception as e:
                logger.warning(f"AcroForm fill error: {e}")

        # Step 4: Create transparent vector overlay layer with ReportLab
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        fields_map = mapping_config.get("fields", {})

        # Draw header/footer fields
        for field_key, cfg in fields_map.items():
            if field_key == "_acroform_fields":
                continue
            self._draw_field(c, field_key, cfg, invoice_data)

        # Draw line items table
        self._draw_line_items(c, items, mapping_config.get("table", DEFAULT_TABLE_CONFIG))

        c.save()
        packet.seek(0)

        # Step 5: Merge vector overlay onto original PDF
        overlay_reader = PdfReader(packet)
        if overlay_reader.pages:
            writer.pages[0].merge_page(overlay_reader.pages[0])

        # Step 6: Write output
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        with open(output_pdf_path, "wb") as f_out:
            writer.write(f_out)

        logger.info(f"Invoice PDF generated: {output_pdf_path}")
        return os.path.abspath(output_pdf_path)

    def _draw_field(
        self,
        c: canvas.Canvas,
        field_key: str,
        cfg: Dict[str, Any],
        invoice_data: Dict[str, Any],
    ):
        """Draw a single header/footer field onto the canvas."""
        raw_val = invoice_data.get(field_key, "")
        if raw_val is None or raw_val == "":
            return

        # Format numeric values
        if isinstance(raw_val, float):
            val_str = f"{raw_val:,.0f}"
        elif isinstance(raw_val, int):
            val_str = f"{raw_val:,}"
        else:
            val_str = str(raw_val)

        # Optionally cover/erase the <<TAG>> placeholder with a white box
        if cfg.get("cover_rect") and cfg.get("is_tag"):
            rx, ry, rw, rh = cfg["cover_rect"]
            c.setFillColor(HexColor("#FFFFFF"))
            c.rect(rx, ry, rw, rh, stroke=0, fill=1)

        # Set font and color
        font_size = cfg.get("font_size", 10)
        color_hex = cfg.get("color", "#0F172A")
        try:
            c.setFont(self.font_name, font_size)
            c.setFillColor(HexColor(color_hex))
        except Exception:
            c.setFont("Helvetica", font_size)
            c.setFillColor(HexColor("#0F172A"))

        x, y = float(cfg["x"]), float(cfg["y"])
        align = cfg.get("align", "left")

        try:
            if align == "right":
                c.drawRightString(x, y, val_str)
            elif align == "center":
                c.drawCentredString(x, y, val_str)
            else:
                c.drawString(x, y, val_str)
        except Exception as e:
            logger.debug(f"Field draw error [{field_key}]: {e}")

    def _draw_line_items(
        self,
        c: canvas.Canvas,
        items: List[Dict[str, Any]],
        table_cfg: Dict[str, Any],
    ):
        """Draw product line item rows onto the invoice."""
        curr_y = float(table_cfg.get("start_y", 480.0))
        row_h = float(table_cfg.get("row_height", 22.0))
        cols = table_cfg.get("columns", DEFAULT_TABLE_CONFIG["columns"])
        font_size = table_cfg.get("font_size", 10)
        max_rows = table_cfg.get("max_rows", 15)

        try:
            c.setFont(self.font_name, font_size)
            c.setFillColor(HexColor("#0F172A"))
        except Exception:
            c.setFont("Helvetica", font_size)
            c.setFillColor(HexColor("#0F172A"))

        for idx, item in enumerate(items[:max_rows], start=1):
            row_values = {
                "no":         str(idx),
                "name":       str(item.get("name", "")),
                "qty":        str(int(item.get("qty", 0))),
                "foc":        str(int(item.get("foc", 0))) if item.get("foc") else "-",
                "unit_price": f"{float(item.get('unit_price', 0)):,.0f}",
                "line_total": f"{float(item.get('line_total', 0)):,.0f}",
            }

            for col_key, text_val in row_values.items():
                if col_key not in cols:
                    continue
                col_cfg = cols[col_key]
                col_x = float(col_cfg.get("x", 0))
                align = col_cfg.get("align", "left")
                try:
                    if align == "right":
                        c.drawRightString(col_x, curr_y, text_val)
                    elif align == "center":
                        c.drawCentredString(col_x, curr_y, text_val)
                    else:
                        c.drawString(col_x, curr_y, text_val)
                except Exception as e:
                    logger.debug(f"Line item draw error [{col_key}]: {e}")

            curr_y -= row_h

    def _map_to_acroform(
        self,
        invoice_data: Dict[str, Any],
        items: List[Dict[str, Any]],
        acroform_fields: Dict[str, Any],
    ) -> Dict[str, str]:
        """Map standard invoice data to AcroForm field names."""
        result = {}
        # Try common AcroForm field naming conventions
        field_aliases = {
            "invoice_no": ["invoice_no", "invoice_number", "inv_no", "InvoiceNo", "InvoiceNumber"],
            "invoice_date": ["invoice_date", "date", "Date", "InvoiceDate"],
            "customer_name": ["customer_name", "customer", "name", "CustomerName", "CustName"],
            "customer_phone": ["customer_phone", "phone", "Phone", "CustPhone"],
            "customer_address": ["customer_address", "address", "Address", "CustAddress"],
            "grand_total": ["grand_total", "total", "Total", "GrandTotal", "Amount"],
            "paid_amount": ["paid_amount", "paid", "Paid", "PaidAmount"],
        }

        for field_key, aliases in field_aliases.items():
            val = invoice_data.get(field_key, "")
            for alias in aliases:
                if alias in acroform_fields:
                    result[alias] = str(val) if val is not None else ""
                    break

        # Line items (1-indexed)
        for i, item in enumerate(items[:10], start=1):
            for acro_name in [f"item_{i}_name", f"Item{i}Name", f"product_{i}"]:
                if acro_name in acroform_fields:
                    result[acro_name] = str(item.get("name", ""))
            for acro_name in [f"item_{i}_qty", f"Item{i}Qty", f"qty_{i}"]:
                if acro_name in acroform_fields:
                    result[acro_name] = str(int(item.get("qty", 0)))
            for acro_name in [f"item_{i}_total", f"Item{i}Total", f"total_{i}"]:
                if acro_name in acroform_fields:
                    result[acro_name] = f"{float(item.get('line_total', 0)):,.0f}"

        return result

    # ──────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ──────────────────────────────────────────────────────────────

    def get_template_preview_info(self, pdf_template_path: str) -> Dict[str, Any]:
        """Get basic template info for the frontend preview."""
        try:
            reader = PdfReader(pdf_template_path)
            page = reader.pages[0]
            return {
                "num_pages": len(reader.pages),
                "width": float(page.mediabox.width),
                "height": float(page.mediabox.height),
                "has_acroform": bool(reader.get_fields()),
                "file_size_kb": round(os.path.getsize(pdf_template_path) / 1024, 1),
            }
        except Exception as e:
            return {"error": str(e)}

    def update_mapping_field(
        self,
        mapping_config: Dict[str, Any],
        field_key: str,
        x: float,
        y: float,
        font_size: int = 10,
        align: str = "left",
        color: str = "#0F172A",
    ) -> Dict[str, Any]:
        """Update a single field in an existing mapping config (for drag-drop calibration)."""
        if "fields" not in mapping_config:
            mapping_config["fields"] = {}
        mapping_config["fields"][field_key] = {
            "x": x, "y": y, "font_size": font_size,
            "align": align, "color": color, "is_tag": False, "cover_rect": None,
        }
        return mapping_config

    def save_mapping_config(self, config: Dict[str, Any], output_path: str):
        """Save mapping configuration to JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_mapping_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load mapping configuration from JSON file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading mapping config: {e}")
            return None
