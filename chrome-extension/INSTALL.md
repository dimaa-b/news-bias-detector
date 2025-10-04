# Quick Start Guide - Chrome Extension

## 🚀 Installation Steps

### 1. Create Icon Files

The extension needs 3 PNG icon files. You have 2 options:

**Option A: Use Online Converter (Easiest)**
1. Go to https://redketchup.io/icon-converter
2. Upload `chrome-extension/icons/icon.svg`
3. Download PNG files in 16x16, 48x48, and 128x128 sizes
4. Rename them to `icon16.png`, `icon48.png`, `icon128.png`
5. Place in `chrome-extension/icons/` folder

**Option B: Use ImageMagick (if installed)**
```bash
cd chrome-extension/icons
convert icon.svg -resize 16x16 icon16.png
convert icon.svg -resize 48x48 icon48.png
convert icon.svg -resize 128x128 icon128.png
```

### 2. Load Extension in Chrome

1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable **Developer mode** (toggle switch in top-right corner)
4. Click **Load unpacked**
5. Navigate to and select the `chrome-extension` folder
6. Click **Select Folder**

You should see "News Bias Detector" appear in your extensions list!

### 3. Test the Extension

1. Make sure your backend is running:
   ```bash
   cd /Users/dima/Documents/news-bias-detector
   source venv/bin/activate
   python app.py
   ```

2. Navigate to a news article (try https://www.bbc.com/news)

3. Click the extension icon (🔍) in Chrome toolbar

4. Click **"Analyze This Article"**

5. Wait 15-30 seconds for analysis

6. Sentences will be highlighted on the page!

## 🎨 How to Use

### Analyzing an Article

1. **Open any news article** in Chrome
2. **Click extension icon** (magnifying glass) in toolbar
3. **Click "Analyze This Article"** button
4. **Wait** for analysis (shows progress in popup)
5. **View results**:
   - Highlighted sentences on page
   - Summary in popup
   - Hover over highlights for details

### Understanding Highlights

| Color | Verdict | Meaning |
|-------|---------|---------|
| 🟢 Light Green | Supported | Claim is backed by evidence |
| 🔴 Light Red | Contradicted | Claim conflicts with facts |
| 🟡 Orange | Unverifiable | No evidence found |
| 🟠 Dark Orange | Misleading | Missing critical context |
| ⚪ Gray | No Claim | Opinion or non-factual |

### Viewing Details

- **Hover over any highlight** to see:
  - Verdict type
  - Confidence score
  - Explanation
  - Issues found

- **Check the popup** for:
  - Misleading risk score (0-100)
  - Total verdict breakdown
  - Top recurring issues
  - Overall summary

### Clearing Highlights

Click **"Clear Highlights"** button to remove all highlighting from the page.

## ⚙️ Configuration

### Change Backend URL

If your backend is running on a different port:

1. Click extension icon
2. Scroll to bottom of popup
3. Update "Backend API URL" field
4. URL is saved automatically

Default: `http://localhost:3000/api/search-and-fetch`

## 🐛 Troubleshooting

### Extension doesn't appear after loading

- Make sure you selected the `chrome-extension` folder (not the parent folder)
- Check that `manifest.json` is in the selected folder
- Look for errors on `chrome://extensions/` page

### "Could not extract article text"

The page might not be a news article. Try:
- A different news site (BBC, Reuters, CNN work well)
- Clicking directly on an article headline
- Refreshing the page

### "API error" or "Analysis failed"

Check backend:
```bash
# Make sure backend is running
cd /Users/dima/Documents/news-bias-detector
source venv/bin/activate  
python app.py

# Check it's accessible
curl http://localhost:3000/health
```

Check environment:
- `GEMINI_API_KEY` is set in `.env` file
- `APIFY_API_TOKEN` is set in `.env` file
- All Python packages installed (`pip install -r requirements.txt`)

### Highlights don't appear

- Check browser console (F12) for JavaScript errors
- Make sure analysis completed successfully (check popup status)
- Try clicking "Clear Highlights" then re-analyzing
- Refresh the page and try again

### Popup shows blank/white screen

- Right-click extension icon → Inspect popup
- Check console for errors
- Try reloading extension on `chrome://extensions/`

## 📊 Example Workflow

1. **Open BBC News article** about climate policy
2. **Click extension icon**
3. Extension extracts:
   - Title: "Biden's New Climate Rules..."
   - Text: Full article content
   - Date: 2024-10-03
4. **Sends to backend** which:
   - Searches "Biden climate rules" on Google
   - Finds 5 reference articles from Reuters, WSJ, etc.
   - Fetches full content of references
   - Sends to Gemini AI for analysis
5. **AI analyzes** each sentence:
   - "Biden announced new rules" → Supported ✅
   - "Experts say it will save millions" → Unverifiable ⚠️
   - "Critics call it devastating" → No claim (opinion) ⚪
6. **Extension highlights** sentences with colors
7. **Popup shows** summary:
   - Misleading Risk: 35/100
   - 8 Supported, 3 Unverifiable, 2 Misleading
   - Top issue: "Ambiguous attribution"

## 🎯 Best Practices

1. **Use on full articles**, not headlines or snippets
2. **Wait for complete loading** before analyzing
3. **Read the explanations** by hovering over highlights
4. **Check the summary** in popup for overall assessment
5. **Compare multiple sources** on the same story
6. **Clear highlights** before analyzing a new article

## 📝 Notes

- First analysis may take longer (30-40 seconds)
- Each analysis costs ~3000-8000 Gemini API tokens
- Works best on English news articles
- May not work on paywalled content
- Some sites block content extraction (rare)

## 🆘 Still Having Issues?

Check the detailed README.md in the chrome-extension folder for:
- Complete troubleshooting guide
- Development/debugging instructions
- Extension architecture details
- Future enhancement plans
