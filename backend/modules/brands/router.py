"""Brands router - Multi-Brand Profile management and theme engine."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import Brand, Company
from core.security import get_current_user, TokenData
from core.config import settings
import os, shutil

router = APIRouter()


class BrandTheme(BaseModel):
    theme_primary_color: str
    theme_gradient_start: str
    theme_gradient_mid: str
    theme_gradient_end: str
    theme_surface_tint: str
    theme_border_tint: str
    theme_deep_text: str


class BrandCreate(BaseModel):
    name: str
    full_name: Optional[str] = None
    tagline: Optional[str] = None
    invoice_prefix: str = "INV-"
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    commercial_tax_rate: float = 0.0
    theme_primary_color: str = "#10B981"
    theme_gradient_start: str = "#059669"
    theme_gradient_mid: str = "#10B981"
    theme_gradient_end: str = "#34D399"
    theme_surface_tint: str = "#ECFDF5"
    theme_border_tint: str = "#A7F3D0"
    theme_deep_text: str = "#064E3B"


class BrandResponse(BaseModel):
    id: int
    name: str
    full_name: Optional[str]
    tagline: Optional[str]
    invoice_prefix: str
    phone: Optional[str]
    address: Optional[str]
    email: Optional[str]
    theme_primary_color: str
    theme_gradient_start: str
    theme_gradient_mid: str
    theme_gradient_end: str
    theme_surface_tint: str
    theme_border_tint: str
    theme_deep_text: str
    commercial_tax_rate: float
    template_calibrated: bool
    invoice_sequence: int
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[BrandResponse])
async def list_brands(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List all active brand profiles."""
    brands = db.query(Brand).filter(Brand.is_active == True).order_by(Brand.sort_order).all()
    return brands


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific brand profile."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.post("/", response_model=BrandResponse)
async def create_brand(
    brand_data: BrandCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new brand profile."""
    company = db.query(Company).first()
    brand = Brand(company_id=company.id, **brand_data.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: int,
    brand_data: BrandCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Update brand profile (including theme colors)."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in brand_data.model_dump().items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return brand


@router.put("/{brand_id}/theme", response_model=BrandResponse)
async def update_brand_theme(
    brand_id: int,
    theme: BrandTheme,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Update only the theme colors for a brand."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in theme.model_dump().items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return brand


@router.post("/{brand_id}/upload-template")
async def upload_pdf_template(
    brand_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Upload a custom PDF invoice template for a brand."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save to templates directory
    template_filename = f"brand_{brand_id}_{brand.name.upper()}_template.pdf"
    template_path = os.path.join(settings.templates_dir, template_filename)

    with open(template_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Auto-detect the template layout
    from modules.pdf_invoice_engine.pdf_auto_filler import SmartPDFInvoiceEngine
    engine = SmartPDFInvoiceEngine(fonts_dir=settings.fonts_dir)
    mapping = engine.auto_detect_template_layout(template_path)

    # Save to brand
    brand.invoice_template_path = template_path
    brand.invoice_template_mapping = mapping
    brand.template_calibrated = True
    db.commit()

    return {
        "message": "Template uploaded and auto-detected successfully",
        "template_path": template_filename,
        "mapping_summary": mapping.get("detection_summary", {}),
        "fields_detected": list(mapping.get("fields", {}).keys()),
        "page_size": f"{mapping.get('page_width', 0):.0f}x{mapping.get('page_height', 0):.0f} pts",
    }


@router.get("/{brand_id}/template-mapping")
async def get_template_mapping(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get the coordinate mapping JSON for a brand's PDF template."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if not brand.invoice_template_mapping:
        raise HTTPException(status_code=404, detail="No template mapping found. Upload a PDF template first.")
    return brand.invoice_template_mapping


@router.put("/{brand_id}/template-mapping")
async def update_template_mapping(
    brand_id: int,
    mapping: dict,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Update/calibrate the template mapping (drag-drop calibration results)."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand.invoice_template_mapping = mapping
    brand.template_calibrated = True
    db.commit()
    return {"message": "Template mapping updated", "fields": list(mapping.get("fields", {}).keys())}
