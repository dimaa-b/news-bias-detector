const express = require('express');
const { searchNews, getNewsForBiasAnalysis } = require('./apify-client');
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to parse JSON bodies
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Basic route
app.get('/', (req, res) => {
  res.json({
    message: 'Welcome to News Bias Detector API',
    status: 'Server is running successfully!',
    timestamp: new Date().toISOString()
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// Sample API endpoint
app.get('/api/status', (req, res) => {
  res.json({
    api: 'News Bias Detector API',
    version: '1.0.0',
    status: 'active'
  });
});

// News search endpoint using Apify
app.post('/api/search-news', async (req, res) => {
  try {
    const { queries, options } = req.body;
    
    if (!queries) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Queries parameter is required'
      });
    }

    const results = await searchNews(queries, options);
    
    res.json({
      success: true,
      count: results.length,
      data: results
    });

  } catch (error) {
    console.error('Error searching news:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to search news articles'
    });
  }
});

// Bias analysis endpoint
app.post('/api/analyze-bias', async (req, res) => {
  try {
    const { topic, maxResults = 50 } = req.body;
    
    if (!topic) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Topic parameter is required'
      });
    }

    const articles = await getNewsForBiasAnalysis(topic, maxResults);
    
    res.json({
      success: true,
      topic: topic,
      count: articles.length,
      data: articles,
      message: 'Articles retrieved for bias analysis'
    });

  } catch (error) {
    console.error('Error fetching articles for bias analysis:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to fetch articles for bias analysis'
    });
  }
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    message: `The route ${req.originalUrl} does not exist`
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err.stack);
  res.status(500).json({
    error: 'Internal Server Error',
    message: 'Something went wrong!'
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`🚀 Server is running on http://localhost:${PORT}`);
  console.log(`📊 Health check available at http://localhost:${PORT}/health`);
  console.log(`🔗 API status at http://localhost:${PORT}/api/status`);
});

module.exports = app;