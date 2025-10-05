# News Bias Detector - Chrome Extension

A Chrome extension that analyzes news articles for bias and misleading claims using AI-powered fact-checking.

## Features

- 📰 **Extract Article Content**: Automatically extracts article text from news websites
- 🔍 **AI Analysis**: Sends article to backend for claims verification against reference sources
- 🎨 **Visual Highlighting**: Highlights sentences based on verification status:
  - 🟢 **Green**: Supported by references
  - 🔴 **Red**: Contradicted by evidence
  - 🟡 **Orange**: Unverifiable/no evidence
  - 🟠 **Dark Orange**: Misleading by context
  - ⚪ **Gray**: No factual claim
- 📊 **Detailed Analysis**: Shows misleading risk score, verdict counts, and top issues
- 💡 **Interactive**: Hover over highlights to see explanations and confidence scores
- 🎯 **Floating Panel**: Always-visible status panel in top-right corner with real-time updates
- ⚡ **Streaming Analysis**: Sentence-by-sentence analysis with live progress updates
- 💾 **State Persistence**: Analysis results saved per-page and restored automatically

## Installation

### Load Unpacked Extension (Development)

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Navigate to `/Users/dima/Documents/news-bias-detector/chrome-extension`
5. Select the folder and click **Select**

### Create Icons (Optional)

The extension uses placeholder icons. To create proper icons:

```bash
cd chrome-extension/icons

# Convert SVG to PNG using ImageMagick or online tool
# Create 3 sizes: icon16.png, icon48.png, icon128.png
```

Or use online tools like:
- https://redketchup.io/icon-converter
- https://www.favicon-generator.org/

## Usage

### 1. Start Your Backend Server

Make sure your Flask backend is running:

```bash
cd /Users/dima/Documents/news-bias-detector
source venv/bin/activate
python app.py
```

The server should be running on `http://localhost:3000`

### 2. Analyze an Article

1. Navigate to any news article in Chrome
2. Click the extension icon (🔍) in the toolbar
3. Click **"Analyze This Article"**
4. Wait for analysis (15-30 seconds)
5. Sentences will be highlighted on the page
6. View results in the popup

### 3. View Results

The popup shows:
- **Misleading Risk Score** (0-100)
- **Verdict Breakdown** (how many sentences in each category)
- **Summary** of overall accuracy
- **Top Issues** found in the article

### 4. Clear Highlights

Click **"Clear Highlights"** to remove all highlighting from the page.

## Configuration

### Change Backend URL

1. Click the extension icon
2. Scroll to "Backend API URL" at the bottom
3. Update the URL if your backend is on a different port or server
4. The setting is saved automatically

## How It Works

### 1. Article Extraction

The extension extracts:
- Article title (from `<h1>` or `<title>`)
- Article text (from `<article>`, `<main>`, or paragraph tags)
- Publication date (from `<time>` or date metadata)
- Current URL

### 2. Backend Processing

Sends to `/api/search-and-fetch` endpoint:
```json
{
  "targetArticle": {
    "title": "Article Title",
    "text": "Full article text...",
    "url": "https://...",
    "date": "2024-10-04"
  },
  "query": "Article Title",
  "maxResults": 5,
  "useReputableSources": true
}
```

### 3. AI Analysis

Backend:
1. Searches for 5 reference articles from reputable sources
2. Fetches full content of references
3. Sends target + references to Gemini AI
4. AI analyzes each sentence for:
   - Factual accuracy
   - Missing context
   - Loaded language
   - Statistical manipulation
   - Other rhetorical issues

### 4. Visual Feedback

Extension:
1. Receives sentence-by-sentence verdicts
2. Finds matching sentences in the page
3. Highlights them with appropriate colors
4. Adds tooltips with explanations

## Verdict Types

| Verdict | Color | Meaning |
|---------|-------|---------|
| **Supported** | Green | Claim backed by reference sources |
| **Contradicted** | Red | Claim conflicts with evidence |
| **Unverifiable** | Orange | No evidence found in references |
| **Misleading by context** | Dark Orange | Technically true but missing critical context |
| **No factual claim** | Gray | Opinion, rhetoric, or non-factual statement |

## Common Issues

### "Could not extract article text"

The extension looks for common article patterns. If it fails:
- Make sure you're on an actual article page (not homepage)
- Try a different news site
- The site might have unusual HTML structure

### "API error: 500"

Backend error. Check:
- Backend server is running
- `GEMINI_API_KEY` is set in `.env`
- Backend logs for detailed error

### "Claims analysis not available"

This happens when:
- Less than 1 reference article was found
- Search didn't return results
- API quota exceeded

### Highlights don't appear

- Refresh the page and try again
- Make sure analysis completed successfully
- Check browser console for errors (F12)

## Development

### File Structure

```
chrome-extension/
├── manifest.json       # Extension configuration
├── popup.html          # Extension popup UI
├── popup.js            # Popup logic
├── content.js          # Runs on web pages
├── content.css         # Highlight styles
├── background.js       # Service worker
└── icons/              # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

### Testing

1. Test on various news sites:
   - https://www.bbc.com/news
   - https://www.reuters.com
   - https://www.wsj.com
   - https://www.cnn.com

2. Check browser console for errors:
   - Right-click extension popup → Inspect
   - Press F12 on article page

3. Monitor backend logs for API errors

### Debugging

Enable detailed logging:

```javascript
// In popup.js, add:
console.log('Article data:', articleData);
console.log('API response:', data);

// In content.js, add:
console.log('Highlighting sentences:', sentenceReviews);
```

## Limitations

1. **Article Detection**: Works best on standard news sites with `<article>` tags
2. **Text Extraction**: May not work on sites with paywalls or dynamic loading
3. **API Costs**: Each analysis uses ~3000-8000 Gemini tokens
4. **Rate Limits**: Gemini free tier: 60 requests/minute
5. **Language**: Currently only supports English articles

## Future Enhancements

- [ ] Better article extraction using Readability.js
- [ ] Support for paywalled articles
- [ ] Batch analysis of multiple articles
- [ ] Export reports as PDF
- [ ] Browser notification on high misleading risk
- [ ] Support for other languages
- [ ] Popup shows individual sentence details
- [ ] Source credibility ratings

## License

MIT License - See backend project for details
