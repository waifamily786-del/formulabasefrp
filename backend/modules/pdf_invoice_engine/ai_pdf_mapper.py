"""
FormulaBase Nexus - AI PDF Template Mapper
Uses pdfplumber + Gemini Vision to auto-detect invoice field positions.
Supports both plain PDF analysis and AI-enhanced coordinate refinement.
"""
import os
import re
import json
import base64
import logging
from typing import Dict, List, Any, Optional

import pdfplumber

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Field keyword detection patterns (English + Myanmar)
# ──────────────────────────────────────────────────────────────────
FIELD_PATTERNS = {
    "invoice_no": re.compile(
        r"invoice\s*(?:no|number|#)|inv\s*(?:no|#)|voucher\s*no|ဘောင်ချာ(?:အမှတ်)?|<<INVOICE_NO>>|{{INVOICE_NO}}",
        re.IGNORECASE
    ),
    "invoice_date": re.compile(
        r"\bdate\b|invoice\s*date|နေ့စွဲ|<<INVOICE_DATE>>|{{INVOICE_DATE}}",
        re.IGNORECASE
    ),
    "customer_name": re.compile(
        r"customer\s*(?:name)?|bill\s*to|buyer|အမည်|ဝယ်သူ|<<CUST_NAME>>|{{CUST_NAME}}",
        re.IGNORECASE
    ),
    "customer_phone": re.compile(
        r"\bphone\b|\btel\b|\bmobile\b|ဖုန်း|<<CUST_PHONE>>|{{CUST_PHONE}}",
        re.IGNORECASE
    ),
    "customer_address": re.compile(
        r"\baddress\b|ship\s*to|လိပ်စာ|<<CUST_ADDRESS>>|{{CUST_ADDRESS}}",
        re.IGNORECASE
    ),
    "payment_method": re.compile(
        r"payment\s*(?:method|type)?|ငွေချေစနစ်|<<PAYMENT_METHOD>>|{{PAYMENT_METHOD}}",
        re.IGNORECASE
    ),
    "subtotal": re.compile(
        r"sub\s*total|subtotal|sub-total|စုစုပေါင်း|<<SUB_TOTAL>>|{{SUB_TOTAL}}",
        re.IGNORECASE
    ),
    "discount": re.compile(
        r"\bdiscount\b|\bdisc\.\b|လျှော့ငွေ|<<DISCOUNT_AMT>>|{{DISCOUNT_AMT}}",
        re.IGNORECASE
    ),
    "delivery_fee": re.compile(
        r"delivery\s*(?:fee|charge)?|\bshipping\b|ပို့ဆောင်ခ|<<DELIVERY_FEE>>|{{DELIVERY_FEE}}",
        re.IGNORECASE
    ),
    "tax_amount": re.compile(
        r"\btax\b|\bct\b|commercial\s*tax|\bvat\b|<<TAX_AMOUNT>>|{{TAX_AMOUNT}}",
        re.IGNORECASE
    ),
    "grand_total": re.compile(
        r"grand\s*total|net\s*total|total\s*due|ကျသင့်ငွေ|<<GRAND_TOTAL>>|{{GRAND_TOTAL}}",
        re.IGNORECASE
    ),
    "paid_amount": re.compile(
        r"paid\s*(?:amount)?|amount\s*paid|ပေးငွေ|<<PAID_AMOUNT>>|{{PAID_AMOUNT}}",
        re.IGNORECASE
    ),
    "balance_due": re.compile(
        r"balance\s*(?:due)?|\bdue\b|\bchange\b|ကျန်ငွေ|<<BALANCE_DUE>>|{{BALANCE_DUE}}",
        re.IGNORECASE
    ),
    "remarks": re.compile(
        r"\bremarks\b|\bnotes?\b|မှတ်ချက်|<<REMARKS>>|{{REMARKS}}",
        re.IGNORECASE
    ),
}

# Table header detection patterns
TABLE_HEADER_PATTERNS = {
    "description_col": re.compile(r"description|particulars|item|product|ကုန်ပစ္စည်း|အမျိုးအမည်", re.IGNORECASE),
    "qty_col": re.compile(r"\bqty\b|\bquantity\b|\bpcs\b", re.IGNORECASE),
    "price_col": re.compile(r"\bprice\b|unit\s*price|\brate\b", re.IGNORECASE),
    "total_col": re.compile(r"\btotal\b|\bamount\b", re.IGNORECASE),
    "foc_col": re.compile(r"\bfoc\b|free\s*(?:of\s*charge)?", re.IGNORECASE),
    "no_col": re.compile(r"^\s*(?:#|no\.?|s\.?n\.?)\s*$", re.IGNORECASE),
}


class AIPDFMapper:
    """
    AI-enhanced PDF layout mapper.
    Uses pdfplumber for coordinate extraction and optionally Gemini Vision
    for enhanced understanding of complex invoice layouts.
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key
        self._gemini_model = None

    def _get_gemini_model(self):
        """Lazy load Gemini Vision model."""
        if not self.gemini_api_key or self._gemini_model:
            return self._gemini_model
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")
        return self._gemini_model

    def analyze_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF using pdfplumber to extract text coordinates.
        Returns a complete field mapping configuration.
        """
        detected_fields = {}
        table_config = {
            "start_y": 480.0,
            "row_height": 22.0,
            "font_size": 10,
            "max_rows": 14,
            "columns": {
                "no":         {"x": 42.0,  "align": "center"},
                "name":       {"x": 75.0,  "align": "left"},
                "qty":        {"x": 315.0, "align": "center"},
                "foc":        {"x": 360.0, "align": "center"},
                "unit_price": {"x": 435.0, "align": "right"},
                "line_total": {"x": 550.0, "align": "right"},
            },
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]
                page_width = float(page.width)
                page_height = float(page.height)
                words = page.extract_words(
                    extra_attrs=["size", "fontname", "stroking_color", "non_stroking_color"],
                    use_text_flow=False,
                )

                # Process each word
                for w in words:
                    text_raw = w.get("text", "").strip()
                    if not text_raw:
                        continue

                    text_lower = text_raw.lower()
                    # Convert pdfplumber top-origin to ReportLab bottom-origin
                    word_x0 = float(w.get("x0", 0))
                    word_x1 = float(w.get("x1", 0))
                    word_top = float(w.get("top", 0))
                    word_bottom = float(w.get("bottom", 0))
                    word_y_rl = page_height - word_bottom + 2.0  # ReportLab Y

                    # Detect TAG placeholders
                    is_tag = bool(re.match(r"^(<<[A-Z0-9_]+>>|\{\{[A-Z0-9_]+\}\})$", text_raw, re.IGNORECASE))

                    # Match field patterns
                    for field_key, pattern in FIELD_PATTERNS.items():
                        if pattern.search(text_raw):
                            if field_key not in detected_fields:
                                field_entry = {
                                    "x": word_x0 if is_tag else word_x1 + 5.0,
                                    "y": word_y_rl,
                                    "font_size": max(7, int(float(w.get("size", 10)))),
                                    "align": "right" if field_key in [
                                        "subtotal", "discount", "delivery_fee",
                                        "tax_amount", "grand_total", "paid_amount", "balance_due",
                                    ] else "left",
                                    "color": "#0F172A",
                                    "is_tag": is_tag,
                                    "cover_rect": [
                                        word_x0 - 2,
                                        page_height - word_bottom - 2,
                                        word_x1 - word_x0 + 4,
                                        word_bottom - word_top + 4,
                                    ] if is_tag else None,
                                }
                                detected_fields[field_key] = field_entry
                            break

                    # Detect table structure
                    for col_key, pattern in TABLE_HEADER_PATTERNS.items():
                        if pattern.search(text_raw):
                            if col_key == "description_col":
                                table_config["start_y"] = word_y_rl - 26.0
                                table_config["columns"]["name"]["x"] = word_x0
                            elif col_key == "qty_col":
                                table_config["columns"]["qty"]["x"] = (word_x0 + word_x1) / 2
                            elif col_key == "price_col":
                                table_config["columns"]["unit_price"]["x"] = word_x1
                            elif col_key == "total_col":
                                table_config["columns"]["line_total"]["x"] = word_x1
                            elif col_key == "foc_col":
                                table_config["columns"]["foc"]["x"] = (word_x0 + word_x1) / 2
                            elif col_key == "no_col":
                                table_config["columns"]["no"]["x"] = (word_x0 + word_x1) / 2

                # Extract tables using pdfplumber
                tables = page.extract_tables()
                if tables:
                    logger.info(f"Found {len(tables)} table(s) in PDF")
                    # Use first table's bounding box for better row positioning
                    table_bbox = page.find_tables()
                    if table_bbox:
                        first_table = table_bbox[0]
                        bbox = first_table.bbox
                        # bbox is (x0, top, x1, bottom) in top-origin coords
                        table_top_rl = page_height - bbox[1] - 25
                        table_config["start_y"] = max(table_top_rl, table_config["start_y"])

                return {
                    "page_width": page_width,
                    "page_height": page_height,
                    "fields": detected_fields,
                    "table": table_config,
                    "detection_summary": {
                        "method": "pdfplumber",
                        "fields_found": len(detected_fields),
                        "has_tables": bool(tables),
                        "table_start_y": table_config["start_y"],
                        "word_count": len(words),
                    },
                }
        except Exception as e:
            logger.error(f"pdfplumber analysis error: {e}")
            return {
                "page_width": 595.0,
                "page_height": 842.0,
                "fields": {},
                "table": table_config,
                "detection_summary": {"error": str(e)},
            }

    def analyze_with_gemini_vision(self, pdf_path: str, base_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini Vision to enhance and verify the pdfplumber-detected mapping.
        Renders the first PDF page as image and sends to Gemini for analysis.
        """
        model = self._get_gemini_model()
        if not model:
            logger.info("Gemini not configured - using pdfplumber result only")
            return base_mapping

        try:
            # Render PDF page to image
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(pdf_path)
            page = pdf[0]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()

            import io
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()
            pdf.close()

            # Send to Gemini
            import google.generativeai as genai
            img_part = {"mime_type": "image/png", "data": img_bytes}
            prompt = """
Analyze this invoice template image. List all visible text labels and their approximate positions
(as percentage of image width and height from top-left corner).
Focus on: Invoice No, Date, Customer Name, Phone, Address, Payment Method,
Subtotal, Discount, Delivery, Tax, Grand Total, Paid Amount, Balance Due.
Also identify the table area for line items.
Return as JSON with structure:
{
  "detected_labels": [{"label": "...", "x_pct": 0.1, "y_pct": 0.2}],
  "table_area": {"top_pct": 0.4, "bottom_pct": 0.8}
}
"""
            response = model.generate_content([prompt, img_part])
            if response.text:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    gemini_result = json.loads(json_match.group())
                    # Merge Gemini insights with base mapping
                    page_h = base_mapping.get("page_height", 842.0)
                    page_w = base_mapping.get("page_width", 595.0)

                    for label_info in gemini_result.get("detected_labels", []):
                        label = label_info.get("label", "").lower()
                        x_pct = label_info.get("x_pct", 0)
                        y_pct = label_info.get("y_pct", 0)

                        # Convert percentage to PDF coordinates
                        x = x_pct * page_w
                        y = page_h - (y_pct * page_h)

                        # Map to field key
                        for fk, pattern in FIELD_PATTERNS.items():
                            if pattern.search(label):
                                if fk not in base_mapping["fields"]:
                                    base_mapping["fields"][fk] = {
                                        "x": x + 80,  # Offset past the label
                                        "y": y,
                                        "font_size": 9,
                                        "align": "right" if fk in [
                                            "subtotal", "discount", "delivery_fee",
                                            "tax_amount", "grand_total", "paid_amount", "balance_due",
                                        ] else "left",
                                        "color": "#0F172A",
                                        "is_tag": False,
                                        "cover_rect": None,
                                        "source": "gemini_vision",
                                    }
                                break

                    # Update table start Y
                    table_area = gemini_result.get("table_area", {})
                    if "top_pct" in table_area:
                        table_y = page_h - (table_area["top_pct"] * page_h) - 25
                        base_mapping["table"]["start_y"] = table_y

                    base_mapping["detection_summary"]["method"] = "pdfplumber+gemini_vision"

        except Exception as e:
            logger.warning(f"Gemini Vision analysis failed (using pdfplumber result): {e}")

        return base_mapping

    def analyze(self, pdf_path: str, use_gemini: bool = False) -> Dict[str, Any]:
        """
        Main analysis method. Runs pdfplumber then optionally Gemini Vision.
        """
        mapping = self.analyze_with_pdfplumber(pdf_path)
        if use_gemini and self.gemini_api_key:
            mapping = self.analyze_with_gemini_vision(pdf_path, mapping)
        return mapping
