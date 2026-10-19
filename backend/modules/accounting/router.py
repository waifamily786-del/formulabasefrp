"""Accounting router - P&L, Balance Sheet, AR/AP Aging, Journal Entries."""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import (
    Expense, ExpenseCategory, JournalEntry, JournalLine, ChartOfAccount, Company
)
from core.security import get_current_user, TokenData
from modules.accounting.auto_accountant import AutoAccountantEngine

router = APIRouter()


@router.get("/income-statement")
async def income_statement(
    start_date: date,
    end_date: date,
    brand_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Generate Income Statement (P&L) for a period."""
    company = db.query(Company).first()
    engine = AutoAccountantEngine(db)
    return engine.get_income_statement(company.id, start_date, end_date, brand_id)


@router.get("/balance-sheet")
async def balance_sheet(
    as_of_date: date,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Generate Balance Sheet as of a date."""
    company = db.query(Company).first()
    engine = AutoAccountantEngine(db)
    return engine.get_balance_sheet(company.id, as_of_date)


@router.get("/ar-aging")
async def ar_aging_report(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Accounts Receivable Aging Report."""
    company = db.query(Company).first()
    engine = AutoAccountantEngine(db)
    return engine.get_ar_aging_report(company.id)


@router.get("/journal-entries")
async def list_journal_entries(
    limit: int = 50,
    brand_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List recent journal entries."""
    q = db.query(JournalEntry)
    if brand_id:
        q = q.filter(JournalEntry.brand_id == brand_id)
    entries = q.order_by(JournalEntry.id.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "entry_number": e.entry_number,
            "entry_type": e.entry_type,
            "entry_date": str(e.entry_date),
            "description": e.description,
            "total_debit": e.total_debit,
            "total_credit": e.total_credit,
            "is_balanced": e.is_balanced,
        }
        for e in entries
    ]


@router.get("/chart-of-accounts")
async def chart_of_accounts(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get the full chart of accounts."""
    company = db.query(Company).first()
    accounts = db.query(ChartOfAccount).filter(
        ChartOfAccount.company_id == company.id,
        ChartOfAccount.is_active == True,
    ).order_by(ChartOfAccount.sort_order).all()
    return [
        {
            "id": a.id,
            "account_code": a.account_code,
            "account_name": a.account_name,
            "account_type": a.account_type,
            "normal_balance": a.normal_balance,
        }
        for a in accounts
    ]


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    expense_date: Optional[date] = None
    payment_method: str = "CASH"
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    notes: Optional[str] = None


@router.post("/expenses")
async def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Log a business expense with automatic journal entry."""
    company = db.query(Company).first()

    # Get account code from category
    expense_account_code = "6900"  # Default: Miscellaneous
    if data.category_id:
        cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == data.category_id).first()
        if cat and cat.account_code:
            expense_account_code = cat.account_code

    expense = Expense(
        company_id=company.id,
        brand_id=data.brand_id,
        category_id=data.category_id,
        description=data.description,
        amount=data.amount,
        expense_date=data.expense_date or date.today(),
        payment_method=data.payment_method,
        notes=data.notes,
        created_by_user_id=current_user.user_id,
    )
    db.add(expense)
    db.flush()

    # Auto-create journal entry
    engine = AutoAccountantEngine(db)
    engine.create_expense_journal_entry(expense, company.id, expense_account_code)

    return {"expense_id": expense.id, "description": expense.description, "amount": expense.amount}


@router.get("/expenses")
async def list_expenses(
    brand_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    company = db.query(Company).first()
    q = db.query(Expense).filter(Expense.company_id == company.id)
    if brand_id:
        q = q.filter(Expense.brand_id == brand_id)
    expenses = q.order_by(Expense.id.desc()).limit(limit).all()
    return [
        {
            "id": e.id, "description": e.description, "amount": e.amount,
            "expense_date": str(e.expense_date), "payment_method": e.payment_method,
            "brand_id": e.brand_id,
        }
        for e in expenses
    ]


@router.get("/summary")
async def financial_summary(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Quick financial summary for the dashboard."""
    from datetime import datetime
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    company = db.query(Company).first()
    engine = AutoAccountantEngine(db)

    monthly = engine.get_income_statement(company.id, month_start, today)
    ytd = engine.get_income_statement(company.id, year_start, today)

    return {
        "monthly": monthly,
        "year_to_date": ytd,
        "balance_sheet": engine.get_balance_sheet(company.id, today),
    }
