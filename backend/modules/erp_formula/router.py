"""ERP Formula router - Raw Materials, BOM recipes, Production Batches."""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import (
    RawMaterial, RawMaterialCategory, BOM, BOMIngredient,
    Product, ProductionBatch, ProductionConsumption,
    RawMaterialStockMovement, ProductStockMovement, Brand
)
from core.security import get_current_user, TokenData
from modules.accounting.auto_accountant import AutoAccountantEngine

router = APIRouter()


# ─── Raw Materials ────────────────────────────────────────────────

@router.get("/raw-materials", response_model=List[dict])
async def list_raw_materials(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List all raw materials with current stock and cost."""
    materials = db.query(RawMaterial).filter(RawMaterial.is_active == True).all()
    result = []
    for m in materials:
        cat = db.query(RawMaterialCategory).filter(RawMaterialCategory.id == m.category_id).first()
        result.append({
            "id": m.id,
            "item_code": m.item_code,
            "name": m.name,
            "category": cat.name if cat else "Uncategorized",
            "category_color": cat.color_hex if cat else "#6B7280",
            "unit": m.unit,
            "current_stock": m.current_stock,
            "weighted_avg_cost": m.weighted_avg_cost,
            "total_value": round(m.current_stock * m.weighted_avg_cost, 2),
            "minimum_reorder_level": m.minimum_reorder_level,
            "is_low_stock": m.current_stock <= m.minimum_reorder_level,
            "is_packaging": m.is_packaging,
            "default_supplier": m.default_supplier_name,
        })
    return result


@router.get("/raw-materials/{rm_id}")
async def get_raw_material(rm_id: int, db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    rm = db.query(RawMaterial).filter(RawMaterial.id == rm_id).first()
    if not rm:
        raise HTTPException(status_code=404, detail="Raw material not found")
    return rm


class RawMaterialCreate(BaseModel):
    item_code: str
    name: str
    category_id: Optional[int] = None
    unit: str = "kg"
    minimum_reorder_level: float = 10.0
    is_packaging: bool = False
    default_supplier_name: Optional[str] = None

@router.post("/raw-materials")
async def create_raw_material(
    data: RawMaterialCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    from database.models import Company
    company = db.query(Company).first()
    rm = RawMaterial(company_id=company.id, **data.model_dump(), current_stock=0.0, weighted_avg_cost=0.0)
    db.add(rm)
    db.commit()
    db.refresh(rm)
    return {"id": rm.id, "name": rm.name, "item_code": rm.item_code}


# ─── BOM / Formula Engine ─────────────────────────────────────────

@router.get("/bom/{product_id}")
async def get_bom(product_id: int, db: Session = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    """Get BOM/recipe for a product with full ingredient list."""
    bom = db.query(BOM).filter(BOM.product_id == product_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found for this product")

    ingredients = []
    for ing in bom.ingredients:
        rm = ing.raw_material
        ingredients.append({
            "id": ing.id,
            "raw_material_id": rm.id,
            "raw_material_code": rm.item_code,
            "raw_material_name": rm.name,
            "unit": ing.unit or rm.unit,
            "quantity_per_batch": ing.quantity_per_batch,
            "unit_cost": rm.weighted_avg_cost,
            "ingredient_cost": round(ing.quantity_per_batch * rm.weighted_avg_cost, 2),
            "current_stock": rm.current_stock,
            "is_sufficient_for_1_batch": rm.current_stock >= ing.quantity_per_batch,
        })

    return {
        "bom_id": bom.id,
        "product_id": bom.product_id,
        "batch_size": bom.batch_size,
        "wastage_percent": bom.wastage_percent,
        "labor_cost": bom.labor_cost_per_batch,
        "overhead_cost": bom.overhead_cost_per_batch,
        "raw_material_cost": bom.raw_material_cost_per_batch,
        "total_batch_cost": bom.total_batch_cost,
        "unit_cost": bom.unit_cost,
        "ingredients": ingredients,
    }


# ─── Production Feasibility Simulator ────────────────────────────

@router.get("/simulate-production/{product_id}")
async def simulate_production(
    product_id: int,
    desired_qty: float = 100.0,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """AI Production Simulator: Can we produce X units? What's missing?"""
    bom = db.query(BOM).filter(BOM.product_id == product_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="No BOM found for this product")

    multiplier = desired_qty / bom.batch_size
    can_produce = True
    missing_materials = []
    required_materials = []

    for ing in bom.ingredients:
        rm = ing.raw_material
        needed_qty = ing.quantity_per_batch * multiplier * (1 + bom.wastage_percent / 100)
        is_sufficient = rm.current_stock >= needed_qty
        if not is_sufficient:
            can_produce = False
            missing_materials.append({
                "raw_material": rm.name,
                "code": rm.item_code,
                "unit": rm.unit,
                "needed": round(needed_qty, 3),
                "available": rm.current_stock,
                "shortage": round(needed_qty - rm.current_stock, 3),
                "estimated_cost_to_buy": round((needed_qty - rm.current_stock) * rm.last_purchase_price, 2),
            })
        required_materials.append({
            "raw_material": rm.name,
            "code": rm.item_code,
            "unit": rm.unit,
            "needed": round(needed_qty, 3),
            "available": rm.current_stock,
            "sufficient": is_sufficient,
        })

    # Calculate max producible units from current stock
    max_units = None
    if bom.ingredients:
        max_multipliers = []
        for ing in bom.ingredients:
            rm = ing.raw_material
            if ing.quantity_per_batch > 0:
                max_m = rm.current_stock / (ing.quantity_per_batch * (1 + bom.wastage_percent / 100))
                max_multipliers.append(max_m)
        if max_multipliers:
            max_units = round(min(max_multipliers) * bom.batch_size, 0)

    estimated_batch_cost = bom.unit_cost * desired_qty

    return {
        "product_id": product_id,
        "desired_qty": desired_qty,
        "can_produce": can_produce,
        "max_producible_units": max_units,
        "estimated_batch_cost": round(estimated_batch_cost, 2),
        "estimated_unit_cost": bom.unit_cost,
        "missing_materials": missing_materials,
        "required_materials": required_materials,
        "shopping_list_total": round(sum(m["estimated_cost_to_buy"] for m in missing_materials), 2),
    }


# ─── Production Batch Execution ──────────────────────────────────

class ProductionBatchCreate(BaseModel):
    product_id: int
    brand_id: int
    desired_qty: float
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


@router.post("/production-batches")
async def execute_production_batch(
    data: ProductionBatchCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Execute a production batch: deduct raw materials, add finished goods, post journal entry."""
    bom = db.query(BOM).filter(BOM.product_id == data.product_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="No BOM found for this product")

    product = db.query(Product).filter(Product.id == data.product_id).first()
    brand = db.query(Brand).filter(Brand.id == data.brand_id).first()

    multiplier = data.desired_qty / bom.batch_size
    raw_material_cost = 0.0

    # Generate batch number
    from datetime import datetime
    batch_num = f"BATCH-{brand.name}-{datetime.now().strftime('%Y%m%d%H%M')}"

    # Check and deduct raw materials
    for ing in bom.ingredients:
        rm = ing.raw_material
        needed = ing.quantity_per_batch * multiplier * (1 + bom.wastage_percent / 100)
        if rm.current_stock < needed:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock: {rm.name}. Need {needed:.2f} {rm.unit}, have {rm.current_stock:.2f}"
            )
        rm.current_stock -= needed
        cost = needed * rm.weighted_avg_cost
        raw_material_cost += cost

    labor_cost = bom.labor_cost_per_batch * multiplier
    overhead_cost = bom.overhead_cost_per_batch * multiplier
    total_cost = raw_material_cost + labor_cost + overhead_cost
    unit_cost = total_cost / data.desired_qty if data.desired_qty > 0 else 0

    # Create production batch
    batch = ProductionBatch(
        brand_id=data.brand_id,
        product_id=data.product_id,
        bom_id=bom.id,
        batch_number=batch_num,
        batch_multiplier=multiplier,
        planned_qty=data.desired_qty,
        actual_qty=data.desired_qty,
        manufacturing_date=data.manufacturing_date or date.today(),
        expiry_date=data.expiry_date,
        raw_material_cost=round(raw_material_cost, 2),
        labor_cost=round(labor_cost, 2),
        overhead_cost=round(overhead_cost, 2),
        total_batch_cost=round(total_cost, 2),
        unit_cost=round(unit_cost, 2),
        status="COMPLETED",
        notes=data.notes,
        created_by_user_id=current_user.user_id,
    )
    db.add(batch)
    db.flush()

    # Add finished goods to product inventory
    product.current_stock += data.desired_qty
    product.unit_cost_cogs = round(unit_cost, 2)
    bom.unit_cost = round(unit_cost, 2)

    # Post journal entry
    accountant = AutoAccountantEngine(db)
    accountant.create_production_journal_entry(batch, _get_company_id(db), brand.name)

    db.commit()

    return {
        "batch_number": batch_num,
        "product_id": data.product_id,
        "quantity_produced": data.desired_qty,
        "unit_cost": round(unit_cost, 2),
        "total_batch_cost": round(total_cost, 2),
        "new_product_stock": product.current_stock,
        "status": "COMPLETED",
    }


@router.get("/production-batches")
async def list_production_batches(
    brand_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    q = db.query(ProductionBatch)
    if brand_id:
        q = q.filter(ProductionBatch.brand_id == brand_id)
    batches = q.order_by(ProductionBatch.id.desc()).limit(50).all()
    return [
        {
            "id": b.id,
            "batch_number": b.batch_number,
            "product_id": b.product_id,
            "brand_id": b.brand_id,
            "actual_qty": b.actual_qty,
            "unit_cost": b.unit_cost,
            "total_batch_cost": b.total_batch_cost,
            "manufacturing_date": str(b.manufacturing_date) if b.manufacturing_date else None,
            "expiry_date": str(b.expiry_date) if b.expiry_date else None,
            "status": b.status,
        }
        for b in batches
    ]


def _get_company_id(db: Session) -> int:
    from database.models import Company
    company = db.query(Company).first()
    return company.id if company else 1


# ─── Inventory Summary ────────────────────────────────────────────

@router.get("/inventory/summary")
async def inventory_summary(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Central ERP inventory summary - raw materials and finished goods."""
    materials = db.query(RawMaterial).filter(RawMaterial.is_active == True).all()
    total_rm_value = sum(m.current_stock * m.weighted_avg_cost for m in materials)
    low_stock_rm = [m for m in materials if m.current_stock <= m.minimum_reorder_level]

    products = db.query(Product).filter(Product.is_active == True).all()
    total_fg_value = sum(p.current_stock * p.unit_cost_cogs for p in products)
    low_stock_fg = [p for p in products if p.current_stock <= p.minimum_reorder_level]

    return {
        "raw_materials": {
            "count": len(materials),
            "total_value": round(total_rm_value, 2),
            "low_stock_count": len(low_stock_rm),
            "low_stock_items": [{"name": m.name, "stock": m.current_stock, "min": m.minimum_reorder_level} for m in low_stock_rm],
        },
        "finished_goods": {
            "count": len(products),
            "total_value": round(total_fg_value, 2),
            "low_stock_count": len(low_stock_fg),
            "low_stock_items": [{"name": p.name, "stock": p.current_stock, "min": p.minimum_reorder_level} for p in low_stock_fg],
        },
    }
