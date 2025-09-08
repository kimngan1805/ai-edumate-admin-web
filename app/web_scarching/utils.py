# ===== app/web_scraping/utils.py =====
"""
Utility functions for web scraping
"""
from pathlib import Path
import re
from datetime import datetime
from urllib.parse import urlparse
from typing import List


def get_timestamp() -> str:
    """Get current timestamp in format YYYYMMDD_HHMMSS"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_domain_slug(url: str) -> str:
    """Extract domain slug from URL for filename purposes"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        domain = domain.replace('www.', '').split('.')[0]
        return re.sub(r'[^a-zA-Z0-9_-]', '', domain).lower()
    except Exception as e:
        print(f"DEBUG: Error getting domain slug for {url}: {e}")
        return "unknown_domain"


def save_txt(filename: str, lines: List[str], mode: str = "w") -> None:
    """Save lines to text file"""
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, mode, encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"DEBUG: Saved TXT to {filename}")


def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text content"""
    url_regex = r'(https?:\/\/[^\s"\']+|www\.[^\s"\']+\.[^\s"\']+)'
    found_urls = re.findall(url_regex, text)
    
    cleaned_urls = []
    for url in found_urls:
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        url = url.split('"')[0].split("'")[0].split('<')[0].split(' ')[0]
        cleaned_urls.append(url)
    return list(set(cleaned_urls))


def is_valid_crawl_url(url: str, base_domain_stripped: str) -> bool:
    """Check if URL is valid for crawling"""
    try:
        parsed_url = urlparse(url)
        return (parsed_url.scheme in ['http', 'https'] and
                parsed_url.netloc and
                base_domain_stripped in parsed_url.netloc) # type: ignore
    except:
        return False
