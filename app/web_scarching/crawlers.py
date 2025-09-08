# ===== app/web_scraping/crawlers.py =====
"""
Main crawling logic
"""
import hashlib
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Any

from .request_handler import RequestHandler
from .utils import get_domain_slug, is_valid_crawl_url, save_txt


class WebCrawler:
    def __init__(self, request_handler: RequestHandler):
        self.request_handler = request_handler
    
    def crawl_category_links(self, url: str, save_dir: str, ts: str, domain_config: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Crawl category/intermediate links from a page"""
        base_domain = urlparse(url).netloc
        base_domain_stripped = base_domain.replace('www.', '')
        domain_slug = get_domain_slug(url)
        
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        file_path = Path(save_dir) / f"category_{domain_slug}_{url_hash[:10]}_{ts}.txt"
        
        if file_path.exists():
            print(f"✅ File exists {file_path}, skipping category crawl")
            with open(file_path, "r", encoding="utf-8") as f:
                return [(line.split(" | ")[0], line.split(" | ")[1]) 
                       for line in f.read().splitlines() if " | " in line]
        
        print(f"🔍 Crawling categories from: {url}")
        
        response = self.request_handler.robust_get_request(url, max_retries=5, base_delay=5)
        if response is None:
            print(f"❌ Cannot connect to {url} after 5 attempts")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        category_links = []
        
        intermediate_pattern = domain_config.get("intermediate_link_pattern")
        detail_pattern = domain_config.get("detail_link_pattern")
        
        print(f"🔍 Found {len(soup.find_all('a', href=True))} links on page")
        
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a.get('href', '')# type: ignore
            if not href:
                continue
                
            full_url = urljoin(url, href)# type: ignore
            parsed_path = urlparse(full_url).path
            
            if len(category_links) < 10:
                print(f"  📎 Link: {title[:30]} -> {href}")
            
            if (is_valid_crawl_url(full_url, base_domain_stripped) and len(title) > 3):
                is_intermediate = (intermediate_pattern and 
                                 re.search(intermediate_pattern, parsed_path, re.IGNORECASE))
                is_detail = (detail_pattern and 
                           re.search(detail_pattern, parsed_path, re.IGNORECASE))
                
                if is_intermediate and not is_detail:
                    category_links.append((title, full_url))
                    print(f"  ✅ Match intermediate: {title} -> {full_url}")
        
        # Remove duplicates
        unique_links = []
        seen_urls = set()
        for title, full_url in category_links:
            if full_url not in seen_urls:
                unique_links.append(f"{title} | {full_url}")
                seen_urls.add(full_url)
        
        if unique_links:
            save_txt(str(file_path), unique_links)
            print(f"📁 Saved {len(unique_links)} category links to {file_path}")
        else:
            print(f"⚠️ No category links found from '{url}'")
        
        return [(item.split(" | ")[0], item.split(" | ")[1]) for item in unique_links]
    
    def crawl_detail_links(self, source_urls: List[Tuple[str, str]], base_url: str, 
                          domain_config: Dict[str, Any], max_links_per_source: int = 100) -> List[Tuple[str, str]]:
        """Crawl detail links from source URLs"""
        base_domain = urlparse(base_url).netloc
        base_domain_stripped = base_domain.replace('www.', '')
        
        all_detail_links = []
        seen_urls = set()
        detail_pattern = domain_config.get("detail_link_pattern")
        
        print(f"🎯 Crawling detail links from {len(source_urls)} sources")
        
        for text_source, url_source in source_urls:
            print(f"🔍 Crawling details from: {text_source} ({url_source})")
            
            response = self.request_handler.robust_get_request(url_source, max_retries=3, base_delay=3)
            if response is None:
                print(f"❌ Cannot connect to {url_source}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            count = 0
            
            for a in soup.find_all("a", href=True):
                if count >= max_links_per_source:
                    break
                
                text = a.get_text(strip=True)
                href = a.get('href', '')# type: ignore
                if not href:
                    continue
                    
                link = urljoin(url_source, href)# type: ignore
                parsed_path = urlparse(link).path
                
                if (is_valid_crawl_url(link, base_domain_stripped) and 
                    len(text) > 3 and link not in seen_urls):
                    
                    if detail_pattern and re.search(detail_pattern, parsed_path, re.IGNORECASE):
                        all_detail_links.append((text, link))
                        seen_urls.add(link)
                        count += 1
                        print(f"    ✅ Match detail: {text} -> {link}")
            
            print(f"✅ Got {count} detail links from: {text_source}")
        
        print(f"🎉 TOTAL: {len(all_detail_links)} detail links")
        return all_detail_links
    
    def crawl_multi_level_vndoc(self, initial_url: str, save_dir: str, ts: str, 
                               domain_config: Dict[str, Any], max_depth: int = 3) -> List[Tuple[str, str]]:
        """Multi-level crawling for VnDoc: Home → Grade → Subject → Detail"""
        base_domain = urlparse(initial_url).netloc
        base_domain_stripped = base_domain.replace('www.', '')
        
        all_sources = [(base_domain_stripped, initial_url)]
        visited_urls = set([initial_url])
        
        print(f"🔄 Starting VnDoc multi-level crawl with max depth: {max_depth}")
        
        previous_level = [(base_domain_stripped, initial_url)]
        
        for depth in range(max_depth):
            print(f"\n📍 === LEVEL {depth + 1}: Finding intermediate pages ===")
            current_level = []
            
            for text_source, url_source in previous_level:
                try:
                    print(f"🔍 Finding intermediate from: {text_source} ({url_source})")
                    
                    response = self.request_handler.robust_get_request(url_source)
                    if response is None:
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    intermediate_pattern = domain_config.get("intermediate_link_pattern")
                    detail_pattern = domain_config.get("detail_link_pattern")
                    
                    found_intermediate = []
                    
                    for a in soup.find_all("a", href=True):
                        text = a.get_text(strip=True)
                        href = a.get('href', '')# type: ignore
                        if not href:
                            continue
                            
                        link = urljoin(url_source, href) # type: ignore
                        parsed_path = urlparse(link).path
                        
                        if (is_valid_crawl_url(link, base_domain_stripped) and 
                            len(text) > 3 and link not in visited_urls):
                            
                            is_intermediate = (intermediate_pattern and 
                                             re.search(intermediate_pattern, parsed_path, re.IGNORECASE))
                            is_detail = (detail_pattern and 
                                       re.search(detail_pattern, parsed_path, re.IGNORECASE))
                            
                            if is_intermediate and not is_detail:
                                found_intermediate.append((text, link))
                                visited_urls.add(link)
                                all_sources.append((text, link))
                    
                    current_level.extend(found_intermediate)
                    print(f"📝 Found {len(found_intermediate)} new intermediate pages")
                    
                except Exception as e:
                    print(f"⚠️ Error processing {url_source}: {e}")
            
            previous_level = current_level
            
            if not current_level:
                print(f"🔚 No intermediate pages found at level {depth + 1}. Stopping.")
                break
        
        print(f"\n🎯 === MULTI-LEVEL CRAWL RESULT ===")
        print(f"Total {len(all_sources)} sources for detail crawling")
        
        return all_sources