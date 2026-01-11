"""Parser service for extracting song information using Claude."""

import json
from typing import Optional

import anthropic

from tomt.models.post import Post
from tomt.models.song import Song


EXTRACT_DESCRIPTION_PROMPT = """You are analyzing a "tip of my tongue" post where someone is trying to identify a song they can't remember.

Extract a clean, searchable description of the song from this post. Focus on:
- Genre or style mentioned
- Era/decade the song might be from
- Memorable lyrics or phrases
- Instruments or sounds mentioned
- Where they heard it (movie, commercial, etc.)
- Mood or feeling of the song
- Male/female vocals
- Any other distinctive characteristics

Post Title: {title}

Post Body:
{body}

Respond with a JSON object:
{{
    "description": "A clean 1-3 sentence description of the song being searched for",
    "genre_hints": ["list", "of", "possible", "genres"],
    "era_hint": "decade or year range if mentioned, null otherwise",
    "has_lyrics": true/false,
    "partial_lyrics": "any lyrics mentioned, or null",
    "mood": "mood/feeling if described, or null",
    "voice_type": "male/female/unknown",
    "context": "where they heard it (movie, game, etc.) or null"
}}"""

EXTRACT_SOLUTION_PROMPT = """You are analyzing comments on a "tip of my tongue" post that has been marked as SOLVED.

The original poster was looking for a song. Find the comment that correctly identified the song.

Post Title: {title}
Post Body: {body}

Comments:
{comments}

If you can identify the solution, respond with a JSON object:
{{
    "found": true,
    "song_title": "Title of the song",
    "artist": "Artist name",
    "album": "Album name if mentioned, or null",
    "year": year as integer if mentioned, or null,
    "comment_id": "ID of the comment with the answer",
    "confidence": "high/medium/low"
}}

If you cannot find a clear solution, respond with:
{{
    "found": false,
    "reason": "Brief explanation why"
}}"""


class PostParser:
    """Parses TOMT posts to extract song information using Claude."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """Initialize the parser.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_description(self, post: Post) -> dict:
        """Extract a clean description from a TOMT post.

        Args:
            post: The Post to analyze

        Returns:
            Dict with extracted description and metadata
        """
        prompt = EXTRACT_DESCRIPTION_PROMPT.format(
            title=post.title,
            body=post.body,
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            return {
                "description": post.title,
                "genre_hints": [],
                "era_hint": None,
                "has_lyrics": False,
                "partial_lyrics": None,
                "mood": None,
                "voice_type": "unknown",
                "context": None,
            }

    def extract_solution(self, post: Post, comments: list[dict]) -> Optional[Song]:
        """Extract the solution from a solved post's comments.

        Args:
            post: The solved Post
            comments: List of comment dicts from the post

        Returns:
            Song if solution found, None otherwise
        """
        if not comments:
            return None

        # Format comments for the prompt
        comments_text = "\n\n".join(
            [
                f"[Comment ID: {c['id']}] (score: {c['score']}, by: {c['author']})\n{c['body']}"
                for c in comments[:50]  # Limit to top 50 comments
            ]
        )

        prompt = EXTRACT_SOLUTION_PROMPT.format(
            title=post.title,
            body=post.body,
            comments=comments_text,
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())

            if result.get("found"):
                # Create a unique ID from artist and title
                song_id = f"{result['artist']}_{result['song_title']}".lower()
                song_id = "".join(c if c.isalnum() else "_" for c in song_id)

                return Song(
                    id=song_id,
                    title=result["song_title"],
                    artist=result["artist"],
                    album=result.get("album"),
                    year=result.get("year"),
                    source_post_ids=[post.id],
                )

        except (json.JSONDecodeError, KeyError):
            pass

        return None

    def enrich_post(self, post: Post) -> Post:
        """Enrich a post with extracted description.

        Args:
            post: Post to enrich

        Returns:
            Post with description field populated
        """
        extraction = self.extract_description(post)
        post.description = extraction.get("description")
        return post
