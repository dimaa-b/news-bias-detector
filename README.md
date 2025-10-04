# News Bias Detector - Flask Server

A Python Flask server for the News Bias Detector application with Apify integration for news scraping.

## Features

- Flask web server with RESTful API endpoints
- Apify client integration for news scraping
- JSON request/response handling
- Health check endpoint
- Error handling middleware
- News search and bias analysis endpoints

## Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file with your Apify API token
```

## Running the Server

### Development Mode
```bash
python app.py
```

The server will start on `http://localhost:3000` by default with debug mode enabled.

## Available Endpoints

- `GET /` - Welcome message and server status
- `GET /health` - Health check endpoint  
- `GET /api/status` - API status information
- `POST /api/search-news` - Search for news articles using Apify
- `POST /api/analyze-bias` - Get news articles for bias analysis

## API Usage Examples

### Search News
```bash
curl -X POST http://localhost:3000/api/search-news \
  -H "Content-Type: application/json" \
  -d '{"queries": "climate change", "options": {"resultsPerPage": 50}}'
```

### Analyze Bias
```bash
curl -X POST http://localhost:3000/api/analyze-bias \
  -H "Content-Type: application/json" \
  -d '{"topic": "artificial intelligence", "maxResults": 30}'
```

## Environment Variables

- `PORT` - Server port (default: 3000)
- `APIFY_API_TOKEN` - Your Apify API token for news scraping
- `FLASK_ENV` - Flask environment (development/production)
- `FLASK_DEBUG` - Enable/disable debug mode

## Project Structure

```
news-bias-detector/
├── app.py                # Main Flask application
├── apify_client.py      # Apify client for news scraping
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── news_scraper.py     # News scraping utilities
└── README.md          # This file
```

## Apify Integration

This application uses Apify actors to scrape news articles. You'll need to:

1. Sign up for an Apify account at https://apify.com/
2. Get your API token from the Apify console
3. Add the token to your `.env` file as `APIFY_API_TOKEN`

The application uses the actor `nFJndFXA5zjCTuudP` for news scraping.