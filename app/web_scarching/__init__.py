# ===== app/web_scraping/__init__.py =====
"""
Web scraping module for educational content
"""

from .domain_manager import DomainManager
from .request_handler import RequestHandler
from .crawlers import WebCrawler
from .pdf_crawler import PDFCrawler
from .pdf_downloader import EnhancedPDFDownloader  # New import
from .api import create_web_scraping_blueprint
from .config import CrawlType, ALLOWED_DOMAINS_FILE, SCRAPED_DATA_DIR

__all__ = [
    'DomainManager',
    'RequestHandler', 
    'WebCrawler',
    'PDFCrawler',
    'create_web_scraping_blueprint',
    'CrawlType',
    'ALLOWED_DOMAINS_FILE',
    'SCRAPED_DATA_DIR',
    'EnhancedPDFDownloader' 

]

__version__ = '1.0.0'