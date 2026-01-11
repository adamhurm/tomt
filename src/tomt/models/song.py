"""Song model representing an identified song."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Song(BaseModel):
    """A song that was identified from a TOMT post."""

    id: str = Field(description="Unique identifier")
    title: str = Field(description="Song title")
    artist: str = Field(description="Artist/band name")
    album: Optional[str] = Field(default=None)
    year: Optional[int] = Field(default=None, description="Release year")

    # Links to streaming services / more info
    spotify_url: Optional[str] = Field(default=None)
    youtube_url: Optional[str] = Field(default=None)
    apple_music_url: Optional[str] = Field(default=None)

    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    source_post_ids: list[str] = Field(default_factory=list, description="Posts where identified")
    discovery_count: int = Field(default=1, description="How many times this song was sought")

    # Original descriptions that led to finding this song
    original_descriptions: list[str] = Field(
        default_factory=list,
        description="How people described this song before knowing what it was",
    )

    class Config:
        from_attributes = True
