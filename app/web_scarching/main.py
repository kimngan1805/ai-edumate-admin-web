"""
Main application entry point
"""
from flask import Flask

from app.web_scarching.api import create_web_scraping_blueprint
from app.web_scarching.config import ALLOWED_DOMAINS_FILE
from app.web_scarching.crawlers import WebCrawler
from app.web_scarching.domain_manager import DomainManager
from app.web_scarching.request_handler import RequestHandler


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Initialize components
    domain_manager = DomainManager(str(ALLOWED_DOMAINS_FILE))
    request_handler = RequestHandler()
    crawler = WebCrawler(request_handler)
    
    # Register blueprint
    web_scraping_bp = create_web_scraping_blueprint(domain_manager, crawler)
    app.register_blueprint(web_scraping_bp)
    
    @app.route('/')
    def index():
        return {
            "message": "Web Scraping API",
            "endpoints": [
                "/api/crawl",
                "/api/analyze-pdf", 
                "/api/crawl-pdf-only"
            ]
        }
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)