// Background service worker
chrome.runtime.onInstalled.addListener(() => {
  console.log('News Bias Detector extension installed');
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'analyzeFromPanel') {
    // Trigger analysis in the content script itself
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'triggerAnalysis' });
      }
    });
  }
});


