// Popup script for the News Bias Detector extension

const statusDiv = document.getElementById('status');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const resultsDiv = document.getElementById('results');
const legendDiv = document.getElementById('legend');
const apiUrlInput = document.getElementById('apiUrl');

// Load saved API URL
chrome.storage.sync.get(['apiUrl'], (result) => {
  if (result.apiUrl) {
    apiUrlInput.value = result.apiUrl;
  }
});

// Save API URL when changed
apiUrlInput.addEventListener('change', () => {
  chrome.storage.sync.set({ apiUrl: apiUrlInput.value });
});

// Analyze button click
analyzeBtn.addEventListener('click', async () => {
  try {
    updateStatus('Extracting article content...', 'info');
    analyzeBtn.disabled = true;
    resultsDiv.style.display = 'none';
    legendDiv.style.display = 'none';
    
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.id) {
      throw new Error('No active tab found');
    }
    
    // Extract article content from the page
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractArticleContent
    });
    
    if (!result || !result.result) {
      throw new Error('Failed to extract article content');
    }
    
    const articleData = result.result;
    
    // Log extracted content to console
    console.log('=== EXTRACTED ARTICLE ===');
    console.log('Title:', articleData.title);
    console.log('URL:', articleData.url);
    console.log('Date:', articleData.date);
    console.log('Text Length:', articleData.text.length, 'characters');
    console.log('\nFull Text:\n', articleData.text);
    console.log('=========================');
    
    if (!articleData.text || articleData.text.length < 100) {
      throw new Error('Could not extract article text. This might not be a news article page.');
    }
    
    updateStatus(`Analyzing article: "${articleData.title.substring(0, 40)}..."`, 'info');
    
    // Send to backend
    const apiUrl = apiUrlInput.value;
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        targetArticle: articleData,
        query: articleData.title || 'news article',
        maxResults: 5,
        maxArticlesToFetch: 5,
        useReputableSources: true,
        saveToFile: false
      })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || 'Analysis failed');
    }
    
    // Check if claims analysis was successful
    if (!data.claims_analysis || !data.claims_analysis.success) {
      const errorMsg = data.claims_analysis?.message || 'Claims analysis not available';
      throw new Error(errorMsg);
    }
    
    const analysis = data.claims_analysis.analysis;
    
    // Highlight sentences in the page
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: highlightSentences,
      args: [analysis.sentence_reviews]
    });
    
    // Display results
    displayResults(analysis);
    
    updateStatus('Analysis complete! Sentences highlighted on page.', 'success');
    legendDiv.style.display = 'block';
    
  } catch (error) {
    console.error('Analysis error:', error);
    updateStatus(`Error: ${error.message}`, 'error');
  } finally {
    analyzeBtn.disabled = false;
  }
});

// Clear highlights button
clearBtn.addEventListener('click', async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: clearHighlights
    });
    
    resultsDiv.style.display = 'none';
    legendDiv.style.display = 'none';
    updateStatus('Highlights cleared', 'info');
  } catch (error) {
    updateStatus(`Error: ${error.message}`, 'error');
  }
});

// Update status message
function updateStatus(message, type) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
}

// Display analysis results
function displayResults(analysis) {
  const assessment = analysis.overall_assessment;
  const verdicts = analysis.pattern_summary.counts_by_verdict;
  
  let html = '<div class="result-item">';
  html += `<div class="result-label">Misleading Risk Score:</div>`;
  html += `<div>${assessment.misleading_risk_score}/100</div>`;
  html += '</div>';
  
  html += '<div class="result-item">';
  html += `<div class="result-label">Verdicts:</div>`;
  for (const [verdict, count] of Object.entries(verdicts)) {
    if (count > 0) {
      const verdictClass = verdict.toLowerCase().replace(/ /g, '-');
      html += `<span class="verdict-badge verdict-${verdictClass}">${verdict}: ${count}</span> `;
    }
  }
  html += '</div>';
  
  html += '<div class="result-item">';
  html += `<div class="result-label">Summary:</div>`;
  html += `<div style="margin-top: 5px; color: #666;">${assessment.summary}</div>`;
  html += '</div>';
  
  if (analysis.pattern_summary.top_recurring_patterns.length > 0) {
    html += '<div class="result-item">';
    html += `<div class="result-label">Top Issues:</div>`;
    html += '<ul style="margin: 5px 0; padding-left: 20px;">';
    for (const pattern of analysis.pattern_summary.top_recurring_patterns.slice(0, 3)) {
      html += `<li>${pattern.pattern} (${pattern.instances}x)</li>`;
    }
    html += '</ul></div>';
  }
  
  resultsDiv.innerHTML = html;
  resultsDiv.style.display = 'block';
}

// Function to extract article content (runs in page context)
function extractArticleContent() {
  // Simple extraction based on common article patterns
  const result = {
    title: '',
    text: '',
    url: window.location.href,
    date: new Date().toISOString().split('T')[0]
  };
  
  // Try to get title
  result.title = document.querySelector('h1')?.textContent?.trim() ||
                 document.querySelector('title')?.textContent?.trim() ||
                 'Untitled Article';
  
  // Try to get article date
  const dateSelectors = [
    'time[datetime]',
    '[class*="date"]',
    '[class*="publish"]',
    '[class*="timestamp"]'
  ];
  
  for (const selector of dateSelectors) {
    const dateEl = document.querySelector(selector);
    if (dateEl) {
      const datetime = dateEl.getAttribute('datetime') || dateEl.textContent;
      if (datetime) {
        result.date = datetime.split('T')[0];
        break;
      }
    }
  }
  
  // Try to get article text using common selectors
  const articleSelectors = [
    'article',
    '[role="article"]',
    '.article-content',
    '.article-body',
    '.post-content',
    '.entry-content',
    'main',
    '.content'
  ];
  
  let articleElement = null;
  for (const selector of articleSelectors) {
    articleElement = document.querySelector(selector);
    if (articleElement) break;
  }
  
  if (!articleElement) {
    articleElement = document.body;
  }
  
  // Extract paragraphs
  const paragraphs = articleElement.querySelectorAll('p');
  const textParts = [];
  
  for (const p of paragraphs) {
    const text = p.textContent.trim();
    if (text.length > 50) { // Filter out short paragraphs
      textParts.push(text);
    }
  }
  
  result.text = textParts.join('\n\n');
  
  return result;
}

// Function to highlight sentences (runs in page context)
function highlightSentences(sentenceReviews) {
  // Remove existing highlights
  document.querySelectorAll('.bias-detector-highlight').forEach(el => {
    const parent = el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent), el);
    parent.normalize();
  });
  
  // Color mapping for verdicts
  const verdictColors = {
    'Supported': 'rgba(76, 175, 80, 0.3)',
    'Contradicted': 'rgba(244, 67, 54, 0.3)',
    'Unverifiable': 'rgba(255, 152, 0, 0.3)',
    'Misleading by context': 'rgba(255, 87, 34, 0.3)',
    'No factual claim': 'rgba(158, 158, 158, 0.2)'
  };
  
  // Create a map of sentences to highlight
  const sentenceMap = new Map();
  for (const review of sentenceReviews) {
    sentenceMap.set(review.sentence.trim(), {
      verdict: review.verdict,
      confidence: review.confidence,
      explanation: review.explanation,
      issues: review.issues
    });
  }
  
  // Find and highlight sentences in the page
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );
  
  const nodesToProcess = [];
  let node;
  while (node = walker.nextNode()) {
    if (node.nodeValue.trim().length > 20) {
      nodesToProcess.push(node);
    }
  }
  
  for (const textNode of nodesToProcess) {
    const text = textNode.nodeValue;
    
    for (const [sentence, data] of sentenceMap.entries()) {
      if (text.includes(sentence)) {
        const parent = textNode.parentNode;
        if (parent && !parent.classList.contains('bias-detector-highlight')) {
          const parts = text.split(sentence);
          const fragment = document.createDocumentFragment();
          
          // Add text before sentence
          if (parts[0]) {
            fragment.appendChild(document.createTextNode(parts[0]));
          }
          
          // Create highlighted span
          const span = document.createElement('span');
          span.className = 'bias-detector-highlight';
          span.style.backgroundColor = verdictColors[data.verdict] || 'rgba(255, 255, 0, 0.3)';
          span.style.cursor = 'help';
          span.style.borderRadius = '2px';
          span.style.padding = '2px 0';
          span.textContent = sentence;
          span.title = `${data.verdict} (${(data.confidence * 100).toFixed(0)}%)\n${data.explanation}${data.issues.length > 0 ? '\nIssues: ' + data.issues.join(', ') : ''}`;
          
          fragment.appendChild(span);
          
          // Add text after sentence
          if (parts[1]) {
            fragment.appendChild(document.createTextNode(parts[1]));
          }
          
          parent.replaceChild(fragment, textNode);
          break;
        }
      }
    }
  }
}

// Function to clear highlights (runs in page context)
function clearHighlights() {
  document.querySelectorAll('.bias-detector-highlight').forEach(el => {
    const parent = el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent), el);
    parent.normalize();
  });
}
