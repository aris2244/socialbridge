from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SAEnum
from sqlalchemy.sql import func
from backend.database import Base
import enum

class PostStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    posted     = "posted"
    failed     = "failed"

class PlatformStatus(str, enum.Enum):
    pending = "pending"
    posted  = "posted"
    failed  = "failed"

class Post(Base):
    """One row per scheduled video upload."""
    __tablename__ = "posts"

    id           = Column(Integer, primary_key=True, index=True)
    video_path   = Column(String,  nullable=False)  # relative path under /uploads
    caption      = Column(Text,    nullable=True)   # AI-generated caption + hashtags
    hashtags     = Column(Text,    nullable=True)   # JSON: ["#shorts", "#reels", ...]
    user_hint    = Column(Text,    nullable=True)   # optional description the user typed
    scheduled_at = Column(DateTime, nullable=False) # UTC datetime to publish
    status       = Column(SAEnum(PostStatus), default=PostStatus.pending, nullable=False)
    created_at   = Column(DateTime, server_default=func.now())

class PostPlatform(Base):
    """One row per (post × platform) combination."""
    __tablename__ = "post_platforms"

    id               = Column(Integer, primary_key=True, index=True)
    post_id          = Column(Integer, nullable=False, index=True)
    platform         = Column(String,  nullable=False)  # "youtube" | "instagram" | "facebook" | "tiktok" | "twitter"
    status           = Column(SAEnum(PlatformStatus), default=PlatformStatus.pending, nullable=False)
    platform_post_id = Column(String, nullable=True)   # ID returned by the platform
    error_message    = Column(Text,   nullable=True)
    posted_at        = Column(DateTime, nullable=True)

class Account(Base):
    """OAuth credentials for each platform (one row per platform)."""
    __tablename__ = "accounts"

    id           = Column(Integer, primary_key=True, index=True)
    platform     = Column(String, nullable=False, unique=True)
    account_name = Column(String, nullable=True)
    access_token  = Column(Text,  nullable=True)
    refresh_token = Column(Text,  nullable=True)
    expires_at   = Column(DateTime, nullable=True)
    extra_data   = Column(Text,    nullable=True)  # JSON: page_id, channel_id, etc.
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())