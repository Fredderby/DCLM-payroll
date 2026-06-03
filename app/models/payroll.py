from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String(255), default="", index=True)  # Name as identifier
    month = Column(String(20))
    
    # Staff category: "pastoral" or "non_pastoral"
    staff_category = Column(String(20), default="pastoral")
    
    # Earnings
    basic_salary = Column(Float, default=0)
    meals_monthly = Column(Float, default=0)
    responsibility_allowance = Column(Float, default=0)
    cola = Column(Float, default=0)
    leave_allowance = Column(Float, default=0)
    other_earnings = Column(Float, default=0)
    total_earnings = Column(Float, default=0)
    
    # Non-Pastoral specific earnings
    rent_monthly = Column(Float, default=0)
    utility_monthly = Column(Float, default=0)
    transport_monthly = Column(Float, default=0)
    
    # Deductions
    paye = Column(Float, default=0)
    tithe = Column(Float, default=0)
    future_savings = Column(Float, default=0)
    other_deductions = Column(Float, default=0)
    total_deductions = Column(Float, default=0)
    
    # Historical PF-8% field (kept for backward compatibility with existing records)
    employee_pf = Column(Float, default=0)
    # SSNIT 5.5% Deduction (uploaded from spreadsheet, used for Non-Pastoral)
    ssnit_deduction = Column(Float, default=0)
    
    # Net
    net_salary = Column(Float, default=0)
    
    # Additional info
    employer_contribution = Column(Float, default=0)
    pdf_generated = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
