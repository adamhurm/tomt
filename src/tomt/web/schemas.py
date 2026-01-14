"""Pydantic schemas for web API requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiKeys(BaseModel):
    """API keys that can be provided by users (BYOK - bring your own keys)."""

    reddit_client_id: Optional[str] = Field(
        default=None,
        description="Reddit API client ID (overrides env var)",
    )
    reddit_client_secret: Optional[str] = Field(
        default=None,
        description="Reddit API client secret (optional for installed apps)",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key (overrides env var)",
    )


class DiscoverRequest(BaseModel):
    """Request for discover endpoint."""

    mode: str = Field(
        default="solved",
        description="Scraping mode: new, hot, or solved",
        pattern="^(new|hot|solved)$",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum posts per subreddit",
    )
    process: bool = Field(
        default=True,
        description="Whether to process solved posts for song extraction",
    )
    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class DiscoverResponse(BaseModel):
    """Response from discover endpoint."""

    posts_scraped: int
    songs_found: int
    total_posts: int
    total_songs: int
    solve_rate: float


class SongsRequest(BaseModel):
    """Request for songs endpoint."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return",
    )
    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class SongResponse(BaseModel):
    """Response model for a song."""

    id: str
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    spotify_url: Optional[str] = None
    youtube_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    discovered_at: datetime
    discovery_count: int


class SearchRequest(BaseModel):
    """Request for search endpoint."""

    query: str = Field(
        min_length=1,
        description="Search query for title or artist",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return",
    )
    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class OpenRequestsRequest(BaseModel):
    """Request for open requests endpoint."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return",
    )
    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class RandomRequest(BaseModel):
    """Request for random song endpoint."""

    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class PostResponse(BaseModel):
    """Response model for a post."""

    id: str
    subreddit: str
    title: str
    body: str
    author: str
    url: str
    created_at: datetime
    status: str
    score: int
    num_comments: int
    audio_links: list[str]
    description: Optional[str] = None


class StatsRequest(BaseModel):
    """Request for stats endpoint."""

    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class StatsResponse(BaseModel):
    """Response from stats endpoint."""

    total_posts: int
    solved_posts: int
    unsolved_posts: int
    solve_rate: float
    total_songs: int


class ProcessRequest(BaseModel):
    """Request for process endpoint."""

    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum posts to process",
    )
    keys: Optional[ApiKeys] = Field(
        default=None,
        description="Optional API keys (BYOK)",
    )


class ProcessResponse(BaseModel):
    """Response from process endpoint."""

    songs_found: int


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    has_reddit_key: bool
    has_anthropic_key: bool
