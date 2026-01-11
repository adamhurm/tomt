"""SQLite database storage for TOMT service."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from tomt.models.post import Post, PostStatus
from tomt.models.song import Song


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


# Association table for songs and posts
song_posts = Table(
    "song_posts",
    Base.metadata,
    Column("song_id", String, ForeignKey("songs.id"), primary_key=True),
    Column("post_id", String, ForeignKey("posts.id"), primary_key=True),
)


class PostRecord(Base):
    """SQLAlchemy model for posts."""

    __tablename__ = "posts"

    id = Column(String, primary_key=True)
    subreddit = Column(String, nullable=False, index=True)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    author = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, nullable=False, default="unknown")
    flair = Column(String, nullable=True)
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)
    audio_links_json = Column(Text, default="[]")
    description = Column(Text, nullable=True)
    solution_comment_id = Column(String, nullable=True)
    solution_text = Column(Text, nullable=True)
    identified_song_id = Column(String, ForeignKey("songs.id"), nullable=True)

    identified_song = relationship("SongRecord", back_populates="source_posts")

    def to_model(self) -> Post:
        """Convert to Pydantic model."""
        return Post(
            id=self.id,
            subreddit=self.subreddit,
            title=self.title,
            body=self.body,
            author=self.author,
            url=self.url,
            created_at=self.created_at,
            scraped_at=self.scraped_at,
            status=PostStatus(self.status),
            flair=self.flair,
            score=self.score,
            num_comments=self.num_comments,
            audio_links=json.loads(self.audio_links_json),
            description=self.description,
            solution_comment_id=self.solution_comment_id,
            solution_text=self.solution_text,
            identified_song_id=self.identified_song_id,
        )

    @classmethod
    def from_model(cls, post: Post) -> "PostRecord":
        """Create from Pydantic model."""
        return cls(
            id=post.id,
            subreddit=post.subreddit,
            title=post.title,
            body=post.body,
            author=post.author,
            url=post.url,
            created_at=post.created_at,
            scraped_at=post.scraped_at,
            status=post.status.value,
            flair=post.flair,
            score=post.score,
            num_comments=post.num_comments,
            audio_links_json=json.dumps(post.audio_links),
            description=post.description,
            solution_comment_id=post.solution_comment_id,
            solution_text=post.solution_text,
            identified_song_id=post.identified_song_id,
        )


class SongRecord(Base):
    """SQLAlchemy model for songs."""

    __tablename__ = "songs"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, index=True)
    artist = Column(String, nullable=False, index=True)
    album = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    spotify_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    apple_music_url = Column(String, nullable=True)
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    discovery_count = Column(Integer, default=1)
    original_descriptions_json = Column(Text, default="[]")

    source_posts = relationship("PostRecord", back_populates="identified_song")

    def to_model(self) -> Song:
        """Convert to Pydantic model."""
        return Song(
            id=self.id,
            title=self.title,
            artist=self.artist,
            album=self.album,
            year=self.year,
            spotify_url=self.spotify_url,
            youtube_url=self.youtube_url,
            apple_music_url=self.apple_music_url,
            discovered_at=self.discovered_at,
            source_post_ids=[p.id for p in self.source_posts],
            discovery_count=self.discovery_count,
            original_descriptions=json.loads(self.original_descriptions_json),
        )

    @classmethod
    def from_model(cls, song: Song) -> "SongRecord":
        """Create from Pydantic model."""
        return cls(
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
            original_descriptions_json=json.dumps(song.original_descriptions),
        )


class Database:
    """SQLite database interface for TOMT service."""

    def __init__(self, db_path: str = "tomt.db"):
        """Initialize the database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self):
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    # Post operations
    def save_post(self, post: Post) -> None:
        """Save or update a post."""
        with self.get_session() as session:
            existing = session.get(PostRecord, post.id)
            if existing:
                # Update existing
                for key, value in PostRecord.from_model(post).__dict__.items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
            else:
                session.add(PostRecord.from_model(post))
            session.commit()

    def get_post(self, post_id: str) -> Optional[Post]:
        """Get a post by ID."""
        with self.get_session() as session:
            record = session.get(PostRecord, post_id)
            return record.to_model() if record else None

    def get_posts(
        self,
        subreddit: Optional[str] = None,
        status: Optional[PostStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Post]:
        """Get posts with optional filtering."""
        with self.get_session() as session:
            query = session.query(PostRecord)

            if subreddit:
                query = query.filter(PostRecord.subreddit == subreddit)
            if status:
                query = query.filter(PostRecord.status == status.value)

            query = query.order_by(PostRecord.created_at.desc())
            query = query.offset(offset).limit(limit)

            return [r.to_model() for r in query.all()]

    def get_unsolved_posts(self, limit: int = 100) -> list[Post]:
        """Get posts that haven't been solved yet."""
        with self.get_session() as session:
            query = (
                session.query(PostRecord)
                .filter(PostRecord.status.in_(["open", "unknown"]))
                .order_by(PostRecord.created_at.desc())
                .limit(limit)
            )
            return [r.to_model() for r in query.all()]

    # Song operations
    def save_song(self, song: Song, source_post: Optional[Post] = None) -> None:
        """Save or update a song."""
        with self.get_session() as session:
            existing = session.get(SongRecord, song.id)
            if existing:
                # Update discovery count
                existing.discovery_count += 1
                # Add description if new
                descriptions = json.loads(existing.original_descriptions_json)
                for desc in song.original_descriptions:
                    if desc not in descriptions:
                        descriptions.append(desc)
                existing.original_descriptions_json = json.dumps(descriptions)
            else:
                session.add(SongRecord.from_model(song))

            # Link to source post if provided
            if source_post:
                post_record = session.get(PostRecord, source_post.id)
                if post_record:
                    post_record.identified_song_id = song.id

            session.commit()

    def get_song(self, song_id: str) -> Optional[Song]:
        """Get a song by ID."""
        with self.get_session() as session:
            record = session.get(SongRecord, song_id)
            return record.to_model() if record else None

    def search_songs(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Song]:
        """Search songs by title or artist."""
        with self.get_session() as session:
            search_query = session.query(SongRecord).filter(
                (SongRecord.title.ilike(f"%{query}%"))
                | (SongRecord.artist.ilike(f"%{query}%"))
            )
            search_query = search_query.order_by(SongRecord.discovery_count.desc())
            search_query = search_query.limit(limit)

            return [r.to_model() for r in search_query.all()]

    def get_most_sought_songs(self, limit: int = 20) -> list[Song]:
        """Get songs that have been searched for most often."""
        with self.get_session() as session:
            query = (
                session.query(SongRecord)
                .order_by(SongRecord.discovery_count.desc())
                .limit(limit)
            )
            return [r.to_model() for r in query.all()]

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self.get_session() as session:
            total_posts = session.query(PostRecord).count()
            solved_posts = (
                session.query(PostRecord).filter(PostRecord.status == "solved").count()
            )
            total_songs = session.query(SongRecord).count()

            return {
                "total_posts": total_posts,
                "solved_posts": solved_posts,
                "unsolved_posts": total_posts - solved_posts,
                "solve_rate": solved_posts / total_posts if total_posts > 0 else 0,
                "total_songs": total_songs,
            }
