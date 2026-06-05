from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from app.core.database import Base

class UploadHistory(Base):
    __tablename__ = "upload_history"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255))
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    month = Column(String(20), nullable=True)
    payroll_type = Column(String(50), nullable=True)
    total_employees = Column(Integer, default=0)
    imported_count = Column(Integer, default=0)
    unmatched_count = Column(Integer, default=0)
    skip_reasons = Column(Text, nullable=True)  # Removed - no more large JSON payloads
    status = Column(String(50))  # success, failed, partial
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class UploadMismatch(Base):
    __tablename__ = "upload_mismatches"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("upload_history.id"))
    employee_name = Column(String(255), default="")
    employee_number = Column(String(50), default="")
    email = Column(String(255), default="")
    payroll_type = Column(String(50), default="")
    month = Column(String(20), nullable=True)
    reason = Column(String(255), default="")
    suggested_match = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())