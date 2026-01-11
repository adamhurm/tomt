"""Post model representing a TOMT request."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PostStatus(str, Enum):
    """Status of a TOMT post."""

    OPEN = "open"  # Still looking for the song
    SOLVED = "solved"  # Song has been identified
    UNSOLVED = "unsolved"  # Marked as closed but not solved
    UNKNOWN = "unknown"  # Status cannot be determined


class Post(BaseModel):
    """A post from a TOMT subreddit."""

    id: str = Field(description="Unique identifier (Reddit post ID)")
    subreddit: str = Field(description="Source subreddit name")
    title: str = Field(description="Post title")
    body: str = Field(description="Post body/selftext")
    author: str = Field(description="Reddit username of poster")
    url: str = Field(description="Permalink to the post")
    created_at: datetime = Field(description="When the post was created")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    status: PostStatus = Field(default=PostStatus.UNKNOWN)
    flair: Optional[str] = Field(default=None, description="Post flair if any")
    score: int = Field(default=0, description="Post score/upvotes")
    num_comments: int = Field(default=0)

    # Extracted information
    audio_links: list[str] = Field(default_factory=list, description="Links to audio/video")
    description: Optional[str] = Field(default=None, description="Cleaned description of song")

    # Solution information (if solved)
    solution_comment_id: Optional[str] = Field(default=None)
    solution_text: Optional[str] = Field(default=None)
    identified_song_id: Optional[str] = Field(default=None, description="Link to Song if identified")

    class Config:
        from_attributes = True
