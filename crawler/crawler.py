import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import logging
from typing import Set, List, Tuple
import time

class WebCrawler:
    def __init__(self, max_pages=50, delay=1):
        """
        Initialize the web crawler
        
        Args:
            max_pages (int): Maximum number of pages to crawl per domain
            delay (int): Delay between requests in seconds
        """
        self.max_pages = max_pages
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PixelPulse-Crawler/1.0'
        })
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing query strings, fragments, and trailing slashes
        
        Args:
            url (str): URL to normalize
            
        Returns:
            str: Normalized URL
        """
        parsed = urlparse(url)
        # Remove query and fragment, normalize path
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
        return normalized
    
    def extract_path(self, url: str) -> str:
        """
        Extract path from URL for matching purposes
        
        Args:
            url (str): Full URL
            
        Returns:
            str: Path component of URL
        """
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return path if path else '/'
    
    def get_internal_links(self, url: str, base_domain: str) -> Set[str]:
        """
        Extract all internal links from a webpage
        
        Args:
            url (str): URL to crawl
            base_domain (str): Base domain to filter internal links
            
        Returns:
            Set[str]: Set of internal URLs found
        """
        try:
            self.logger.info(f"Crawling: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = set()
            
            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, href)
                
                # Check if link is internal (same domain)
                parsed_link = urlparse(absolute_url)
                if parsed_link.netloc == base_domain:
                    normalized_url = self.normalize_url(absolute_url)
                    links.add(normalized_url)
            
            return links
            
        except requests.RequestException as e:
            self.logger.error(f"Error crawling {url}: {str(e)}")
            return set()
        except Exception as e:
            self.logger.error(f"Unexpected error crawling {url}: {str(e)}")
            return set()
    
    def crawl_domain(self, start_url: str) -> Set[str]:
        """
        Crawl a domain starting from the given URL
        
        Args:
            start_url (str): Starting URL for crawling
            
        Returns:
            Set[str]: Set of all discovered URLs
        """
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        
        discovered_urls = set()
        urls_to_crawl = {self.normalize_url(start_url)}
        crawled_urls = set()
        
        self.logger.info(f"Starting crawl of domain: {base_domain}")
        
        while urls_to_crawl and len(crawled_urls) < self.max_pages:
            current_url = urls_to_crawl.pop()
            
            if current_url in crawled_urls:
                continue
                
            crawled_urls.add(current_url)
            discovered_urls.add(current_url)
            
            # Get links from current page
            new_links = self.get_internal_links(current_url, base_domain)
            
            # Add new links to crawl queue
            for link in new_links:
                if link not in crawled_urls:
                    urls_to_crawl.add(link)
            
            # Respect delay between requests
            if self.delay > 0:
                time.sleep(self.delay)
        
        self.logger.info(f"Crawl completed. Found {len(discovered_urls)} URLs for {base_domain}")
        return discovered_urls
    
    def find_matching_pages(self, staging_url: str, production_url: str) -> List[Tuple[str, str, str]]:
        """
        Crawl both staging and production URLs and find matching pages
        
        Args:
            staging_url (str): Staging environment URL
            production_url (str): Production environment URL
            
        Returns:
            List[Tuple[str, str, str]]: List of (path, staging_full_url, production_full_url)
        """
        self.logger.info(f"Starting crawl comparison between staging and production")
        
        # Crawl both domains
        staging_urls = self.crawl_domain(staging_url)
        production_urls = self.crawl_domain(production_url)
        
        # Extract paths for matching
        staging_paths = {self.extract_path(url): url for url in staging_urls}
        production_paths = {self.extract_path(url): url for url in production_urls}
        
        # Find matching paths
        common_paths = set(staging_paths.keys()) & set(production_paths.keys())
        
        matched_pages = []
        for path in common_paths:
            staging_full_url = staging_paths[path]
            production_full_url = production_paths[path]
            matched_pages.append((path, staging_full_url, production_full_url))
        
        self.logger.info(f"Found {len(matched_pages)} matching pages")
        return matched_pages