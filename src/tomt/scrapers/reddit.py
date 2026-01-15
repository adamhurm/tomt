"""Reddit scraper for TOMT subreddits."""

import re
from datetime import datetime
from typing import Iterator, Optional

import praw
from praw.models import Submission

from tomt.models.post import Post, PostStatus


# Default subreddits to scrape for music-related TOMT posts
DEFAULT_SUBREDDITS = [
    "tipofmytongue",
    "WhatsThisSong",
    "NameThatSong",
]

# Patterns to identify music-related posts in r/tipofmytongue
MUSIC_FLAIR_PATTERNS = [
    r"\[TOMT\]\s*\[(?:song|music|band|artist)",
    r"\[song\]",
    r"\[music\]",
]

# Common audio/video hosting patterns
AUDIO_LINK_PATTERNS = [
    r"(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)",
    r"(https?://(?:www\.)?youtu\.be/[\w-]+)",
    r"(https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+)",
    r"(https?://(?:www\.)?vocaroo\.com/[\w-]+)",
    r"(https?://voca\.ro/[\w-]+)",
    r"(https?://(?:www\.)?clyp\.it/[\w-]+)",
    r"(https?://(?:www\.)?onlinesequencer\.net/[\w-]+)",
    r"(https?://(?:www\.)?spotify\.com/track/[\w-]+)",
    r"(https?://open\.spotify\.com/track/[\w-]+)",
    r"(https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+)",
    r"(https?://(?:www\.)?reddit\.com/link/[\w-]+/video/[\w-]+)",
    r"(https?://v\.redd\.it/[\w-]+)",
    r"(https?://streamable\.com/[\w-]+)",
]


class RedditScraper:
    """Scrapes music-related TOMT posts from Reddit."""

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        user_agent: str = "TOMT Music Discovery Bot v0.1",
        subreddits: Optional[list[str]] = None,
    ):
        """Initialize the Reddit scraper.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret (optional for installed apps)
            user_agent: User agent string for API requests
            subreddits: List of subreddits to scrape (defaults to music TOMT subs)
        """
        # Support both script apps (with secret) and installed apps (without)
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret or "",
            user_agent=user_agent,
        )
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self._music_patterns = [re.compile(p, re.IGNORECASE) for p in MUSIC_FLAIR_PATTERNS]
        self._audio_patterns = [re.compile(p, re.IGNORECASE) for p in AUDIO_LINK_PATTERNS]

    def _is_music_post(self, submission: Submission) -> bool:
        """Check if a post is music-related.

        For dedicated music subreddits, all posts are music-related.
        For r/tipofmytongue, we check the flair/title.
        """
        subreddit_name = submission.subreddit.display_name.lower()

        # Dedicated music subs - all posts are relevant
        if subreddit_name in ["whatsthissong", "namethatsong"]:
            return True

        # For r/tipofmytongue, check if it's music-related
        if subreddit_name == "tipofmytongue":
            title = submission.title.lower()
            flair = (submission.link_flair_text or "").lower()

            # Check flair
            if any(term in flair for term in ["song", "music"]):
                return True

            # Check title patterns
            for pattern in self._music_patterns:
                if pattern.search(submission.title):
                    return True

            return False

        return True

    def _extract_audio_links(self, text: str) -> list[str]:
        """Extract audio/video links from text."""
        links = []
        for pattern in self._audio_patterns:
            matches = pattern.findall(text)
            links.extend(matches)
        return list(set(links))  # Deduplicate

    def _determine_status(self, submission: Submission) -> PostStatus:
        """Determine the status of a post based on flair and other indicators."""
        flair = (submission.link_flair_text or "").lower()

        if "solved" in flair or "answered" in flair:
            return PostStatus.SOLVED
        if "open" in flair or "searching" in flair:
            return PostStatus.OPEN
        if "unsolved" in flair or "closed" in flair:
            return PostStatus.UNSOLVED

        # Default to unknown
        return PostStatus.UNKNOWN

    def _submission_to_post(self, submission: Submission) -> Post:
        """Convert a Reddit submission to a Post model."""
        body = submission.selftext or ""

        # Extract audio links from title and body
        audio_links = self._extract_audio_links(submission.title + " " + body)

        return Post(
            id=submission.id,
            subreddit=submission.subreddit.display_name,
            title=submission.title,
            body=body,
            author=str(submission.author) if submission.author else "[deleted]",
            url=f"https://reddit.com{submission.permalink}",
            created_at=datetime.utcfromtimestamp(submission.created_utc),
            status=self._determine_status(submission),
            flair=submission.link_flair_text,
            score=submission.score,
            num_comments=submission.num_comments,
            audio_links=audio_links,
        )

    def scrape_new(self, limit: int = 100) -> Iterator[Post]:
        """Scrape new posts from configured subreddits.

        Args:
            limit: Maximum number of posts to fetch per subreddit

        Yields:
            Post objects for music-related TOMT posts
        """
        for subreddit_name in self.subreddits:
            subreddit = self.reddit.subreddit(subreddit_name)

            for submission in subreddit.new(limit=limit):
                if self._is_music_post(submission):
                    yield self._submission_to_post(submission)

    def scrape_hot(self, limit: int = 100) -> Iterator[Post]:
        """Scrape hot posts from configured subreddits.

        Args:
            limit: Maximum number of posts to fetch per subreddit

        Yields:
            Post objects for music-related TOMT posts
        """
        for subreddit_name in self.subreddits:
            subreddit = self.reddit.subreddit(subreddit_name)

            for submission in subreddit.hot(limit=limit):
                if self._is_music_post(submission):
                    yield self._submission_to_post(submission)

    def scrape_solved(self, limit: int = 100) -> Iterator[Post]:
        """Scrape solved posts - these are valuable for building our song database.

        Args:
            limit: Maximum number of posts to fetch per subreddit

        Yields:
            Post objects that have been solved
        """
        for subreddit_name in self.subreddits:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Search for posts with solved flair
            for submission in subreddit.search("flair:solved OR flair:answered", limit=limit):
                if self._is_music_post(submission):
                    post = self._submission_to_post(submission)
                    post.status = PostStatus.SOLVED
                    yield post

    def get_post_with_comments(self, post_id: str) -> tuple[Post, list[dict]]:
        """Fetch a specific post with its comments.

        Args:
            post_id: Reddit post ID

        Returns:
            Tuple of (Post, list of comment dicts)
        """
        submission = self.reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)  # Flatten comment tree

        post = self._submission_to_post(submission)

        comments = []
        for comment in submission.comments.list():
            comments.append(
                {
                    "id": comment.id,
                    "author": str(comment.author) if comment.author else "[deleted]",
                    "body": comment.body,
                    "score": comment.score,
                    "created_at": datetime.utcfromtimestamp(comment.created_utc),
                    "is_submitter": comment.is_submitter,
                    "is_op_reply": comment.parent_id.startswith("t3_"),  # Reply to post
                }
            )

        return post, comments
