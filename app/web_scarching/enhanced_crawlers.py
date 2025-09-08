# ===== app/web_scraping/enhanced_crawlers.py (Fixed - Keep Original Download Logic) =====
"""
Enhanced crawlers for deep PDF extraction with Selenium auto download, metadata analysis, and MinIO upload
"""
import re
import time
import os
import json
from typing import List, Tuple, Dict, Any, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path

from .crawlers import WebCrawler
from .utils import is_valid_crawl_url, save_txt, get_timestamp

# Import libraries for metadata analysis (optional)
try:
    import google.generativeai as genai
    from unidecode import unidecode
    import PyPDF2
    from minio import Minio
    METADATA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Some metadata libraries not available: {e}")
    print("   Core download functionality will still work")
    METADATA_AVAILABLE = False


class DeepPDFCrawler(WebCrawler):
    """Enhanced crawler for deep PDF extraction from edu.vn sites with auto download"""
    
    def __init__(self, request_handler, gemini_api_key=None, minio_config=None):
        super().__init__(request_handler)
        self.pdf_links = []
        self.visited_pages = set()
        self.pdf_patterns = [
            r'\.pdf$',
            r'/upload/.*\.pdf',
            r'/files/.*\.pdf',
            r'/documents/.*\.pdf',
            r'/tai-lieu/.*\.pdf'
        ]
        
        # Download statistics
        self.download_stats = {
            "total_found": 0,
            "total_attempted": 0,
            "total_downloaded": 0,
            "total_analyzed": 0,
            "total_uploaded_minio": 0,
            "download_errors": 0,
            "analysis_errors": 0,
            "upload_errors": 0
        }
        
        # Optional: Metadata analysis setup
        self.gemini_api_key = gemini_api_key
        self.gemini_client = None
        if gemini_api_key and METADATA_AVAILABLE:
            try:
                genai.configure(api_key=gemini_api_key) # type: ignore
                self.gemini_client = genai.GenerativeModel('gemini-2.0-flash-exp') # type: ignore
                print("✅ Gemini API initialized for metadata analysis")
            except Exception as e:
                print(f"⚠️ Failed to initialize Gemini API: {e}")
        
        # Optional: MinIO setup
        self.minio_client = None
        self.minio_bucket = None
        if minio_config and METADATA_AVAILABLE:
            try:
                self.minio_client = Minio( # type: ignore
                    minio_config['endpoint'],
                    access_key=minio_config['access_key'],
                    secret_key=minio_config['secret_key'],
                    secure=minio_config.get('secure', False)
                )
                self.minio_bucket = minio_config['bucket_name']
                print(f"✅ MinIO client initialized for bucket: {self.minio_bucket}")
            except Exception as e:
                print(f"⚠️ Failed to initialize MinIO client: {e}")
    
    def is_pdf_link(self, url: str) -> bool:
        """Check if URL is a PDF file"""
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in self.pdf_patterns)
    
    def setup_selenium_driver(self, download_dir: str):
        """Setup Chrome driver for PDF downloads - ORIGINAL LOGIC"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            print(f"🔧 Setting up Chrome driver for downloads...")
            print(f"📁 Download directory: {download_dir}")
            
            # Chrome options for PDF download - KEEP ORIGINAL
            options = Options()
            options.add_argument("--headless")  # Run in background
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # Download preferences - KEEP ORIGINAL
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "plugins.always_open_pdf_externally": True,
                "plugins.plugins_disabled": ["Chrome PDF Viewer"]
            }
            options.add_experimental_option("prefs", prefs)
            
            # Initialize driver - KEEP ORIGINAL
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            print("✅ Chrome driver initialized successfully")
            return driver
            
        except ImportError:
            print("❌ Selenium not installed. Please install: pip install selenium webdriver-manager")
            return None
        except Exception as e:
            print(f"❌ Error setting up Chrome driver: {e}")
            return None
    
    def analyze_pdf_metadata(self, file_path, original_filename):
        """Analyze PDF metadata using Gemini AI - OPTIONAL FEATURE"""
        if not METADATA_AVAILABLE or not self.gemini_client:
            print(f"⚠️ Metadata analysis not available for: {original_filename}")
            return None
        
        try:
            print(f"🤖 Analyzing metadata for: {original_filename}")
            
            # Extract text from PDF
            text = ""
            try:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)# type: ignore
                    for page in reader.pages:
                        text += page.extract_text() or ""
                text = text[:10000]  # Limit text length
            except Exception as e:
                print(f"⚠️ Could not extract text from PDF: {e}")
                text = ""
            
            # Gemini AI analysis
            prompt = f"""
            Phân tích tài liệu giáo dục dựa trên tên file và nội dung. Trả về JSON:
            {{
                "mon_hoc": "Toán/Ngữ văn/Vật lý/Hóa học/Sinh học/Lịch sử/Địa lý/Tiếng Anh/GDCD/Tin học/Khác",
                "cap_do_hoc": "Tiểu học/THCS/THPT/Không xác định",
                "loai_tai_lieu": "Đề thi/Bài tập/Bài giảng/Sách-Tài liệu/Soạn bài/Khác"
            }}
            
            Tên file: {original_filename}
            Nội dung: {text}
            """
            
            response = self.gemini_client.generate_content(
                contents=[prompt],
                generation_config=genai.GenerationConfig(# type: ignore
                    response_mime_type="application/json", 
                    temperature=0.0
                )
            )
            
            ai_output = json.loads(response.text)
            
            # Generate path-friendly names
            subject = unidecode(ai_output.get("mon_hoc", "khac")).replace(" ", "-").lower()# type: ignore
            level = unidecode(ai_output.get("cap_do_hoc", "khac")).replace(" ", "-").lower()# type: ignore
            content_type = unidecode(ai_output.get("loai_tai_lieu", "khac")).replace(" ", "-").lower()# type: ignore
            
            if subject in ["khong-xac-dinh", "unknown", "khac"]: 
                subject = "tong-hop"
            if level in ["khong-xac-dinh", "unknown", "khac"]: 
                level = "khac"
            if content_type in ["khong-xac-dinh", "unknown", "khac"]: 
                content_type = "tai-lieu-khac"
            
            self.download_stats["total_analyzed"] += 1
            
            return {
                "original_filename": original_filename,
                "subject_raw": ai_output.get("mon_hoc", "Khác"),
                "level_raw": ai_output.get("cap_do_hoc", "Không xác định"),
                "content_type_raw": ai_output.get("loai_tai_lieu", "Khác"),
                "subject": subject,
                "level": level,
                "content_type": content_type,
                "minio_path": f"{subject}/{level}/{content_type}/{original_filename}"
            }
            
        except Exception as e:
            print(f"❌ Metadata analysis failed: {e}")
            self.download_stats["analysis_errors"] += 1
            return None
    
    def upload_to_minio(self, file_path, minio_path, metadata_dict):
        """Upload file to MinIO - OPTIONAL FEATURE"""
        if not self.minio_client or not self.minio_bucket:
            return False
        
        try:
            print(f"📤 Uploading to MinIO: {minio_path}")
            
            self.minio_client.fput_object(
                self.minio_bucket,
                minio_path,
                file_path,
                metadata=metadata_dict
            )
            
            print(f"✅ Successfully uploaded to MinIO")
            self.download_stats["total_uploaded_minio"] += 1
            return True
            
        except Exception as e:
            print(f"❌ MinIO upload failed: {e}")
            self.download_stats["upload_errors"] += 1
            return False
    
    def download_pdfs_with_selenium(self, pdf_file_path: str, download_dir: str = "downloaded_pdfs", 
                                   wait_time: int = 30, max_files: int = None):# type: ignore
        """Download PDFs using Selenium - KEEP ORIGINAL LOGIC + ADD METADATA"""
        
        if not Path(pdf_file_path).exists():
            print(f"❌ PDF links file not found: {pdf_file_path}")
            return
        
        # Create download directory - ORIGINAL
        download_path = os.path.abspath(download_dir)
        os.makedirs(download_path, exist_ok=True)
        
        # Read PDF links from file - ORIGINAL
        print(f"📖 Reading PDF links from: {pdf_file_path}")
        with open(pdf_file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not lines:
            print("⚠️ No PDF links found in file")
            return
        
        # Limit files if specified - ORIGINAL
        if max_files:
            lines = lines[:max_files]
            print(f"📊 Limited to first {max_files} files")
        
        self.download_stats["total_found"] = len(lines)
        self.download_stats["total_attempted"] = len(lines)
        
        print(f"🚀 Starting download of {len(lines)} PDF files...")
        print(f"⏱️ Wait time per file: {wait_time} seconds")
        if self.gemini_client:
            print("🤖 Metadata analysis enabled")
        if self.minio_client:
            print(f"📤 MinIO upload enabled")
        print("=" * 60)
        
        # Setup Selenium driver - ORIGINAL
        driver = self.setup_selenium_driver(download_path)
        if not driver:
            print("❌ Cannot initialize Chrome driver. Aborting download.")
            return
        
        try:
            # Process each PDF link - KEEP ORIGINAL LOGIC
            for idx, line in enumerate(lines, start=1):
                try:
                    # Parse line format: "title | url" or just "url" - ORIGINAL
                    if "|" in line:
                        parts = line.split("|", 1)
                        title = parts[0].strip()
                        url = parts[1].strip()
                    else:
                        url = line.strip()
                        title = f"PDF_File_{idx}"
                    
                    print(f"\n📥 [{idx}/{len(lines)}] Downloading: {title}")
                    print(f"    🔗 URL: {url}")
                    
                    # Navigate to PDF URL - ORIGINAL
                    driver.get(url)
                    
                    # Wait for download to complete - ORIGINAL
                    print(f"    ⏳ Waiting {wait_time}s for download...")
                    time.sleep(wait_time)
                    
                    # Check if download completed - ORIGINAL LOGIC
                    pdf_files_before = len([f for f in os.listdir(download_path) if f.endswith('.pdf')])
                    time.sleep(2)  # Small delay
                    pdf_files_after = len([f for f in os.listdir(download_path) if f.endswith('.pdf')])
                    
                    if pdf_files_after > pdf_files_before or any(f.endswith('.pdf') for f in os.listdir(download_path)):
                        print(f"    ✅ Download completed")
                        self.download_stats["total_downloaded"] += 1
                        
                        # === NEW: OPTIONAL METADATA PROCESSING ===
                        if self.gemini_client or self.minio_client:
                            try:
                                # Find the downloaded file
                                pdf_files = [f for f in os.listdir(download_path) if f.endswith('.pdf')]
                                if pdf_files:
                                    # Get most recent file
                                    latest_file = max(pdf_files, key=lambda x: os.path.getctime(os.path.join(download_path, x)))
                                    file_path = os.path.join(download_path, latest_file)
                                    
                                    # Analyze metadata if enabled
                                    metadata = None
                                    if self.gemini_client:
                                        metadata = self.analyze_pdf_metadata(file_path, latest_file)
                                    
                                    # Upload to MinIO if enabled
                                    if self.minio_client and metadata:
                                        minio_metadata = {
                                            'Content-Type': 'application/pdf',
                                            'X-Amz-Meta-Subject': metadata['subject_raw'],
                                            'X-Amz-Meta-Level': metadata['level_raw'],
                                            'X-Amz-Meta-Content-Type': metadata['content_type_raw'],
                                            'X-Amz-Meta-Original-Url': url
                                        }
                                        
                                        self.upload_to_minio(
                                            file_path,
                                            metadata['minio_path'],
                                            minio_metadata
                                        )
                            except Exception as e:
                                print(f"    ⚠️ Metadata processing failed: {e}")
                                # Continue with download even if metadata fails
                    else:
                        print(f"    ⚠️ Download may have failed (no new PDF detected)")
                        self.download_stats["download_errors"] += 1
                    
                    # Rate limiting between downloads - ORIGINAL
                    if idx < len(lines):
                        time.sleep(3)
                    
                except Exception as e:
                    print(f"    ❌ Error downloading {url}: {e}")# type: ignore
                    self.download_stats["download_errors"] += 1
                    continue
        
        finally:
            # Clean up - ORIGINAL
            try:
                driver.quit()
                print(f"\n🔄 Chrome driver closed")
            except:
                pass
        
        # Final summary - ENHANCED
        print(f"\n🎉 DOWNLOAD COMPLETE!")
        print(f"📊 Download Statistics:")
        print(f"   📄 Total found: {self.download_stats['total_found']}")
        print(f"   🎯 Total attempted: {self.download_stats['total_attempted']}")
        print(f"   ✅ Successfully downloaded: {self.download_stats['total_downloaded']}")
        print(f"   ❌ Download errors: {self.download_stats['download_errors']}")
        if self.gemini_client:
            print(f"   🤖 Metadata analyzed: {self.download_stats['total_analyzed']}")
        if self.minio_client:
            print(f"   📤 Uploaded to MinIO: {self.download_stats['total_uploaded_minio']}")
        print(f"   📁 Download directory: {download_path}")
        
        # List downloaded files - ORIGINAL
        try:
            pdf_files = [f for f in os.listdir(download_path) if f.endswith('.pdf')]
            if pdf_files:
                print(f"\n📂 Downloaded files ({len(pdf_files)} total):")
                for i, filename in enumerate(pdf_files[:10], 1):  # Show first 10
                    print(f"   {i}. {filename}")
                if len(pdf_files) > 10:
                    print(f"   ... and {len(pdf_files) - 10} more files")
            else:
                print(f"\n⚠️ No PDF files found in download directory")
        except Exception as e:
            print(f"⚠️ Error listing downloaded files: {e}")
    
    def extract_pdf_from_page(self, url: str, base_domain_stripped: str, max_depth: int = 3) -> List[Dict[str, str]]:
        """Extract PDF links from a single page with deep crawling - ORIGINAL"""
        if url in self.visited_pages or max_depth <= 0:
            return []
        
        self.visited_pages.add(url)
        found_pdfs = []
        
        print(f"🔍 Scanning for PDFs: {url} (depth: {max_depth})")
        
        try:
            response = self.request_handler.robust_get_request(url, max_retries=2, base_delay=5)
            if response is None:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all links from page
            for a in soup.find_all("a", href=True):
                href = a.get('href', '').strip()# type: ignore
                if not href:
                    continue
                
                full_url = urljoin(url, href)
                text = a.get_text(strip=True)
                
                # Skip if not valid domain
                if not is_valid_crawl_url(full_url, base_domain_stripped):
                    continue
                
                # Direct PDF link found
                if self.is_pdf_link(full_url):
                    pdf_info = {
                        'title': text or 'Untitled PDF',
                        'url': full_url,
                        'source_page': url,
                        'type': 'direct_pdf'
                    }
                    found_pdfs.append(pdf_info)
                    print(f"  📄 Found PDF: {text} -> {full_url}")
                
                # Recursive crawl for deeper PDF links
                elif max_depth > 1 and self.should_crawl_deeper(full_url, url):
                    deeper_pdfs = self.extract_pdf_from_page(full_url, base_domain_stripped, max_depth - 1)
                    found_pdfs.extend(deeper_pdfs)
            
            # Also check for embedded PDFs in iframes, object tags, etc.
            for element in soup.find_all(['iframe', 'object', 'embed']):
                src = element.get('src') or element.get('data', '')# type: ignore
                if src and self.is_pdf_link(src):# type: ignore
                    full_url = urljoin(url, src)# type: ignore
                    if is_valid_crawl_url(full_url, base_domain_stripped):
                        found_pdfs.append({
                            'title': element.get('title', 'Embedded PDF'),# type: ignore
                            'url': full_url,
                            'source_page': url,
                            'type': 'embedded_pdf'
                        })
                        print(f"  📎 Found embedded PDF: {full_url}")
            
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error scanning {url}: {e}")
        
        return found_pdfs
    
    def should_crawl_deeper(self, target_url: str, current_url: str) -> bool:
        """Determine if we should crawl deeper into this URL - ORIGINAL"""
        target_path = urlparse(target_url).path.lower()
        
        # Skip if already visited
        if target_url in self.visited_pages:
            return False
        
        # Skip external links
        if 'http' in target_url and not 'thpttamnongdongthap.edu.vn' in target_url:
            return False
        
        # Patterns that indicate potentially valuable pages
        valuable_patterns = [
            r'/mon-[a-z\-]+/',
            r'/giao-an-dien-tu/',
            r'/tai-lieu/',
            r'/upload/',
            r'\.html$',
            r'/tong-hop/',
            r'/chuyen-de/',
            r'/bai-[0-9]+',
            r'/khbd-'
        ]
        
        # Skip patterns that are unlikely to contain PDFs
        skip_patterns = [
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$',
            r'\.css$', r'\.js$',
            r'/images/', r'/css/', r'/js/',
            r'#', r'javascript:', r'mailto:'
        ]
        
        # Skip if matches skip patterns
        if any(re.search(pattern, target_path) for pattern in skip_patterns):
            return False
        
        # Crawl if matches valuable patterns
        return any(re.search(pattern, target_path) for pattern in valuable_patterns)
    
    def crawl_edu_for_pdfs(self, initial_urls: List[Tuple[str, str]], max_depth: int = 3, 
                          auto_download: bool = True, download_dir: str = "downloaded_pdfs",
                          wait_time: int = 30, max_download_files: int = None) -> List[Dict[str, str]]:# type: ignore
        """Main function to crawl edu.vn sites for PDF files with auto download - KEEP ORIGINAL + METADATA"""
        base_domain_stripped = 'thpttamnongdongthap.edu.vn'
        all_pdfs = []
        
        print(f"🔥 Starting DEEP PDF crawl for {len(initial_urls)} URLs (max depth: {max_depth})")
        if auto_download:
            print(f"📥 Auto-download enabled to: {download_dir}")
            print(f"⏱️ Wait time per download: {wait_time}s")
        print("=" * 80)
        
        for i, (title, url) in enumerate(initial_urls, 1):
            print(f"\n📚 [{i}/{len(initial_urls)}] Processing: {title}")
            print(f"    URL: {url}")
            
            try:
                # Extract PDFs from this page and deeper levels
                page_pdfs = self.extract_pdf_from_page(url, base_domain_stripped, max_depth)
                
                if page_pdfs:
                    print(f"    ✅ Found {len(page_pdfs)} PDFs from this source")
                    all_pdfs.extend(page_pdfs)
                else:
                    print(f"    ⚠️ No PDFs found from this source")
                
                # Rate limiting between major pages
                time.sleep(3)
                
            except Exception as e:
                print(f"    ❌ Error processing {url}: {e}")
                continue
        
        # Remove duplicates
        unique_pdfs = []
        seen_urls = set()
        for pdf in all_pdfs:
            if pdf['url'] not in seen_urls:
                unique_pdfs.append(pdf)
                seen_urls.add(pdf['url'])
        
        print(f"\n🎉 DEEP PDF CRAWL COMPLETE!")
        print(f"📊 Total unique PDFs found: {len(unique_pdfs)}")
        print(f"📝 Total pages visited: {len(self.visited_pages)}")
        
        # Save PDF links to file
        pdf_file_path = None
        if unique_pdfs:
            ts = get_timestamp()
            pdf_file_path = f"pdf_links_thpttamnongdongthap_{ts}.txt"
            
            # Format: "title | url"
            pdf_lines = [f"{pdf['title']} | {pdf['url']}" for pdf in unique_pdfs]
            save_txt(pdf_file_path, pdf_lines)
            
            print(f"💾 Saved {len(unique_pdfs)} PDF links to: {pdf_file_path}")
        
        # Group by source for summary
        by_source = {}
        for pdf in unique_pdfs:
            source = pdf.get('source_page', 'Unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(pdf)
        
        print(f"\n📋 PDFs by source page:")
        for source, pdfs in by_source.items():
            print(f"  📄 {len(pdfs)} PDFs from: {source}")
        
        # ===== AUTO DOWNLOAD WITH SELENIUM (KEEP ORIGINAL + METADATA) =====
        if auto_download and pdf_file_path and unique_pdfs:
            print(f"\n🚀 STARTING AUTO DOWNLOAD WITH SELENIUM...")
            print("=" * 60)
            
            try:
                self.download_pdfs_with_selenium(
                    pdf_file_path=pdf_file_path,
                    download_dir=download_dir,
                    wait_time=wait_time,
                    max_files=max_download_files
                )
            except Exception as e:
                print(f"❌ Auto download failed: {e}")
                print("⚠️ PDF links are still saved in file for manual download")
        elif auto_download and not unique_pdfs:
            print(f"\n⚠️ No PDFs found to download")
        elif not auto_download:
            print(f"\n💾 Auto-download disabled. PDF links saved to: {pdf_file_path}")
        
        return unique_pdfs