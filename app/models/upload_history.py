from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class UploadHistory(Base):
    __tablename__ = "upload_history"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255))
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    month = Column(String(20), nullable=True)
    status = Column(String(50))  # success, failed, partial_failure
    timestamp = Column(DateTime(timezone=True), server_default=func.now())