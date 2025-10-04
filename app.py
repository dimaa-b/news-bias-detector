from flask import Flask, request, jsonify
from datetime import datetime
import os
from apify_news_client import apify_news_client
from newspaper_client import newspaper_client

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

@app.route('/api/fetch-article', methods=['POST'])
def fetch_article():
    """Fetch and parse a single article from URL"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'URL parameter is required'
            }), 400

        url = data['url']
        
        # Validate URL first
        validation = newspaper_client.validate_url(url)
        if not validation['valid']:
            return jsonify({
                'error': 'Invalid URL',
                'message': validation['error'],
                'url': url
            }), 400
        
        article_data = newspaper_client.fetch_article(url)
        
        if not article_data.get('success', False):
            return jsonify({
                'error': 'Article Fetch Failed',
                'message': article_data.get('error', 'Unknown error'),
                'url': url
            }), 400
        
        return jsonify({
            'success': True,
            'data': article_data
        })

    except Exception as error:
        print(f'Error fetching article: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to fetch article'
        }), 500

@app.route('/api/fetch-articles', methods=['POST'])
def fetch_articles():
    """Fetch and parse multiple articles from URLs"""
    try:
        data = request.get_json()
        
        if not data or 'urls' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'URLs parameter is required'
            }), 400

        urls = data['urls']
        
        if not isinstance(urls, list):
            return jsonify({
                'error': 'Bad Request',
                'message': 'URLs must be an array'
            }), 400
        
        if len(urls) > 10:  # Limit to prevent abuse
            return jsonify({
                'error': 'Bad Request',
                'message': 'Maximum 10 URLs allowed per request'
            }), 400
        
        articles_data = newspaper_client.fetch_multiple_articles(urls)
        
        successful_articles = [article for article in articles_data if article.get('success', False)]
        failed_articles = [article for article in articles_data if not article.get('success', False)]
        
        return jsonify({
            'success': True,
            'total_requested': len(urls),
            'successful_count': len(successful_articles),
            'failed_count': len(failed_articles),
            'successful_articles': successful_articles,
            'failed_articles': failed_articles
        })

    except Exception as error:
        print(f'Error fetching articles: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to fetch articles'
        }), 500

@app.route('/api/validate-url', methods=['POST'])
def validate_url():
    """Validate if a URL is accessible and contains article content"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'URL parameter is required'
            }), 400

        url = data['url']
        validation_result = newspaper_client.validate_url(url)
        
        return jsonify(validation_result)

    except Exception as error:
        print(f'Error validating URL: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to validate URL'
        }), 500

@app.route('/api/article-bias-analysis', methods=['POST'])
def article_bias_analysis():
    """Get article formatted for bias analysis"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'URL parameter is required'
            }), 400

        url = data['url']
        article_data = newspaper_client.get_article_for_bias_analysis(url)
        
        if not article_data.get('analysis_ready', False) and not article_data.get('success', False):
            return jsonify({
                'error': 'Article Processing Failed',
                'message': article_data.get('error', 'Unknown error'),
                'url': url
            }), 400
        
        return jsonify({
            'success': True,
            'data': article_data
        })

    except Exception as error:
        print(f'Error processing article for bias analysis: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to process article for bias analysis'
        }), 500

@app.route('/api/search-and-fetch', methods=['POST'])
def search_and_fetch():
    """Search for articles using Apify and fetch full content using Newspaper3k"""
    try:
        data = request.get_json() if request.get_json() else {}
        
        # Get search query (default to the Sean Combs query if not provided)
        query = data.get('query', 'Sean Combs Sentenced to More Than 4 Years in Prison After Apologizing for \'Sick\' Conduct')
        max_results = data.get('maxResults', 10)
        max_articles_to_fetch = data.get('maxArticlesToFetch', 5) 
        save_to_file = data.get('saveToFile', True)  # Default to saving
        
        # Step 1: Search using Apify
        search_params = {
            'queries': query,
            'resultsPerPage': max_results,
            'maxPagesPerQuery': 1
        }
        
        apify_results = apify_news_client.run_actor_sync(search_params)
        
        if not apify_results or len(apify_results) == 0:
            return jsonify({
                'success': False,
                'message': 'No search results found',
                'query': query
            }), 404
        
        # Step 2: Extract URLs from search results
        urls = []
        for result in apify_results:
            # Apify returns results with organic results
            if 'organicResults' in result:
                for organic in result['organicResults'][:max_articles_to_fetch]:
                    if 'url' in organic:
                        urls.append(organic['url'])
        
        if not urls:
            return jsonify({
                'success': False,
                'message': 'No URLs found in search results',
                'query': query,
                'search_results': apify_results
            }), 400
        
        # Step 3: Fetch articles using Newspaper3k
        fetched_articles = []
        failed_articles = []
        
        for url in urls:
            article_data = newspaper_client.fetch_article(url)
            
            if article_data.get('success', False):
                fetched_articles.append(article_data)
            else:
                failed_articles.append(article_data)
        
        # Step 4: Prepare results
        results = {
            'success': True,
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'search_results_count': len(apify_results),
            'urls_extracted': len(urls),
            'articles_fetched': len(fetched_articles),
            'articles_failed': len(failed_articles),
            'articles': fetched_articles,
            'failed': failed_articles,
            'summary': {
                'query': query,
                'total_search_results': len(apify_results),
                'urls_found': len(urls),
                'successfully_fetched': len(fetched_articles),
                'failed_to_fetch': len(failed_articles)
            }
        }
        
        # Step 5: Save to file if requested
        if save_to_file:
            import json
            
            # Create output directory if it doesn't exist
            output_dir = 'output'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_query = query.replace(' ', '_').replace('/', '_')[:50]  # Sanitize query for filename
            filename = f"{output_dir}/search_results_{safe_query}_{timestamp}.json"
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            results['saved_to_file'] = filename
        
        return jsonify(results)

    except Exception as error:
        print(f'Error in search and fetch: {error}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(error)
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