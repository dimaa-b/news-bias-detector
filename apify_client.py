import os
from apify_client import ApifyClient

class ApifyNewsClient:
    """
    A client for interacting with Apify actors to scrape news data
    """
    
    def __init__(self, api_token=None):
        """
        Initialize the ApifyClient with API token
        """
        self.client = ApifyClient(token=api_token or os.getenv('APIFY_API_TOKEN', '<YOUR_API_TOKEN>'))
        self.actor_id = "nFJndFXA5zjCTuudP"
    
    async def run_actor(self, search_params=None):
        """
        Run Apify actor to scrape search results
        
        Args:
            search_params (dict): Search parameters for the actor
            
        Returns:
            list: Array of scraped results
        """
        if search_params is None:
            search_params = {}
        
        # Default input configuration
        default_input = {
            "queries": "javascript\ntypescript\npython",
            "resultsPerPage": 100,
            "maxPagesPerQuery": 1,
            "aiMode": "aiModeOff",
            "maximumLeadsEnrichmentRecords": 0,
            "focusOnPaidAds": False,
            "searchLanguage": "",
            "languageCode": "",
            "forceExactMatch": False,
            "wordsInTitle": [],
            "wordsInText": [],
            "wordsInUrl": [],
            "mobileResults": False,
            "includeUnfilteredResults": False,
            "saveHtml": False,
            "saveHtmlToKeyValueStore": True,
            "includeIcons": False
        }

        # Merge default input with provided search parameters
        input_data = {**default_input, **search_params}

        print('Starting Apify actor run...')
        
        try:
            # Run the Actor and wait for it to finish
            run = self.client.actor(self.actor_id).call(input_data)

            print('Actor run completed. Fetching results...')

            # Fetch and return Actor results from the run's dataset
            dataset_items = self.client.dataset(run['defaultDatasetId']).list_items()
            items = dataset_items.items
            
            print(f'Retrieved {len(items)} items from dataset')
            
            return items

        except Exception as error:
            print(f'Error running Apify actor: {error}')
            raise error
    
    def search_news(self, queries, options=None):
        """
        Search for news articles with specific queries
        
        Args:
            queries (list or str): Array of search queries or single query string
            options (dict): Additional search options
            
        Returns:
            list: Array of news articles
        """
        if options is None:
            options = {}
            
        search_params = {
            'queries': '\n'.join(queries) if isinstance(queries, list) else queries,
            **options
        }

        return self.run_actor(search_params)
    
    def get_news_for_bias_analysis(self, topic, max_results=50):
        """
        Get news articles for bias analysis
        
        Args:
            topic (str): Topic to search for
            max_results (int): Maximum number of results per page
            
        Returns:
            list: Array of news articles for analysis
        """
        search_params = {
            'queries': topic,
            'resultsPerPage': max_results,
            'maxPagesPerQuery': 2,  # Get more pages for better analysis
            'saveHtml': True,  # Save HTML for detailed analysis
            'includeUnfilteredResults': True  # Include all results for comprehensive analysis
        }

        return self.run_actor(search_params)
    
    def run_actor_sync(self, search_params=None):
        """
        Synchronous version of run_actor for use with Flask
        """
        if search_params is None:
            search_params = {}
        
        # Default input configuration
        default_input = {
            "queries": "javascript\ntypescript\npython",
            "resultsPerPage": 100,
            "maxPagesPerQuery": 1,
            "aiMode": "aiModeOff",
            "maximumLeadsEnrichmentRecords": 0,
            "focusOnPaidAds": False,
            "searchLanguage": "",
            "languageCode": "",
            "forceExactMatch": False,
            "wordsInTitle": [],
            "wordsInText": [],
            "wordsInUrl": [],
            "mobileResults": False,
            "includeUnfilteredResults": False,
            "saveHtml": False,
            "saveHtmlToKeyValueStore": True,
            "includeIcons": False
        }

        # Merge default input with provided search parameters
        input_data = {**default_input, **search_params}

        print('Starting Apify actor run...')
        
        try:
            # Run the Actor and wait for it to finish
            run = self.client.actor(self.actor_id).call(input_data)

            print('Actor run completed. Fetching results...')

            # Fetch and return Actor results from the run's dataset
            dataset_items = self.client.dataset(run['defaultDatasetId']).list_items()
            items = dataset_items.items
            
            print(f'Retrieved {len(items)} items from dataset')
            
            return items

        except Exception as error:
            print(f'Error running Apify actor: {error}')
            raise error


# Create a global instance for easy import
apify_news_client = ApifyNewsClient()


def search_news_simple(queries, options=None):
    """
    Simple function to search for news articles
    """
    return apify_news_client.search_news(queries, options)


def get_news_for_bias_analysis_simple(topic, max_results=50):
    """
    Simple function to get news articles for bias analysis
    """
    return apify_news_client.get_news_for_bias_analysis(topic, max_results)