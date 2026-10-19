"""
FormulaBase Nexus - Zero-Touch Auto-Accountant Engine
Automated Double-Entry Accounting System:
- Every invoice/purchase/production/expense automatically creates journal entries
- Real-time P&L, Balance Sheet, Cash Flow statements
- AR/AP aging reports
- Monthly/Yearly closings
"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# STANDARD CHART OF ACCOUNTS CODES
# ─────────────────────────────────────────────────────────────────

class AccountCodes:
    """Standard account codes for the Chart of Accounts."""
    # ASSETS (1xxx)
    CASH_ON_HAND          = "1001"
    KPAY_WALLET           = "1002"
    WAVEPAY_WALLET        = "1003"
    BANK_ACCOUNT          = "1010"
    ACCOUNTS_RECEIVABLE   = "1100"
    RAW_MATERIAL_INV      = "1200"
    FINISHED_GOODS_INV_SARA = "1210"
    FINISHED_GOODS_INV_LMN  = "1211"
    FINISHED_GOODS_INV    = "1215"  # Generic brand
    PREPAID_EXPENSES      = "1300"
    OTHER_CURRENT_ASSETS  = "1900"

    # LIABILITIES (2xxx)
    ACCOUNTS_PAYABLE      = "2001"
    COMMERCIAL_TAX_PAYABLE = "2100"
    INCOME_TAX_PAYABLE    = "2200"
    OTHER_LIABILITIES     = "2900"

    # EQUITY (3xxx)
    OWNERS_EQUITY         = "3001"
    RETAINED_EARNINGS     = "3100"
    CURRENT_YEAR_EARNINGS = "3200"

    # REVENUE (4xxx)
    SALES_REVENUE_SARA    = "4001"
    SALES_REVENUE_LMN     = "4002"
    SALES_REVENUE_GENERAL = "4010"
    DELIVERY_INCOME       = "4050"
    OTHER_INCOME          = "4900"

    # COST OF GOODS SOLD (5xxx)
    COGS_SARA             = "5001"
    COGS_LMN              = "5002"
    COGS_GENERAL          = "5010"

    # EXPENSES (6xxx)
    DIRECT_LABOR          = "6001"
    MANUFACTURING_OVERHEAD = "6002"
    RENT_EXPENSE          = "6100"
    UTILITIES_EXPENSE     = "6101"
    SALARIES_EXPENSE      = "6102"
    MARKETING_EXPENSE     = "6103"
    TRANSPORT_EXPENSE     = "6104"
    PACKAGING_EXPENSE     = "6105"
    BANK_CHARGES          = "6200"
    DEPRECIATION          = "6300"
    MISCELLANEOUS_EXPENSE = "6900"


STANDARD_CHART_OF_ACCOUNTS = [
    # ASSETS
    {"code": AccountCodes.CASH_ON_HAND,        "name": "Cash on Hand",               "type": "ASSET",   "normal": "DEBIT",  "sort": 10},
    {"code": AccountCodes.KPAY_WALLET,         "name": "KPay Wallet",                "type": "ASSET",   "normal": "DEBIT",  "sort": 11},
    {"code": AccountCodes.WAVEPAY_WALLET,      "name": "WavePay Wallet",             "type": "ASSET",   "normal": "DEBIT",  "sort": 12},
    {"code": AccountCodes.BANK_ACCOUNT,        "name": "Bank Account",               "type": "ASSET",   "normal": "DEBIT",  "sort": 13},
    {"code": AccountCodes.ACCOUNTS_RECEIVABLE, "name": "Accounts Receivable (AR)",   "type": "ASSET",   "normal": "DEBIT",  "sort": 20},
    {"code": AccountCodes.RAW_MATERIAL_INV,    "name": "Raw Material Inventory",     "type": "ASSET",   "normal": "DEBIT",  "sort": 30},
    {"code": AccountCodes.FINISHED_GOODS_INV_SARA, "name": "Finished Goods - SARA", "type": "ASSET",   "normal": "DEBIT",  "sort": 31},
    {"code": AccountCodes.FINISHED_GOODS_INV_LMN,  "name": "Finished Goods - LMN",  "type": "ASSET",   "normal": "DEBIT",  "sort": 32},
    {"code": AccountCodes.FINISHED_GOODS_INV,  "name": "Finished Goods Inventory",  "type": "ASSET",   "normal": "DEBIT",  "sort": 33},
    {"code": AccountCodes.OTHER_CURRENT_ASSETS,"name": "Other Current Assets",       "type": "ASSET",   "normal": "DEBIT",  "sort": 40},
    # LIABILITIES
    {"code": AccountCodes.ACCOUNTS_PAYABLE,    "name": "Accounts Payable (AP)",      "type": "LIABILITY","normal": "CREDIT", "sort": 100},
    {"code": AccountCodes.COMMERCIAL_TAX_PAYABLE,"name": "Commercial Tax Payable",   "type": "LIABILITY","normal": "CREDIT", "sort": 110},
    {"code": AccountCodes.INCOME_TAX_PAYABLE,  "name": "Income Tax Payable",         "type": "LIABILITY","normal": "CREDIT", "sort": 120},
    {"code": AccountCodes.OTHER_LIABILITIES,   "name": "Other Liabilities",          "type": "LIABILITY","normal": "CREDIT", "sort": 130},
    # EQUITY
    {"code": AccountCodes.OWNERS_EQUITY,       "name": "Owner's Equity / Capital",   "type": "EQUITY",  "normal": "CREDIT", "sort": 200},
    {"code": AccountCodes.RETAINED_EARNINGS,   "name": "Retained Earnings",          "type": "EQUITY",  "normal": "CREDIT", "sort": 210},
    # REVENUE
    {"code": AccountCodes.SALES_REVENUE_SARA,  "name": "Sales Revenue - SARA",       "type": "REVENUE", "normal": "CREDIT", "sort": 300},
    {"code": AccountCodes.SALES_REVENUE_LMN,   "name": "Sales Revenue - LMN",        "type": "REVENUE", "normal": "CREDIT", "sort": 301},
    {"code": AccountCodes.SALES_REVENUE_GENERAL,"name": "Sales Revenue - General",   "type": "REVENUE", "normal": "CREDIT", "sort": 305},
    {"code": AccountCodes.DELIVERY_INCOME,     "name": "Delivery Income",            "type": "REVENUE", "normal": "CREDIT", "sort": 310},
    {"code": AccountCodes.OTHER_INCOME,        "name": "Other Income",               "type": "REVENUE", "normal": "CREDIT", "sort": 320},
    # COGS
    {"code": AccountCodes.COGS_SARA,           "name": "Cost of Goods Sold - SARA",  "type": "EXPENSE", "normal": "DEBIT",  "sort": 400},
    {"code": AccountCodes.COGS_LMN,            "name": "Cost of Goods Sold - LMN",   "type": "EXPENSE", "normal": "DEBIT",  "sort": 401},
    {"code": AccountCodes.COGS_GENERAL,        "name": "Cost of Goods Sold - General","type": "EXPENSE","normal": "DEBIT",  "sort": 405},
    # EXPENSES
    {"code": AccountCodes.DIRECT_LABOR,        "name": "Direct Labor Cost",          "type": "EXPENSE", "normal": "DEBIT",  "sort": 500},
    {"code": AccountCodes.MANUFACTURING_OVERHEAD,"name": "Manufacturing Overhead",   "type": "EXPENSE", "normal": "DEBIT",  "sort": 501},
    {"code": AccountCodes.RENT_EXPENSE,        "name": "Rent / Shop Expense",        "type": "EXPENSE", "normal": "DEBIT",  "sort": 510},
    {"code": AccountCodes.UTILITIES_EXPENSE,   "name": "Utilities (Electric/Water)", "type": "EXPENSE", "normal": "DEBIT",  "sort": 511},
    {"code": AccountCodes.SALARIES_EXPENSE,    "name": "Salaries & Wages",           "type": "EXPENSE", "normal": "DEBIT",  "sort": 512},
    {"code": AccountCodes.MARKETING_EXPENSE,   "name": "Marketing & Advertising",    "type": "EXPENSE", "normal": "DEBIT",  "sort": 513},
    {"code": AccountCodes.TRANSPORT_EXPENSE,   "name": "Transport & Delivery",       "type": "EXPENSE", "normal": "DEBIT",  "sort": 514},
    {"code": AccountCodes.BANK_CHARGES,        "name": "Bank Charges",               "type": "EXPENSE", "normal": "DEBIT",  "sort": 520},
    {"code": AccountCodes.MISCELLANEOUS_EXPENSE,"name": "Miscellaneous Expenses",    "type": "EXPENSE", "normal": "DEBIT",  "sort": 530},
]


class AutoAccountantEngine:
    """
    Zero-Touch Double-Entry Accounting Engine.
    Automatically generates journal entries for all business transactions.
    User never needs to know Debit/Credit accounting.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_account(self, account_code: str, company_id: int):
        """Fetch a chart of accounts entry by code."""
        from database.models import ChartOfAccount
        account = self.db.query(ChartOfAccount).filter(
            ChartOfAccount.company_id == company_id,
            ChartOfAccount.account_code == account_code,
        ).first()
        if not account:
            logger.error(f"Account code {account_code} not found for company {company_id}")
        return account

    def _get_payment_account_code(self, payment_method: str) -> str:
        """Map payment method to the correct cash/bank account code."""
        mapping = {
            "CASH": AccountCodes.CASH_ON_HAND,
            "KPAY": AccountCodes.KPAY_WALLET,
            "WAVEPAY": AccountCodes.WAVEPAY_WALLET,
            "BANK_TRANSFER": AccountCodes.BANK_ACCOUNT,
            "CREDIT": AccountCodes.ACCOUNTS_RECEIVABLE,
            "PARTIAL": AccountCodes.ACCOUNTS_RECEIVABLE,
        }
        return mapping.get(payment_method.upper(), AccountCodes.CASH_ON_HAND)

    def _get_brand_revenue_account(self, brand_name: str) -> str:
        """Get revenue account code for a brand."""
        name_upper = brand_name.upper()
        if "SARA" in name_upper:
            return AccountCodes.SALES_REVENUE_SARA
        elif "LMN" in name_upper:
            return AccountCodes.SALES_REVENUE_LMN
        return AccountCodes.SALES_REVENUE_GENERAL

    def _get_brand_cogs_account(self, brand_name: str) -> str:
        """Get COGS account code for a brand."""
        name_upper = brand_name.upper()
        if "SARA" in name_upper:
            return AccountCodes.COGS_SARA
        elif "LMN" in name_upper:
            return AccountCodes.COGS_LMN
        return AccountCodes.COGS_GENERAL

    def _get_brand_fg_account(self, brand_name: str) -> str:
        """Get Finished Goods Inventory account code for a brand."""
        name_upper = brand_name.upper()
        if "SARA" in name_upper:
            return AccountCodes.FINISHED_GOODS_INV_SARA
        elif "LMN" in name_upper:
            return AccountCodes.FINISHED_GOODS_INV_LMN
        return AccountCodes.FINISHED_GOODS_INV

    def _generate_entry_number(self, entry_type: str, company_id: int) -> str:
        """Generate a unique journal entry number."""
        from database.models import JournalEntry
        count = self.db.query(func.count(JournalEntry.id)).filter(
            JournalEntry.company_id == company_id,
            JournalEntry.entry_type == entry_type,
        ).scalar() or 0
        prefix_map = {
            "SALES": "JV-SL", "PURCHASE": "JV-PU",
            "PRODUCTION": "JV-PR", "EXPENSE": "JV-EX", "PAYMENT": "JV-PA",
        }
        prefix = prefix_map.get(entry_type, "JV")
        today = date.today().strftime("%Y%m")
        return f"{prefix}-{today}-{count + 1:04d}"

    # ──────────────────────────────────────────────────────────────
    # JOURNAL ENTRY CREATORS
    # ──────────────────────────────────────────────────────────────

    def create_sales_journal_entry(self, invoice, company_id: int, brand_name: str):
        """
        Auto-create double-entry journal for a sales invoice:
        Dr Cash/Bank/AR → Cr Sales Revenue + Tax Payable + Delivery Income
        Dr COGS → Cr Finished Goods Inventory
        """
        from database.models import JournalEntry, JournalLine, Invoice

        try:
            # Determine payment account
            payment_code = self._get_payment_account_code(invoice.payment_method)
            revenue_code = self._get_brand_revenue_account(brand_name)
            cogs_code = self._get_brand_cogs_account(brand_name)
            fg_inv_code = self._get_brand_fg_account(brand_name)

            payment_acct = self._get_account(payment_code, company_id)
            revenue_acct = self._get_account(revenue_code, company_id)
            cogs_acct = self._get_account(cogs_code, company_id)
            fg_inv_acct = self._get_account(fg_inv_code, company_id)

            if not all([payment_acct, revenue_acct]):
                logger.error("Missing accounts for sales journal entry")
                return None

            entry = JournalEntry(
                company_id=company_id,
                brand_id=invoice.brand_id,
                entry_number=self._generate_entry_number("SALES", company_id),
                entry_type="SALES",
                entry_date=invoice.invoice_date or date.today(),
                description=f"Sales Invoice #{invoice.invoice_number} - {brand_name}",
                total_debit=invoice.grand_total,
                total_credit=invoice.grand_total,
                invoice_id=invoice.id,
            )
            self.db.add(entry)
            self.db.flush()

            lines = []

            # PART 1: Revenue recognition
            # Dr: Cash/Bank/AR (grand total)
            lines.append(JournalLine(
                journal_entry_id=entry.id,
                debit_account_id=payment_acct.id,
                amount=invoice.grand_total,
                description=f"Payment received - {invoice.payment_method}",
                brand_id=invoice.brand_id,
            ))

            # Cr: Sales Revenue (net sales after discount)
            net_sales = invoice.subtotal - invoice.discount_amount
            if net_sales > 0 and revenue_acct:
                lines.append(JournalLine(
                    journal_entry_id=entry.id,
                    credit_account_id=revenue_acct.id,
                    amount=net_sales,
                    description=f"Sales revenue - {brand_name}",
                    brand_id=invoice.brand_id,
                ))

            # Cr: Commercial Tax Payable
            if invoice.commercial_tax_amount > 0:
                ct_acct = self._get_account(AccountCodes.COMMERCIAL_TAX_PAYABLE, company_id)
                if ct_acct:
                    lines.append(JournalLine(
                        journal_entry_id=entry.id,
                        credit_account_id=ct_acct.id,
                        amount=invoice.commercial_tax_amount,
                        description="Commercial Tax collected",
                        brand_id=invoice.brand_id,
                    ))

            # Cr: Delivery Income
            if invoice.delivery_fee > 0:
                del_acct = self._get_account(AccountCodes.DELIVERY_INCOME, company_id)
                if del_acct:
                    lines.append(JournalLine(
                        journal_entry_id=entry.id,
                        credit_account_id=del_acct.id,
                        amount=invoice.delivery_fee,
                        description="Delivery fee income",
                        brand_id=invoice.brand_id,
                    ))

            # PART 2: COGS recognition
            if invoice.total_cogs > 0 and cogs_acct and fg_inv_acct:
                # Dr: COGS
                lines.append(JournalLine(
                    journal_entry_id=entry.id,
                    debit_account_id=cogs_acct.id,
                    amount=invoice.total_cogs,
                    description=f"Cost of goods sold - {brand_name}",
                    brand_id=invoice.brand_id,
                ))
                # Cr: Finished Goods Inventory
                lines.append(JournalLine(
                    journal_entry_id=entry.id,
                    credit_account_id=fg_inv_acct.id,
                    amount=invoice.total_cogs,
                    description=f"FG inventory reduced - {brand_name}",
                    brand_id=invoice.brand_id,
                ))

            for line in lines:
                self.db.add(line)

            self.db.commit()
            logger.info(f"Sales journal entry created: {entry.entry_number}")
            return entry

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating sales journal entry: {e}")
            raise

    def create_purchase_journal_entry(self, purchase, company_id: int):
        """
        Auto-create journal for raw material purchase:
        Dr Raw Material Inventory → Cr Cash/Bank/AP (Accounts Payable)
        """
        from database.models import JournalEntry, JournalLine

        try:
            rm_acct = self._get_account(AccountCodes.RAW_MATERIAL_INV, company_id)

            if purchase.is_credit:
                payment_code = AccountCodes.ACCOUNTS_PAYABLE
            else:
                payment_code = self._get_payment_account_code(purchase.payment_method or "CASH")

            credit_acct = self._get_account(payment_code, company_id)

            if not all([rm_acct, credit_acct]):
                return None

            entry = JournalEntry(
                company_id=company_id,
                entry_number=self._generate_entry_number("PURCHASE", company_id),
                entry_type="PURCHASE",
                entry_date=purchase.purchase_date or date.today(),
                description=f"Raw Material Purchase #{purchase.purchase_number}",
                total_debit=purchase.total_amount,
                total_credit=purchase.total_amount,
                purchase_id=purchase.id,
            )
            self.db.add(entry)
            self.db.flush()

            self.db.add(JournalLine(
                journal_entry_id=entry.id,
                debit_account_id=rm_acct.id,
                amount=purchase.total_amount,
                description="Raw material inventory increase",
            ))
            self.db.add(JournalLine(
                journal_entry_id=entry.id,
                credit_account_id=credit_acct.id,
                amount=purchase.total_amount,
                description=f"Payment: {purchase.payment_method or 'Credit/AP'}",
            ))

            self.db.commit()
            logger.info(f"Purchase journal entry created: {entry.entry_number}")
            return entry

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating purchase journal entry: {e}")
            raise

    def create_production_journal_entry(self, batch, company_id: int, brand_name: str):
        """
        Auto-create journal for production batch:
        Dr Finished Goods Inventory → Cr Raw Material Inventory + Direct Labor + Overhead
        """
        from database.models import JournalEntry, JournalLine

        try:
            fg_code = self._get_brand_fg_account(brand_name)
            fg_acct = self._get_account(fg_code, company_id)
            rm_acct = self._get_account(AccountCodes.RAW_MATERIAL_INV, company_id)
            labor_acct = self._get_account(AccountCodes.DIRECT_LABOR, company_id)
            overhead_acct = self._get_account(AccountCodes.MANUFACTURING_OVERHEAD, company_id)

            if not all([fg_acct, rm_acct]):
                return None

            total_cost = batch.total_batch_cost
            entry = JournalEntry(
                company_id=company_id,
                brand_id=batch.brand_id,
                entry_number=self._generate_entry_number("PRODUCTION", company_id),
                entry_type="PRODUCTION",
                entry_date=batch.manufacturing_date or date.today(),
                description=f"Production Batch #{batch.batch_number} - {brand_name}",
                total_debit=total_cost,
                total_credit=total_cost,
                production_batch_id=batch.id,
            )
            self.db.add(entry)
            self.db.flush()

            # Dr: Finished Goods Inventory (total batch cost)
            self.db.add(JournalLine(
                journal_entry_id=entry.id,
                debit_account_id=fg_acct.id,
                amount=total_cost,
                description=f"FG produced: {batch.actual_qty or batch.planned_qty} pcs of {brand_name}",
                brand_id=batch.brand_id,
            ))

            # Cr: Raw Material Inventory
            if batch.raw_material_cost > 0:
                self.db.add(JournalLine(
                    journal_entry_id=entry.id,
                    credit_account_id=rm_acct.id,
                    amount=batch.raw_material_cost,
                    description="Raw materials consumed in production",
                ))

            # Cr: Direct Labor
            if batch.labor_cost > 0 and labor_acct:
                self.db.add(JournalLine(
                    journal_entry_id=entry.id,
                    credit_account_id=labor_acct.id,
                    amount=batch.labor_cost,
                    description="Direct labor cost",
                ))

            # Cr: Overhead
            if batch.overhead_cost > 0 and overhead_acct:
                self.db.add(JournalLine(
                    journal_entry_id=entry.id,
                    credit_account_id=overhead_acct.id,
                    amount=batch.overhead_cost,
                    description="Manufacturing overhead allocated",
                ))

            self.db.commit()
            logger.info(f"Production journal entry created: {entry.entry_number}")
            return entry

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating production journal entry: {e}")
            raise

    def create_expense_journal_entry(self, expense, company_id: int, expense_account_code: str = None):
        """
        Auto-create journal for general expenses:
        Dr Expense Account → Cr Cash/Bank
        """
        from database.models import JournalEntry, JournalLine

        try:
            exp_code = expense_account_code or AccountCodes.MISCELLANEOUS_EXPENSE
            exp_acct = self._get_account(exp_code, company_id)
            payment_code = self._get_payment_account_code(expense.payment_method or "CASH")
            payment_acct = self._get_account(payment_code, company_id)

            if not all([exp_acct, payment_acct]):
                return None

            entry = JournalEntry(
                company_id=company_id,
                brand_id=expense.brand_id,
                entry_number=self._generate_entry_number("EXPENSE", company_id),
                entry_type="EXPENSE",
                entry_date=expense.expense_date or date.today(),
                description=f"Expense: {expense.description[:100]}",
                total_debit=expense.amount,
                total_credit=expense.amount,
                expense_id=expense.id,
            )
            self.db.add(entry)
            self.db.flush()

            self.db.add(JournalLine(
                journal_entry_id=entry.id,
                debit_account_id=exp_acct.id,
                amount=expense.amount,
                description=expense.description,
                brand_id=expense.brand_id,
            ))
            self.db.add(JournalLine(
                journal_entry_id=entry.id,
                credit_account_id=payment_acct.id,
                amount=expense.amount,
                description=f"Paid via {expense.payment_method}",
            ))

            self.db.commit()
            return entry

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating expense journal entry: {e}")
            raise

    # ──────────────────────────────────────────────────────────────
    # FINANCIAL REPORTS
    # ──────────────────────────────────────────────────────────────

    def get_income_statement(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        brand_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate real-time Income Statement (P&L).
        Can be filtered by brand or show consolidated company P&L.
        """
        from database.models import Invoice, Expense, InvoiceItem, Brand

        # Base query filter
        def inv_filter(q):
            q = q.filter(Invoice.company_id == company_id if hasattr(Invoice, 'company_id') else True)
            q = q.join(Brand).filter(Brand.company_id == company_id)
            q = q.filter(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
            q = q.filter(Invoice.status != "CANCELLED")
            if brand_id:
                q = q.filter(Invoice.brand_id == brand_id)
            return q

        # Revenue
        invoices_q = inv_filter(self.db.query(Invoice))
        invoices = invoices_q.all()

        gross_revenue = sum(i.subtotal for i in invoices)
        total_discounts = sum(i.discount_amount for i in invoices)
        total_ct = sum(i.commercial_tax_amount for i in invoices)
        total_delivery = sum(i.delivery_fee for i in invoices)
        net_revenue = gross_revenue - total_discounts

        # COGS
        total_cogs = sum(i.total_cogs for i in invoices)
        gross_profit = net_revenue - total_cogs
        gross_margin_pct = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0

        # Operating Expenses
        exp_q = self.db.query(func.sum(Expense.amount)).filter(
            Expense.company_id == company_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
        )
        if brand_id:
            exp_q = exp_q.filter(or_(Expense.brand_id == brand_id, Expense.brand_id == None))
        total_opex = exp_q.scalar() or 0.0

        net_profit = gross_profit - total_opex
        net_margin_pct = (net_profit / net_revenue * 100) if net_revenue > 0 else 0

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "brand_id": brand_id,
            "revenue": {
                "gross_revenue": round(gross_revenue, 2),
                "total_discounts": round(total_discounts, 2),
                "net_revenue": round(net_revenue, 2),
                "commercial_tax_collected": round(total_ct, 2),
                "delivery_income": round(total_delivery, 2),
            },
            "cogs": {
                "total_cogs": round(total_cogs, 2),
            },
            "gross_profit": round(gross_profit, 2),
            "gross_margin_percent": round(gross_margin_pct, 2),
            "operating_expenses": round(total_opex, 2),
            "net_profit": round(net_profit, 2),
            "net_margin_percent": round(net_margin_pct, 2),
            "invoice_count": len(invoices),
        }

    def get_balance_sheet(self, company_id: int, as_of_date: date) -> Dict[str, Any]:
        """Generate real-time Balance Sheet."""
        from database.models import Customer, Supplier, RawMaterial, Product

        # Assets
        total_ar = self.db.query(func.sum(Customer.outstanding_credit)).filter(
            Customer.brand.has(company_id=company_id)
        ).scalar() or 0

        total_rm_value = self.db.query(
            func.sum(RawMaterial.current_stock * RawMaterial.weighted_avg_cost)
        ).filter(RawMaterial.company_id == company_id).scalar() or 0

        total_fg_value = self.db.query(
            func.sum(Product.current_stock * Product.unit_cost_cogs)
        ).filter(Product.brand.has(company_id=company_id)).scalar() or 0

        # Liabilities
        total_ap = self.db.query(func.sum(Supplier.outstanding_payable)).filter(
            Supplier.company_id == company_id
        ).scalar() or 0

        # Get P&L for retained earnings estimate
        income = self.get_income_statement(company_id, date(as_of_date.year, 1, 1), as_of_date)
        net_profit = income.get("net_profit", 0)

        total_assets = total_ar + total_rm_value + total_fg_value
        total_liabilities = total_ap
        total_equity = total_assets - total_liabilities

        return {
            "as_of_date": str(as_of_date),
            "assets": {
                "accounts_receivable": round(total_ar, 2),
                "raw_material_inventory": round(total_rm_value, 2),
                "finished_goods_inventory": round(total_fg_value, 2),
                "total_assets": round(total_assets, 2),
            },
            "liabilities": {
                "accounts_payable": round(total_ap, 2),
                "total_liabilities": round(total_liabilities, 2),
            },
            "equity": {
                "net_profit_ytd": round(net_profit, 2),
                "total_equity": round(total_equity, 2),
            },
        }

    def get_ar_aging_report(self, company_id: int) -> List[Dict[str, Any]]:
        """Accounts Receivable Aging Report."""
        from database.models import Customer, Brand
        today = date.today()

        customers = (
            self.db.query(Customer)
            .join(Brand)
            .filter(Brand.company_id == company_id, Customer.outstanding_credit > 0)
            .all()
        )

        result = []
        for c in customers:
            # Find oldest unpaid invoice
            oldest_inv = (
                self.db.query(__import__("backend.database.models", fromlist=["Invoice"]).Invoice)
                .filter(
                    __import__("backend.database.models", fromlist=["Invoice"]).Invoice.customer_id == c.id,
                    __import__("backend.database.models", fromlist=["Invoice"]).Invoice.credit_amount > 0,
                    __import__("backend.database.models", fromlist=["Invoice"]).Invoice.status != "CANCELLED",
                )
                .order_by(__import__("backend.database.models", fromlist=["Invoice"]).Invoice.invoice_date)
                .first()
            )

            days_overdue = 0
            if oldest_inv and oldest_inv.invoice_date:
                days_overdue = (today - oldest_inv.invoice_date).days

            result.append({
                "customer_id": c.id,
                "customer_name": c.name,
                "phone": c.phone,
                "outstanding_amount": round(c.outstanding_credit, 2),
                "days_overdue": days_overdue,
                "aging_bucket": (
                    "0-30 days" if days_overdue <= 30 else
                    "31-60 days" if days_overdue <= 60 else
                    "61-90 days" if days_overdue <= 90 else
                    "90+ days (Overdue!)"
                ),
            })

        return sorted(result, key=lambda x: x["days_overdue"], reverse=True)

    def initialize_chart_of_accounts(self, company_id: int):
        """Seed the standard Chart of Accounts for a new company."""
        from database.models import ChartOfAccount
        existing = self.db.query(ChartOfAccount).filter(
            ChartOfAccount.company_id == company_id
        ).count()
        if existing > 0:
            logger.info(f"Chart of accounts already exists for company {company_id}")
            return

        for acct_def in STANDARD_CHART_OF_ACCOUNTS:
            acct = ChartOfAccount(
                company_id=company_id,
                account_code=acct_def["code"],
                account_name=acct_def["name"],
                account_type=acct_def["type"],
                normal_balance=acct_def["normal"],
                sort_order=acct_def.get("sort", 0),
                is_active=True,
            )
            self.db.add(acct)

        try:
            self.db.commit()
            logger.info(f"Chart of accounts initialized for company {company_id}: {len(STANDARD_CHART_OF_ACCOUNTS)} accounts")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initializing chart of accounts: {e}")
            raise
