from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.sql import func
from app.core.database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee_name = Column("employee_name", String(255), nullable=True)
    employee_number = Column(String(50), nullable=True)
    payroll_id = Column(Integer, ForeignKey("payroll_records.id"), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    status = Column(String(50))  # sent, failed, pending
    month = Column(String(20), nullable=True)
    net_salary = Column(Float, default=0)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
