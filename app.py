from flask import Flask, request, jsonify
from datetime import datetime
import os
from apify_client import apify_news_client

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    """Basic route"""
    return jsonify({
        'message': 'Welcome to News Bias Detector API',
        'status': 'Server is running successfully!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/status', methods=['GET'])
def api_status():
    """Sample API endpoint"""
    return jsonify({
        'api': 'News Bias Detector API',
        'version': '1.0.0',
        'status': 'active'
    })

@app.route('/api/search-news', methods=['POST'])
def search_news():
    """News search endpoint using Apify"""
    try:
        data = request.get_json()
        
        if not data or 'queries' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Queries parameter is required'
            }), 400

        queries = data['queries']
        options = data.get('options', {})
        
        results = apify_news_client.run_actor_sync({
            'queries': queries if isinstance(queries, str) else '\n'.join(queries),
            **options
        })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'data': results
        })

    except Exception as error:
        print(f'Error searching news: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to search news articles'
        }), 500

@app.route('/api/analyze-bias', methods=['POST'])
def analyze_bias():
    """Bias analysis endpoint"""
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Topic parameter is required'
            }), 400

        topic = data['topic']
        max_results = data.get('maxResults', 50)
        
        articles = apify_news_client.get_news_for_bias_analysis(topic, max_results)
        
        return jsonify({
            'success': True,
            'topic': topic,
            'count': len(articles),
            'data': articles,
            'message': 'Articles retrieved for bias analysis'
        })

    except Exception as error:
        print(f'Error fetching articles for bias analysis: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to fetch articles for bias analysis'
        }), 500

@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    return jsonify({
        'error': 'Route not found',
        'message': f'The route {request.url} does not exist'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Error handling middleware"""
    print(f'Error: {error}')
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Something went wrong!'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f'🚀 Server is running on http://localhost:{port}')
    print(f'📊 Health check available at http://localhost:{port}/health')
    print(f'🔗 API status at http://localhost:{port}/api/status')
    
    app.run(host='0.0.0.0', port=port, debug=True)