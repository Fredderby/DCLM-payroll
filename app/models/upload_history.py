from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class UploadHistory(Base):
    __tablename__ = "upload_history"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255))
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    month = Column(String(20), nullable=True)
    total_employees = Column(Integer, default=0)
    imported_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    skip_reasons = Column(Text, nullable=True)  # JSON string of {name, reason} details
    status = Column(String(50))  # success, failed, partial_failure
    timestamp = Column(DateTime(timezone=True), server_default=func.now())