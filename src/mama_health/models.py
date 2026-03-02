"""Data models for Reddit and patient journey data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RedditComment(BaseModel):
    """Model for a Reddit comment."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "comment_id": "abc123",
                "post_id": "xyz789",
                "author": "redditor",
                "text": "I had similar symptoms...",
                "score": 42,
                "created_at": "2024-01-15T10:30:00",
                "parent_comment_id": None,
            }
        }
    )

    comment_id: str = Field(..., description="Reddit comment ID")
    post_id: str = Field(..., description="Parent post ID")
    author: str = Field(..., description="Comment author username")
    text: str = Field(..., description="Comment text content")
    score: int = Field(..., description="Comment upvote score")
    created_at: datetime = Field(..., description="When comment was created")
    parent_comment_id: Optional[str] = Field(None, description="Parent comment ID if reply")


class RedditPost(BaseModel):
    """Model for a Reddit post with associated comments."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_id": "xyz789",
                "title": "Diagnosed with Crohn's last week",
                "content": "I was just diagnosed...",
                "author": "patient123",
                "subreddit": "Crohns",
                "score": 156,
                "num_comments": 23,
                "created_at": "2024-01-15T08:00:00",
                "url": "https://reddit.com/r/Crohns/...",
                "comments": [],
            }
        }
    )

    post_id: str = Field(..., description="Reddit post ID")
    title: str = Field(..., description="Post title")
    content: str = Field(..., description="Post content/selftext")
    author: str = Field(..., description="Post author username")
    subreddit: str = Field(..., description="Subreddit name")
    score: int = Field(..., description="Post upvote score")
    num_comments: int = Field(..., description="Number of comments")
    created_at: datetime = Field(..., description="When post was created")
    url: str = Field(..., description="Post URL")
    comments: list[RedditComment] = Field(default_factory=list, description="Associated comments")


class PatientJourneyEvent(BaseModel):
    """Model for extracted patient journey event."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "evt_001",
                "source_post_id": "xyz789",
                "source_comment_id": None,
                "event_type": "diagnosis",
                "description": "User was diagnosed with Crohn's disease",
                "mentioned_entity": "Crohn's disease",
                "entity_type": "condition",
                "timestamp_mentioned": "2023-12-15",
                "timestamp_posted": "2024-01-15T08:00:00",
                "confidence": 0.95,
            }
        }
    )

    event_id: str = Field(..., description="Unique event identifier")
    source_post_id: str = Field(..., description="Source Reddit post ID")
    source_comment_id: Optional[str] = Field(None, description="Source comment ID if from comment")
    event_type: str = Field(..., description="Type of event (symptom, diagnosis, treatment, etc)")
    description: str = Field(..., description="Human-readable description")
    mentioned_entity: str = Field(..., description="Main entity mentioned (e.g. medication name)")
    entity_type: str = Field(..., description="Type of entity (medication, symptom, procedure, etc)")
    timestamp_mentioned: Optional[datetime] = Field(None, description="When event occurred")
    timestamp_posted: datetime = Field(..., description="When post/comment was made")
    confidence: float = Field(..., description="Extraction confidence score (0-1)")
