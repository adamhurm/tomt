"""Command-line interface for TOMT music discovery service."""

import os
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from tomt.services.discovery import DiscoveryService

# Load environment variables
load_dotenv()

console = Console()


def get_service(db_path: str = "tomt.db") -> DiscoveryService:
    """Create a DiscoveryService from environment variables."""
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")  # Optional for installed apps
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    if not reddit_client_id:
        raise click.ClickException(
            "Reddit client ID not found. Set REDDIT_CLIENT_ID environment variable."
        )

    if not anthropic_api_key:
        raise click.ClickException(
            "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable."
        )

    return DiscoveryService(
        reddit_client_id=reddit_client_id,
        anthropic_api_key=anthropic_api_key,
        reddit_client_secret=reddit_client_secret,  # Can be None for installed apps
        db_path=db_path,
    )


@click.group()
@click.version_option()
def main():
    """TOMT - Tip of my tongue music discovery service.

    Discovers songs that people are searching for on Reddit.
    """
    pass


@main.command()
@click.option("--mode", "-m", default="solved", type=click.Choice(["new", "hot", "solved"]),
              help="Scraping mode")
@click.option("--limit", "-l", default=100, help="Max posts per subreddit")
@click.option("--db", default="tomt.db", help="Database path")
@click.option("--no-process", is_flag=True, help="Skip processing solved posts")
def discover(mode: str, limit: int, db: str, no_process: bool):
    """Run a discovery cycle to find new songs."""
    service = get_service(db_path=db)

    results = service.discover(
        scrape_mode=mode,
        scrape_limit=limit,
        process=not no_process,
    )

    console.print("\n[bold]Discovery Results:[/bold]")
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Posts scraped", str(results["posts_scraped"]))
    table.add_row("Songs found", str(results["songs_found"]))
    table.add_row("Total posts in DB", str(results["total_posts"]))
    table.add_row("Total songs in DB", str(results["total_songs"]))
    table.add_row("Solve rate", f"{results['solve_rate']:.1%}")

    console.print(table)


@main.command()
@click.option("--limit", "-l", default=20, help="Max results")
@click.option("--db", default="tomt.db", help="Database path")
def songs(limit: int, db: str):
    """List discovered songs, ordered by how often they were sought."""
    service = get_service(db_path=db)
    discoveries = service.get_discoveries(limit=limit)

    if not discoveries:
        console.print("[yellow]No songs discovered yet. Run 'tomt discover' first.[/yellow]")
        return

    table = Table(title="Most Sought Songs")
    table.add_column("#", style="dim")
    table.add_column("Artist", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Year", style="yellow")
    table.add_column("Searches", style="magenta")

    for i, song in enumerate(discoveries, 1):
        table.add_row(
            str(i),
            song.artist,
            song.title,
            str(song.year) if song.year else "-",
            str(song.discovery_count),
        )

    console.print(table)


@main.command()
@click.argument("query")
@click.option("--limit", "-l", default=20, help="Max results")
@click.option("--db", default="tomt.db", help="Database path")
def search(query: str, limit: int, db: str):
    """Search for songs by title or artist."""
    service = get_service(db_path=db)
    results = service.search(query=query, limit=limit)

    if not results:
        console.print(f"[yellow]No songs found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search Results: {query}")
    table.add_column("Artist", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Album", style="blue")
    table.add_column("Year", style="yellow")

    for song in results:
        table.add_row(
            song.artist,
            song.title,
            song.album or "-",
            str(song.year) if song.year else "-",
        )

    console.print(table)


@main.command()
@click.option("--db", default="tomt.db", help="Database path")
def random(db: str):
    """Roll the dice and get a random song from the database."""
    service = get_service(db_path=db)
    song = service.db.get_random_song()

    if not song:
        console.print("[yellow]No songs in the database yet. Run 'tomt discover' first.[/yellow]")
        return

    table = Table(title="Random Song")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Artist", song.artist)
    table.add_row("Title", song.title)
    table.add_row("Album", song.album or "-")
    table.add_row("Year", str(song.year) if song.year else "-")
    table.add_row("Times Searched", str(song.discovery_count))

    if song.spotify_url:
        table.add_row("Spotify", song.spotify_url)
    if song.youtube_url:
        table.add_row("YouTube", song.youtube_url)
    if song.apple_music_url:
        table.add_row("Apple Music", song.apple_music_url)

    console.print(table)


@main.command()
@click.option("--limit", "-l", default=20, help="Max results")
@click.option("--db", default="tomt.db", help="Database path")
def open_requests(limit: int, db: str):
    """Show currently open song identification requests."""
    service = get_service(db_path=db)
    posts = service.get_open_requests(limit=limit)

    if not posts:
        console.print("[yellow]No open requests found.[/yellow]")
        return

    table = Table(title="Open Song Requests")
    table.add_column("Subreddit", style="cyan")
    table.add_column("Title", style="green", max_width=60)
    table.add_column("Score", style="yellow")
    table.add_column("URL", style="dim")

    for post in posts:
        table.add_row(
            post.subreddit,
            post.title[:60] + "..." if len(post.title) > 60 else post.title,
            str(post.score),
            post.url,
        )

    console.print(table)


@main.command()
@click.option("--db", default="tomt.db", help="Database path")
def stats(db: str):
    """Show database statistics."""
    service = get_service(db_path=db)
    db_stats = service.db.get_stats()

    table = Table(title="Database Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total posts", str(db_stats["total_posts"]))
    table.add_row("Solved posts", str(db_stats["solved_posts"]))
    table.add_row("Unsolved posts", str(db_stats["unsolved_posts"]))
    table.add_row("Solve rate", f"{db_stats['solve_rate']:.1%}")
    table.add_row("Total songs discovered", str(db_stats["total_songs"]))

    console.print(table)


@main.command()
@click.option("--limit", "-l", default=50, help="Max posts to process")
@click.option("--db", default="tomt.db", help="Database path")
def process(limit: int, db: str):
    """Process solved posts to extract song information."""
    service = get_service(db_path=db)
    songs_found = service.process_solved_posts(limit=limit)
    console.print(f"[green]Discovered {songs_found} new songs[/green]")


if __name__ == "__main__":
    main()
