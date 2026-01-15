"""API routes for TOMT web service."""

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from tomt import __version__
from tomt.services.discovery import DiscoveryService
from tomt.web.schemas import (
    ApiKeys,
    DiscoverRequest,
    DiscoverResponse,
    ErrorResponse,
    HealthResponse,
    OpenRequestsRequest,
    PostResponse,
    ProcessRequest,
    ProcessResponse,
    RandomRequest,
    SearchRequest,
    SongResponse,
    SongsRequest,
    StatsRequest,
    StatsResponse,
)

router = APIRouter()

# Templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Database path
DB_PATH = os.getenv("TOMT_DB_PATH", "tomt.db")


def get_api_keys(
    keys: Optional[ApiKeys] = None,
    x_reddit_client_id: Optional[str] = None,
    x_reddit_client_secret: Optional[str] = None,
    x_anthropic_api_key: Optional[str] = None,
) -> tuple[str, Optional[str], str]:
    """Get API keys from request body, headers, or environment.

    Priority: Request body > Headers > Environment variables

    Returns:
        Tuple of (reddit_client_id, reddit_client_secret, anthropic_api_key)

    Raises:
        HTTPException: If required keys are missing
    """
    # Start with environment variables
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    # Override with headers if provided
    if x_reddit_client_id:
        reddit_client_id = x_reddit_client_id
    if x_reddit_client_secret:
        reddit_client_secret = x_reddit_client_secret
    if x_anthropic_api_key:
        anthropic_api_key = x_anthropic_api_key

    # Override with request body if provided
    if keys:
        if keys.reddit_client_id:
            reddit_client_id = keys.reddit_client_id
        if keys.reddit_client_secret:
            reddit_client_secret = keys.reddit_client_secret
        if keys.anthropic_api_key:
            anthropic_api_key = keys.anthropic_api_key

    # Validate required keys
    if not reddit_client_id:
        raise HTTPException(
            status_code=400,
            detail="Reddit client ID is required. Provide via request body, "
            "X-Reddit-Client-Id header, or REDDIT_CLIENT_ID env var.",
        )

    if not anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="Anthropic API key is required. Provide via request body, "
            "X-Anthropic-Api-Key header, or ANTHROPIC_API_KEY env var.",
        )

    return reddit_client_id, reddit_client_secret, anthropic_api_key


def get_service(
    keys: Optional[ApiKeys] = None,
    x_reddit_client_id: Optional[str] = None,
    x_reddit_client_secret: Optional[str] = None,
    x_anthropic_api_key: Optional[str] = None,
) -> DiscoveryService:
    """Create a DiscoveryService with the provided or default API keys."""
    reddit_client_id, reddit_client_secret, anthropic_api_key = get_api_keys(
        keys=keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    return DiscoveryService(
        reddit_client_id=reddit_client_id,
        anthropic_api_key=anthropic_api_key,
        reddit_client_secret=reddit_client_secret,
        db_path=DB_PATH,
    )


# Health check endpoint
@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
)
async def health_check():
    """Check service health and configuration status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        has_reddit_key=bool(os.getenv("REDDIT_CLIENT_ID")),
        has_anthropic_key=bool(os.getenv("ANTHROPIC_API_KEY")),
    )


# Web UI endpoint
@router.get("/", response_class=HTMLResponse, tags=["UI"], include_in_schema=False)
async def index(request: Request):
    """Serve the web UI."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "has_reddit_key": bool(os.getenv("REDDIT_CLIENT_ID")),
            "has_anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        },
    )


# API endpoints
@router.post(
    "/api/discover",
    response_model=DiscoverResponse,
    responses={400: {"model": ErrorResponse}},
    tags=["Discovery"],
    summary="Run discovery cycle",
    description="Scrape Reddit for song identification posts and extract song information.",
)
async def discover(
    request: DiscoverRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Run a discovery cycle to find new songs."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    try:
        results = await service.discover(
            scrape_mode=request.mode,
            scrape_limit=request.limit,
            process=request.process,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return DiscoverResponse(
        posts_scraped=results["posts_scraped"],
        songs_found=results["songs_found"],
        total_posts=results["total_posts"],
        total_songs=results["total_songs"],
        solve_rate=results["solve_rate"],
    )


@router.post(
    "/api/songs",
    response_model=list[SongResponse],
    responses={400: {"model": ErrorResponse}},
    tags=["Songs"],
    summary="List discovered songs",
    description="Get discovered songs ordered by search frequency.",
)
async def get_songs(
    request: SongsRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """List discovered songs, ordered by how often they were sought."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    songs = service.get_discoveries(limit=request.limit)

    return [
        SongResponse(
            id=song.id,
            title=song.title,
            artist=song.artist,
            album=song.album,
            year=song.year,
            spotify_url=song.spotify_url,
            youtube_url=song.youtube_url,
            apple_music_url=song.apple_music_url,
            discovered_at=song.discovered_at,
            discovery_count=song.discovery_count,
        )
        for song in songs
    ]


@router.get(
    "/api/songs",
    response_model=list[SongResponse],
    tags=["Songs"],
    summary="List discovered songs (GET)",
    description="Get discovered songs ordered by search frequency. Uses environment API keys.",
)
async def get_songs_simple(
    limit: int = 20,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """List discovered songs with simple GET request."""
    service = get_service(
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    songs = service.get_discoveries(limit=limit)

    return [
        SongResponse(
            id=song.id,
            title=song.title,
            artist=song.artist,
            album=song.album,
            year=song.year,
            spotify_url=song.spotify_url,
            youtube_url=song.youtube_url,
            apple_music_url=song.apple_music_url,
            discovered_at=song.discovered_at,
            discovery_count=song.discovery_count,
        )
        for song in songs
    ]


@router.post(
    "/api/search",
    response_model=list[SongResponse],
    responses={400: {"model": ErrorResponse}},
    tags=["Songs"],
    summary="Search songs",
    description="Search for songs by title or artist.",
)
async def search_songs(
    request: SearchRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Search for songs by title or artist."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    songs = service.search(query=request.query, limit=request.limit)

    return [
        SongResponse(
            id=song.id,
            title=song.title,
            artist=song.artist,
            album=song.album,
            year=song.year,
            spotify_url=song.spotify_url,
            youtube_url=song.youtube_url,
            apple_music_url=song.apple_music_url,
            discovered_at=song.discovered_at,
            discovery_count=song.discovery_count,
        )
        for song in songs
    ]


@router.get(
    "/api/search",
    response_model=list[SongResponse],
    tags=["Songs"],
    summary="Search songs (GET)",
    description="Search for songs by title or artist. Uses environment API keys.",
)
async def search_songs_simple(
    query: str,
    limit: int = 20,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Search for songs with simple GET request."""
    service = get_service(
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    songs = service.search(query=query, limit=limit)

    return [
        SongResponse(
            id=song.id,
            title=song.title,
            artist=song.artist,
            album=song.album,
            year=song.year,
            spotify_url=song.spotify_url,
            youtube_url=song.youtube_url,
            apple_music_url=song.apple_music_url,
            discovered_at=song.discovered_at,
            discovery_count=song.discovery_count,
        )
        for song in songs
    ]


@router.post(
    "/api/random",
    response_model=Optional[SongResponse],
    responses={400: {"model": ErrorResponse}},
    tags=["Songs"],
    summary="Get random song",
    description="Roll the dice and get a random song from the database.",
)
async def get_random_song(
    request: RandomRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Get a random song from the database."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    song = service.db.get_random_song()

    if not song:
        return None

    return SongResponse(
        id=song.id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        year=song.year,
        spotify_url=song.spotify_url,
        youtube_url=song.youtube_url,
        apple_music_url=song.apple_music_url,
        discovered_at=song.discovered_at,
        discovery_count=song.discovery_count,
    )


@router.get(
    "/api/random",
    response_model=Optional[SongResponse],
    tags=["Songs"],
    summary="Get random song (GET)",
    description="Roll the dice and get a random song from the database. Uses environment API keys.",
)
async def get_random_song_simple(
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Get a random song with simple GET request."""
    service = get_service(
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    song = service.db.get_random_song()

    if not song:
        return None

    return SongResponse(
        id=song.id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        year=song.year,
        spotify_url=song.spotify_url,
        youtube_url=song.youtube_url,
        apple_music_url=song.apple_music_url,
        discovered_at=song.discovered_at,
        discovery_count=song.discovery_count,
    )


@router.post(
    "/api/open-requests",
    response_model=list[PostResponse],
    responses={400: {"model": ErrorResponse}},
    tags=["Posts"],
    summary="List open requests",
    description="Get currently open song identification requests.",
)
async def get_open_requests(
    request: OpenRequestsRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Show currently open song identification requests."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    posts = service.get_open_requests(limit=request.limit)

    return [
        PostResponse(
            id=post.id,
            subreddit=post.subreddit,
            title=post.title,
            body=post.body,
            author=post.author,
            url=post.url,
            created_at=post.created_at,
            status=post.status.value,
            score=post.score,
            num_comments=post.num_comments,
            audio_links=post.audio_links,
            description=post.description,
        )
        for post in posts
    ]


@router.get(
    "/api/open-requests",
    response_model=list[PostResponse],
    tags=["Posts"],
    summary="List open requests (GET)",
    description="Get currently open song identification requests. Uses environment API keys.",
)
async def get_open_requests_simple(
    limit: int = 20,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """List open requests with simple GET request."""
    service = get_service(
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    posts = service.get_open_requests(limit=limit)

    return [
        PostResponse(
            id=post.id,
            subreddit=post.subreddit,
            title=post.title,
            body=post.body,
            author=post.author,
            url=post.url,
            created_at=post.created_at,
            status=post.status.value,
            score=post.score,
            num_comments=post.num_comments,
            audio_links=post.audio_links,
            description=post.description,
        )
        for post in posts
    ]


@router.post(
    "/api/stats",
    response_model=StatsResponse,
    responses={400: {"model": ErrorResponse}},
    tags=["System"],
    summary="Get statistics",
    description="Get database statistics and metrics.",
)
async def get_stats(
    request: StatsRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Show database statistics."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    db_stats = service.db.get_stats()

    return StatsResponse(
        total_posts=db_stats["total_posts"],
        solved_posts=db_stats["solved_posts"],
        unsolved_posts=db_stats["unsolved_posts"],
        solve_rate=db_stats["solve_rate"],
        total_songs=db_stats["total_songs"],
    )


@router.get(
    "/api/stats",
    response_model=StatsResponse,
    tags=["System"],
    summary="Get statistics (GET)",
    description="Get database statistics and metrics. Uses environment API keys.",
)
async def get_stats_simple(
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Get stats with simple GET request."""
    service = get_service(
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    db_stats = service.db.get_stats()

    return StatsResponse(
        total_posts=db_stats["total_posts"],
        solved_posts=db_stats["solved_posts"],
        unsolved_posts=db_stats["unsolved_posts"],
        solve_rate=db_stats["solve_rate"],
        total_songs=db_stats["total_songs"],
    )


@router.post(
    "/api/process",
    response_model=ProcessResponse,
    responses={400: {"model": ErrorResponse}},
    tags=["Discovery"],
    summary="Process solved posts",
    description="Process solved posts to extract song information.",
)
async def process_posts(
    request: ProcessRequest,
    x_reddit_client_id: Optional[str] = Header(None),
    x_reddit_client_secret: Optional[str] = Header(None),
    x_anthropic_api_key: Optional[str] = Header(None),
):
    """Process solved posts to extract song information."""
    service = get_service(
        keys=request.keys,
        x_reddit_client_id=x_reddit_client_id,
        x_reddit_client_secret=x_reddit_client_secret,
        x_anthropic_api_key=x_anthropic_api_key,
    )

    try:
        songs_found = await service.process_solved_posts(limit=request.limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ProcessResponse(songs_found=songs_found)
