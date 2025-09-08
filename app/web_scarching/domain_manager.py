# ===== app/web_scraping/domain_manager.py =====
"""
Domain configuration management
"""
from pathlib import Path
import re
from urllib.parse import urlparse
from typing import Optional, Dict, Any

from .config import DEFAULT_DOMAIN_CONFIG, SPECIFIC_DOMAIN_CONFIGS, CrawlType


class DomainManager:
    def __init__(self, allowed_domains_file: str):
        self.allowed_domains_file = allowed_domains_file
        self.allowed_domains = self.load_allowed_domains()
    
    def load_allowed_domains(self) -> set:
        """Load allowed domains from file"""
        allowed_domains = set()
        if Path(self.allowed_domains_file).exists():
            try:
                with open(self.allowed_domains_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        domain = line.strip()
                        if domain and not domain.startswith('#'):
                            allowed_domains.add(domain)
                print(f"DEBUG: Loaded {len(allowed_domains)} domains from {self.allowed_domains_file}")
            except Exception as e:
                print(f"Error loading domains from {self.allowed_domains_file}: {e}")
        else:
            print(f"WARNING: File '{self.allowed_domains_file}' not found")
        return allowed_domains
    
    def get_domain_configuration(self, url: str) -> Optional[Dict[str, Any]]:
        """Get domain configuration for URL"""
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        stripped_domain = base_domain.replace('www.', '')
        
        if stripped_domain in SPECIFIC_DOMAIN_CONFIGS:
            print(f"DEBUG: Domain '{stripped_domain}' has specific configuration")
            return SPECIFIC_DOMAIN_CONFIGS[stripped_domain]
        
        if stripped_domain in self.allowed_domains:
            print(f"DEBUG: Domain '{stripped_domain}' allowed but using default config")
            return DEFAULT_DOMAIN_CONFIG
        
        print(f"ERROR: Domain '{stripped_domain}' not allowed or configured")
        return None
    
    def determine_crawl_type(self, url: str, config: Dict[str, Any]) -> Optional[CrawlType]:
        """Determine crawl type based on URL and configuration"""
        if self.is_hocmai_domain(url):
            print(f"DEBUG: URL '{url}' detected as HOCMAI_SPECIAL")
            return CrawlType.HOCMAI_SPECIAL
        if not config:
            return None
        
        parsed_url = urlparse(url)
        path = parsed_url.path if parsed_url.path else '/'
        
        intermediate_pattern = config.get("intermediate_link_pattern")
        if intermediate_pattern and re.search(intermediate_pattern, path, re.IGNORECASE):
            print(f"DEBUG: URL '{url}' inferred as: LIST_PAGE (matches intermediate pattern)")
            return CrawlType.LIST_PAGE
        
        detail_pattern = config.get("detail_link_pattern")
        if detail_pattern and re.search(detail_pattern, path, re.IGNORECASE):
            print(f"DEBUG: URL '{url}' inferred as: SINGLE_PAGE (matches detail pattern)")
            return CrawlType.SINGLE_PAGE
        
        if path == '/':
            print(f"DEBUG: URL '{url}' inferred as: LIST_PAGE (default for root domain)")
            return CrawlType.LIST_PAGE
        else:
            print(f"DEBUG: URL '{url}' inferred as: SINGLE_PAGE (default)")
            return CrawlType.SINGLE_PAGE
        
    def is_hocmai_domain(self, url: str) -> bool:
        """Kiểm tra có phải domain HocMai không"""
        return "hocmai.vn" in url.lower()