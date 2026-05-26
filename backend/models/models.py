from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, JSON, String, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.session import Base


class User(Base):
    __tablename__ = "users"

    id: str = Column(String, primary_key=True)
    email: str = Column(String, unique=True, nullable=False, index=True)
    plan: str = Column(String, default="free", index=True)
    daily_limit: int = Column(Integer, default=5)
    daily_used: int = Column(Integer, default=0)
    api_key: Optional[str] = Column(String, nullable=True, unique=True, index=True)  # stores SHA-256 hash
    api_key_prefix: Optional[str] = Column(String, nullable=True)  # display prefix, e.g. "mgpt_ab12…"
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    preferences: dict = Column(JSON, default={}, nullable=False)

    memes = relationship("GeneratedMeme", back_populates="user", cascade="all, delete-orphan")
    jobs  = relationship("MemeJob", backref="user_ref")

    @property
    def is_premium(self) -> bool:
        return self.plan in ("pro", "api")

    @property
    def has_api_access(self) -> bool:
        return self.plan == "api" and self.api_key is not None

    @property
    def remaining_generations(self) -> int:
        return max(0, (self.daily_limit or 5) - (self.daily_used or 0))

    def can_generate(self) -> bool:
        return (self.daily_used or 0) < (self.daily_limit or 5)


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
    trending_score: float = Column(Float, default=0.0, nullable=False, index=True)
    is_public: bool = Column(Boolean, default=True, index=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="memes")

    __table_args__ = (
        Index("ix_memes_public_created",   "is_public",     "created_at"),
        Index("ix_memes_template_created", "template_name", "created_at"),
        Index("ix_memes_user_created",     "user_id",       "created_at"),
        Index("ix_memes_public_trending",  "is_public",     "trending_score"),
    )

    @property
    def is_anonymous(self) -> bool:
        return self.user_id is None

    @property
    def display_url(self) -> str:
        return self.thumbnail_url or self.image_url

    def increment_share_count(self) -> None:
        self.share_count += 1


class MemeJob(Base):
    __tablename__ = "meme_jobs"

    id: str = Column(String, primary_key=True)
    user_id: Optional[str] = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    prompt: str = Column(Text, nullable=False)
    ai_provider: str = Column(String, default="gemini", nullable=False, index=True)
    generation_mode: str = Column(String, default="auto", nullable=False, index=True)
    manual_template_id: Optional[int] = Column(Integer, nullable=True)
    manual_captions: Optional[List[str]] = Column(JSON, nullable=True)
    status: str = Column(String, default="pending", index=True)
    result_meme_ids: Optional[List[str]] = Column(JSON, nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_jobs_status_created", "status",  "created_at"),
        Index("ix_jobs_user_status",    "user_id", "status"),
    )

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_processing(self) -> bool:
        return self.status in ("pending", "processing")

    def mark_as_processing(self) -> None:
        self.status = "processing"

    def mark_as_completed(self, meme_ids: List[str]) -> None:
        self.status = "completed"
        self.result_meme_ids = meme_ids

    def mark_as_failed(self, error: str) -> None:
        self.status = "failed"
        self.error_message = error


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

    # Coordinate fields
    text_coordinates: Optional[List[List[int]]] = Column(JSON, nullable=True)
    text_coordinates_xy_wh: List[List[int]] = Column(JSON, nullable=False)

    example_output: List[str] = Column(JSON, nullable=False)
    image_url: Optional[str] = Column(String, nullable=True)
    preview_image_url: Optional[str] = Column(String, nullable=True)

    # Fallback CDN URL for templates without local files
    fallback_url: Optional[str] = Column(String, nullable=True)

    # Template source metadata
    source: str = Column(String, nullable=False, default="local", index=True)

    # Gen-Z metadata
    gen_z_ready: bool = Column(Boolean, default=False, index=True)
    vibe_tags: Optional[List[str]] = Column(JSON, nullable=True)

    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def all_names(self) -> List[str]:
        return [self.name] + (self.alternative_names or [])

    def matches_name(self, name: str) -> bool:
        nl = name.lower()
        return self.name.lower() == nl or any(a.lower() == nl for a in (self.alternative_names or []))

    @property
    def has_text_stroke(self) -> bool:
        return self.text_stroke

    def validate_text_count(self, text_list: List[str]) -> bool:
        return len(text_list) == self.number_of_text_fields

    @property
    def effective_image_url(self) -> Optional[str]:
        """Return the best available image URL."""
        return self.image_url or (
            f"/api/memes/proxy-image?url={self.fallback_url}" if self.fallback_url else None
        )
