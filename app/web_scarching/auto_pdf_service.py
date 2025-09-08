# ===== app/web_scarching/auto_pdf_service.py =====
"""
Simple background service for automatic PDF scanning and downloading
No UI, completely automatic
"""
import os
import time
import json
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, List, Any
from .pdf_downloader import PDFDownloader # type: ignore
from .config import MULTI_DETAIL_LINK_DIR, PDF_BASE_DIR


class SimpleAutoPDFService:
    """Fully automatic background PDF scanner and downloader"""
    
    def __init__(self, scan_interval: int = 300):  # 5 minutes default
        self.scan_interval = scan_interval
        self.is_running = False
        self.thread = None
        self.downloader = PDFDownloader()
        
        # Track downloaded PDFs
        self.downloaded_urls = set()
        self.state_file = PDF_BASE_DIR / "auto_download_state.json"
        self.last_scan_times = {}
        
        # Load previous state
        self._load_state()
        
        print(f"🤖 Auto PDF Service ready - will scan every {scan_interval//60} minutes")
    
    def _load_state(self):
        """Load previous download state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.downloaded_urls = set(state.get('downloaded_urls', []))
                    self.last_scan_times = state.get('last_scan_times', {})
                print(f"📚 Loaded {len(self.downloaded_urls)} previously downloaded PDFs")
        except Exception as e:
            print(f"⚠️ State load error: {e}")
            self.downloaded_urls = set()
            self.last_scan_times = {}
    
    def _save_state(self):
        """Save current state"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                'downloaded_urls': list(self.downloaded_urls),
                'last_scan_times': self.last_scan_times,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ State save error: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get file content hash"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def _scan_for_new_pdfs(self) -> List[Dict[str, str]]:
        """Scan detail files for new PDF links"""
        new_pdfs = []
        current_time = time.time()
        
        # Find detail files
        detail_files = list(MULTI_DETAIL_LINK_DIR.glob("*.txt"))
        detail_files = [f for f in detail_files if "detail_links_" in f.name or "link_chi_tiet_" in f.name]
        
        if not detail_files:
            return []
        
        for file_path in detail_files:
            try:
                file_str = str(file_path)
                file_stat = file_path.stat()
                file_mtime = file_stat.st_mtime
                file_hash = self._get_file_hash(file_path)
                
                # Check if file changed
                last_scan_info = self.last_scan_times.get(file_str, {})
                last_mtime = last_scan_info.get('mtime', 0)
                last_hash = last_scan_info.get('hash', '')
                
                if file_mtime > last_mtime or file_hash != last_hash:
                    # Read and process file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                    
                    for line in lines:
                        # Parse line: "Title | URL" or just "URL"
                        if "|" in line:
                            parts = line.split("|", 1)
                            if len(parts) == 2:
                                title, url = parts[0].strip(), parts[1].strip()
                            else:
                                continue
                        else:
                            url = line.strip()
                            title = os.path.basename(url)
                        
                        # Check if it's a new PDF
                        if self.downloader.is_pdf_link(url) and url not in self.downloaded_urls:
                            new_pdfs.append({
                                'title': title,
                                'url': url,
                                'subject': self.downloader.extract_subject_from_url(url),
                                'source_file': file_path.name
                            })
                    
                    # Update tracking
                    self.last_scan_times[file_str] = {
                        'mtime': file_mtime,
                        'hash': file_hash,
                        'last_scan': current_time
                    }
                    
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
        
        return new_pdfs
    
    def _download_pdfs(self, pdf_links: List[Dict[str, str]]) -> int:
        """Download PDFs and return success count"""
        if not pdf_links:
            return 0
        
        # Limit batch size
        max_batch = 10
        if len(pdf_links) > max_batch:
            pdf_links = pdf_links[:max_batch]
        
        print(f"📥 Downloading {len(pdf_links)} new PDFs...")
        
        # Download
        results = self.downloader.download_pdfs_from_links(
            pdf_links, 
            max_downloads=len(pdf_links), 
            delay=20
        )
        
        # Update state
        success_count = 0
        for result in results:
            if result['status'] == 'success':
                self.downloaded_urls.add(result['url'])
                success_count += 1
        
        self._save_state()
        return success_count
    
    def _run_scan_cycle(self):
        """Single scan and download cycle"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Scan for new PDFs
            new_pdfs = self._scan_for_new_pdfs()
            
            if new_pdfs:
                print(f"🎯 [{timestamp}] Found {len(new_pdfs)} new PDF links")
                
                # Download them
                downloaded = self._download_pdfs(new_pdfs)
                
                if downloaded > 0:
                    subjects = list(set([pdf['subject'] for pdf in new_pdfs[:downloaded]]))
                    print(f"✅ [{timestamp}] Downloaded {downloaded} PDFs ({', '.join(subjects)})")
                    print(f"📊 Total downloaded: {len(self.downloaded_urls)} PDFs")
                else:
                    print(f"⚠️ [{timestamp}] Download failed for new PDFs")
            else:
                print(f"ℹ️ [{timestamp}] No new PDFs found")
                
        except Exception as e:
            print(f"❌ Error in scan cycle: {e}")
    
    def _background_loop(self):
        """Main background service loop"""
        print(f"🚀 Auto PDF Service started - scanning every {self.scan_interval//60} minutes")
        
        while self.is_running:
            try:
                self._run_scan_cycle()
                time.sleep(self.scan_interval)
            except Exception as e:
                print(f"❌ Critical error: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    def start(self):
        """Start the background service"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._background_loop, daemon=True)
        self.thread.start()
        print("✅ Auto PDF Service started in background")
    
    def stop(self):
        """Stop the service"""
        if self.is_running:
            self.is_running = False
            print("🛑 Auto PDF Service stopped")


# ===== Global service instance =====
_auto_service = None

def start_auto_pdf_service(scan_minutes: int = 5):
    """Start the automatic PDF service"""
    global _auto_service
    
    if _auto_service is None:
        _auto_service = SimpleAutoPDFService(scan_interval=scan_minutes * 60)
        _auto_service.start()
    
    return _auto_service
