// Popup script for the News Bias Detector extension

const statusDiv = document.getElementById('status');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const clearDataBtn = document.getElementById('clearDataBtn');
const resultsDiv = document.getElementById('results');
const legendDiv = document.getElementById('legend');
const apiUrlInput = document.getElementById('apiUrl');

// State management
let currentState = {
  hasAnalysis: false,
  currentUrl: null,
  analysisData: null,
  sentenceReviews: [],
  status: { message: 'Ready to analyze article', type: 'info' }
};

// Load saved state on popup open
async function loadSavedState() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const currentUrl = tab.url;
  
  chrome.storage.local.get([`analysis_${currentUrl}`], (result) => {
    const savedState = result[`analysis_${currentUrl}`];
    
    if (savedState) {
      currentState = savedState;
      
      // Restore UI state
      if (currentState.status) {
        updateStatus(currentState.status.message + ' (restored)', currentState.status.type);
      }
      
      if (currentState.hasAnalysis && currentState.analysisData) {
        displayFinalResults(currentState.analysisData);
        legendDiv.style.display = 'block';
        
        // Re-apply highlights to the page
        if (currentState.sentenceReviews && currentState.sentenceReviews.length > 0) {
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: highlightSentences,
            args: [currentState.sentenceReviews]
          }).catch(err => console.warn('Could not restore highlights:', err));
          
          console.log(`Restored ${currentState.sentenceReviews.length} sentence reviews`);
        }
      }
    }
  });
  
  // Also load API URL from sync storage
  chrome.storage.sync.get(['apiUrl'], (result) => {
    if (result.apiUrl) {
      apiUrlInput.value = result.apiUrl;
    }
  });
}

// Save current state
async function saveState() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const currentUrl = tab.url;
  
  chrome.storage.local.set({
    [`analysis_${currentUrl}`]: currentState
  });
}

// Initialize - load saved state
loadSavedState();

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
    
    // Get API URL and ensure it's the streaming endpoint
    let apiUrl = apiUrlInput.value;
    if (!apiUrl.includes('search-and-fetch-stream')) {
      apiUrl = apiUrl.replace('/api/search-and-fetch', '/api/search-and-fetch-stream');
    }
    
    await analyzeWithStreaming(apiUrl, articleData, tab.id);
    
  } catch (error) {
    console.error('Analysis error:', error);
    updateStatus(`Error: ${error.message}`, 'error');
    
    // Save error state
    currentState.status = { message: `Error: ${error.message}`, type: 'error' };
    await saveState();
  } finally {
    analyzeBtn.disabled = false;
  }
});

// Streaming analysis function
async function analyzeWithStreaming(apiUrl, articleData, tabId) {
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
      useReputableSources: true
    })
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  let sentenceReviews = [];
  let finalAnalysis = null;
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    
    // Process complete SSE messages
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line in buffer
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6));
        
        switch (data.type) {
          case 'status':
            updateStatus(data.message, 'info');
            break;
            
          case 'progress':
            updateStatus(`${data.message} (${data.current}/${data.total})`, 'info');
            break;
            
          case 'warning':
            console.warn(data.message);
            break;
            
          case 'fetch_summary':
            updateStatus(`Fetched ${data.data.articles_fetched} articles, starting analysis...`, 'info');
            break;
            
          case 'analysis_start':
            updateStatus(`Analyzing ${data.total_sentences} sentences...`, 'info');
            resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>Analyzing sentences...</p></div>';
            resultsDiv.style.display = 'block';
            break;
            
          case 'sentence_review':
            sentenceReviews.push(data.data);
            updateStatus(`Analyzed sentence ${data.progress.current}/${data.progress.total}`, 'info');
            
            // Highlight sentence immediately
            await chrome.scripting.executeScript({
              target: { tabId: tabId },
              func: highlightSingleSentence,
              args: [data.data]
            });
            
            // Update progress display
            displayProgressResults(sentenceReviews, data.progress.total);
            
            // Save state periodically (every 5 sentences)
            if (sentenceReviews.length % 5 === 0) {
              currentState.sentenceReviews = sentenceReviews;
              await saveState();
            }
            break;
            
          case 'generating_summary':
            updateStatus(data.message, 'info');
            break;
            
          case 'analysis_complete':
            finalAnalysis = data.data;
            displayFinalResults(finalAnalysis);
            updateStatus('Analysis complete! Sentences highlighted on page.', 'success');
            legendDiv.style.display = 'block';
            
            // Save final state
            currentState.sentenceReviews = sentenceReviews;
            await saveState();
            break;
            
          case 'complete':
            console.log('Streaming complete');
            break;
            
          case 'error':
            throw new Error(data.message);
        }
      }
    }
  }
  
  if (!finalAnalysis) {
    throw new Error('Analysis did not complete successfully');
  }
}

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
    
    // Clear saved state
    currentState = {
      hasAnalysis: false,
      currentUrl: tab.url,
      analysisData: null,
      sentenceReviews: [],
      status: { message: 'Highlights cleared', type: 'info' }
    };
    await saveState();
    
  } catch (error) {
    updateStatus(`Error: ${error.message}`, 'error');
  }
});

// Clear all saved data button
clearDataBtn.addEventListener('click', async () => {
  if (confirm('This will clear all saved analysis data for all pages. Continue?')) {
    try {
      // Clear all local storage
      chrome.storage.local.clear(() => {
        updateStatus('All saved data cleared', 'info');
        resultsDiv.style.display = 'none';
        legendDiv.style.display = 'none';
        
        // Reset current state
        currentState = {
          hasAnalysis: false,
          currentUrl: null,
          analysisData: null,
          sentenceReviews: [],
          status: { message: 'All saved data cleared', type: 'info' }
        };
        
        console.log('All saved analysis data has been cleared');
      });
      
      // Also clear highlights on current page
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: clearHighlights
      }).catch(err => console.warn('Could not clear highlights:', err));
      
    } catch (error) {
      updateStatus(`Error: ${error.message}`, 'error');
    }
  }
});

// Update status message
function updateStatus(message, type) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
  
  // Update state
  currentState.status = { message, type };
}

// Display progress results during streaming
function displayProgressResults(sentenceReviews, totalSentences) {
  const verdictCounts = {};
  
  for (const review of sentenceReviews) {
    const verdict = review.verdict;
    verdictCounts[verdict] = (verdictCounts[verdict] || 0) + 1;
  }
  
  let html = '<div class="progress-container">';
  html += `<h3>Progress: ${sentenceReviews.length}/${totalSentences} sentences analyzed</h3>`;
  
  if (Object.keys(verdictCounts).length > 0) {
    html += '<div class="result-item">';
    html += `<div class="result-label">Verdicts so far:</div>`;
    for (const [verdict, count] of Object.entries(verdictCounts)) {
      const verdictClass = verdict.toLowerCase().replace(/ /g, '-');
      html += `<span class="verdict-badge verdict-${verdictClass}">${verdict}: ${count}</span> `;
    }
    html += '</div>';
  }
  
  html += '</div>';
  
  resultsDiv.innerHTML = html;
}

// Display final analysis results
function displayFinalResults(analysisData) {
  const assessment = analysisData.overall_assessment;
  const verdicts = analysisData.pattern_summary.counts_by_verdict;
  
  let html = '<div class="result-item">';
  html += `<div class="result-label">Misleading Risk Score:</div>`;
  html += `<div class="risk-score">${assessment.misleading_risk_score}/100</div>`;
  html += '</div>';
  
  html += '<div class="result-item">';
  html += `<div class="result-label">Final Verdicts:</div>`;
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
  
  resultsDiv.innerHTML = html;
  resultsDiv.style.display = 'block';
  
  // Update state
  currentState.hasAnalysis = true;
  currentState.analysisData = analysisData;
}

// Display analysis results (legacy, keeping for compatibility)
function displayResults(analysis) {
  displayFinalResults({
    overall_assessment: analysis.overall_assessment,
    pattern_summary: analysis.pattern_summary
  });
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

// Function to highlight a single sentence (runs in page context)
function highlightSingleSentence(review) {
  const verdictColors = {
    'Supported': 'rgba(76, 175, 80, 0.3)',
    'Contradicted': 'rgba(244, 67, 54, 0.3)',
    'Unverifiable': 'rgba(255, 152, 0, 0.3)',
    'Misleading by context': 'rgba(255, 87, 34, 0.3)',
    'No factual claim': 'rgba(158, 158, 158, 0.2)'
  };
  
  const sentence = review.sentence.trim();
  const data = {
    verdict: review.verdict,
    confidence: review.confidence,
    explanation: review.explanation,
    issues: review.issues || []
  };
  
  // Find and highlight the sentence in the page
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );
  
  let node;
  while (node = walker.nextNode()) {
    const text = node.nodeValue;
    
    if (text.includes(sentence)) {
      const parent = node.parentNode;
      if (parent && !parent.classList.contains('bias-detector-highlight')) {
        const parts = text.split(sentence);
        
        // Only process if we get exactly 2 parts (before and after)
        if (parts.length === 2) {
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
          span.style.transition = 'background-color 0.3s ease';
          span.textContent = sentence;
          span.title = `${data.verdict} (${(data.confidence * 100).toFixed(0)}%)\n${data.explanation}${data.issues.length > 0 ? '\nIssues: ' + data.issues.join(', ') : ''}`;
          
          fragment.appendChild(span);
          
          // Add text after sentence
          if (parts[1]) {
            fragment.appendChild(document.createTextNode(parts[1]));
          }
          
          parent.replaceChild(fragment, node);
          
          // Scroll to the highlighted sentence briefly
          span.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          
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
