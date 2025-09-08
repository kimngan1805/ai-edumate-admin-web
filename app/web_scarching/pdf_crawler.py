# ===== app/web_scraping/pdf_crawler.py =====
"""
PDF crawling and processing functionality
"""
import os
import json
from urllib.parse import urljoin
import urllib.request
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from bs4 import BeautifulSoup
from .request_handler import RequestHandler


class PDFCrawler:
    """Handles PDF detection, download, and organization"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Subject mapping for Vietnamese educational content
        self.subject_mapping = {
            'toan': 'Toán',
            'van': 'Văn',
            'ly': 'Lý',
            'hoa': 'Hóa',
            'sinh': 'Sinh',
            'su': 'Sử',
            'dia': 'Địa',
            'anh': 'Tiếng Anh',
            'gdcd': 'GDCD',
            'tin': 'Tin học',
            'the-duc': 'Thể dục',
            'my-thuat': 'Mỹ thuật',
            'am-nhac': 'Âm nhạc'
        }
    
    def detect_subject_from_url(self, url: str) -> str:
        """Detect subject from URL path"""
        url_lower = url.lower()
        
        for key, subject in self.subject_mapping.items():
            if key in url_lower:
                return subject
        
        # Try to extract from path patterns
        import re
        subject_pattern = r'/mon-([a-z-]+)/'
        match = re.search(subject_pattern, url_lower)
        if match:
            subject_key = match.group(1)
            return self.subject_mapping.get(subject_key, subject_key.title())
        
        return 'Khác'
    
    def is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file"""
        return url.lower().endswith('.pdf')
    
    def download_pdf(self, url: str, filename: str) -> bool:
        """Download PDF file from URL"""
        try:
            print(f"📥 Downloading PDF: {filename}")
            
            # Create directory if not exists
            file_path = self.base_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with custom headers
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.getcode() == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.read())
                    
                    print(f"✅ Downloaded: {filename}")
                    return True
                else:
                    print(f"❌ HTTP {response.getcode()} for {url}")
                    return False
                    
        except Exception as e:
            print(f"❌ Download failed for {url}: {e}")
            return False
    
    def process_detail_links(self, detail_links: List[Tuple[str, str]], 
                           base_url: str) -> List[Dict[str, Any]]:
        """Process detail links to find and download PDFs"""
        downloaded_pdfs = []
        request_handler = RequestHandler()
        
        for title, url in detail_links:
            try:
                print(f"🔍 Processing: {title} -> {url}")
                
                # Direct PDF link
                if self.is_pdf_url(url):
                    subject = self.detect_subject_from_url(url)
                    filename = f"{subject}/{title.replace('/', '_')}.pdf"
                    
                    if self.download_pdf(url, filename):
                        downloaded_pdfs.append({
                            'title': title,
                            'url': url,
                            'subject': subject,
                            'filename': filename,
                            'type': 'direct_pdf'
                        })
                    continue
                
                # Crawl page for PDF links
                response = request_handler.robust_get_request(url)
                if response is None:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find PDF links in page
                pdf_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href'] # type: ignore
                    full_url = urljoin(url, href) # type: ignore
                    
                    if self.is_pdf_url(full_url):
                        pdf_links.append({
                            'text': link.get_text(strip=True),
                            'url': full_url
                        })
                
                # Download found PDFs
                subject = self.detect_subject_from_url(url)
                for pdf_link in pdf_links:
                    pdf_title = pdf_link['text'] or title
                    filename = f"{subject}/{pdf_title.replace('/', '_')}.pdf"
                    
                    if self.download_pdf(pdf_link['url'], filename):
                        downloaded_pdfs.append({
                            'title': pdf_title,
                            'url': pdf_link['url'],
                            'subject': subject,
                            'filename': filename,
                            'type': 'page_pdf',
                            'source_page': url
                        })
                
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
                continue
        
        return downloaded_pdfs
    
    def create_download_report(self, downloaded_pdfs: List[Dict[str, Any]], 
                              base_url: str, ts: str) -> str:
        """Create download report"""
        report_file = self.base_dir.parent / f"pdf_download_report_{ts}.json"
        
        # Group by subject
        subjects = {}
        for pdf in downloaded_pdfs:
            subject = pdf['subject']
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(pdf)
        
        report_data = {
            "timestamp": ts,
            "base_url": base_url,
            "total_pdfs": len(downloaded_pdfs),
            "subjects": list(subjects.keys()),
            "downloads_by_subject": subjects,
            "summary": {
                subject: len(pdfs) for subject, pdfs in subjects.items()
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 Created download report: {report_file}")
        return str(report_file)
