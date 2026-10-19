"""
FormulaBase Nexus - Demo Data Seeder
Seeds the database with realistic Myanmar OEM soap business data:
- Master Company: Formula Base OEM Services Myanmar
- Brand: SARA Natural Soap (Emerald Green)
- Brand: LMN Vitamin C Soap (Citrus Orange)
- Raw Materials, BOM Formulas, Production Batches, Customers, Invoices
"""
import logging
import random
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database.models import (
    Company, User, Brand, RawMaterial, RawMaterialCategory,
    Product, BOM, BOMIngredient, ProductionBatch, ProductionConsumption,
    Customer, Invoice, InvoiceItem, Supplier, Purchase, PurchaseItem,
    ExpenseCategory, Expense, ChartOfAccount,
    RawMaterialStockMovement, ProductStockMovement,
)
from core.security import get_password_hash
from modules.accounting.auto_accountant import AutoAccountantEngine, STANDARD_CHART_OF_ACCOUNTS

logger = logging.getLogger(__name__)


def seed_database(db: Session, force: bool = False) -> bool:
    """
    Seed the database with realistic demo data.
    Returns True if seeded, False if already seeded.
    """
    # Check if already seeded
    existing = db.query(Company).first()
    if existing and not force:
        logger.info("Database already seeded - skipping")
        return False

    logger.info("🌱 Starting database seed...")

    # ─────────────────────────────────────────────────────────────
    # 1. MASTER COMPANY
    # ─────────────────────────────────────────────────────────────
    company = Company(
        name="Formula Base OEM Services Myanmar",
        tagline="Premium OEM Soap & Skincare Manufacturer",
        phone="09-123-456-789",
        address="No. 42, Industrial Zone, Hlaing Thar Yar Township, Yangon, Myanmar",
        email="info@formulabase.mm",
        website="www.formulabase.mm",
        license_mode="PRO",
        currency="MMK",
        timezone="Asia/Yangon",
    )
    db.add(company)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 2. USERS
    # ─────────────────────────────────────────────────────────────
    owner = User(
        company_id=company.id,
        username="admin",
        full_name="Ko Kyaw Zin (Owner)",
        email="owner@formulabase.mm",
        password_hash=get_password_hash("admin123"),
        role="OWNER",
        is_active=True,
    )
    db.add(owner)

    accountant = User(
        company_id=company.id,
        username="accountant",
        full_name="Ma Hnin Wai (Accountant)",
        email="accountant@formulabase.mm",
        password_hash=get_password_hash("acc123"),
        role="ACCOUNTANT",
        is_active=True,
    )
    db.add(accountant)

    factory_mgr = User(
        company_id=company.id,
        username="factory",
        full_name="Ko Htet Aung (Factory Manager)",
        password_hash=get_password_hash("factory123"),
        role="FACTORY_MANAGER",
        is_active=True,
    )
    db.add(factory_mgr)

    cashier_sara = User(
        company_id=company.id,
        username="sara_cashier",
        full_name="Ma Su Su (SARA Cashier)",
        password_hash=get_password_hash("sara123"),
        role="BRAND_CASHIER",
        is_active=True,
    )
    db.add(cashier_sara)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 3. CHART OF ACCOUNTS
    # ─────────────────────────────────────────────────────────────
    accountant_engine = AutoAccountantEngine(db)
    for acct_def in STANDARD_CHART_OF_ACCOUNTS:
        acct = ChartOfAccount(
            company_id=company.id,
            account_code=acct_def["code"],
            account_name=acct_def["name"],
            account_type=acct_def["type"],
            normal_balance=acct_def["normal"],
            sort_order=acct_def.get("sort", 0),
            is_active=True,
        )
        db.add(acct)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 4. BRAND PROFILES
    # ─────────────────────────────────────────────────────────────
    sara = Brand(
        company_id=company.id,
        name="SARA",
        full_name="SARA Natural Soap",
        tagline="Pure. Natural. Radiant.",
        invoice_prefix="SARA-",
        phone="09-111-222-333",
        address="No. 42, Industrial Zone, Hlaing Thar Yar, Yangon",
        email="sara@formulabase.mm",
        # Emerald Green Theme
        theme_primary_color="#10B981",
        theme_gradient_start="#059669",
        theme_gradient_mid="#10B981",
        theme_gradient_end="#34D399",
        theme_surface_tint="#ECFDF5",
        theme_border_tint="#A7F3D0",
        theme_deep_text="#064E3B",
        commercial_tax_rate=5.0,
        default_price_tier="RETAIL",
        invoice_sequence=1,
        is_active=True,
        sort_order=1,
    )
    db.add(sara)

    lmn = Brand(
        company_id=company.id,
        name="LMN",
        full_name="LMN Vitamin C Soap",
        tagline="Bright. Fresh. Glowing.",
        invoice_prefix="LMN-",
        phone="09-444-555-666",
        address="No. 42, Industrial Zone, Hlaing Thar Yar, Yangon",
        email="lmn@formulabase.mm",
        # Citrus Orange Theme
        theme_primary_color="#F97316",
        theme_gradient_start="#EA580C",
        theme_gradient_mid="#F97316",
        theme_gradient_end="#FBBF24",
        theme_surface_tint="#FFF7ED",
        theme_border_tint="#FED7AA",
        theme_deep_text="#7C2D12",
        commercial_tax_rate=5.0,
        default_price_tier="RETAIL",
        invoice_sequence=1,
        is_active=True,
        sort_order=2,
    )
    db.add(lmn)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 5. RAW MATERIAL CATEGORIES
    # ─────────────────────────────────────────────────────────────
    cat_oils = RawMaterialCategory(company_id=company.id, name="Oils & Fats", color_hex="#F59E0B", icon="droplets", sort_order=1)
    cat_alkali = RawMaterialCategory(company_id=company.id, name="Alkali & Lye", color_hex="#EF4444", icon="flask-conical", sort_order=2)
    cat_actives = RawMaterialCategory(company_id=company.id, name="Active Ingredients", color_hex="#8B5CF6", icon="sparkles", sort_order=3)
    cat_fragrance = RawMaterialCategory(company_id=company.id, name="Fragrances & Botanicals", color_hex="#EC4899", icon="flower", sort_order=4)
    cat_packaging = RawMaterialCategory(company_id=company.id, name="Packaging Materials", color_hex="#6B7280", icon="box", sort_order=5)
    cat_additives = RawMaterialCategory(company_id=company.id, name="Additives & Preservatives", color_hex="#14B8A6", icon="test-tube", sort_order=6)

    for cat in [cat_oils, cat_alkali, cat_actives, cat_fragrance, cat_packaging, cat_additives]:
        db.add(cat)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 6. RAW MATERIALS (Central ERP - Shared)
    # ─────────────────────────────────────────────────────────────
    raw_materials_data = [
        # Oils & Fats
        dict(code="RM-OIL-001", name="Coconut Oil (Virgin)", cat=cat_oils.id, unit="kg",  cost=3500.0,  stock=200.0, min_stock=50.0,  supplier="Shan Coconut Co."),
        dict(code="RM-OIL-002", name="Palm Oil (RBD)",       cat=cat_oils.id, unit="kg",  cost=2800.0,  stock=150.0, min_stock=30.0,  supplier="Delta Palm Trading"),
        dict(code="RM-OIL-003", name="Olive Oil (Extra Virgin)", cat=cat_oils.id, unit="kg", cost=15000.0, stock=30.0, min_stock=10.0, supplier="Import Trading Co."),
        dict(code="RM-OIL-004", name="Castor Oil",           cat=cat_oils.id, unit="kg",  cost=8000.0,  stock=20.0,  min_stock=5.0,   supplier="Nay Pyi Taw Chem"),
        dict(code="RM-OIL-005", name="Shea Butter",          cat=cat_oils.id, unit="kg",  cost=25000.0, stock=15.0,  min_stock=5.0,   supplier="Import Trading Co."),
        # Alkali
        dict(code="RM-ALK-001", name="Sodium Hydroxide (NaOH / Lye)", cat=cat_alkali.id, unit="kg", cost=2500.0, stock=100.0, min_stock=20.0, supplier="Myanmar Chemical Supply"),
        dict(code="RM-ALK-002", name="Potassium Hydroxide (KOH)",     cat=cat_alkali.id, unit="kg", cost=4200.0, stock=20.0,  min_stock=5.0,  supplier="Myanmar Chemical Supply"),
        # Active Ingredients
        dict(code="RM-ACT-001", name="Vitamin C (L-Ascorbic Acid)", cat=cat_actives.id, unit="g",  cost=120.0,   stock=5000.0, min_stock=1000.0, supplier="Pharma Raw Co."),
        dict(code="RM-ACT-002", name="Niacinamide (B3)",            cat=cat_actives.id, unit="g",  cost=85.0,    stock=3000.0, min_stock=500.0,  supplier="Pharma Raw Co."),
        dict(code="RM-ACT-003", name="Kojic Acid",                  cat=cat_actives.id, unit="g",  cost=95.0,    stock=2000.0, min_stock=500.0,  supplier="Pharma Raw Co."),
        dict(code="RM-ACT-004", name="Activated Charcoal Powder",   cat=cat_actives.id, unit="g",  cost=45.0,    stock=8000.0, min_stock=2000.0, supplier="Natural Ingredients MM"),
        dict(code="RM-ACT-005", name="Turmeric Extract",            cat=cat_actives.id, unit="g",  cost=55.0,    stock=3000.0, min_stock=500.0,  supplier="Herbal Source MM"),
        # Fragrances
        dict(code="RM-FRG-001", name="Lavender Essential Oil",  cat=cat_fragrance.id, unit="ml", cost=180.0,  stock=2000.0, min_stock=500.0, supplier="Aroma Trading"),
        dict(code="RM-FRG-002", name="Lemon Fragrance Oil",     cat=cat_fragrance.id, unit="ml", cost=85.0,   stock=3000.0, min_stock=500.0, supplier="Aroma Trading"),
        dict(code="RM-FRG-003", name="Peppermint Essential Oil", cat=cat_fragrance.id, unit="ml", cost=220.0, stock=1000.0, min_stock=300.0, supplier="Aroma Trading"),
        # Packaging
        dict(code="PKG-BOX-001", name="SARA Soap Box (Green, 100g)", cat=cat_packaging.id, unit="pcs", cost=250.0, stock=2000.0, min_stock=500.0, supplier="Print & Pack Co.", is_pkg=True),
        dict(code="PKG-BOX-002", name="LMN Soap Box (Orange, 100g)", cat=cat_packaging.id, unit="pcs", cost=250.0, stock=2000.0, min_stock=500.0, supplier="Print & Pack Co.", is_pkg=True),
        dict(code="PKG-WRP-001", name="Shrink Wrap (per roll)",      cat=cat_packaging.id, unit="pcs", cost=15000.0, stock=10.0, min_stock=3.0, supplier="Wrap Supply Co.", is_pkg=True),
        dict(code="PKG-LBL-001", name="Holographic Sticker Labels",  cat=cat_packaging.id, unit="pcs", cost=80.0, stock=5000.0, min_stock=1000.0, supplier="Label Print Co.", is_pkg=True),
        # Additives
        dict(code="RM-ADD-001", name="EDTA (Chelating Agent)",    cat=cat_additives.id, unit="g",  cost=30.0,  stock=5000.0, min_stock=1000.0, supplier="Myanmar Chemical Supply"),
        dict(code="RM-ADD-002", name="Titanium Dioxide (TiO2)",   cat=cat_additives.id, unit="g",  cost=25.0,  stock=8000.0, min_stock=2000.0, supplier="Myanmar Chemical Supply"),
        dict(code="RM-ADD-003", name="Sodium Lactate",            cat=cat_additives.id, unit="ml", cost=40.0,  stock=3000.0, min_stock=500.0,  supplier="Pharma Raw Co."),
    ]

    rm_map = {}  # code -> RawMaterial object
    for r in raw_materials_data:
        rm = RawMaterial(
            company_id=company.id,
            category_id=r["cat"],
            item_code=r["code"],
            name=r["name"],
            unit=r["unit"],
            current_stock=r["stock"],
            weighted_avg_cost=r["cost"],
            last_purchase_price=r["cost"],
            minimum_reorder_level=r["min_stock"],
            is_packaging=r.get("is_pkg", False),
            default_supplier_name=r.get("supplier", ""),
            is_active=True,
        )
        db.add(rm)
        rm_map[r["code"]] = rm
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 7. FINISHED PRODUCTS
    # ─────────────────────────────────────────────────────────────
    # SARA Products
    sara_soap_100 = Product(
        brand_id=sara.id, sku="SARA-S100", name="SARA Natural Soap 100g",
        category="Soap", unit="pcs", weight_grams=100.0,
        current_stock=350.0, minimum_reorder_level=100.0,
        price_retail=3500.0, price_wholesale=2800.0,
        price_distributor=2500.0, price_vip=3000.0,
        is_active=True, sort_order=1,
    )
    sara_soap_200 = Product(
        brand_id=sara.id, sku="SARA-S200", name="SARA Natural Soap 200g (Gift Set)",
        category="Soap", unit="pcs", weight_grams=200.0,
        current_stock=120.0, minimum_reorder_level=50.0,
        price_retail=6500.0, price_wholesale=5500.0,
        price_distributor=4800.0, price_vip=6000.0,
        is_active=True, sort_order=2,
    )
    sara_serum = Product(
        brand_id=sara.id, sku="SARA-SR001", name="SARA Brightening Serum 30ml",
        category="Serum", unit="pcs", weight_grams=35.0,
        current_stock=80.0, minimum_reorder_level=30.0,
        price_retail=18500.0, price_wholesale=15000.0,
        price_distributor=13000.0, price_vip=17000.0,
        is_active=True, sort_order=3,
    )

    # LMN Products
    lmn_soap_100 = Product(
        brand_id=lmn.id, sku="LMN-S100", name="LMN Vitamin C Soap 100g",
        category="Soap", unit="pcs", weight_grams=100.0,
        current_stock=420.0, minimum_reorder_level=100.0,
        price_retail=4000.0, price_wholesale=3200.0,
        price_distributor=2800.0, price_vip=3500.0,
        is_active=True, sort_order=1,
    )
    lmn_soap_set = Product(
        brand_id=lmn.id, sku="LMN-SET03", name="LMN Vitamin C Soap Set (3 pcs)",
        category="Soap Set", unit="set", weight_grams=320.0,
        current_stock=95.0, minimum_reorder_level=30.0,
        price_retail=11000.0, price_wholesale=9000.0,
        price_distributor=8000.0, price_vip=10000.0,
        is_active=True, sort_order=2,
    )
    lmn_scrub = Product(
        brand_id=lmn.id, sku="LMN-SC001", name="LMN Vitamin C Facial Scrub 100g",
        category="Scrub", unit="pcs", weight_grams=100.0,
        current_stock=60.0, minimum_reorder_level=20.0,
        price_retail=12000.0, price_wholesale=9500.0,
        price_distributor=8500.0, price_vip=11000.0,
        is_active=True, sort_order=3,
    )

    for p in [sara_soap_100, sara_soap_200, sara_serum, lmn_soap_100, lmn_soap_set, lmn_scrub]:
        db.add(p)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 8. BOM / FORMULAS (per 100 bars batch)
    # ─────────────────────────────────────────────────────────────

    # SARA Natural Soap 100g BOM (Batch of 100 bars)
    sara_bom = BOM(
        product_id=sara_soap_100.id,
        batch_size=100.0,
        batch_size_unit="pcs",
        wastage_percent=3.0,
        labor_cost_per_batch=15000.0,
        overhead_cost_per_batch=5000.0,
        raw_material_cost_per_batch=155000.0,  # calculated below
        total_batch_cost=175000.0,
        unit_cost=1750.0,
        is_active=True,
    )
    db.add(sara_bom)
    db.flush()

    sara_bom_ingredients = [
        # (raw_material_code, qty_per_batch, unit)
        ("RM-OIL-001", 35.0, "kg"),   # Coconut Oil 35kg
        ("RM-OIL-002", 20.0, "kg"),   # Palm Oil 20kg
        ("RM-OIL-003", 5.0,  "kg"),   # Olive Oil 5kg
        ("RM-OIL-004", 2.0,  "kg"),   # Castor Oil 2kg
        ("RM-ALK-001", 10.5, "kg"),   # NaOH (lye)
        ("RM-ACT-004", 500.0,"g"),    # Activated Charcoal 500g
        ("RM-ACT-005", 300.0,"g"),    # Turmeric Extract 300g
        ("RM-FRG-001", 800.0,"ml"),   # Lavender EO 800ml
        ("RM-ADD-001", 100.0,"g"),    # EDTA 100g
        ("RM-ADD-002", 200.0,"g"),    # TiO2 200g
        ("PKG-BOX-001",100.0,"pcs"),  # SARA Boxes
        ("PKG-LBL-001",100.0,"pcs"),  # Labels
    ]

    for i, (rm_code, qty, unit) in enumerate(sara_bom_ingredients):
        rm_obj = rm_map.get(rm_code)
        if rm_obj:
            db.add(BOMIngredient(
                bom_id=sara_bom.id,
                raw_material_id=rm_obj.id,
                quantity_per_batch=qty,
                unit=unit,
                sort_order=i,
            ))

    # LMN Vitamin C Soap 100g BOM (Batch of 100 bars)
    lmn_bom = BOM(
        product_id=lmn_soap_100.id,
        batch_size=100.0,
        batch_size_unit="pcs",
        wastage_percent=3.0,
        labor_cost_per_batch=15000.0,
        overhead_cost_per_batch=5000.0,
        raw_material_cost_per_batch=185000.0,
        total_batch_cost=205000.0,
        unit_cost=2050.0,
        is_active=True,
    )
    db.add(lmn_bom)
    db.flush()

    lmn_bom_ingredients = [
        ("RM-OIL-001", 30.0, "kg"),   # Coconut Oil 30kg
        ("RM-OIL-002", 20.0, "kg"),   # Palm Oil 20kg
        ("RM-OIL-005", 3.0,  "kg"),   # Shea Butter 3kg
        ("RM-OIL-004", 2.0,  "kg"),   # Castor Oil 2kg
        ("RM-ALK-001", 9.8,  "kg"),   # NaOH
        ("RM-ACT-001", 2000.0,"g"),   # Vitamin C Powder 2000g
        ("RM-ACT-002", 500.0, "g"),   # Niacinamide 500g
        ("RM-ACT-003", 300.0, "g"),   # Kojic Acid 300g
        ("RM-FRG-002", 600.0, "ml"),  # Lemon Fragrance Oil
        ("RM-ADD-001", 100.0, "g"),   # EDTA
        ("RM-ADD-002", 150.0, "g"),   # TiO2
        ("PKG-BOX-002", 100.0,"pcs"), # LMN Boxes
        ("PKG-LBL-001", 100.0,"pcs"), # Labels
    ]

    for i, (rm_code, qty, unit) in enumerate(lmn_bom_ingredients):
        rm_obj = rm_map.get(rm_code)
        if rm_obj:
            db.add(BOMIngredient(
                bom_id=lmn_bom.id,
                raw_material_id=rm_obj.id,
                quantity_per_batch=qty,
                unit=unit,
                sort_order=i,
            ))

    db.flush()

    # Update product unit costs
    sara_soap_100.unit_cost_cogs = 1750.0
    lmn_soap_100.unit_cost_cogs = 2050.0

    # ─────────────────────────────────────────────────────────────
    # 9. SUPPLIERS
    # ─────────────────────────────────────────────────────────────
    suppliers_data = [
        dict(name="Shan Coconut Co., Ltd.", phone="09-222-333-444", address="Pathein, Ayeyarwady Region"),
        dict(name="Myanmar Chemical Supply", phone="09-333-444-555", address="Industrial Zone, Yangon"),
        dict(name="Pharma Raw Materials Co.", phone="09-444-555-666", address="Bahan, Yangon"),
        dict(name="Aroma Trading Myanmar", phone="09-555-666-777", address="Kyauktada, Yangon"),
        dict(name="Print & Pack Co., Ltd.", phone="09-666-777-888", address="Hlaing, Yangon"),
    ]
    supplier_objs = []
    for s in suppliers_data:
        sup = Supplier(company_id=company.id, **s, is_active=True)
        db.add(sup)
        supplier_objs.append(sup)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 10. CUSTOMERS
    # ─────────────────────────────────────────────────────────────
    sara_customers = [
        dict(name="Ma Ei Ei Phyu", phone="09-711-222-333", address="Kamaryut, Yangon", tier="RETAIL",      credit=0.0),
        dict(name="Ko Zaw Myo",    phone="09-722-333-444", address="Sanchaung, Yangon", tier="WHOLESALE",   credit=0.0),
        dict(name="Daw Khin Lay",  phone="09-733-444-555", address="Bahan, Yangon",     tier="RETAIL",      credit=150000.0),
        dict(name="Beauty Corner Store", phone="09-744-555-666", address="Hledan, Yangon", tier="WHOLESALE", credit=0.0),
        dict(name="Shwe Myanmar Trading", phone="09-755-666-777", address="Dagon, Yangon", tier="DISTRIBUTOR", credit=500000.0),
        dict(name="Golden Skin Shop",    phone="09-766-777-888", address="Pyay Road, Yangon", tier="WHOLESALE", credit=0.0),
        dict(name="Ma Nwe Nwe",         phone="09-777-888-999", address="Thingangyun, Yangon", tier="RETAIL", credit=0.0),
        dict(name="Sky Beauty Myanmar",  phone="09-788-999-000", address="Insein, Yangon", tier="DISTRIBUTOR", credit=250000.0),
    ]
    sara_cust_objs = []
    for c_data in sara_customers:
        cust = Customer(
            brand_id=sara.id,
            name=c_data["name"], phone=c_data["phone"],
            address=c_data["address"],
            price_tier=c_data["tier"],
            outstanding_credit=c_data["credit"],
            total_purchases=random.uniform(100000, 2000000),
            is_active=True,
        )
        db.add(cust)
        sara_cust_objs.append(cust)

    lmn_customers = [
        dict(name="Ko Aung Kyaw",    phone="09-811-222-333", address="Hlaing, Yangon",      tier="RETAIL",      credit=0.0),
        dict(name="Ma Mya Mya",      phone="09-822-333-444", address="Kyauktada, Yangon",   tier="RETAIL",      credit=80000.0),
        dict(name="Vita Beauty Shop",phone="09-833-444-555", address="Lanmadaw, Yangon",    tier="WHOLESALE",   credit=0.0),
        dict(name="Lemon Fresh Store",phone="09-844-555-666", address="Tamwe, Yangon",      tier="WHOLESALE",   credit=0.0),
        dict(name="Delta Distribution",phone="09-855-666-777", address="Mingalar Taung Nyunt", tier="DISTRIBUTOR", credit=380000.0),
        dict(name="Citymart Beauty",  phone="09-866-777-888", address="Shwedagon Pagoda Rd", tier="WHOLESALE",   credit=0.0),
    ]
    lmn_cust_objs = []
    for c_data in lmn_customers:
        cust = Customer(
            brand_id=lmn.id,
            name=c_data["name"], phone=c_data["phone"],
            address=c_data["address"],
            price_tier=c_data["tier"],
            outstanding_credit=c_data["credit"],
            total_purchases=random.uniform(80000, 1500000),
            is_active=True,
        )
        db.add(cust)
        lmn_cust_objs.append(cust)
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 11. EXPENSE CATEGORIES
    # ─────────────────────────────────────────────────────────────
    exp_cats = [
        dict(name="Rent & Utilities", code="6100", color="#EF4444"),
        dict(name="Salaries & Wages", code="6102", color="#8B5CF6"),
        dict(name="Marketing & Ads",  code="6103", color="#3B82F6"),
        dict(name="Transport",        code="6104", color="#F59E0B"),
        dict(name="Raw Material Wastage",code="6002",color="#6B7280"),
        dict(name="Miscellaneous",    code="6900", color="#14B8A6"),
    ]
    exp_cat_objs = {}
    for ec in exp_cats:
        eco = ExpenseCategory(
            company_id=company.id,
            name=ec["name"], account_code=ec["code"], color_hex=ec["color"]
        )
        db.add(eco)
        exp_cat_objs[ec["code"]] = eco
    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 12. SAMPLE INVOICES (last 3 months)
    # ─────────────────────────────────────────────────────────────
    today = date.today()

    def make_invoice(brand, inv_num, customer, products_qtys, payment, inv_date, discount_pct=0.0):
        """Helper to create a complete invoice with items."""
        subtotal = 0.0
        total_cogs = 0.0
        items = []

        for prod, qty, tier in products_qtys:
            price = {
                "RETAIL": prod.price_retail,
                "WHOLESALE": prod.price_wholesale,
                "DISTRIBUTOR": prod.price_distributor,
                "VIP": prod.price_vip,
            }.get(tier, prod.price_retail)

            line_total = price * qty
            line_cogs = prod.unit_cost_cogs * qty
            subtotal += line_total
            total_cogs += line_cogs
            items.append((prod, qty, price, line_total, line_cogs))

        disc_amount = subtotal * (discount_pct / 100.0)
        ct = (subtotal - disc_amount) * (brand.commercial_tax_rate / 100.0)
        grand_total = subtotal - disc_amount + ct

        inv = Invoice(
            brand_id=brand.id,
            customer_id=customer.id if customer else None,
            invoice_number=inv_num,
            invoice_date=inv_date,
            subtotal=round(subtotal, 2),
            discount_percent=discount_pct,
            discount_amount=round(disc_amount, 2),
            commercial_tax_percent=brand.commercial_tax_rate,
            commercial_tax_amount=round(ct, 2),
            grand_total=round(grand_total, 2),
            payment_method=payment,
            paid_amount=round(grand_total, 2) if payment != "CREDIT" else 0.0,
            credit_amount=round(grand_total, 2) if payment == "CREDIT" else 0.0,
            total_cogs=round(total_cogs, 2),
            status="CONFIRMED",
            created_by_user_id=owner.id,
        )
        db.add(inv)
        db.flush()

        for prod, qty, price, line_total, line_cogs in items:
            db.add(InvoiceItem(
                invoice_id=inv.id,
                product_id=prod.id,
                product_name_snapshot=prod.name,
                qty=qty,
                unit_price=price,
                line_total=round(line_total, 2),
                unit_cost_at_sale=prod.unit_cost_cogs,
                line_cogs=round(line_cogs, 2),
            ))
            # Update product stock
            prod.current_stock = max(0, prod.current_stock - qty)

        # Update customer credit
        if customer and payment == "CREDIT":
            customer.outstanding_credit += grand_total
        if customer:
            customer.total_purchases += grand_total

        return inv

    # Generate 30 sample invoices over the past 90 days
    sara_invoices_data = [
        # (customer_index, [(product, qty, tier)], payment, days_ago, discount%)
        (0, [(sara_soap_100, 5,  "RETAIL")],      "CASH",   1, 0),
        (1, [(sara_soap_100, 50, "WHOLESALE")],   "KPAY",   3, 5),
        (2, [(sara_soap_100, 3,  "RETAIL"),
             (sara_serum,    2,  "RETAIL")],       "CASH",   5, 0),
        (3, [(sara_soap_100, 30, "WHOLESALE"),
             (sara_soap_200, 10, "WHOLESALE")],    "BANK_TRANSFER", 8, 3),
        (4, [(sara_soap_100, 200,"DISTRIBUTOR"),
             (sara_soap_200, 50, "DISTRIBUTOR")],  "CREDIT", 12, 8),
        (5, [(sara_soap_100, 20, "WHOLESALE")],   "KPAY",   15, 0),
        (0, [(sara_serum,    5,  "RETAIL")],       "CASH",   18, 0),
        (1, [(sara_soap_100, 80, "WHOLESALE")],   "WAVEPAY",22, 5),
        (6, [(sara_soap_100, 10, "RETAIL")],       "CASH",   25, 0),
        (7, [(sara_soap_100, 150,"DISTRIBUTOR"),
             (sara_serum,    20, "DISTRIBUTOR")],  "CREDIT", 30, 10),
        (2, [(sara_soap_200, 5,  "RETAIL")],       "KPAY",   35, 0),
        (3, [(sara_soap_100, 25, "WHOLESALE")],    "CASH",   40, 0),
        (4, [(sara_soap_100, 300,"DISTRIBUTOR")],  "BANK_TRANSFER", 45, 8),
        (5, [(sara_soap_100, 15, "WHOLESALE"),
             (sara_soap_200, 8,  "WHOLESALE")],    "CASH",   50, 2),
        (0, [(sara_soap_100, 8,  "RETAIL")],       "CASH",   55, 0),
    ]

    sara.invoice_sequence = 1
    for idx, (cust_idx, prods, payment, days_ago, disc) in enumerate(sara_invoices_data):
        inv_date = today - timedelta(days=days_ago)
        inv_num = f"SARA-{sara.invoice_sequence:05d}"
        sara.invoice_sequence += 1
        cust = sara_cust_objs[cust_idx % len(sara_cust_objs)]
        make_invoice(sara, inv_num, cust, prods, payment, inv_date, disc)

    lmn_invoices_data = [
        (0, [(lmn_soap_100, 8,   "RETAIL")],      "CASH",   2, 0),
        (1, [(lmn_soap_100, 5,   "RETAIL"),
             (lmn_scrub,    3,   "RETAIL")],       "KPAY",   4, 0),
        (2, [(lmn_soap_100, 40,  "WHOLESALE"),
             (lmn_soap_set, 10,  "WHOLESALE")],    "BANK_TRANSFER", 7, 5),
        (3, [(lmn_soap_100, 60,  "WHOLESALE")],    "WAVEPAY",11, 3),
        (4, [(lmn_soap_100, 250, "DISTRIBUTOR"),
             (lmn_scrub,    30,  "DISTRIBUTOR")],  "CREDIT", 14, 10),
        (5, [(lmn_soap_100, 20,  "WHOLESALE"),
             (lmn_soap_set, 5,   "WHOLESALE")],    "KPAY",   20, 0),
        (0, [(lmn_scrub,    4,   "RETAIL")],       "CASH",   24, 0),
        (1, [(lmn_soap_100, 100, "WHOLESALE")],    "CASH",   28, 5),
        (2, [(lmn_soap_100, 15,  "WHOLESALE")],    "KPAY",   33, 0),
        (3, [(lmn_soap_100, 180, "DISTRIBUTOR"),
             (lmn_soap_set, 40,  "DISTRIBUTOR")],  "CREDIT", 38, 10),
        (0, [(lmn_soap_100, 12,  "RETAIL")],       "CASH",   42, 0),
        (4, [(lmn_soap_100, 300, "DISTRIBUTOR")],  "BANK_TRANSFER", 48, 8),
        (5, [(lmn_soap_set, 15,  "WHOLESALE")],    "WAVEPAY",53, 0),
    ]

    lmn.invoice_sequence = 1
    for idx, (cust_idx, prods, payment, days_ago, disc) in enumerate(lmn_invoices_data):
        inv_date = today - timedelta(days=days_ago)
        inv_num = f"LMN-{lmn.invoice_sequence:05d}"
        lmn.invoice_sequence += 1
        cust = lmn_cust_objs[cust_idx % len(lmn_cust_objs)]
        make_invoice(lmn, inv_num, cust, prods, payment, inv_date, disc)

    db.flush()

    # ─────────────────────────────────────────────────────────────
    # 13. SAMPLE EXPENSES
    # ─────────────────────────────────────────────────────────────
    expenses_data = [
        dict(cat_code="6100", desc="Factory Rent - October 2026",     amount=800000.0,  days_ago=30, payment="CASH"),
        dict(cat_code="6102", desc="Salaries - Factory Staff (5 pax)",amount=1500000.0, days_ago=30, payment="BANK_TRANSFER"),
        dict(cat_code="6101", desc="Electricity Bill - October",       amount=185000.0,  days_ago=5,  payment="BANK_TRANSFER"),
        dict(cat_code="6103", desc="Facebook Ads - SARA Brand",        amount=250000.0,  days_ago=10, payment="KPAY"),
        dict(cat_code="6103", desc="Facebook Ads - LMN Brand",         amount=200000.0,  days_ago=10, payment="KPAY"),
        dict(cat_code="6104", desc="Delivery Van Fuel - October",      amount=120000.0,  days_ago=3,  payment="CASH"),
        dict(cat_code="6100", desc="Factory Rent - September 2026",    amount=800000.0,  days_ago=60, payment="CASH"),
        dict(cat_code="6102", desc="Salaries - September",             amount=1500000.0, days_ago=60, payment="BANK_TRANSFER"),
        dict(cat_code="6900", desc="Office Supplies & Misc",           amount=45000.0,   days_ago=15, payment="CASH"),
    ]

    for e_data in expenses_data:
        e_date = today - timedelta(days=e_data["days_ago"])
        exp = Expense(
            company_id=company.id,
            category_id=exp_cat_objs.get(e_data["cat_code"]).id if exp_cat_objs.get(e_data["cat_code"]) else None,
            description=e_data["desc"],
            amount=e_data["amount"],
            expense_date=e_date,
            payment_method=e_data["payment"],
            created_by_user_id=owner.id,
        )
        db.add(exp)

    db.commit()
    logger.info("✅ Database seeding completed successfully!")
    logger.info(f"  Company: {company.name}")
    logger.info(f"  Brands: SARA (id={sara.id}), LMN (id={lmn.id})")
    logger.info(f"  Raw Materials: {len(raw_materials_data)}")
    logger.info(f"  Products: SARA x3, LMN x3")
    logger.info(f"  Customers: SARA x{len(sara_customers)}, LMN x{len(lmn_customers)}")
    logger.info(f"  Sample Invoices: SARA x{len(sara_invoices_data)}, LMN x{len(lmn_invoices_data)}")
    logger.info(f"  Expenses: {len(expenses_data)}")
    return True
