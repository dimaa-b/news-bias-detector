from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from datetime import datetime
import os
import json
from apify_news_client import apify_news_client
from newspaper_client import newspaper_client
from gemini_client import analyze_claims_simple, gemini_client

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

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

@app.route('/api/search-and-fetch-stream', methods=['POST'])
def search_and_fetch_stream():
    """Search for articles and stream analysis results sentence by sentence"""
    def generate():
        try:
            data = request.get_json() if request.get_json() else {}
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting search and fetch...'})}\n\n"
            
            # Get parameters
            target_article_data = data.get('targetArticle')
            base_query = data.get('query', 'Sean Combs Sentenced to More Than 4 Years in Prison After Apologizing for \'Sick\' Conduct')
            max_results = data.get('maxResults', 10)
            max_articles_to_fetch = data.get('maxArticlesToFetch', 10)
            use_reputable_sources = data.get('useReputableSources', True)
            
            # Load reputable sources
            query = base_query
            if use_reputable_sources:
                try:
                    with open('reputable_sources.json', 'r') as f:
                        sources_data = json.load(f)
                        websites = sources_data.get('websites', [])
                    
                    if websites:
                        site_query = ' OR '.join([f'site:{site}' for site in websites])
                        query = f'{base_query} {site_query}'
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'warning', 'message': f'Could not load reputable sources: {str(e)}'})}\n\n"
            
            # Step 1: Search using Apify
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching for articles...'})}\n\n"
            
            search_params = {
                'queries': query,
                'resultsPerPage': max_results,
                'maxPagesPerQuery': 1
            }
            
            apify_results = apify_news_client.run_actor_sync(search_params)
            
            if not apify_results or len(apify_results) == 0:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No search results found'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(apify_results)} search results'})}\n\n"
            
            # Step 2: Extract URLs
            urls = []
            for result in apify_results:
                if 'organicResults' in result:
                    for organic in result['organicResults'][:max_articles_to_fetch]:
                        if 'url' in organic:
                            urls.append(organic['url'])
            
            if not urls:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No URLs found in search results'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Extracted {len(urls)} URLs'})}\n\n"
            
            # Step 3: Fetch articles
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching article contents...'})}\n\n"
            
            fetched_articles = []
            failed_articles = []
            
            for i, url in enumerate(urls):
                yield f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': len(urls), 'message': f'Fetching article {i + 1}/{len(urls)}'})}\n\n"
                
                article_data = newspaper_client.fetch_article(url)
                
                if article_data.get('success', False):
                    fetched_articles.append(article_data)
                else:
                    failed_articles.append(article_data)
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Successfully fetched {len(fetched_articles)} articles'})}\n\n"
            
            # Send summary of fetched articles
            summary_data = {
                'type': 'fetch_summary',
                'data': {
                    'original_query': base_query,
                    'google_search_query': query,
                    'used_reputable_sources': use_reputable_sources,
                    'search_results_count': len(apify_results),
                    'urls_extracted': len(urls),
                    'articles_fetched': len(fetched_articles),
                    'articles_failed': len(failed_articles)
                }
            }
            yield f"data: {json.dumps(summary_data)}\n\n"
            
            # Step 4: Analyze claims with streaming
            if target_article_data and len(fetched_articles) >= 1:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Starting claims analysis...'})}\n\n"
                
                target_title = target_article_data.get('title', 'Untitled')
                target_text = target_article_data.get('text', '')
                target_date = target_article_data.get('date', 'Unknown')
                target_url = target_article_data.get('url', 'Unknown')
                
                # Prepare references
                references = []
                for ref in fetched_articles:
                    references.append({
                        'title': ref.get('title', 'Untitled'),
                        'text': ref.get('text', ''),
                        'date': ref.get('publish_date'),
                        'url': ref.get('url')
                    })
                
                # Use streaming analysis
                for chunk in gemini_client.analyze_claims_streaming(target_title, target_text, references, target_date):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                yield f"data: {json.dumps({'type': 'status', 'message': 'Analysis complete'})}\n\n"
            else:
                if not target_article_data:
                    yield f"data: {json.dumps({'type': 'warning', 'message': 'No target article provided'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'warning', 'message': f'Need at least 1 reference article, got {len(fetched_articles)}'})}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as error:
            yield f"data: {json.dumps({'type': 'error', 'message': str(error)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/search-and-fetch', methods=['POST'])
def search_and_fetch():
    """Search for articles using Apify and fetch full content using Newspaper3k"""
    try:
        data = request.get_json() if request.get_json() else {}
        
        # Print received data to console
        print('\n' + '='*80)
        print('📥 RECEIVED DATA FROM EXTENSION')
        print('='*80)
        
        # Get target article from extension (optional - if not provided, use first search result)
        target_article_data = data.get('targetArticle')  # {title, text, url, date}
        
        if target_article_data:
            print('\n🎯 TARGET ARTICLE:')
            print(f'  Title: {target_article_data.get("title", "N/A")}')
            print(f'  URL: {target_article_data.get("url", "N/A")}')
            print(f'  Date: {target_article_data.get("date", "N/A")}')
            print(f'  Text Length: {len(target_article_data.get("text", ""))} characters')
            print(f'\n  First 200 chars of text:')
            print(f'  {target_article_data.get("text", "")[:200]}...')
        else:
            print('\n⚠️  No target article provided in request')
        
        # Get search query (default to the Sean Combs query if not provided)
        base_query = data.get('query', 'Sean Combs Sentenced to More Than 4 Years in Prison After Apologizing for \'Sick\' Conduct')
        max_results = data.get('maxResults', 10)
        max_articles_to_fetch = data.get('maxArticlesToFetch', 10) 
        save_to_file = data.get('saveToFile', True)  # Default to saving
        use_reputable_sources = data.get('useReputableSources', True)  # Default to using reputable sources
        
        print(f'\n🔍 SEARCH PARAMETERS:')
        print(f'  Query: {base_query}')
        print(f'  Max Results: {max_results}')
        print(f'  Max to Fetch: {max_articles_to_fetch}')
        print(f'  Use Reputable Sources: {use_reputable_sources}')
        print(f'  Save to File: {save_to_file}')
        print('='*80 + '\n')
        
        # Load reputable sources and construct site-specific query
        query = base_query
        if use_reputable_sources:
            try:
                import json
                with open('reputable_sources.json', 'r') as f:
                    sources_data = json.load(f)
                    websites = sources_data.get('websites', [])
                
                if websites:
                    # Construct the site query: query site:site1.com OR site:site2.com
                    site_query = ' OR '.join([f'site:{site}' for site in websites])
                    query = f'{base_query} {site_query}'
            except Exception as e:
                print(f'Warning: Could not load reputable sources: {e}')
                # Continue with original query if file loading fails
        
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
            'original_query': base_query,
            'google_search_query': query,
            'used_reputable_sources': use_reputable_sources,
            'timestamp': datetime.now().isoformat(),
            'search_results_count': len(apify_results),
            'urls_extracted': len(urls),
            'articles_fetched': len(fetched_articles),
            'articles_failed': len(failed_articles),
            'articles': fetched_articles,
            'failed': failed_articles,
            'summary': {
                'original_query': base_query,
                'google_search_query': query,
                'used_reputable_sources': use_reputable_sources,
                'total_search_results': len(apify_results),
                'urls_found': len(urls),
                'successfully_fetched': len(fetched_articles),
                'failed_to_fetch': len(failed_articles)
            }
        }
        
        # Step 5: Analyze claims using Gemini (target from extension, all fetched articles as references)
        if target_article_data and len(fetched_articles) >= 1:
            print(f'\n=== STEP 5: ANALYZING CLAIMS WITH GEMINI ===')
            print(f'Using provided target article from extension')
            
            # Use the provided target article
            target_title = target_article_data.get('title', 'Untitled')
            target_text = target_article_data.get('text', '')
            target_date = target_article_data.get('date', 'Unknown')
            target_url = target_article_data.get('url', 'Unknown')
            
            # ALL fetched articles become references
            reference_articles = fetched_articles
            
            print(f'Target Article: {target_title[:60]}...')
            print(f'Target URL: {target_url}')
            print(f'Reference Articles: {len(reference_articles)}')
            
            # Prepare references for Gemini
            references = []
            for ref in reference_articles:
                references.append({
                    'title': ref.get('title', 'Untitled'),
                    'text': ref.get('text', ''),
                    'date': ref.get('publish_date'),
                    'url': ref.get('url')
                })
            
            # Run claims analysis
            claims_result = analyze_claims_simple(
                target_title=target_title,
                target_text=target_text,
                references=references,
                target_date=target_date
            )
            
            if claims_result.get('success'):
                print(f'\n✅ CLAIMS ANALYSIS COMPLETED')
                analysis = claims_result['analysis']
                
                # Print summary
                print(f'\n📊 ANALYSIS SUMMARY:')
                print(f'Target: {analysis["document_metadata"]["target_title"]}')
                print(f'References Used: {len(analysis["document_metadata"]["references_used"])}')
                print(f'Sentences Analyzed: {len(analysis["sentence_reviews"])}')
                
                # Print verdict counts
                print(f'\n📈 VERDICT COUNTS:')
                for verdict, count in analysis['pattern_summary']['counts_by_verdict'].items():
                    print(f'  {verdict}: {count}')
                
                # Print overall assessment
                print(f'\n🎯 OVERALL ASSESSMENT:')
                print(f'Misleading Risk Score: {analysis["overall_assessment"]["misleading_risk_score"]}/100')
                print(f'Summary: {analysis["overall_assessment"]["summary"][:200]}...')
                
                # Print top issues
                if analysis['pattern_summary']['top_recurring_patterns']:
                    print(f'\n⚠️  TOP ISSUES:')
                    for pattern in analysis['pattern_summary']['top_recurring_patterns'][:3]:
                        print(f'  - {pattern["pattern"]}: {pattern["instances"]} instances')
                
                # Print suggested corrections
                if analysis.get('suggested_corrections'):
                    print(f'\n💡 SUGGESTED CORRECTIONS: {len(analysis["suggested_corrections"])}')
                    for correction in analysis['suggested_corrections'][:3]:
                        print(f'  Sentence {correction["sentence_index"]}: {correction["problem"]}')
                
                # Add to results
                results['claims_analysis'] = claims_result
                results['target_article'] = {
                    'title': target_title,
                    'url': target_url,
                    'date': target_date
                }
                print(f'\n✅ Claims analysis added to response')
            else:
                print(f'\n❌ CLAIMS ANALYSIS FAILED: {claims_result.get("error")}')
                results['claims_analysis'] = {
                    'success': False,
                    'error': claims_result.get('error'),
                    'message': 'Failed to analyze claims with Gemini'
                }
                results['target_article'] = {
                    'title': target_title,
                    'url': target_url,
                    'date': target_date
                }
        elif not target_article_data:
            print(f'\n⚠️  SKIPPING CLAIMS ANALYSIS: No target article provided in request')
            results['claims_analysis'] = {
                'success': False,
                'message': 'No target article provided. Include "targetArticle" with title, text, url, and date in request.'
            }
        else:
            print(f'\n⚠️  SKIPPING CLAIMS ANALYSIS: Need at least 1 reference article, got {len(fetched_articles)}')
            results['claims_analysis'] = {
                'success': False,
                'message': f'Need at least 1 reference article for claims analysis. Got {len(fetched_articles)} articles.'
            }
            results['target_article'] = {
                'title': target_article_data.get('title', 'Unknown'),
                'url': target_article_data.get('url', 'Unknown'),
                'date': target_article_data.get('date', 'Unknown')
            }
        
        # Step 6: Save to file if requested
        if save_to_file:
            import json
            
            # Create output directory if it doesn't exist
            output_dir = 'output'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_query = base_query.replace(' ', '_').replace('/', '_').replace('\'', '')[:50]  # Sanitize query for filename
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