# ===== app/web_scraping/pdf_downloader.py =====
"""
Enhanced PDF downloader using Selenium for automatic PDF downloads
"""
import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, unquote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
from .utils import get_timestamp


class EnhancedPDFDownloader:
    """Enhanced PDF downloader with Selenium and fallback methods"""
    
    def __init__(self, base_download_dir: str = "downloaded_pdfs"):
        self.base_download_dir = Path(base_download_dir)
        self.base_download_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            "total_attempted": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "selenium_downloads": 0,
            "direct_downloads": 0,
            "skipped_existing": 0
        }
        
        # Subject mapping for organizing files
        self.subject_mapping = {
            'toan': 'Toán',
            'van': 'Văn',
            'ngu-van': 'Ngữ Văn',
            'ly': 'Lý',
            'vat-ly': 'Vật Lý',
            'hoa': 'Hóa',
            'hoa-hoc': 'Hóa Học',
            'sinh': 'Sinh',
            'sinh-hoc': 'Sinh Học',
            'su': 'Sử',
            'lich-su': 'Lịch Sử',
            'dia': 'Địa',
            'dia-li': 'Địa Lý',
            'anh': 'Tiếng Anh',
            'tieng-anh': 'Tiếng Anh',
            'gdcd': 'GDCD',
            'tin': 'Tin Học',
            'tin-hoc': 'Tin Học',
            'khbd': 'Kế hoạch bài dạy'
        }
    
    def detect_subject_from_url(self, url: str) -> str:
        """Detect subject from URL for file organization"""
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
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        import re
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized.strip()
    
    def setup_selenium_driver(self, download_dir: str, headless: bool = True) -> webdriver.Chrome:
        """Setup Chrome driver with download preferences"""
        options = Options()
        
        if headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Download preferences
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "plugins.plugins_disabled": ["Chrome PDF Viewer"]
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            print(f"❌ Failed to setup Chrome driver: {e}")
            raise
    
    def download_pdf_direct(self, url: str, filepath: Path) -> bool:
        """Direct download method using requests"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                print(f"⚠️ Response might not be PDF: {content_type}")
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file size
            if filepath.stat().st_size > 1024:  # At least 1KB
                print(f"✅ Direct download successful: {filepath.name}")
                self.stats["direct_downloads"] += 1
                return True
            else:
                filepath.unlink(missing_ok=True)
                print(f"❌ Downloaded file too small, might be error page")
                return False
                
        except Exception as e:
            print(f"❌ Direct download failed: {e}")
            return False
    
    def download_pdf_selenium(self, url: str, title: str, subject_dir: Path, 
                            driver: webdriver.Chrome, wait_time: int = 30) -> Optional[str]:
        """Download PDF using Selenium"""
        try:
            print(f"🌐 Opening page with Selenium: {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Check if it's a direct PDF URL
            if url.lower().endswith('.pdf'):
                print(f"📄 Direct PDF URL detected")
                time.sleep(wait_time)  # Wait for download
                self.stats["selenium_downloads"] += 1
                return self.find_downloaded_file(subject_dir, title)
            
            # Look for PDF download links on the page
            pdf_links = []
            
            # Common selectors for PDF links
            selectors = [
                "a[href$='.pdf']",
                "a[href*='.pdf']",
                "a:contains('Tải xuống')",
                "a:contains('Download')",
                ".download-link",
                ".pdf-link"
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and '.pdf' in href.lower():
                            pdf_links.append(href)
                except:
                    continue
            
            if pdf_links:
                print(f"📎 Found {len(pdf_links)} PDF links on page")
                # Click first PDF link
                first_pdf_link = pdf_links[0]
                driver.get(first_pdf_link)
                time.sleep(wait_time)
                self.stats["selenium_downloads"] += 1
                return self.find_downloaded_file(subject_dir, title)
            else:
                print(f"⚠️ No PDF links found on page")
                return None
                
        except Exception as e:
            print(f"❌ Selenium download failed: {e}")
            return None
    
    def find_downloaded_file(self, subject_dir: Path, expected_title: str) -> Optional[str]:
        """Find the most recently downloaded file in directory"""
        try:
            # List all PDF files in directory
            pdf_files = list(subject_dir.glob("*.pdf"))
            
            if not pdf_files:
                return None
            
            # Get the most recently modified file
            latest_file = max(pdf_files, key=lambda f: f.stat().st_mtime)
            
            # Rename to expected title if needed
            sanitized_title = self.sanitize_filename(expected_title)
            if not sanitized_title.endswith('.pdf'):
                sanitized_title += '.pdf'
            
            target_path = subject_dir / sanitized_title
            
            if latest_file != target_path:
                try:
                    latest_file.rename(target_path)
                    return str(target_path)
                except:
                    return str(latest_file)
            
            return str(target_path)
            
        except Exception as e:
            print(f"❌ Error finding downloaded file: {e}")
            return None
    
    def download_pdfs_from_links(self, pdf_links: List[Dict[str, str]], 
                                max_files: int = None,  # type: ignore
                                use_selenium: bool = True,
                                selenium_wait_time: int = 30) -> Dict[str, Any]:
        """Download PDFs from a list of links with both methods"""
        
        if max_files:
            pdf_links = pdf_links[:max_files]
        
        self.stats["total_attempted"] = len(pdf_links)
        
        print(f"🚀 Starting download of {len(pdf_links)} PDF files")
        print(f"📁 Base download directory: {self.base_download_dir}")
        print("=" * 60)
        
        driver = None
        downloaded_files = []
        
        try:
            # Setup Selenium driver if needed
            if use_selenium:
                driver = self.setup_selenium_driver(str(self.base_download_dir))
                print("✅ Selenium driver initialized")
        
            for idx, pdf_info in enumerate(pdf_links, 1):
                try:
                    title = pdf_info.get('title', f'file_{idx}')
                    url = pdf_info.get('url', '')
                    
                    if not url:
                        print(f"⚠️ [{idx}/{len(pdf_links)}] Skipping - no URL")
                        continue
                    
                    print(f"\n📥 [{idx}/{len(pdf_links)}] Processing: {title}")
                    print(f"    URL: {url}")
                    
                    # Detect subject and create directory
                    subject = self.detect_subject_from_url(url)
                    subject_dir = self.base_download_dir / subject
                    subject_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create target filename
                    sanitized_title = self.sanitize_filename(title)
                    if not sanitized_title.endswith('.pdf'):
                        sanitized_title += '.pdf'
                    
                    target_filepath = subject_dir / sanitized_title
                    
                    # Check if file already exists
                    if target_filepath.exists() and target_filepath.stat().st_size > 1024:
                        print(f"    ✅ File already exists, skipping")
                        self.stats["skipped_existing"] += 1
                        downloaded_files.append({
                            'title': title,
                            'url': url,
                            'filepath': str(target_filepath),
                            'subject': subject,
                            'method': 'already_exists'
                        })
                        continue
                    
                    # Try direct download first
                    print(f"    🔄 Attempting direct download...")
                    if self.download_pdf_direct(url, target_filepath):
                        self.stats["successful_downloads"] += 1
                        downloaded_files.append({
                            'title': title,
                            'url': url,
                            'filepath': str(target_filepath),
                            'subject': subject,
                            'method': 'direct'
                        })
                        continue
                    
                    # Fallback to Selenium if direct download failed
                    if use_selenium and driver:
                        print(f"    🌐 Trying Selenium download...")
                        selenium_file = self.download_pdf_selenium(
                            url, title, subject_dir, driver, selenium_wait_time
                        )
                        
                        if selenium_file:
                            self.stats["successful_downloads"] += 1
                            downloaded_files.append({
                                'title': title,
                                'url': url,
                                'filepath': selenium_file,
                                'subject': subject,
                                'method': 'selenium'
                            })
                        else:
                            print(f"    ❌ Both methods failed")
                            self.stats["failed_downloads"] += 1
                    else:
                        print(f"    ❌ Direct download failed, Selenium disabled")
                        self.stats["failed_downloads"] += 1
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"    ❌ Error processing file {idx}: {e}")
                    self.stats["failed_downloads"] += 1
                    continue
        
        finally:
            if driver:
                driver.quit()
                print("🔄 Selenium driver closed")
        
        # Create download report
        report = self.create_download_report(downloaded_files)
        
        print(f"\n🎉 DOWNLOAD COMPLETE!")
        print(f"📊 Statistics:")
        print(f"   Total attempted: {self.stats['total_attempted']}")
        print(f"   Successful: {self.stats['successful_downloads']}")
        print(f"   Failed: {self.stats['failed_downloads']}")
        print(f"   Already existed: {self.stats['skipped_existing']}")
        print(f"   Direct downloads: {self.stats['direct_downloads']}")
        print(f"   Selenium downloads: {self.stats['selenium_downloads']}")
        
        return {
            'downloaded_files': downloaded_files,
            'statistics': self.stats,
            'report_file': report
        }
    
    def create_download_report(self, downloaded_files: List[Dict[str, Any]]) -> str:
        """Create detailed download report"""
        ts = get_timestamp()
        report_file = self.base_download_dir / f"download_report_{ts}.json"
        
        # Group by subject
        by_subject = {}
        for file_info in downloaded_files:
            subject = file_info['subject']
            if subject not in by_subject:
                by_subject[subject] = []
            by_subject[subject].append(file_info)
        
        report_data = {
            "timestamp": ts,
            "statistics": self.stats,
            "total_files": len(downloaded_files),
            "files_by_subject": by_subject,
            "subject_summary": {
                subject: len(files) for subject, files in by_subject.items()
            },
            "all_files": downloaded_files
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 Download report saved: {report_file}")
        return str(report_file)
    
    def download_from_txt_file(self, txt_file_path: str, max_files: int = None) -> Dict[str, Any]: # type: ignore
        """Download PDFs from a text file containing links"""
        if not Path(txt_file_path).exists():
            raise FileNotFoundError(f"Text file not found: {txt_file_path}")
        
        print(f"📖 Reading PDF links from: {txt_file_path}")
        
        pdf_links = []
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Parse line format: "title | url" or just "url"
                if ' | ' in line:
                    parts = line.split(' | ', 1)
                    title = parts[0].strip()
                    url = parts[1].strip()
                else:
                    url = line.strip()
                    title = f"PDF_File_{line_num}"
                
                pdf_links.append({
                    'title': title,
                    'url': url
                })
        
        print(f"📄 Found {len(pdf_links)} PDF links in file")
        
        return self.download_pdfs_from_links(pdf_links, max_files)