from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class UploadMismatch(Base):
    __tablename__ = "upload_mismatches"
    __table_args__ = {'extend_existing': True}

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
