from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee_name = Column(String(255), nullable=True)
    payroll_id = Column(Integer, ForeignKey("payroll_records.id"), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    status = Column(String(50))  # sent, failed, pending
    month = Column(String(20), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())