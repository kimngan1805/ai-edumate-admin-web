# ===== app/web_scraping/specialized_crawlers.py =====
"""
Specialized crawlers for specific domains
"""
import re
import time
from typing import List, Tuple, Dict, Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from .crawlers import WebCrawler
from .utils import is_valid_crawl_url


class EducationCrawler(WebCrawler):
    """Specialized crawler for .edu.vn domains"""
    
    def crawl_edu_deep_levels(self, initial_url: str, save_dir: str, ts: str, 
                             domain_config: Dict[str, Any], max_depth: int = 4) -> List[Tuple[str, str]]:
        """Deep crawling for edu.vn domains"""
        base_domain = urlparse(initial_url).netloc
        base_domain_stripped = base_domain.replace('www.', '')
        
        all_sources = []
        visited_urls = set([initial_url])
        
        print(f"🔄 Starting deep EDU.VN crawl with {max_depth} levels")
        print("=" * 60)
        
        current_level = [(urlparse(initial_url).netloc, initial_url)]
        
        for depth in range(max_depth):
            print(f"\n📍 === LEVEL {depth + 1}: Crawling {len(current_level)} URLs ===")
            next_level = []
            
            for i, (text_source, url_source) in enumerate(current_level, 1):
                try:
                    print(f"\n🔍 [{i}/{len(current_level)}] Crawling: {text_source}")
                    print(f"    URL: {url_source}")
                    
                    response = self.request_handler.robust_get_request(
                        url_source, max_retries=2, base_delay=15
                    )
                    
                    if response is None:
                        print(f"    ❌ Cannot access after multiple attempts")
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    found_links = []
                    potential_pdf_links = []
                    
                    for a in soup.find_all("a", href=True):
                        href = a.get('href', '') # type: ignore
                        if not href:
                            continue
                            
                        text = a.get_text(strip=True)
                        full_url = urljoin(url_source, href) # type: ignore
                        
                        if (not is_valid_crawl_url(full_url, base_domain_stripped) or 
                            full_url in visited_urls):
                            continue
                        
                        path = urlparse(full_url).path
                        
                        # Pattern matching for edu.vn structure - FIXED REGEX
                        intermediate_patterns = [
                            r'/udcntt/giao-an-dien-tu/?$',
                            r'/udcntt/giao-an-dien-tu/mon-[a-z\-]+/?$',
                            r'/udcntt/giao-an-dien-tu/mon-[a-z\-]+/[a-z\-0-9]+/?$'
                        ]
                        
                        pdf_patterns = [
                            r'/udcntt/giao-an-dien-tu/mon-[a-z\-]+/[a-z\-0-9]+/[a-z\-0-9]+.*\.html$',
                            r'\.pdf$'
                        ]
                        
                        is_intermediate = any(
                            re.search(pattern, path, re.IGNORECASE) 
                            for pattern in intermediate_patterns
                        )
                        
                        is_pdf_level = any(
                            re.search(pattern, path, re.IGNORECASE) 
                            for pattern in pdf_patterns
                        )
                        
                        if len(text) > 3:
                            if is_intermediate:
                                found_links.append((text, full_url))
                                visited_urls.add(full_url)
                                print(f"    📂 Intermediate: {text[:30]} -> {path}")
                            elif is_pdf_level:
                                potential_pdf_links.append((text, full_url))
                                visited_urls.add(full_url)
                                print(f"    📄 PDF Level: {text[:30]} -> {path}")
                    
                    # Add to next level if not at max depth
                    if depth < max_depth - 1:
                        next_level.extend(found_links)
                        print(f"    ✅ Found {len(found_links)} links for next level")
                    
                    # Add PDF sources
                    all_sources.extend(potential_pdf_links)
                    if potential_pdf_links:
                        print(f"    📁 Added {len(potential_pdf_links)} potential PDF links")
                    
                    # Rate limiting for slow servers
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"    ❌ Error processing {url_source}: {e}")
                    continue
            
            current_level = next_level
            
            if not current_level:
                print(f"\n🔚 No links found at level {depth + 2}. Stopping deep crawl.")
                break
        
        print(f"\n🎯 === DEEP CRAWL RESULT ===")
        print(f"Total {len(all_sources)} sources with potential PDFs")
        
        return all_sources


class VndocCrawler(WebCrawler):
    """Specialized crawler for VnDoc.com"""
    
    def crawl_with_exclusions(self, detail_links: List[Tuple[str, str]], 
                             domain_config: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Filter out excluded keywords for VnDoc"""
        exclude_keywords = domain_config.get("exclude_keywords", [])
        
        if not exclude_keywords:
            return detail_links
        
        filtered_links = []
        for title, url in detail_links:
            url_lower = url.lower()
            title_lower = title.lower()
            
            # Check if any exclude keyword is in URL or title
            excluded = any(
                keyword.lower() in url_lower or keyword.lower() in title_lower 
                for keyword in exclude_keywords
            )
            
            if not excluded:
                filtered_links.append((title, url))
            else:
                print(f"🚫 Excluded: {title} (contains excluded keyword)")
        
        print(f"📋 Filtered {len(detail_links)} -> {len(filtered_links)} links")
        return filtered_links