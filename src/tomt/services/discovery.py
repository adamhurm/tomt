"""Main discovery service that orchestrates scraping and processing."""

from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from tomt.models.post import Post, PostStatus
from tomt.models.song import Song
from tomt.scrapers.reddit import RedditScraper
from tomt.services.parser import PostParser
from tomt.storage.database import Database


class DiscoveryService:
    """Orchestrates the TOMT music discovery process."""

    def __init__(
        self,
        reddit_client_id: str,
        anthropic_api_key: str,
        reddit_client_secret: Optional[str] = None,
        db_path: str = "tomt.db",
        subreddits: Optional[list[str]] = None,
    ):
        """Initialize the discovery service.

        Args:
            reddit_client_id: Reddit API client ID
            anthropic_api_key: Anthropic API key for Claude
            reddit_client_secret: Reddit API client secret (optional for installed apps)
            db_path: Path to SQLite database
            subreddits: Optional list of subreddits to scrape
        """
        self.scraper = RedditScraper(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            subreddits=subreddits,
        )
        self.parser = PostParser(api_key=anthropic_api_key)
        self.db = Database(db_path=db_path)
        self.db.init_db()
        self.console = Console()

    def scrape_and_store(
        self,
        mode: str = "new",
        limit: int = 100,
        enrich: bool = False,
    ) -> int:
        """Scrape posts and store them in the database.

        Args:
            mode: Scraping mode - "new", "hot", or "solved"
            limit: Maximum posts per subreddit
            enrich: Whether to enrich posts with Claude-extracted descriptions

        Returns:
            Number of posts scraped
        """
        if mode == "new":
            posts = self.scraper.scrape_new(limit=limit)
        elif mode == "hot":
            posts = self.scraper.scrape_hot(limit=limit)
        elif mode == "solved":
            posts = self.scraper.scrape_solved(limit=limit)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        count = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Scraping posts...", total=None)

            for post in posts:
                if enrich:
                    progress.update(task, description=f"Enriching: {post.id}")
                    post = self.parser.enrich_post(post)

                self.db.save_post(post)
                count += 1
                progress.update(task, description=f"Scraped {count} posts...")

        return count

    def process_solved_posts(self, limit: int = 50) -> int:
        """Process solved posts to extract song information.

        Args:
            limit: Maximum number of solved posts to process

        Returns:
            Number of songs discovered
        """
        # Get solved posts that don't have an identified song yet
        posts = self.db.get_posts(status=PostStatus.SOLVED, limit=limit)
        posts = [p for p in posts if not p.identified_song_id]

        songs_found = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Processing solved posts...", total=len(posts))

            for post in posts:
                progress.update(task, description=f"Processing: {post.id}")

                # Fetch comments
                try:
                    _, comments = self.scraper.get_post_with_comments(post.id)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not fetch comments for {post.id}: {e}[/yellow]")
                    progress.advance(task)
                    continue

                # Extract solution
                try:
                    song = self.parser.extract_solution(post, comments)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not extract solution for {post.id}: {e}[/yellow]")
                    progress.advance(task)
                    continue

                if song:
                    # Add the original description to the song
                    if post.description:
                        song.original_descriptions.append(post.description)

                    self.db.save_song(song, source_post=post)
                    songs_found += 1
                    self.console.print(
                        f"[green]Found: {song.artist} - {song.title}[/green]"
                    )

                progress.advance(task)

        return songs_found

    def discover(
        self,
        scrape_mode: str = "solved",
        scrape_limit: int = 100,
        process: bool = True,
    ) -> dict:
        """Run a full discovery cycle.

        Args:
            scrape_mode: Mode for scraping ("new", "hot", "solved")
            scrape_limit: Maximum posts to scrape per subreddit
            process: Whether to process solved posts for song extraction

        Returns:
            Stats about the discovery run
        """
        self.console.print("[bold blue]Starting discovery cycle...[/bold blue]")

        # Scrape posts
        posts_scraped = self.scrape_and_store(
            mode=scrape_mode,
            limit=scrape_limit,
            enrich=True,
        )
        self.console.print(f"[green]Scraped {posts_scraped} posts[/green]")

        songs_found = 0
        if process and scrape_mode == "solved":
            songs_found = self.process_solved_posts(limit=scrape_limit)
            self.console.print(f"[green]Discovered {songs_found} songs[/green]")

        stats = self.db.get_stats()
        return {
            "posts_scraped": posts_scraped,
            "songs_found": songs_found,
            **stats,
        }

    def get_discoveries(self, limit: int = 20) -> list[Song]:
        """Get the most interesting song discoveries.

        Args:
            limit: Maximum number of songs to return

        Returns:
            List of most-sought songs
        """
        return self.db.get_most_sought_songs(limit=limit)

    def search(self, query: str, limit: int = 20) -> list[Song]:
        """Search for songs.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching songs
        """
        return self.db.search_songs(query=query, limit=limit)

    def get_open_requests(self, limit: int = 50) -> list[Post]:
        """Get currently open song identification requests.

        Args:
            limit: Maximum posts to return

        Returns:
            List of unsolved posts
        """
        return self.db.get_unsolved_posts(limit=limit)
