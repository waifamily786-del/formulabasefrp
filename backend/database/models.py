"""
FormulaBase Nexus - Complete SQLAlchemy Models
Unified Formula ERP + Isolated Multi-Brand POS
All tables for: Auth, Brands, Raw Materials, BOM, Production, POS, PDF Templates, Accounting
"""
import json
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, Date,
    ForeignKey, Enum, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.sql import func
import enum

from .db import Base


# ─────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ACCOUNTANT = "ACCOUNTANT"
    FACTORY_MANAGER = "FACTORY_MANAGER"
    BRAND_CASHIER = "BRAND_CASHIER"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    KPAY = "KPAY"
    WAVEPAY = "WAVEPAY"
    BANK_TRANSFER = "BANK_TRANSFER"
    CREDIT = "CREDIT"
    PARTIAL = "PARTIAL"


class PriceTier(str, enum.Enum):
    RETAIL = "RETAIL"
    WHOLESALE = "WHOLESALE"
    DISTRIBUTOR = "DISTRIBUTOR"
    VIP = "VIP"
    CUSTOM_OEM = "CUSTOM_OEM"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PRINTED = "PRINTED"
    CANCELLED = "CANCELLED"


class JournalEntryType(str, enum.Enum):
    SALES = "SALES"
    PURCHASE = "PURCHASE"
    PRODUCTION = "PRODUCTION"
    EXPENSE = "EXPENSE"
    PAYMENT = "PAYMENT"
    ADJUSTMENT = "ADJUSTMENT"


class StockMovementType(str, enum.Enum):
    PURCHASE_IN = "PURCHASE_IN"
    PRODUCTION_CONSUMED = "PRODUCTION_CONSUMED"
    PRODUCTION_OUTPUT = "PRODUCTION_OUTPUT"
    SALES_OUT = "SALES_OUT"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"


class UnitOfMeasure(str, enum.Enum):
    KG = "kg"
    G = "g"
    L = "L"
    ML = "ml"
    PCS = "pcs"
    BOX = "box"
    BOTTLE = "bottle"


# ─────────────────────────────────────────────────────────────────
# 1. MASTER COMPANY & USER AUTH
# ─────────────────────────────────────────────────────────────────

class Company(Base):
    """Master company / tenant."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, default="Formula Base OEM Services Myanmar")
    tagline = Column(String(300))
    phone = Column(String(50))
    address = Column(Text)
    email = Column(String(100))
    website = Column(String(200))
    logo_path = Column(String(500))
    license_key = Column(String(64), unique=True)
    license_mode = Column(String(20), default="TRIAL")  # TRIAL | PRO | ENTERPRISE
    hardware_id = Column(String(64))
    invoice_count = Column(Integer, default=0)
    currency = Column(String(10), default="MMK")
    timezone = Column(String(50), default="Asia/Yangon")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="company")
    brands = relationship("Brand", back_populates="company")
    raw_materials = relationship("RawMaterial", back_populates="company")
    chart_of_accounts = relationship("ChartOfAccount", back_populates="company")


class User(Base):
    """System users with role-based access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150))
    email = Column(String(100))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default=UserRole.BRAND_CASHIER)
    is_active = Column(Boolean, default=True)
    # Brand access: which brand IDs this user can access (null = all for OWNER)
    allowed_brand_ids = Column(JSON, default=list)
    pin_hash = Column(String(255))  # Quick PIN for brand switching
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    company = relationship("Company", back_populates="users")
    sessions = relationship("UserSession", back_populates="user")


class UserSession(Base):
    """Track user login sessions."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    active_brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    token_jti = Column(String(64), unique=True)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)

    user = relationship("User", back_populates="sessions")


# ─────────────────────────────────────────────────────────────────
# 2. MULTI-BRAND PROFILES
# ─────────────────────────────────────────────────────────────────

class Brand(Base):
    """Isolated Brand Profiles (SARA, LMN, etc.) under a Master Company."""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)  # "SARA"
    full_name = Column(String(200))  # "SARA Natural Soap"
    tagline = Column(String(300))
    invoice_prefix = Column(String(20), default="INV-")  # "SARA-INV-"
    phone = Column(String(50))
    address = Column(Text)
    email = Column(String(100))
    logo_path = Column(String(500))

    # Two-Tone Gradient Theme
    theme_primary_color = Column(String(20), default="#10B981")  # Emerald for SARA
    theme_gradient_start = Column(String(20), default="#059669")
    theme_gradient_mid = Column(String(20), default="#10B981")
    theme_gradient_end = Column(String(20), default="#34D399")
    theme_surface_tint = Column(String(20), default="#ECFDF5")
    theme_border_tint = Column(String(20), default="#A7F3D0")
    theme_deep_text = Column(String(20), default="#064E3B")

    # Tax settings
    commercial_tax_rate = Column(Float, default=0.0)  # % CT
    default_price_tier = Column(String(20), default=PriceTier.RETAIL)

    # PDF Invoice Template
    invoice_template_path = Column(String(500))  # Path to uploaded PDF
    invoice_template_mapping = Column(JSON)  # Auto-detected coordinate mapping JSON
    template_calibrated = Column(Boolean, default=False)

    invoice_sequence = Column(Integer, default=1)  # Auto-increment invoice number
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="brands")
    products = relationship("Product", back_populates="brand")
    customers = relationship("Customer", back_populates="brand")
    invoices = relationship("Invoice", back_populates="brand")
    production_batches = relationship("ProductionBatch", back_populates="brand")

    def next_invoice_number(self) -> str:
        num = f"{self.invoice_prefix}{self.invoice_sequence:05d}"
        return num


# ─────────────────────────────────────────────────────────────────
# 3. CENTRAL ERP - RAW MATERIALS & PACKAGING
# ─────────────────────────────────────────────────────────────────

class RawMaterialCategory(Base):
    """Categories for raw materials."""
    __tablename__ = "raw_material_categories"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)  # Oils, Alkali, Active Ingredients, Fragrances, Packaging
    color_hex = Column(String(10), default="#6B7280")
    icon = Column(String(50), default="box")
    sort_order = Column(Integer, default=0)

    raw_materials = relationship("RawMaterial", back_populates="category")


class RawMaterial(Base):
    """Central ERP raw materials & packaging inventory (shared across all brands)."""
    __tablename__ = "raw_materials"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("raw_material_categories.id"), nullable=True)
    item_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    unit = Column(String(20), default=UnitOfMeasure.KG)
    is_packaging = Column(Boolean, default=False)  # True = packaging material

    # Inventory
    current_stock = Column(Float, default=0.0)
    minimum_reorder_level = Column(Float, default=10.0)
    maximum_stock_level = Column(Float, default=1000.0)

    # Costing (Weighted Average Cost)
    weighted_avg_cost = Column(Float, default=0.0)  # Cost per unit (MMK)
    last_purchase_price = Column(Float, default=0.0)

    # Supplier info
    default_supplier_name = Column(String(200))
    default_supplier_phone = Column(String(50))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="raw_materials")
    category = relationship("RawMaterialCategory", back_populates="raw_materials")
    bom_ingredients = relationship("BOMIngredient", back_populates="raw_material")
    purchase_items = relationship("PurchaseItem", back_populates="raw_material")
    stock_movements = relationship("RawMaterialStockMovement", back_populates="raw_material")
    batches = relationship("RawMaterialBatch", back_populates="raw_material")


class RawMaterialBatch(Base):
    """Batch-level tracking for raw materials (for FEFO/FIFO)."""
    __tablename__ = "raw_material_batches"

    id = Column(Integer, primary_key=True, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    batch_number = Column(String(100))
    supplier_name = Column(String(200))
    quantity_received = Column(Float, nullable=False)
    quantity_remaining = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    manufacturing_date = Column(Date)
    expiry_date = Column(Date)
    received_date = Column(Date, default=date.today)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    raw_material = relationship("RawMaterial", back_populates="batches")


class RawMaterialStockMovement(Base):
    """Audit trail of all raw material stock movements."""
    __tablename__ = "raw_material_stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    movement_type = Column(String(30), nullable=False)
    quantity = Column(Float, nullable=False)  # Positive = in, Negative = out
    unit_cost = Column(Float, default=0.0)
    balance_after = Column(Float, nullable=False)
    reference_type = Column(String(50))  # "PURCHASE", "PRODUCTION", "ADJUSTMENT"
    reference_id = Column(Integer)
    notes = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    raw_material = relationship("RawMaterial", back_populates="stock_movements")


# ─────────────────────────────────────────────────────────────────
# 4. RAW MATERIAL PURCHASES
# ─────────────────────────────────────────────────────────────────

class Supplier(Base):
    """Supplier/vendor master list."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    email = Column(String(100))
    outstanding_payable = Column(Float, default=0.0)  # AP balance
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    purchases = relationship("Purchase", back_populates="supplier")


class Purchase(Base):
    """Raw material purchase orders."""
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_number = Column(String(50), unique=True)
    purchase_date = Column(Date, default=date.today)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    payment_method = Column(String(20), default="CASH")
    is_credit = Column(Boolean, default=False)
    due_date = Column(Date)
    notes = Column(Text)
    status = Column(String(20), default="RECEIVED")  # DRAFT | RECEIVED | CANCELLED
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")
    journal_entry = relationship("JournalEntry", back_populates="purchase", uselist=False)


class PurchaseItem(Base):
    """Individual line items in a purchase order."""
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    batch_number = Column(String(100))
    expiry_date = Column(Date)

    purchase = relationship("Purchase", back_populates="items")
    raw_material = relationship("RawMaterial", back_populates="purchase_items")


# ─────────────────────────────────────────────────────────────────
# 5. FORMULA / BOM ENGINE
# ─────────────────────────────────────────────────────────────────

class Product(Base):
    """Brand-isolated finished goods catalog."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    sku = Column(String(50))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # Soap, Vitamin, etc.
    unit = Column(String(20), default=UnitOfMeasure.PCS)
    weight_grams = Column(Float)  # Net weight per piece in grams

    # Current inventory
    current_stock = Column(Float, default=0.0)
    minimum_reorder_level = Column(Float, default=50.0)

    # Costing (auto-calculated from BOM)
    unit_cost_cogs = Column(Float, default=0.0)  # Cost per piece from BOM

    # Pricing tiers (MMK)
    price_retail = Column(Float, nullable=False, default=0.0)
    price_wholesale = Column(Float, default=0.0)
    price_distributor = Column(Float, default=0.0)
    price_vip = Column(Float, default=0.0)
    price_custom_oem = Column(Float, default=0.0)

    image_path = Column(String(500))
    barcode = Column(String(100))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    brand = relationship("Brand", back_populates="products")
    bom = relationship("BOM", back_populates="product", uselist=False)
    invoice_items = relationship("InvoiceItem", back_populates="product")
    stock_movements = relationship("ProductStockMovement", back_populates="product")


class BOM(Base):
    """Bill of Materials (Formula/Recipe) for each finished product."""
    __tablename__ = "boms"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    batch_size = Column(Float, nullable=False)  # e.g., 100 (pieces per batch)
    batch_size_unit = Column(String(20), default="pcs")
    wastage_percent = Column(Float, default=2.0)  # % raw material wastage
    labor_cost_per_batch = Column(Float, default=0.0)
    overhead_cost_per_batch = Column(Float, default=0.0)

    # Auto-calculated fields (updated when ingredients change)
    raw_material_cost_per_batch = Column(Float, default=0.0)
    total_batch_cost = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)  # Cost per finished piece

    notes = Column(Text)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="bom")
    ingredients = relationship("BOMIngredient", back_populates="bom", cascade="all, delete-orphan")


class BOMIngredient(Base):
    """Individual raw material ingredient in a BOM recipe."""
    __tablename__ = "bom_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    quantity_per_batch = Column(Float, nullable=False)  # Amount used per full batch
    unit = Column(String(20))
    notes = Column(Text)
    sort_order = Column(Integer, default=0)

    bom = relationship("BOM", back_populates="ingredients")
    raw_material = relationship("RawMaterial", back_populates="bom_ingredients")


# ─────────────────────────────────────────────────────────────────
# 6. PRODUCTION BATCHES
# ─────────────────────────────────────────────────────────────────

class ProductionBatch(Base):
    """Batch production execution records."""
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    batch_number = Column(String(100), unique=True, nullable=False)
    batch_multiplier = Column(Float, nullable=False, default=1.0)  # How many BOM batches
    planned_qty = Column(Float, nullable=False)
    actual_qty = Column(Float)  # Can differ from planned due to wastage
    manufacturing_date = Column(Date, default=date.today)
    expiry_date = Column(Date)

    # Costing
    raw_material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    total_batch_cost = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)  # Actual cost per piece this batch

    status = Column(String(20), default="PLANNED")  # PLANNED | IN_PROGRESS | COMPLETED | CANCELLED
    notes = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)

    brand = relationship("Brand", back_populates="production_batches")
    consumption_records = relationship("ProductionConsumption", back_populates="batch")
    journal_entry = relationship("JournalEntry", back_populates="production_batch", uselist=False)


class ProductionConsumption(Base):
    """Records of raw materials consumed during production."""
    __tablename__ = "production_consumptions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    planned_qty = Column(Float, nullable=False)
    actual_qty = Column(Float, nullable=False)
    unit_cost_at_time = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)

    batch = relationship("ProductionBatch", back_populates="consumption_records")


class ProductStockMovement(Base):
    """Audit trail for finished goods inventory."""
    __tablename__ = "product_stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String(30), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0)
    balance_after = Column(Float, nullable=False)
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    notes = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    product = relationship("Product", back_populates="stock_movements")


# ─────────────────────────────────────────────────────────────────
# 7. CUSTOMERS & POS INVOICES
# ─────────────────────────────────────────────────────────────────

class Customer(Base):
    """Brand-isolated customer database."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    email = Column(String(100))
    price_tier = Column(String(20), default=PriceTier.RETAIL)
    credit_limit = Column(Float, default=0.0)
    outstanding_credit = Column(Float, default=0.0)  # AR balance (money owed to us)
    total_purchases = Column(Float, default=0.0)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    brand = relationship("Brand", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")


class Invoice(Base):
    """POS Sales Invoice - fully isolated per brand."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    invoice_date = Column(Date, default=date.today)
    due_date = Column(Date)

    # Financials
    subtotal = Column(Float, nullable=False, default=0.0)
    discount_percent = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    commercial_tax_percent = Column(Float, default=0.0)
    commercial_tax_amount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    grand_total = Column(Float, nullable=False, default=0.0)

    # Payment
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.CASH)
    paid_amount = Column(Float, default=0.0)
    credit_amount = Column(Float, default=0.0)  # Amount on account
    change_amount = Column(Float, default=0.0)

    # Status
    status = Column(String(20), default=InvoiceStatus.CONFIRMED)

    # PDF
    generated_pdf_path = Column(String(500))
    remarks = Column(Text)
    delivery_address = Column(Text)

    # Accounting: total COGS for this invoice (auto-calculated)
    total_cogs = Column(Float, default=0.0)

    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    brand = relationship("Brand", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    journal_entry = relationship("JournalEntry", back_populates="invoice", uselist=False)


class InvoiceItem(Base):
    """Line items in a sales invoice."""
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name_snapshot = Column(String(200))  # Snapshot at time of sale
    qty = Column(Float, nullable=False)
    foc_qty = Column(Float, default=0.0)  # Free of charge quantity
    unit_price = Column(Float, nullable=False)
    item_discount_percent = Column(Float, default=0.0)
    item_discount_amount = Column(Float, default=0.0)
    line_total = Column(Float, nullable=False)
    unit_cost_at_sale = Column(Float, default=0.0)  # COGS per unit at time of sale
    line_cogs = Column(Float, default=0.0)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")


# ─────────────────────────────────────────────────────────────────
# 8. EXPENSES
# ─────────────────────────────────────────────────────────────────

class ExpenseCategory(Base):
    """Expense categories (Rent, Salaries, Utilities, Marketing, etc.)."""
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)
    account_code = Column(String(20))  # Links to Chart of Accounts
    color_hex = Column(String(10), default="#6B7280")
    sort_order = Column(Integer, default=0)

    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    """General expense records."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)  # Null = company-wide
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)
    expense_date = Column(Date, default=date.today)
    payment_method = Column(String(20), default="CASH")
    receipt_path = Column(String(500))
    notes = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    category = relationship("ExpenseCategory", back_populates="expenses")
    journal_entry = relationship("JournalEntry", back_populates="expense", uselist=False)


# ─────────────────────────────────────────────────────────────────
# 9. AUTO-ACCOUNTANT ENGINE - CHART OF ACCOUNTS & DOUBLE-ENTRY
# ─────────────────────────────────────────────────────────────────

class ChartOfAccount(Base):
    """Standard Chart of Accounts for the company."""
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    account_code = Column(String(20), nullable=False)
    account_name = Column(String(200), nullable=False)
    account_type = Column(String(30), nullable=False)  # ASSET | LIABILITY | EQUITY | REVENUE | EXPENSE
    parent_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    normal_balance = Column(String(10), nullable=False)  # DEBIT | CREDIT
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    description = Column(Text)

    company = relationship("Company", back_populates="chart_of_accounts")
    debit_journal_lines = relationship(
        "JournalLine", foreign_keys="JournalLine.debit_account_id", back_populates="debit_account"
    )
    credit_journal_lines = relationship(
        "JournalLine", foreign_keys="JournalLine.credit_account_id", back_populates="credit_account"
    )

    __table_args__ = (
        UniqueConstraint("company_id", "account_code", name="uq_company_account_code"),
    )


class JournalEntry(Base):
    """Auto-generated double-entry journal header."""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    entry_number = Column(String(50), unique=True, nullable=False)
    entry_type = Column(String(30), nullable=False)  # SALES | PURCHASE | PRODUCTION | EXPENSE
    entry_date = Column(Date, default=date.today)
    description = Column(String(500))
    total_debit = Column(Float, nullable=False, default=0.0)
    total_credit = Column(Float, nullable=False, default=0.0)
    is_balanced = Column(Boolean, default=True)
    is_posted = Column(Boolean, default=True)

    # Foreign keys to source transactions
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=True)
    production_batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

    invoice = relationship("Invoice", back_populates="journal_entry")
    purchase = relationship("Purchase", back_populates="journal_entry")
    production_batch = relationship("ProductionBatch", back_populates="journal_entry")
    expense = relationship("Expense", back_populates="journal_entry")
    lines = relationship("JournalLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalLine(Base):
    """Individual debit/credit lines within a journal entry."""
    __tablename__ = "journal_lines"

    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    debit_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    credit_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(String(500))
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)

    journal_entry = relationship("JournalEntry", back_populates="lines")
    debit_account = relationship(
        "ChartOfAccount", foreign_keys=[debit_account_id], back_populates="debit_journal_lines"
    )
    credit_account = relationship(
        "ChartOfAccount", foreign_keys=[credit_account_id], back_populates="credit_journal_lines"
    )


# ─────────────────────────────────────────────────────────────────
# 10. PDF TEMPLATE MAPPING (stored per brand)
# ─────────────────────────────────────────────────────────────────

class PDFTemplateMapping(Base):
    """Detailed coordinate mapping for a brand's uploaded PDF invoice template."""
    __tablename__ = "pdf_template_mappings"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), unique=True, nullable=False)
    template_filename = Column(String(255))
    page_width = Column(Float)
    page_height = Column(Float)
    detection_method = Column(String(30), default="AI_AUTO")  # AI_AUTO | TAG | ACROFORM | MANUAL
    mapping_json = Column(JSON, nullable=False)  # Full coordinate mapping schema
    calibration_version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────────────────────────
# 11. APP SETTINGS (Key-Value Store)
# ─────────────────────────────────────────────────────────────────

class AppSetting(Base):
    """Flexible key-value settings store."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_company_setting_key"),
    )
