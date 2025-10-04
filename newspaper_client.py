from newspaper import Article, Config
import requests
from urllib.parse import urlparse
import logging
from datetime import datetime

class NewspaperClient:
    """
    A client for fetching and parsing news articles using Newspaper3k
    """
    
    def __init__(self, user_agent=None, timeout=10, language='en'):
        """
        Initialize the Newspaper client
        
        Args:
            user_agent (str): Custom user agent string
            timeout (int): Request timeout in seconds
            language (str): Language code for article parsing
        """
        self.config = Config()
        self.config.browser_user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.config.request_timeout = timeout
        self.config.language = language
        self.config.memoize_articles = False
        self.config.fetch_images = False
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def fetch_article(self, url):
        """
        Fetch and parse a single article from a URL
        
        Args:
            url (str): The URL of the article to fetch
            
        Returns:
            dict: Parsed article data or None if failed
        """
        try:
            # Validate URL
            if not self._is_valid_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            self.logger.info(f"Fetching article from: {url}")
            
            # Create article object
            article = Article(url, config=self.config)
            
            # Download and parse the article
            article.download()
            article.parse()
            
            # Perform NLP (Natural Language Processing)
            try:
                article.nlp()
            except Exception as nlp_error:
                self.logger.warning(f"NLP processing failed for {url}: {nlp_error}")
            
            # Extract article data
            article_data = {
                'url': url,
                'title': article.title,
                'text': article.text,
                'summary': article.summary if hasattr(article, 'summary') else '',
                'keywords': list(article.keywords) if hasattr(article, 'keywords') else [],
                'authors': article.authors,
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'top_image': article.top_image,
                'images': list(article.images),
                'movies': list(article.movies),
                'meta_description': article.meta_description,
                'meta_keywords': article.meta_keywords,
                'tags': list(article.tags),
                'source_url': article.source_url,
                'canonical_link': article.canonical_link,
                'word_count': len(article.text.split()) if article.text else 0,
                'fetched_at': datetime.now().isoformat(),
                'language': article.meta_lang or self.config.language,
                'success': True
            }
            
            self.logger.info(f"Successfully fetched article: {article.title[:50]}...")
            return article_data
            
        except Exception as error:
            self.logger.error(f"Error fetching article from {url}: {error}")
            return {
                'url': url,
                'error': str(error),
                'success': False,
                'fetched_at': datetime.now().isoformat()
            }
    
    def fetch_multiple_articles(self, urls):
        """
        Fetch and parse multiple articles from a list of URLs
        
        Args:
            urls (list): List of URLs to fetch
            
        Returns:
            list: List of parsed article data
        """
        articles = []
        
        for url in urls:
            article_data = self.fetch_article(url)
            articles.append(article_data)
        
        self.logger.info(f"Fetched {len(articles)} articles")
        return articles
    
    def get_article_for_bias_analysis(self, url):
        """
        Fetch article specifically formatted for bias analysis
        
        Args:
            url (str): The URL of the article to fetch
            
        Returns:
            dict: Article data formatted for bias analysis
        """
        article_data = self.fetch_article(url)
        
        if not article_data.get('success', False):
            return article_data
        
        # Format for bias analysis
        bias_analysis_data = {
            'url': article_data['url'],
            'title': article_data['title'],
            'content': article_data['text'],
            'summary': article_data['summary'],
            'keywords': article_data['keywords'],
            'authors': article_data['authors'],
            'publish_date': article_data['publish_date'],
            'source': self._extract_domain(article_data['url']),
            'word_count': article_data['word_count'],
            'meta_description': article_data['meta_description'],
            'language': article_data['language'],
            'fetched_at': article_data['fetched_at'],
            'analysis_ready': True
        }
        
        return bias_analysis_data
    
    def validate_url(self, url):
        """
        Validate if a URL is accessible and contains article content
        
        Args:
            url (str): URL to validate
            
        Returns:
            dict: Validation results
        """
        try:
            if not self._is_valid_url(url):
                return {
                    'valid': False,
                    'error': 'Invalid URL format',
                    'url': url
                }
            
            # Check if URL is accessible
            response = requests.head(url, timeout=5)
            
            if response.status_code != 200:
                return {
                    'valid': False,
                    'error': f'HTTP {response.status_code}',
                    'url': url
                }
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return {
                    'valid': False,
                    'error': f'Invalid content type: {content_type}',
                    'url': url
                }
            
            return {
                'valid': True,
                'url': url,
                'status_code': response.status_code,
                'content_type': content_type
            }
            
        except Exception as error:
            return {
                'valid': False,
                'error': str(error),
                'url': url
            }
    
    def _is_valid_url(self, url):
        """
        Check if URL has valid format
        
        Args:
            url (str): URL to check
            
        Returns:
            bool: True if valid URL format
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _extract_domain(self, url):
        """
        Extract domain from URL
        
        Args:
            url (str): URL to extract domain from
            
        Returns:
            str: Domain name
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return 'unknown'


# Create a global instance for easy import
newspaper_client = NewspaperClient()


def fetch_article_simple(url):
    """
    Simple function to fetch a single article
    """
    return newspaper_client.fetch_article(url)


def fetch_articles_simple(urls):
    """
    Simple function to fetch multiple articles
    """
    return newspaper_client.fetch_multiple_articles(urls)


def get_article_for_bias_analysis_simple(url):
    """
    Simple function to get article for bias analysis
    """
    return newspaper_client.get_article_for_bias_analysis(url)