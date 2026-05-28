from sqlalchemy import Column, Integer, String, Date, DateTime, Float
from sqlalchemy.sql import func
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_number = Column(String(50), index=True)
    name = Column(String(255))
    email = Column(String(255), index=True)
    function = Column(String(255), default="")
    designation = Column(String(100), default="")
    location = Column(String(255), default="")
    
    # Bank Details (parsed from bank_account field on import)
    bank_number = Column(String(255), default="")
    bank_name = Column(String(255), default="")
    bank_branch = Column(String(255), default="")
    
    # Tax and Contributions
    date_joined = Column(Date, nullable=True)
    ssnit_number = Column(String(50), default="")
    tax_relief = Column(String(255), default="")
    employer_contribution = Column(Float, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())