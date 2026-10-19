"""PDF Invoice Engine router - Template management and invoice PDF generation."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import Brand, Invoice, Customer, InvoiceItem
from core.security import get_current_user, TokenData
from core.config import settings
from modules.pdf_invoice_engine.pdf_auto_filler import SmartPDFInvoiceEngine

router = APIRouter()


@router.get("/templates")
async def list_templates(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List all brand PDF invoice templates."""
    import os
    brands = db.query(Brand).filter(Brand.is_active == True).all()
    result = []
    for brand in brands:
        result.append({
            "brand_id": brand.id,
            "brand_name": brand.name,
            "template_path": brand.invoice_template_path,
            "template_exists": bool(
                brand.invoice_template_path and
                os.path.exists(brand.invoice_template_path)
            ),
            "template_calibrated": brand.template_calibrated,
            "fields_mapped": list((brand.invoice_template_mapping or {}).get("fields", {}).keys()),
        })
    return result


@router.post("/upload/{brand_id}")
async def upload_template(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Link the pre-generated sample template for a brand (for demo/testing)."""
    import os
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Look for sample template
    templates_dir = settings.templates_dir
    sample = os.path.join(templates_dir, f"{brand.name}_Invoice_Template.pdf")
    if not os.path.exists(sample):
        raise HTTPException(
            status_code=404,
            detail=f"Sample template not found: {sample}. Run generate_pdf_templates.py first."
        )

    engine = SmartPDFInvoiceEngine(fonts_dir=settings.fonts_dir)
    mapping = engine.auto_detect_template_layout(sample)

    brand.invoice_template_path = sample
    brand.invoice_template_mapping = mapping
    brand.template_calibrated = True
    db.commit()

    return {
        "message": f"Template linked for brand {brand.name}",
        "template_path": sample,
        "fields_detected": list(mapping.get("fields", {}).keys()),
    }


@router.get("/generate/{invoice_id}")
async def generate_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Generate/re-generate the PDF for an existing invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    brand = db.query(Brand).filter(Brand.id == invoice.brand_id).first()
    if not brand or not brand.invoice_template_path:
        raise HTTPException(status_code=400, detail="Brand has no PDF template uploaded")

    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first() if invoice.customer_id else None
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()

    # Prepare data
    invoice_data = {
        "invoice_no": invoice.invoice_number,
        "invoice_date": str(invoice.invoice_date),
        "customer_name": customer.name if customer else "Walk-in Customer",
        "customer_phone": customer.phone if customer else "",
        "customer_address": customer.address if customer else "",
        "payment_method": invoice.payment_method,
        "subtotal": invoice.subtotal,
        "discount": invoice.discount_amount,
        "delivery_fee": invoice.delivery_fee,
        "tax_amount": invoice.commercial_tax_amount,
        "grand_total": invoice.grand_total,
        "paid_amount": invoice.paid_amount,
        "balance_due": invoice.credit_amount,
        "remarks": invoice.remarks or "",
    }

    items_list = [
        {
            "name": i.product_name_snapshot,
            "qty": i.qty,
            "foc": i.foc_qty,
            "unit_price": i.unit_price,
            "line_total": i.line_total,
        }
        for i in items
    ]

    import os
    output_path = os.path.join(
        settings.invoices_output_dir,
        f"{invoice.invoice_number.replace('/', '_').replace('-', '_')}.pdf"
    )

    engine = SmartPDFInvoiceEngine(fonts_dir=settings.fonts_dir)
    pdf_path = engine.generate_filled_invoice_pdf(
        template_pdf_path=brand.invoice_template_path,
        output_pdf_path=output_path,
        invoice_data=invoice_data,
        items=items_list,
        mapping_config=brand.invoice_template_mapping,
        brand_accent_color=brand.theme_primary_color,
    )

    # Update stored path
    invoice.generated_pdf_path = pdf_path
    db.commit()

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.get("/download/{invoice_id}")
async def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Download existing generated invoice PDF."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not invoice.generated_pdf_path:
        raise HTTPException(status_code=404, detail="PDF not yet generated. Call /generate first.")
    import os
    if not os.path.exists(invoice.generated_pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(
        path=invoice.generated_pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.post("/detect-template/{brand_id}")
async def re_detect_template(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Re-run auto-detection on an already-uploaded brand template."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand or not brand.invoice_template_path:
        raise HTTPException(status_code=404, detail="No template found for this brand")

    import os
    if not os.path.exists(brand.invoice_template_path):
        raise HTTPException(status_code=404, detail="Template file missing from disk")

    engine = SmartPDFInvoiceEngine(fonts_dir=settings.fonts_dir)
    mapping = engine.auto_detect_template_layout(brand.invoice_template_path)

    brand.invoice_template_mapping = mapping
    brand.template_calibrated = True
    db.commit()

    return {
        "message": "Template re-detected",
        "fields_found": list(mapping.get("fields", {}).keys()),
        "detection_summary": mapping.get("detection_summary", {}),
    }


@router.get("/template-info/{brand_id}")
async def get_template_info(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get info about the uploaded PDF template."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand or not brand.invoice_template_path:
        raise HTTPException(status_code=404, detail="No template for this brand")

    engine = SmartPDFInvoiceEngine(fonts_dir=settings.fonts_dir)
    info = engine.get_template_preview_info(brand.invoice_template_path)
    return {
        "template_path": brand.invoice_template_path,
        "template_calibrated": brand.template_calibrated,
        "mapping_fields": list((brand.invoice_template_mapping or {}).get("fields", {}).keys()),
        **info,
    }
