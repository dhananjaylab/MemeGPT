from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.session import Base


class User(Base):
    __tablename__ = "users"
    
    id: str = Column(String, primary_key=True)
    email: str = Column(String, unique=True, nullable=False, index=True)
    plan: str = Column(String, default="free", index=True)  # "free", "pro", "api"
    daily_limit: int = Column(Integer, default=5)
    daily_used: int = Column(Integer, default=0)
    api_key: Optional[str] = Column(String, nullable=True, unique=True, index=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    preferences: dict = Column(JSON, default={}, nullable=False)
    
    # Relationships
    memes = relationship("GeneratedMeme", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("MemeJob", backref="user_ref")
    
    @property
    def is_premium(self) -> bool:
        """Check if user has a premium plan (pro or api)"""
        return self.plan in ["pro", "api"]
    
    @property
    def has_api_access(self) -> bool:
        """Check if user has API access"""
        return self.plan == "api" and self.api_key is not None
    
    @property
    def remaining_generations(self) -> int:
        """Get remaining generations for today"""
        daily_limit = self.daily_limit or 5
        daily_used = self.daily_used or 0
        return max(0, daily_limit - daily_used)
    
    def can_generate(self) -> bool:
        """Check if user can generate more memes today"""
        daily_limit = self.daily_limit or 5
        daily_used = self.daily_used or 0
        return daily_used < daily_limit


class GeneratedMeme(Base):
    __tablename__ = "memes"
    
    id: str = Column(String, primary_key=True)
    user_id: Optional[str] = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    prompt: str = Column(Text, nullable=False)
    template_name: str = Column(String, nullable=False, index=True)
    template_id: int = Column(Integer, nullable=False, index=True)
    meme_text: List[str] = Column(JSON, nullable=False)
    image_url: str = Column(String, nullable=False)
    thumbnail_url: Optional[str] = Column(String, nullable=True)
    share_count: int = Column(Integer, default=0, index=True)
    like_count: int = Column(Integer, default=0, index=True)
    is_public: bool = Column(Boolean, default=True, index=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="memes")
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_memes_public_created', 'is_public', 'created_at'),
        Index('ix_memes_template_created', 'template_name', 'created_at'),
        Index('ix_memes_user_created', 'user_id', 'created_at'),
    )
    
    @property
    def is_anonymous(self) -> bool:
        """Check if meme was created by anonymous user"""
        return self.user_id is None
    
    @property
    def display_url(self) -> str:
        """Get the best URL for displaying the meme (thumbnail if available, otherwise full image)"""
        return self.thumbnail_url or self.image_url
    
    def increment_share_count(self) -> None:
        """Increment the share count for this meme"""
        self.share_count += 1


class MemeJob(Base):
    __tablename__ = "meme_jobs"
    
    id: str = Column(String, primary_key=True)
    user_id: Optional[str] = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    prompt: str = Column(Text, nullable=False)
    ai_provider: str = Column(String, default="openai", nullable=False, index=True)
    generation_mode: str = Column(String, default="auto", nullable=False, index=True)  # "auto" | "manual"
    manual_template_id: Optional[int] = Column(Integer, nullable=True)
    manual_captions: Optional[List[str]] = Column(JSON, nullable=True)
    status: str = Column(String, default="pending", index=True)  # "pending", "processing", "completed", "failed"
    result_meme_ids: List[str] = Column(JSON, nullable=True)  # List of generated meme IDs
    error_message: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes for job processing queries
    __table_args__ = (
        Index('ix_jobs_status_created', 'status', 'created_at'),
        Index('ix_jobs_user_status', 'user_id', 'status'),
    )
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed successfully"""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if job has failed"""
        return self.status == "failed"
    
    @property
    def is_processing(self) -> bool:
        """Check if job is currently being processed"""
        return self.status in ["pending", "processing"]
    
    def mark_as_processing(self) -> None:
        """Mark job as processing"""
        self.status = "processing"
        self.updated_at = func.now()
    
    def mark_as_completed(self, meme_ids: List[str]) -> None:
        """Mark job as completed with result meme IDs"""
        self.status = "completed"
        self.result_meme_ids = meme_ids
        self.updated_at = func.now()
    
    def mark_as_failed(self, error: str) -> None:
        """Mark job as failed with error message"""
        self.status = "failed"
        self.error_message = error
        self.updated_at = func.now()


class MemeTemplate(Base):
    __tablename__ = "meme_templates"
    
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String, nullable=False, unique=True, index=True)
    alternative_names: List[str] = Column(JSON, nullable=False)
    file_path: str = Column(String, nullable=False)
    font_path: str = Column(String, nullable=False)
    text_color: str = Column(String, nullable=False)
    text_stroke: bool = Column(Boolean, default=False)
    usage_instructions: str = Column(Text, nullable=False)
    number_of_text_fields: int = Column(Integer, nullable=False)
    # New canonical fields used by manual editor APIs.
    text_coordinates: Optional[List[List[int]]] = Column(JSON, nullable=True)
    text_coordinates_xy_wh: List[List[int]] = Column(JSON, nullable=False)
    example_output: List[str] = Column(JSON, nullable=False)
    image_url: Optional[str] = Column(String, nullable=True)
    preview_image_url: Optional[str] = Column(String, nullable=True)
    # Imgflip integration fields
    source: str = Column(String, nullable=False, default="local", index=True)  # "local" or "imgflip"
    imgflip_id: Optional[str] = Column(String, nullable=True, unique=True, index=True)
    box_count: Optional[int] = Column(Integer, nullable=True)
    last_synced_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def all_names(self) -> List[str]:
        """Get all names (primary + alternatives) for this template"""
        return [self.name] + self.alternative_names
    
    def matches_name(self, name: str) -> bool:
        """Check if given name matches this template (case-insensitive)"""
        name_lower = name.lower()
        return (
            self.name.lower() == name_lower or
            any(alt.lower() == name_lower for alt in self.alternative_names)
        )
    
    @property
    def has_text_stroke(self) -> bool:
        """Check if template uses text stroke"""
        return self.text_stroke
    
    def validate_text_count(self, text_list: List[str]) -> bool:
        """Validate that the provided text list matches expected field count"""
        return len(text_list) == self.number_of_text_fields