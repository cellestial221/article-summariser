"""
Article scraping module for extracting article content from URLs
Uses Trafilatura as primary scraper with Newspaper4k as fallback
"""

import trafilatura
from newspaper import Article as NewspaperArticle
from urllib.parse import urlparse
from typing import Dict, Optional
import logging
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleScraper:
    """Handles article scraping from URLs with multiple fallback methods"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def extract_publication_name(self, url: str) -> str:
        """Extract publication name from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove common prefixes
            domain = domain.replace('www.', '')
            domain = domain.replace('edition.', '')
            domain = domain.replace('amp.', '')

            # Get the main part of the domain
            parts = domain.split('.')
            if len(parts) >= 2:
                # Return the main domain name, capitalizing it
                pub_name = parts[0]
                # Handle special cases
                special_cases = {
                    'nytimes': 'The New York Times',
                    'wsj': 'The Wall Street Journal',
                    'ft': 'Financial Times',
                    'bbc': 'BBC News',
                    'cnn': 'CNN',
                    'reuters': 'Reuters',
                    'bloomberg': 'Bloomberg',
                    'theguardian': 'The Guardian',
                    'washingtonpost': 'The Washington Post',
                    'economist': 'The Economist',
                    'forbes': 'Forbes',
                    'businessinsider': 'Business Insider',
                    'techcrunch': 'TechCrunch',
                    'wired': 'Wired',
                    'vox': 'Vox',
                    'politico': 'Politico',
                    'axios': 'Axios',
                    'theatlantic': 'The Atlantic',
                    'newyorker': 'The New Yorker',
                    'buzzfeed': 'BuzzFeed',
                    'huffpost': 'HuffPost',
                    'slate': 'Slate',
                    'salon': 'Salon',
                    'thedailybeast': 'The Daily Beast',
                    'thehill': 'The Hill',
                    'motherjones': 'Mother Jones',
                    'theintercept': 'The Intercept',
                    'propublica': 'ProPublica',
                    'apnews': 'Associated Press',
                    'npr': 'NPR',
                    'cbsnews': 'CBS News',
                    'nbcnews': 'NBC News',
                    'abcnews': 'ABC News',
                    'foxnews': 'Fox News',
                    'usatoday': 'USA Today',
                    'latimes': 'Los Angeles Times',
                    'chicagotribune': 'Chicago Tribune',
                    'bostonglobe': 'The Boston Globe',
                    'seattletimes': 'The Seattle Times',
                    'denverpost': 'The Denver Post',
                    'miamiherald': 'Miami Herald',
                    'startribune': 'Star Tribune',
                    'dallasnews': 'The Dallas Morning News',
                    'sfchronicle': 'San Francisco Chronicle',
                    'newsweek': 'Newsweek',
                    'time': 'TIME',
                    'fortune': 'Fortune',
                    'cnbc': 'CNBC',
                    'marketwatch': 'MarketWatch',
                    'barrons': 'Barron\'s',
                    'investopedia': 'Investopedia',
                    'morningstar': 'Morningstar',
                    'seekingalpha': 'Seeking Alpha',
                    'benzinga': 'Benzinga',
                    'thestreet': 'TheStreet'
                }

                if pub_name.lower() in special_cases:
                    return special_cases[pub_name.lower()]
                else:
                    # Capitalize first letter of each word
                    return pub_name.replace('-', ' ').replace('_', ' ').title()

            return domain.title()
        except:
            return ""

    def scrape_with_trafilatura(self, url: str) -> Optional[Dict[str, str]]:
        """
        Primary scraping method using Trafilatura
        Returns dict with 'text', 'title', and 'author' if successful
        """
        try:
            logger.info(f"Attempting to scrape with Trafilatura: {url}")

            # Download the URL content
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.warning("Trafilatura couldn't download the URL")
                return None

            # Extract the article text
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                deduplicate=True,
                favor_precision=True,
                favor_recall=False,
                output_format='txt'
            )

            if not text:
                logger.warning("Trafilatura couldn't extract text")
                return None

            # Also try to get metadata
            metadata = trafilatura.extract_metadata(downloaded)

            result = {
                'text': text,
                'title': metadata.title if metadata and metadata.title else '',
                'author': metadata.author if metadata and metadata.author else '',
                'publication': self.extract_publication_name(url)
            }

            logger.info("Successfully scraped with Trafilatura")
            return result

        except Exception as e:
            logger.error(f"Trafilatura error: {str(e)}")
            return None

    def scrape_with_newspaper(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fallback scraping method using Newspaper4k
        Returns dict with 'text', 'title', and 'author' if successful
        """
        try:
            logger.info(f"Attempting to scrape with Newspaper4k: {url}")

            # Create article object
            article = NewspaperArticle(url)

            # Download and parse
            article.download()
            article.parse()

            # Check if we got text
            if not article.text or len(article.text.strip()) < 100:
                logger.warning("Newspaper4k couldn't extract sufficient text")
                return None

            result = {
                'text': article.text,
                'title': article.title if article.title else '',
                'author': ', '.join(article.authors) if article.authors else '',
                'publication': self.extract_publication_name(url)
            }

            logger.info("Successfully scraped with Newspaper4k")
            return result

        except Exception as e:
            logger.error(f"Newspaper4k error: {str(e)}")
            return None

    def scrape_article(self, url: str) -> Dict[str, any]:
        """
        Main method to scrape an article from URL
        Tries multiple methods and returns the result

        Returns:
            Dict with keys:
                - 'success': bool indicating if scraping succeeded
                - 'text': article text (if successful)
                - 'title': article title (if available)
                - 'author': article author (if available)
                - 'publication': publication name extracted from URL
                - 'error': error message (if failed)
                - 'method': which scraper succeeded ('trafilatura' or 'newspaper')
        """

        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return {
                'success': False,
                'error': 'Please enter a valid URL starting with http:// or https://'
            }

        # Try to detect if it's a known paywall site
        paywall_domains = [
            'wsj.com', 'ft.com', 'economist.com', 'telegraph.co.uk',
            'thetimes.co.uk', 'hbr.org', 'theatlantic.com',
            'foreignaffairs.com', 'seekingalpha.com', 'barrons.com',
            'investors.com', 'nytimes.com', 'washingtonpost.com',
            'bloomberg.com', 'businessinsider.com', 'wired.com'
        ]

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')

        is_likely_paywalled = any(paywall in domain for paywall in paywall_domains)

        # Try Trafilatura first
        result = self.scrape_with_trafilatura(url)
        if result and result.get('text'):
            return {
                'success': True,
                'text': result['text'],
                'title': result.get('title', ''),
                'author': result.get('author', ''),
                'publication': result.get('publication', ''),
                'method': 'trafilatura',
                'paywall_warning': is_likely_paywalled
            }

        # Fallback to Newspaper4k
        result = self.scrape_with_newspaper(url)
        if result and result.get('text'):
            return {
                'success': True,
                'text': result['text'],
                'title': result.get('title', ''),
                'author': result.get('author', ''),
                'publication': result.get('publication', ''),
                'method': 'newspaper4k',
                'paywall_warning': is_likely_paywalled
            }

        # If both failed
        error_msg = "Unable to extract article content from this URL. "
        if is_likely_paywalled:
            error_msg += "This site often has paywalled content. Please copy and paste the article text manually if you have access."
        else:
            error_msg += "The page might be behind a paywall, use dynamic content loading, or have an unusual structure. Please copy and paste the article text manually."

        return {
            'success': False,
            'error': error_msg,
            'publication': self.extract_publication_name(url)
        }
