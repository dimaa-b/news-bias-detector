# News Bias Detector - Express Server

A simple Express.js server for the News Bias Detector application.

## Features

- Basic Express.js server setup
- JSON middleware for parsing request bodies
- Health check endpoint
- Error handling middleware
- 404 route handler

## Installation

1. Install dependencies:
```bash
npm install
```

## Running the Server

### Development Mode (with auto-restart)
```bash
npm run dev
```

### Production Mode
```bash
npm start
```

The server will start on `http://localhost:3000` by default.

## Available Endpoints

- `GET /` - Welcome message and server status
- `GET /health` - Health check endpoint
- `GET /api/status` - API status information

## Environment Variables

- `PORT` - Server port (default: 3000)

## Project Structure

```
news-bias-detector/
├── package.json          # Project dependencies and scripts
├── server.js            # Main server file
└── README.md           # This file
```