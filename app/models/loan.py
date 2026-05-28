from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String(255), index=True, nullable=False)
    bank_name = Column(String(255), default="")
    loan_amount = Column(Float, default=0.0)
    months_to_pay = Column(Integer, default=1)
    interest_amount = Column(Float, default=0.0)
    total_receivable = Column(Float, default=0.0)
    monthly_deduction = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    months_paid = Column(Integer, default=0)
    balance = Column(Float, default=0.0)
    status = Column(String(50), default="Active")  # Active, Completed, Defaulted
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
