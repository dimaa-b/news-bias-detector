// Content script - runs on all pages
console.log('News Bias Detector extension loaded');

// Create floating status panel
let panel = null;
let isDragging = false;
let currentX = 0;
let currentY = 0;
let initialX = 0;
let initialY = 0;

function createPanel() {
  // Check if panel already exists
  if (document.getElementById('bias-detector-panel')) {
    return;
  }

  panel = document.createElement('div');
  panel.id = 'bias-detector-panel';
  panel.innerHTML = `
    <div class="panel-icon" title="Expand">🔍</div>
    <div class="panel-header">
      <h3>FairLens</h3>
      <div class="panel-controls">
        <button class="panel-btn" id="panel-minimize" title="Minimize">−</button>
        <button class="panel-btn" id="panel-close" title="Close">×</button>
      </div>
    </div>
    <div class="panel-content">
      <div class="status-section">
        <div class="status-message info" id="panel-status">
          Ready to analyze
        </div>
      </div>
      <div class="status-section" id="progress-section" style="display: none;">
        <div id="panel-progress-text" style="margin-bottom: 8px; color: #5f6368; font-size: 13px; font-weight: 500;">0 / 0 sentences</div>
        <div class="progress-bar-container">
          <div class="progress-bar" id="panel-progress-bar" style="width: 0%"></div>
        </div>
      </div>
      <div class="status-section" id="risk-section" style="display: none;">
        <div class="risk-score-display">
          <div class="risk-score-value" id="panel-risk-score">--</div>
          <div class="risk-score-label">Misleading Risk</div>
        </div>
      </div>
      <div class="panel-actions">
        <button class="panel-action-btn primary" id="panel-analyze">Analyze</button>
        <button class="panel-action-btn secondary" id="panel-clear">Clear</button>
      </div>
    </div>
  `;

  document.body.appendChild(panel);

  // Add event listeners
  setupPanelControls();
  setupDragging();
  
  // Listen for messages from popup (if any)
  chrome.runtime.onMessage.addListener(handleMessage);
}

function setupPanelControls() {
  // Minimize/Expand
  const minimizeBtn = document.getElementById('panel-minimize');
  const panelIcon = panel.querySelector('.panel-icon');
  
  minimizeBtn?.addEventListener('click', () => {
    panel.classList.toggle('collapsed');
  });
  
  panelIcon?.addEventListener('click', () => {
    panel.classList.remove('collapsed');
  });

  // Close
  document.getElementById('panel-close')?.addEventListener('click', () => {
    panel.style.display = 'none';
  });

  // Analyze button
  document.getElementById('panel-analyze')?.addEventListener('click', async () => {
    console.log('Analyze button clicked');
    const analyzeBtn = document.getElementById('panel-analyze');
    
    // Disable button during analysis
    if (analyzeBtn) {
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = 'Analyzing...';
    }
    
    try {
      await startAnalysis();
    } catch (error) {
      console.error('Error in startAnalysis:', error);
      updatePanelStatus(`Error: ${error.message}`, 'error');
    } finally {
      // Re-enable button
      if (analyzeBtn) {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze Article';
      }
    }
  });

  // Clear button
  document.getElementById('panel-clear')?.addEventListener('click', () => {
    clearHighlights();
    updatePanelStatus('Highlights cleared', 'info');
    hideProgressSection();
    hideRiskSection();
    
    // Clear saved state
    chrome.storage.local.remove(`analysis_${window.location.href}`);
  });
}

function setupDragging() {
  const header = panel.querySelector('.panel-header');
  
  header.addEventListener('mousedown', dragStart);
  document.addEventListener('mousemove', drag);
  document.addEventListener('mouseup', dragEnd);
}

function dragStart(e) {
  if (e.target.classList.contains('panel-btn')) return;
  
  initialX = e.clientX - currentX;
  initialY = e.clientY - currentY;
  isDragging = true;
}

function drag(e) {
  if (!isDragging) return;
  
  e.preventDefault();
  currentX = e.clientX - initialX;
  currentY = e.clientY - initialY;
  
  panel.style.transform = `translate(${currentX}px, ${currentY}px)`;
}

function dragEnd() {
  isDragging = false;
}

// Message handler
function handleMessage(message, sender, sendResponse) {
  switch (message.type) {
    case 'triggerAnalysis':
      startAnalysis();
      break;
      
    case 'showPanel':
      panel.style.display = 'block';
      panel.classList.remove('collapsed');
      break;
      
    case 'hidePanel':
      panel.style.display = 'none';
      break;
  }
}

// Update functions
function updatePanelStatus(message, type) {
  const statusEl = document.getElementById('panel-status');
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
  }
}

function updateProgress(current, total) {
  const progressText = document.getElementById('panel-progress-text');
  const progressBar = document.getElementById('panel-progress-bar');
  
  if (progressText) {
    progressText.textContent = `${current} / ${total} sentences analyzed`;
  }
  
  if (progressBar && total > 0) {
    const percentage = (current / total) * 100;
    progressBar.style.width = `${percentage}%`;
  }
}

function updateVerdicts(verdictCounts) {
  // Verdicts section removed for cleaner UI
  // Risk score will be shown at the end
}

function updateFinalResults(data) {
  if (!data) return;
  
  // Update risk score
  if (data.overall_assessment) {
    const riskScore = data.overall_assessment.misleading_risk_score;
    const riskEl = document.getElementById('panel-risk-score');
    if (riskEl) {
      riskEl.textContent = riskScore;
      showRiskSection();
    }
  }
}

function showProgressSection() {
  const section = document.getElementById('progress-section');
  if (section) section.style.display = 'block';
}

function hideProgressSection() {
  const section = document.getElementById('progress-section');
  if (section) section.style.display = 'none';
}

function showRiskSection() {
  const section = document.getElementById('risk-section');
  if (section) section.style.display = 'block';
}

function hideRiskSection() {
  const section = document.getElementById('risk-section');
  if (section) section.style.display = 'none';
}

// Initialize panel when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', createPanel);
} else {
  createPanel();
}

// Load saved state for current page
async function loadPanelState() {
  const currentUrl = window.location.href;
  
  chrome.storage.local.get([`analysis_${currentUrl}`], (result) => {
    const savedState = result[`analysis_${currentUrl}`];
    
    if (savedState && savedState.hasAnalysis) {
      // Show panel if there's saved analysis
      if (panel) {
        panel.style.display = 'block';
        
        // Restore status
        if (savedState.status) {
          updatePanelStatus(savedState.status.message, savedState.status.type);
        }
        
        // Restore results if available
        if (savedState.analysisData) {
          updateFinalResults(savedState.analysisData);
        }
      }
    }
  });
}

// Load state after panel is created
setTimeout(loadPanelState, 100);

// Analysis functions
async function startAnalysis() {
  console.log('startAnalysis called');
  try {
    updatePanelStatus('Extracting article content...', 'info');
    
    // Extract article content
    const articleData = extractArticleContent();
    
    console.log('Extracted article data:', {
      title: articleData.title,
      textLength: articleData.text.length,
      url: articleData.url,
      date: articleData.date
    });
    
    if (!articleData.text || articleData.text.length < 100) {
      updatePanelStatus('Could not extract article text. This might not be a news article page.', 'error');
      return;
    }
    
    updatePanelStatus(`Analyzing: "${articleData.title.substring(0, 40)}..."`, 'info');
    
    // Get API URL from storage
    chrome.storage.sync.get(['apiUrl'], async (result) => {
      let apiUrl = result.apiUrl || 'http://localhost:3000/api/search-and-fetch-stream';
      
      // Ensure streaming endpoint
      if (!apiUrl.includes('search-and-fetch-stream')) {
        apiUrl = apiUrl.replace('/api/search-and-fetch', '/api/search-and-fetch-stream');
      }
      
      await analyzeWithStreaming(apiUrl, articleData);
    });
    
  } catch (error) {
    console.error('Analysis error:', error);
    updatePanelStatus(`Error: ${error.message}`, 'error');
  }
}

async function analyzeWithStreaming(apiUrl, articleData) {
  console.log('analyzeWithStreaming called with URL:', apiUrl);
  
  try {
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
    
    console.log('Fetch response status:', response.status);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let sentenceReviews = [];
    let finalAnalysis = null;
    let buffer = '';
    let verdictCounts = {};
    
    console.log('Starting to read stream...');
    
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
            updatePanelStatus(data.message, 'info');
            break;
            
          case 'progress':
            updatePanelStatus(`${data.message} (${data.current}/${data.total})`, 'info');
            updateProgress(data.current, data.total);
            break;
            
          case 'warning':
            console.warn(data.message);
            break;
            
          case 'fetch_summary':
            updatePanelStatus(`Fetched ${data.data.articles_fetched} articles, starting analysis...`, 'info');
            break;
            
          case 'analysis_start':
            updatePanelStatus(`Analyzing ${data.total_sentences} sentences...`, 'info');
            showProgressSection();
            updateProgress(0, data.total_sentences);
            break;
            
          case 'sentence_review':
            sentenceReviews.push(data.data);
            updatePanelStatus(`Analyzed sentence ${data.progress.current}/${data.progress.total}`, 'info');
            
            // Update verdict counts
            const verdict = data.data.verdict;
            verdictCounts[verdict] = (verdictCounts[verdict] || 0) + 1;
            
            // Highlight sentence immediately
            highlightSingleSentence(data.data);
            
            // Update panel
            updateProgress(data.progress.current, data.progress.total);
            break;
            
          case 'generating_summary':
            updatePanelStatus(data.message, 'info');
            break;
            
          case 'analysis_complete':
            finalAnalysis = data.data;
            updatePanelStatus('Analysis complete! Sentences highlighted on page.', 'success');
            updateFinalResults(data.data);
            
            // Save state
            saveAnalysisState(sentenceReviews, data.data);
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
  
  } catch (error) {
    console.error('Streaming error:', error);
    updatePanelStatus(`Error: ${error.message}`, 'error');
    throw error;
  }
}

function extractArticleContent() {
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
      if (parent && !parent.classList.contains('bias-detector-highlight') && 
          !parent.closest('#bias-detector-panel')) {
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
          break;
        }
      }
    }
  }
}

function clearHighlights() {
  document.querySelectorAll('.bias-detector-highlight').forEach(el => {
    const parent = el.parentNode;
    if (parent) {
      parent.replaceChild(document.createTextNode(el.textContent), el);
      parent.normalize();
    }
  });
}

function saveAnalysisState(sentenceReviews, analysisData) {
  const state = {
    hasAnalysis: true,
    currentUrl: window.location.href,
    analysisData: analysisData,
    sentenceReviews: sentenceReviews,
    status: { message: 'Analysis complete! Sentences highlighted on page.', type: 'success' }
  };
  
  chrome.storage.local.set({
    [`analysis_${window.location.href}`]: state
  });
}



