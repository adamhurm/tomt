# tomt

"Tip of my tongue"-driven music discovery service.

This project scrapes Reddit communities where people are trying to identify songs they can't remember, processes the posts with Claude to extract song information, and builds a database of discovered music.

## Data Sources

- [r/tipofmytongue](https://reddit.com/r/tipofmytongue) - General TOMT community (filtered for music posts)
- [r/WhatsThisSong](https://reddit.com/r/WhatsThisSong) - Dedicated song identification
- [r/NameThatSong](https://reddit.com/r/NameThatSong) - Another song identification community

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tomt.git
cd tomt

# Install dependencies
pip install -e .

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API credentials
```

## Configuration

You'll need:

1. **Reddit API credentials** - Create an app at https://www.reddit.com/prefs/apps
2. **Anthropic API key** - Get one at https://console.anthropic.com

Add these to your `.env` file:

```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
ANTHROPIC_API_KEY=your_api_key
```

## Usage

### Run a discovery cycle

Scrape solved posts and extract song information:

```bash
tomt discover
```

Options:
- `--mode/-m`: Scraping mode (`new`, `hot`, `solved`) - default: `solved`
- `--limit/-l`: Max posts per subreddit - default: 100
- `--no-process`: Skip processing solved posts

### View discovered songs

```bash
tomt songs
```

### Search for songs

```bash
tomt search "never gonna give"
```

### View open requests

See what songs people are currently looking for:

```bash
tomt open-requests
```

### View statistics

```bash
tomt stats
```

## Web Service

TOMT also provides a web service with a full REST API and web interface.

### Running the Web Service

```bash
# Start the web server
tomt-web

# The server runs on http://localhost:8000 by default
```

Environment variables for the web service:
- `TOMT_HOST`: Host to bind to (default: `0.0.0.0`)
- `TOMT_PORT`: Port to listen on (default: `8000`)
- `TOMT_DB_PATH`: Database path (default: `tomt.db`)

### Web Interface

Visit `http://localhost:8000` in your browser for a full-featured web UI that includes:
- Discovery runner with mode/limit configuration
- Song browser and search
- Open requests viewer
- Database statistics

### API Endpoints

All CLI features are available via REST API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check and configuration status |
| POST | `/api/discover` | Run discovery cycle |
| GET/POST | `/api/songs` | List discovered songs |
| GET/POST | `/api/search` | Search for songs |
| GET/POST | `/api/open-requests` | List open song requests |
| GET/POST | `/api/stats` | Get database statistics |
| POST | `/api/process` | Process solved posts |

API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Bring Your Own Keys (BYOK)

Users can provide their own API keys instead of relying on server configuration. Keys can be provided via:

1. **Request body** (highest priority):
```json
{
  "keys": {
    "reddit_client_id": "your_id",
    "reddit_client_secret": "your_secret",
    "anthropic_api_key": "your_key"
  }
}
```

2. **HTTP headers**:
```
X-Reddit-Client-Id: your_id
X-Reddit-Client-Secret: your_secret
X-Anthropic-Api-Key: your_key
```

3. **Environment variables** (lowest priority, server default)

### Docker Web Service

Run the web service in Docker:

```bash
# Run CLI (default)
docker run -it ghcr.io/adamhurm/tomt tomt --help

# Run web service
docker run -p 8000:8000 \
  -e REDDIT_CLIENT_ID=your_id \
  -e ANTHROPIC_API_KEY=your_key \
  -v tomt-data:/app/data \
  ghcr.io/adamhurm/tomt tomt-web
```

## Architecture

```
src/tomt/
├── models/          # Pydantic data models
│   ├── post.py      # TOMT post model
│   └── song.py      # Discovered song model
├── scrapers/        # Data collection
│   └── reddit.py    # Reddit API scraper
├── services/        # Core logic
│   ├── discovery.py # Main orchestration service
│   └── parser.py    # Claude-powered post parsing
├── storage/         # Data persistence
│   └── database.py  # SQLite storage layer
├── web/             # Web service
│   ├── __init__.py  # FastAPI app and server
│   ├── routes.py    # API endpoints
│   ├── schemas.py   # Request/response models
│   └── templates/   # Web UI templates
└── cli.py           # Command-line interface
```

## How It Works

1. **Scraping**: The Reddit scraper fetches posts from TOMT subreddits, filtering for music-related content
2. **Parsing**: Claude analyzes posts to extract clean song descriptions (genre, era, lyrics, mood, etc.)
3. **Solution Extraction**: For solved posts, Claude reads the comments to identify the correct answer
4. **Storage**: Songs and their original "tip of my tongue" descriptions are stored in SQLite
5. **Discovery**: The database reveals patterns - which songs are most often forgotten and searched for

## Experimental

This project is experimental and intended for learning/research purposes. It's designed to explore:

- What makes certain songs memorable yet hard to name
- Patterns in how people describe music they can't identify
- The intersection of AI and music discovery
