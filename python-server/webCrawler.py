import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import deque
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelevantWebCrawler:
    def __init__(self, max_pages_per_domain=5, max_depth=2, concurrency=3):
        self.max_pages_per_domain = max_pages_per_domain
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.visited_urls = set()
        self.domain_visit_count = {}
        self.url_queue = deque()
        self.relevant_pages = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.session = None
        self.lock = threading.Lock()
        
    async def init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    def get_domain(self, url):
        return urlparse(url).netloc

    def is_valid_url(self, url):
        """Check if URL is valid and should be crawled."""
        try:
            parsed = urlparse(url)
            # Exclude social media, video sites, etc.
            excluded_domains = {'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com'}
            return (
                parsed.scheme in {'http', 'https'} and
                parsed.netloc not in excluded_domains and
                not url.endswith(('.pdf', '.jpg', '.png', '.gif'))
            )
        except:
            return False

    async def fetch_page(self, url):
        """Fetch page content with error handling and rate limiting."""
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
        return None

    def clean_text(self, html_content):
        """Extract and clean main content from HTML."""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove scripts, styles, and comments
        for element in soup(['script', 'style', 'head']):
            element.decompose()
            
        # Extract text from paragraphs and headers
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'article'])
        text = ' '.join(elem.get_text() for elem in text_elements)
        
        # Clean the text
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip().lower()

    def calculate_similarity(self, text1, text2):
        """Calculate cosine similarity between two texts."""
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except Exception:
            return 0

    async def process_page(self, url, original_content, depth=0):
        """Process a single page and find relevant links."""
        if depth > self.max_depth or url in self.visited_urls:
            return

        domain = self.get_domain(url)
        if self.domain_visit_count.get(domain, 0) >= self.max_pages_per_domain:
            return

        self.visited_urls.add(url)
        with self.lock:
            self.domain_visit_count[domain] = self.domain_visit_count.get(domain, 0) + 1

        html_content = await self.fetch_page(url)
        if not html_content:
            return

        # Extract and clean text
        page_text = self.clean_text(html_content)
        
        # Calculate relevance
        similarity = self.calculate_similarity(original_content, page_text)
        
        # If page is relevant, add to results
        if similarity > 0.2:  # Threshold can be adjusted
            with self.lock:
                self.relevant_pages.append({
                    'url': url,
                    'similarity': similarity
                })

        # Extract links for further crawling
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for link in links:
            next_url = urljoin(url, link['href'])
            if (self.is_valid_url(next_url) and 
                next_url not in self.visited_urls and 
                self.get_domain(next_url) not in self.domain_visit_count):
                self.url_queue.append((next_url, depth + 1))

    async def crawl(self, seed_urls, original_content):
        """Main crawling function that processes multiple pages concurrently."""
        await self.init_session()
        
        # Initialize queue with seed URLs
        for url in seed_urls:
            if self.is_valid_url(url):
                self.url_queue.append((url, 0))

        while self.url_queue and len(self.relevant_pages) < 7:
            # Process multiple pages concurrently
            tasks = []
            for _ in range(min(self.concurrency, len(self.url_queue))):
                if self.url_queue:
                    url, depth = self.url_queue.popleft()
                    tasks.append(self.process_page(url, original_content, depth))
            
            if tasks:
                await asyncio.gather(*tasks)

        await self.close_session()
        
        # Sort pages by relevance and return top 7
        sorted_pages = sorted(self.relevant_pages, 
                            key=lambda x: x['similarity'], 
                            reverse=True)
        return [page['url'] for page in sorted_pages[:7]]

def get_relevant_links(seed_urls, original_content):
    """Helper function to run the crawler with asyncio."""
    crawler = RelevantWebCrawler()
    return asyncio.run(crawler.crawl(seed_urls, original_content))