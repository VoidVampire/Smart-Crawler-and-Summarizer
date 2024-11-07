# webCrawler.py
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import deque
import re
import logging
from aiohttp import ClientTimeout
from typing import List, Dict
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelevantWebCrawler:
    def __init__(self, max_pages_per_domain=5, max_depth=2, concurrency=10, 
                 similarity_threshold=0.2, max_retries=2):
        self.max_pages_per_domain = max_pages_per_domain
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.similarity_threshold = similarity_threshold
        self.max_retries = max_retries
        
        self.visited_urls = set()
        self.domain_visit_count = {}
        self.url_queue = asyncio.Queue()
        self.relevant_pages = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.timeout = ClientTimeout(total=15)
        self.semaphore = None
        
    async def fetch_page(self, url: str, session: aiohttp.ClientSession, retry_count=0) -> str:
        """Fetch page content with retry mechanism and timeout."""
        try:
            async with session.get(url, timeout=self.timeout, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status in {429, 503} and retry_count < self.max_retries:
                    # Rate limited or service temporarily unavailable - wait and retry
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    return await self.fetch_page(url, session, retry_count + 1)
        except Exception as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(1)
                return await self.fetch_page(url, session, retry_count + 1)
            logger.error(f"Error fetching {url}: {str(e)}")
        return None

    def clean_text(self, html_content: str) -> str:
        """Extract and clean main content from HTML with improved cleaning."""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'head', 'nav', 'footer', 'iframe']):
            element.decompose()
            
        # Try to find main content area
        main_content = (soup.find('main') or 
                       soup.find('article') or 
                       soup.find('div', class_=re.compile(r'content|main|article')))
        
        if main_content:
            text_elements = main_content.find_all(['p', 'h1', 'h2', 'h3'])
        else:
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3'])
        
        text = ' '.join(elem.get_text() for elem in text_elements)
        
        # Improved text cleaning
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\b\w{1,2}\b', '', text)  # Remove very short words
        return text.strip().lower()

    async def process_url(self, url: str, original_content: str, depth: int,
                         session: aiohttp.ClientSession) -> None:
        """Process a single URL with improved error handling."""
        if depth > self.max_depth or url in self.visited_urls:
            return

        domain = urlparse(url).netloc
        if self.domain_visit_count.get(domain, 0) >= self.max_pages_per_domain:
            return

        self.visited_urls.add(url)
        self.domain_visit_count[domain] = self.domain_visit_count.get(domain, 0) + 1

        html_content = await self.fetch_page(url, session)
        if not html_content:
            return

        page_text = self.clean_text(html_content)
        if len(page_text) < 100:  # Skip pages with too little content
            return

        similarity = self.calculate_similarity(original_content, page_text)
        
        if similarity > self.similarity_threshold:
            self.relevant_pages.append({
                'url': url,
                'similarity': similarity
            })

        # Extract and queue new URLs
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for link in links:
            next_url = urljoin(url, link['href'])
            if self.is_valid_url(next_url) and next_url not in self.visited_urls:
                await self.url_queue.put((next_url, depth + 1))

    async def crawl(self, seed_urls: List[str], original_content: str) -> List[str]:
        """Main crawling function with concurrency and error handling."""
        start_time = time.time()
        self.semaphore = asyncio.Semaphore(self.concurrency)
        similarities = []
        
        # Initialize URL queue with seed URLs
        valid_seeds = [url for url in seed_urls if self.is_valid_url(url)]
        if not valid_seeds:
            return ["No valid seed URLs provided"]

        for url in valid_seeds:
            await self.url_queue.put((url, 0))

        async with aiohttp.ClientSession() as session:
            workers = []
            while (time.time() - start_time < 30 and  # 30-second timeout
                   (not self.url_queue.empty() or workers) and 
                   len(self.relevant_pages) < 7):
                
                # Start new workers if queue has URLs and we're under concurrency limit
                while not self.url_queue.empty() and len(workers) < self.concurrency:
                    url, depth = await self.url_queue.get()
                    if url not in self.visited_urls:
                        worker = asyncio.create_task(
                            self.process_url(url, original_content, depth, session)
                        )
                        workers.append(worker)
                
                # Remove completed workers
                workers = [w for w in workers if not w.done()]
                await asyncio.sleep(0.1)  # Prevent CPU hogging
                
                # Check if we're stuck
                if not workers and self.url_queue.empty() and not self.relevant_pages:
                    return ["No relevant links could be found. Please try with different keywords."]

        # Sort and return results
        sorted_pages = sorted(self.relevant_pages, 
                            key=lambda x: x['similarity'], 
                            reverse=True)
        for page in sorted_pages:
            similarities.append(page['similarity'])
        avg_similarity = np.mean(similarities) if similarities else 0
        visited_links_count = len(self.visited_urls)
        
        if not sorted_pages:
            return ["No relevant links could be found. Please try with different keywords."]
            
        return [page['url'] for page in sorted_pages[:]],visited_links_count,avg_similarity

    def is_valid_url(self, url: str) -> bool:
        """Enhanced URL validation."""
        try:
            parsed = urlparse(url)
            # Expanded list of excluded domains and patterns
            excluded_domains = {
                'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
                'linkedin.com', 'pinterest.com', 'reddit.com'
            }
            excluded_patterns = ('.pdf', '.jpg', '.png', '.gif', '.zip', '.doc', 
                               'login', 'signin', 'signup', 'register')
            
            return (all([
                parsed.scheme in {'http', 'https'},
                parsed.netloc and '.' in parsed.netloc,
                parsed.netloc not in excluded_domains,
                not any(pattern in url.lower() for pattern in excluded_patterns),
                len(url) < 250  # Avoid extremely long URLs
            ]))
        except:
            return False

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity with error handling."""
        try:
            if not text1 or not text2:
                return 0
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            return float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0

def get_relevant_links(seed_urls: List[str], original_content: str) -> List[str]:
    """Helper function with timeout protection."""
    try:
        crawler = RelevantWebCrawler()
        relevant_links, visited_links_count,avg_similarity = asyncio.run(crawler.crawl(seed_urls, original_content))
        return relevant_links, visited_links_count,avg_similarity
    except Exception as e:
        logger.error(f"Crawler error: {str(e)}")
        return ["An error occurred while searching for relevant links."]