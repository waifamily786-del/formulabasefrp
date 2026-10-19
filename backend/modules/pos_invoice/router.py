"""POS & Invoice router - Fast invoice creation with auto-PDF generation."""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import (
    Invoice, InvoiceItem, Customer, Product, Brand,
)
from core.security import get_current_user, TokenData
from core.config import settings
from modules.accounting.auto_accountant import AutoAccountantEngine

router = APIRouter()


# ─── Customers ────────────────────────────────────────────────────

@router.get("/customers/{brand_id}", response_model=List[dict])
async def list_customers(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List customers for a specific brand (isolated)."""
    customers = db.query(Customer).filter(
        Customer.brand_id == brand_id,
        Customer.is_active == True,
    ).order_by(Customer.name).all()
    return [
        {
            "id": c.id, "name": c.name, "phone": c.phone,
            "address": c.address, "price_tier": c.price_tier,
            "outstanding_credit": c.outstanding_credit,
            "total_purchases": c.total_purchases,
        }
        for c in customers
    ]


class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    price_tier: str = "RETAIL"


@router.post("/customers/{brand_id}")
async def create_customer(
    brand_id: int,
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    cust = Customer(brand_id=brand_id, **data.model_dump(), is_active=True)
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return {"id": cust.id, "name": cust.name}


# ─── Products ─────────────────────────────────────────────────────

@router.get("/products/{brand_id}", response_model=List[dict])
async def list_products(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List products for a brand with all pricing tiers (isolated)."""
    products = db.query(Product).filter(
        Product.brand_id == brand_id,
        Product.is_active == True,
    ).order_by(Product.sort_order).all()
    return [
        {
            "id": p.id, "sku": p.sku, "name": p.name,
            "category": p.category, "unit": p.unit,
            "current_stock": p.current_stock,
            "unit_cost_cogs": p.unit_cost_cogs,
            "is_low_stock": p.current_stock <= p.minimum_reorder_level,
            "prices": {
                "RETAIL": p.price_retail,
                "WHOLESALE": p.price_wholesale,
                "DISTRIBUTOR": p.price_distributor,
                "VIP": p.price_vip,
                "CUSTOM_OEM": p.price_custom_oem,
            },
        }
        for p in products
    ]


# ─── Invoice Creation ─────────────────────────────────────────────

class InvoiceItemInput(BaseModel):
    product_id: int
    qty: float
    foc_qty: float = 0.0
    price_tier: str = "RETAIL"
    custom_unit_price: Optional[float] = None
    item_discount_percent: float = 0.0


class CreateInvoiceRequest(BaseModel):
    brand_id: int
    customer_id: Optional[int] = None
    # Quick customer creation inline
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    invoice_date: Optional[date] = None
    items: List[InvoiceItemInput]
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    delivery_fee: float = 0.0
    payment_method: str = "CASH"
    paid_amount: Optional[float] = None
    remarks: Optional[str] = None
    generate_pdf: bool = True


@router.post("/invoices")
async def create_invoice(
    request: CreateInvoiceRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Create a POS invoice with auto-accounting and optional PDF generation."""
    brand = db.query(Brand).filter(Brand.id == request.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Get or create customer
    customer = None
    if request.customer_id:
        customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
    elif request.customer_name:
        customer = Customer(
            brand_id=request.brand_id,
            name=request.customer_name,
            phone=request.customer_phone,
            address=request.customer_address,
            price_tier="RETAIL",
            is_active=True,
        )
        db.add(customer)
        db.flush()

    # Calculate invoice financials
    invoice_items_data = []
    subtotal = 0.0
    total_cogs = 0.0

    for item_input in request.items:
        product = db.query(Product).filter(Product.id == item_input.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item_input.product_id} not found")
        if product.current_stock < item_input.qty:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}: need {item_input.qty}, have {product.current_stock}"
            )

        # Determine unit price
        if item_input.custom_unit_price is not None:
            unit_price = item_input.custom_unit_price
        else:
            price_map = {
                "RETAIL": product.price_retail,
                "WHOLESALE": product.price_wholesale,
                "DISTRIBUTOR": product.price_distributor,
                "VIP": product.price_vip,
                "CUSTOM_OEM": product.price_custom_oem,
            }
            unit_price = price_map.get(item_input.price_tier, product.price_retail)

        item_disc_amount = unit_price * item_input.qty * (item_input.item_discount_percent / 100)
        line_total = unit_price * item_input.qty - item_disc_amount
        line_cogs = product.unit_cost_cogs * (item_input.qty + item_input.foc_qty)

        subtotal += line_total
        total_cogs += line_cogs

        invoice_items_data.append({
            "product": product,
            "qty": item_input.qty,
            "foc_qty": item_input.foc_qty,
            "unit_price": unit_price,
            "item_discount_percent": item_input.item_discount_percent,
            "item_discount_amount": round(item_disc_amount, 2),
            "line_total": round(line_total, 2),
            "line_cogs": round(line_cogs, 2),
        })

    # Apply invoice-level discount
    if request.discount_percent > 0:
        discount_amount = subtotal * (request.discount_percent / 100)
    else:
        discount_amount = request.discount_amount

    taxable_amount = subtotal - discount_amount
    ct_amount = taxable_amount * (brand.commercial_tax_rate / 100)
    grand_total = taxable_amount + ct_amount + request.delivery_fee

    paid_amount = request.paid_amount if request.paid_amount is not None else grand_total
    credit_amount = max(0, grand_total - paid_amount)
    change_amount = max(0, paid_amount - grand_total)

    # Generate invoice number
    inv_number = f"{brand.invoice_prefix}{brand.invoice_sequence:05d}"
    brand.invoice_sequence += 1

    # Create invoice
    invoice = Invoice(
        brand_id=request.brand_id,
        customer_id=customer.id if customer else None,
        invoice_number=inv_number,
        invoice_date=request.invoice_date or date.today(),
        subtotal=round(subtotal, 2),
        discount_percent=request.discount_percent,
        discount_amount=round(discount_amount, 2),
        commercial_tax_percent=brand.commercial_tax_rate,
        commercial_tax_amount=round(ct_amount, 2),
        delivery_fee=round(request.delivery_fee, 2),
        grand_total=round(grand_total, 2),
        payment_method=request.payment_method,
        paid_amount=round(paid_amount, 2),
        credit_amount=round(credit_amount, 2),
        change_amount=round(change_amount, 2),
        total_cogs=round(total_cogs, 2),
        status="CONFIRMED",
        remarks=request.remarks,
        created_by_user_id=current_user.user_id,
    )
    db.add(invoice)
    db.flush()

    # Create invoice items and deduct stock
    for item_data in invoice_items_data:
        product = item_data["product"]
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            qty=item_data["qty"],
            foc_qty=item_data["foc_qty"],
            unit_price=item_data["unit_price"],
            item_discount_percent=item_data["item_discount_percent"],
            item_discount_amount=item_data["item_discount_amount"],
            line_total=item_data["line_total"],
            unit_cost_at_sale=product.unit_cost_cogs,
            line_cogs=item_data["line_cogs"],
        ))
        # Deduct stock (qty + FOC)
        product.current_stock -= (item_data["qty"] + item_data["foc_qty"])

    # Update customer credit
    if customer:
        if credit_amount > 0:
            customer.outstanding_credit += credit_amount
        customer.total_purchases += grand_total

    db.flush()

    # Auto-Accounting: Create double-entry journal
    from database.models import Company
    company = db.query(Company).first()
    accountant = AutoAccountantEngine(db)
    try:
        accountant.create_sales_journal_entry(invoice, company.id, brand.name)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Accounting error: {str(e)}")

    # Generate PDF if requested
    pdf_path = None
    if request.generate_pdf and brand.invoice_template_path:
        try:
            pdf_path = _generate_invoice_pdf(invoice, brand, customer, invoice_items_data, db)
            invoice.generated_pdf_path = pdf_path
            db.commit()
        except Exception as e:
            db.commit()  # Save invoice even if PDF fails
            return {
                "invoice_id": invoice.id,
                "invoice_number": inv_number,
                "grand_total": invoice.grand_total,
                "pdf_warning": f"Invoice saved but PDF generation failed: {str(e)}",
            }
    else:
        db.commit()

    return {
        "invoice_id": invoice.id,
        "invoice_number": inv_number,
        "subtotal": invoice.subtotal,
        "discount_amount": invoice.discount_amount,
        "tax_amount": invoice.commercial_tax_amount,
        "delivery_fee": invoice.delivery_fee,
        "grand_total": invoice.grand_total,
        "paid_amount": invoice.paid_amount,
        "credit_amount": invoice.credit_amount,
        "change_amount": invoice.change_amount,
        "pdf_path": pdf_path,
        "status": "CONFIRMED",
    }


def _generate_invoice_pdf(invoice, brand, customer, items_data, db) -> str:
    """Generate filled PDF invoice using the SmartPDFInvoiceEngine."""
    from modules.pdf_invoice_engine.pdf_auto_filler import SmartPDFInvoiceEngine
    import os

    engine = SmartPDFInvoiceEngine(fonts_dir=settings.fonts_dir)

    # Prepare invoice data dict
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

    # Prepare line items
    items = [
        {
            "name": item_data["product"].name,
            "qty": item_data["qty"],
            "foc": item_data["foc_qty"],
            "unit_price": item_data["unit_price"],
            "line_total": item_data["line_total"],
        }
        for item_data in items_data
    ]

    output_path = os.path.join(
        settings.invoices_output_dir,
        f"{invoice.invoice_number.replace('/', '_')}.pdf"
    )

    return engine.generate_filled_invoice_pdf(
        template_pdf_path=brand.invoice_template_path,
        output_pdf_path=output_path,
        invoice_data=invoice_data,
        items=items,
        mapping_config=brand.invoice_template_mapping,
        brand_accent_color=brand.theme_primary_color,
    )


# ─── Invoice queries ──────────────────────────────────────────────

@router.get("/invoices/{brand_id}")
async def list_invoices(
    brand_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List invoices for a brand (isolated)."""
    invoices = (
        db.query(Invoice)
        .filter(Invoice.brand_id == brand_id, Invoice.status != "CANCELLED")
        .order_by(Invoice.id.desc())
        .limit(limit)
        .all()
    )
    result = []
    for inv in invoices:
        cust = db.query(Customer).filter(Customer.id == inv.customer_id).first() if inv.customer_id else None
        result.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_date": str(inv.invoice_date),
            "customer_name": cust.name if cust else "Walk-in",
            "grand_total": inv.grand_total,
            "payment_method": inv.payment_method,
            "status": inv.status,
            "has_pdf": bool(inv.generated_pdf_path),
        })
    return result


@router.get("/invoices/detail/{invoice_id}")
async def get_invoice_detail(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get full invoice detail with all line items."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    cust = db.query(Customer).filter(Customer.id == invoice.customer_id).first() if invoice.customer_id else None
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "invoice_date": str(invoice.invoice_date),
        "customer": {"name": cust.name, "phone": cust.phone, "address": cust.address} if cust else {},
        "items": [
            {"product_name": i.product_name_snapshot, "qty": i.qty, "foc_qty": i.foc_qty,
             "unit_price": i.unit_price, "line_total": i.line_total}
            for i in items
        ],
        "subtotal": invoice.subtotal,
        "discount_amount": invoice.discount_amount,
        "tax_amount": invoice.commercial_tax_amount,
        "delivery_fee": invoice.delivery_fee,
        "grand_total": invoice.grand_total,
        "paid_amount": invoice.paid_amount,
        "credit_amount": invoice.credit_amount,
        "payment_method": invoice.payment_method,
        "status": invoice.status,
        "pdf_path": invoice.generated_pdf_path,
        "remarks": invoice.remarks,
    }


@router.get("/dashboard/{brand_id}")
async def brand_dashboard(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get key dashboard metrics for a brand."""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    today = date.today()
    month_start = today.replace(day=1)

    # Today's sales
    today_invs = db.query(Invoice).filter(
        Invoice.brand_id == brand_id,
        Invoice.invoice_date == today,
        Invoice.status == "CONFIRMED",
    ).all()
    today_revenue = sum(i.grand_total for i in today_invs)
    today_cogs = sum(i.total_cogs for i in today_invs)

    # This month's sales
    month_invs = db.query(Invoice).filter(
        Invoice.brand_id == brand_id,
        Invoice.invoice_date >= month_start,
        Invoice.status == "CONFIRMED",
    ).all()
    month_revenue = sum(i.grand_total for i in month_invs)
    month_cogs = sum(i.total_cogs for i in month_invs)
    month_profit = month_revenue - month_cogs

    # Customer count
    cust_count = db.query(Customer).filter(Customer.brand_id == brand_id, Customer.is_active == True).count()
    total_ar = db.query(func.sum(Customer.outstanding_credit)).filter(Customer.brand_id == brand_id).scalar() or 0

    # Product stock summary
    products = db.query(Product).filter(Product.brand_id == brand_id, Product.is_active == True).all()
    low_stock_products = [p for p in products if p.current_stock <= p.minimum_reorder_level]

    return {
        "today": {
            "revenue": round(today_revenue, 2),
            "profit": round(today_revenue - today_cogs, 2),
            "invoice_count": len(today_invs),
        },
        "this_month": {
            "revenue": round(month_revenue, 2),
            "cogs": round(month_cogs, 2),
            "gross_profit": round(month_profit, 2),
            "margin_percent": round((month_profit / month_revenue * 100) if month_revenue > 0 else 0, 1),
            "invoice_count": len(month_invs),
        },
        "customers": {
            "total": cust_count,
            "total_ar": round(total_ar, 2),
        },
        "inventory": {
            "products_count": len(products),
            "low_stock_count": len(low_stock_products),
            "low_stock_items": [{"name": p.name, "stock": p.current_stock} for p in low_stock_products],
        },
    }
