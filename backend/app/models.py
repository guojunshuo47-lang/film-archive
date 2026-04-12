from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rolls = relationship("Roll", back_populates="user", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
    )


class Roll(Base):
    __tablename__ = "rolls"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    roll_id = Column(String(50), nullable=False)  # 用户可见的ID，如 "Roll-001"
    film_stock = Column(String(100), nullable=True)
    camera = Column(String(100), nullable=True)
    iso = Column(Integer, nullable=True)
    total_frames = Column(Integer, default=36)
    status = Column(String(20), default="shooting")  # shooting, finished, developed
    date_created = Column(DateTime, default=datetime.utcnow)
    date_finished = Column(DateTime, nullable=True)
    date_developed = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)
    custom_data = Column(JSON, default=dict)  # 存储其他动态字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="rolls")
    photos = relationship("Photo", back_populates="roll", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_roll_user_id', 'user_id'),
        Index('idx_roll_roll_id', 'roll_id'),
    )


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    roll_id = Column(Integer, ForeignKey("rolls.id", ondelete="CASCADE"), nullable=False)
    frame_number = Column(Integer, nullable=False)
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    exif_data = Column(JSON, default=dict)  # EXIF 信息
    note = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 星评分
    tags = Column(JSON, default=list)  # 标签列表
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="photos")
    roll = relationship("Roll", back_populates="photos")

    __table_args__ = (
        Index('idx_photo_user_id', 'user_id'),
        Index('idx_photo_roll_id', 'roll_id'),
        Index('idx_photo_frame', 'roll_id', 'frame_number'),
    )
