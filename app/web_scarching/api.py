# ===== app/web_scraping/api.py (Enhanced) =====
"""
Flask API endpoints with PDF download functionality
"""
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify
from pathlib import Path

from .config import MULTI_DETAIL_LINK_DIR, SCRAPED_DATA_DIR, SINGLE_DETAIL_LINK_FILE, CrawlType
from .crawlers import WebCrawler
from .domain_manager import DomainManager
from .utils import extract_urls_from_text, get_domain_slug, get_timestamp, save_txt
from .pdf_downloader import EnhancedPDFDownloader
from .hocmai_crawler import HocMaiCrawler
def create_web_scraping_blueprint(domain_manager: DomainManager, crawler: WebCrawler) -> Blueprint:
    """Create Flask blueprint with all endpoints including PDF download"""
    
    web_scraping_bp = Blueprint('web_scraping_bp', __name__)
    
    @web_scraping_bp.route('/api/crawl', methods=['POST'])
    def start_crawl():
        """Main crawl endpoint with optional auto PDF download"""
        data = request.json
        url_input = data.get('url')# type: ignore
        file_content = data.get('file_content')# type: ignore
        auto_download_pdfs = data.get('auto_download_pdfs', False)  # New parameter# type: ignore
        max_pdf_downloads = data.get('max_pdf_downloads', 10)  # Limit downloads# type: ignore
        
        if not url_input and not file_content:
            return jsonify({"status": "error", "message": "Missing URL or file_content"}), 400
        
        ts = get_timestamp()
        save_dir = str(SCRAPED_DATA_DIR)
        
        # Handle file content or direct URL
        if file_content:
            print("DEBUG: Processing file content, extracting URLs")
            extracted_urls = extract_urls_from_text(file_content)
            if not extracted_urls:
                return jsonify({"status": "error", "message": "No URLs found in file content"}), 400
            
            # Save input links
            input_file = SCRAPED_DATA_DIR / f"input_links_{ts}.txt"
            save_txt(str(input_file), extracted_urls)
            url_to_process = extracted_urls[0]
        else:
            url_to_process = url_input
        
        print(f"DEBUG: Processing URL: {url_to_process}")
        
        # Get domain configuration
        domain_config = domain_manager.get_domain_configuration(url_to_process)
        if not domain_config:
            base_domain = urlparse(url_to_process).netloc.replace('www.', '')
            return jsonify({
                "status": "error", 
                "message": f"Domain {base_domain} not allowed or configured"
            }), 400
        
        try:
            # Determine crawl type
            crawl_type = domain_manager.determine_crawl_type(url_to_process, domain_config)
             # === THÊM XỬ LÝ HOCMAI ===
            if crawl_type == CrawlType.HOCMAI_SPECIAL:
                print(f"🎓 HocMai domain detected: {url_to_process}")
                
                try:
                    # Lấy tham số
                    max_lessons = data.get('max_lessons', 20)  # type: ignore # Mặc định 20 bài
                    
                    crawler_hocmai = HocMaiCrawler()
                    result = crawler_hocmai.crawl_hocmai(url_to_process, max_lessons)
                    
                    if result["status"] == "completed":
                        return jsonify({
                            "status": "success",
                           "message": f"HocMai crawl completed: {result['successful_downloads']}/{result['total_lessons_crawled']} lessons downloaded as PDF",
                            "crawler_type": "hocmai_special",
                            "total_lessons": result['total_lessons'],
                            "successful_downloads": result['successful'],
                            "failed_downloads": result['failed'],
                            "download_folders": result['download_folders'],
                            "timestamp": result['timestamp']
                        }), 200
                    else:
                        return jsonify({
                            "status": "error",
                            "message": f"HocMai crawl failed: {result.get('message', 'Unknown error')}"
                        }), 500
                except Exception as e:
                    print(f"❌ HocMai crawl error: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        "status": "error",
                        "message": f"HocMai crawl failed: {str(e)}"
                    }), 500
            
            elif crawl_type == CrawlType.LIST_PAGE:
                print(f"DEBUG: URL '{url_to_process}' is LIST_PAGE. Starting deep crawl.")
                
                base_domain = urlparse(url_to_process).netloc.replace('www.', '')
                
                # Special handling for different domains
                if base_domain == "vndoc.com":
                    print("🔥 VnDoc detected - using multi-level crawl")
                    all_sources = crawler.crawl_multi_level_vndoc(
                        url_to_process, save_dir, ts, domain_config, max_depth=3
                    )
                else:
                    # Standard crawl
                    all_sources = [(base_domain, url_to_process)]
                    category_links = crawler.crawl_category_links(
                        url_to_process, save_dir, ts, domain_config
                    )
                    if category_links:
                        all_sources.extend(category_links)
                
                # Crawl detail links
                detail_links = crawler.crawl_detail_links(
                    all_sources, url_to_process, domain_config, max_links_per_source=100
                )
                
                if not detail_links:
                    return jsonify({
                        "status": "warning", 
                        "message": "No detail links found from sources"
                    }), 200
                
                # Save results
                domain_slug = get_domain_slug(url_to_process)
                output_file = MULTI_DETAIL_LINK_DIR / f"detail_links_{domain_slug}_{ts}.txt"
                
                links_to_save = [f"{title} | {url}" for title, url in detail_links]
                save_txt(str(output_file), links_to_save)
                
                # Enhanced PDF crawl for .edu.vn domains
                pdf_results = None
                download_results = None
                
                if base_domain == "thpttamnongdongthap.edu.vn":
                    try:
                        print("🔥 Edu.vn domain detected - starting automatic deep PDF crawl")
                        from .enhanced_crawlers import DeepPDFCrawler
                        pdf_crawler = DeepPDFCrawler(crawler.request_handler)
                        
                        found_pdfs = pdf_crawler.crawl_edu_for_pdfs(detail_links, max_depth=3)
                        
                        if found_pdfs:
                            # Save PDF results
                            pdf_file = MULTI_DETAIL_LINK_DIR / f"pdf_links_{domain_slug}_{ts}.txt"
                            pdf_lines = [f"{pdf['title']} | {pdf['url']}" for pdf in found_pdfs]
                            save_txt(str(pdf_file), pdf_lines)
                            
                            pdf_results = {
                                "total_pdfs": len(found_pdfs),
                                "pdf_file": str(pdf_file),
                                "subjects": list(set([extract_subject_from_url(pdf['url']) for pdf in found_pdfs]))
                            }
                            print(f"✅ Saved {len(found_pdfs)} PDF links to {pdf_file}")
                            
                            # Auto download PDFs if requested
                            if auto_download_pdfs:
                                try:
                                    print("🚀 Starting automatic PDF download...")
                                    pdf_downloader = EnhancedPDFDownloader()
                                    
                                    # Limit downloads
                                    pdfs_to_download = found_pdfs[:max_pdf_downloads]
                                    
                                    download_results = pdf_downloader.download_pdfs_from_links(
                                        pdfs_to_download,
                                        max_files=max_pdf_downloads,
                                        use_selenium=True,
                                        selenium_wait_time=20
                                    )
                                    
                                    print(f"✅ Downloaded {download_results['statistics']['successful_downloads']} PDFs")
                                    
                                except Exception as e:
                                    print(f"⚠️ PDF download failed but continuing: {e}")
                        
                    except Exception as e:
                        print(f"⚠️ PDF crawl failed but continuing: {e}")
                
                # Build response
                response_data = {
                    "status": "success",
                    "message": f"Successfully crawled {len(detail_links)} detail links",
                    "total_detail_links_found": len(detail_links),
                    "output_file": str(output_file)
                }
                
                if pdf_results:
                    response_data.update({
                        "pdf_crawl": pdf_results,
                        "message": f"Successfully crawled {len(detail_links)} detail links and {pdf_results['total_pdfs']} PDF files"
                    })
                
                if download_results:
                    response_data.update({
                        "pdf_download": {
                            "total_downloaded": download_results['statistics']['successful_downloads'],
                            "total_failed": download_results['statistics']['failed_downloads'],
                            "download_directory": str(Path("downloaded_pdfs").absolute()),
                            "report_file": download_results['report_file']
                        },
                        "message": f"Successfully crawled {len(detail_links)} detail links, found {pdf_results['total_pdfs']} PDFs, and downloaded {download_results['statistics']['successful_downloads']} files"# type: ignore
                    })
                
                return jsonify(response_data), 200
            
            
            
            elif crawl_type == CrawlType.SINGLE_PAGE:
                print(f"DEBUG: URL '{url_to_process}' is SINGLE_PAGE")
                
                # Save single URL
                save_txt(str(SINGLE_DETAIL_LINK_FILE), [url_to_process])
                
                return jsonify({
                    "status": "success",
                    "message": f"URL saved as detail link to {SINGLE_DETAIL_LINK_FILE}",
                    "url_saved": url_to_process,
                    "output_file": str(SINGLE_DETAIL_LINK_FILE)
                }), 200
            
            else:
                return jsonify({
                    "status": "error", 
                    "message": "Cannot determine crawl type for input URL"
                }), 500
        
        except Exception as e:
            print(f"❌ General error crawling {url_to_process}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error", 
                "message": f"General error crawling {url_to_process}: {e}"
            }), 500
    
    @web_scraping_bp.route('/api/crawl-deep-pdf', methods=['POST'])
    def crawl_deep_pdf():
        """Deep crawl for PDF files from detail links"""
        data = request.json
        detail_links = data.get('detail_links', [])# type: ignore
        max_depth = data.get('max_depth', 3)# type: ignore
        auto_download = data.get('auto_download', False)  # New parameter# type: ignore
        max_downloads = data.get('max_downloads', 20)# type: ignore
        
        if not detail_links:
            return jsonify({
                "status": "error", 
                "message": "No detail links provided"
            }), 400
        
        try:
            # Convert to proper format if needed
            if isinstance(detail_links[0], str):
                formatted_links = [(link, link) for link in detail_links]
            else:
                formatted_links = detail_links
            
            # Initialize deep PDF crawler
            from .enhanced_crawlers import DeepPDFCrawler
            pdf_crawler = DeepPDFCrawler(crawler.request_handler)
            
            # Crawl for PDFs
            found_pdfs = pdf_crawler.crawl_edu_for_pdfs(formatted_links, max_depth)
            
            # Group PDFs by subject/type for better organization
            subjects = {}
            for pdf in found_pdfs:
                subject = extract_subject_from_url(pdf['url'])
                if subject not in subjects:
                    subjects[subject] = []
                subjects[subject].append(pdf)
            
            # Save results to file
            download_results = None
            if found_pdfs:
                ts = get_timestamp()
                pdf_file = MULTI_DETAIL_LINK_DIR / f"deep_pdf_crawl_{ts}.txt"
                pdf_lines = [f"{pdf['title']} | {pdf['url']} | {pdf['source_page']}" for pdf in found_pdfs]
                save_txt(str(pdf_file), pdf_lines)
                
                # Auto download if requested
                if auto_download:
                    try:
                        print("🚀 Starting automatic PDF download...")
                        pdf_downloader = EnhancedPDFDownloader()
                        
                        download_results = pdf_downloader.download_pdfs_from_links(
                            found_pdfs[:max_downloads],
                            max_files=max_downloads,
                            use_selenium=True,
                            selenium_wait_time=25
                        )
                        
                    except Exception as e:
                        print(f"⚠️ PDF download failed: {e}")
            
            response_data = {
                "status": "success",
                "message": "Deep PDF crawl completed successfully",
                "total_pdfs_found": len(found_pdfs),
                "subjects": list(subjects.keys()),
                "pdfs_by_subject": subjects,
                "all_pdfs": found_pdfs,
                "pages_visited": len(pdf_crawler.visited_pages),
                "crawl_depth": max_depth,
                "output_file": str(pdf_file) if found_pdfs else None# type: ignore
            }
            
            if download_results:
                response_data.update({
                    "download_results": {
                        "total_downloaded": download_results['statistics']['successful_downloads'],
                        "total_failed": download_results['statistics']['failed_downloads'],
                        "download_directory": str(Path("downloaded_pdfs").absolute()),
                        "report_file": download_results['report_file']
                    }
                })
            
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"❌ Error in deep PDF crawl: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Deep PDF crawl failed: {str(e)}"
            }), 500
    
    @web_scraping_bp.route('/api/download-pdfs', methods=['POST'])
    def download_pdfs():
        """Standalone endpoint for downloading PDFs"""
        data = request.json
        pdf_links = data.get('pdf_links', []) # type: ignore
        txt_file = data.get('txt_file')  # Path to text file with links# type: ignore
        max_downloads = data.get('max_downloads', 50)# type: ignore
        use_selenium = data.get('use_selenium', True)# type: ignore
        selenium_wait_time = data.get('selenium_wait_time', 30)# type: ignore
        download_dir = data.get('download_dir', 'downloaded_pdfs')# type: ignore
        
        if not pdf_links and not txt_file:
            return jsonify({
                "status": "error",
                "message": "Either 'pdf_links' array or 'txt_file' path must be provided"
            }), 400
        
        try:
            pdf_downloader = EnhancedPDFDownloader(download_dir)
            
            if txt_file:
                # Download from text file
                if not Path(txt_file).exists():
                    return jsonify({
                        "status": "error",
                        "message": f"Text file not found: {txt_file}"
                    }), 400
                
                print(f"📖 Downloading PDFs from text file: {txt_file}")
                download_results = pdf_downloader.download_from_txt_file(
                    txt_file, max_files=max_downloads
                )
            else:
                # Download from provided links
                # Normalize link format
                normalized_links = []
                for link in pdf_links:
                    if isinstance(link, str):
                        if ' | ' in link:
                            parts = link.split(' | ', 1)
                            normalized_links.append({
                                'title': parts[0].strip(),
                                'url': parts[1].strip()
                            })
                        else:
                            normalized_links.append({
                                'title': f'PDF_File_{len(normalized_links)+1}',
                                'url': link.strip()
                            })
                    elif isinstance(link, dict):
                        normalized_links.append(link)
                
                print(f"📥 Downloading {len(normalized_links)} PDFs from provided links")
                download_results = pdf_downloader.download_pdfs_from_links(
                    normalized_links,
                    max_files=max_downloads,
                    use_selenium=use_selenium,
                    selenium_wait_time=selenium_wait_time
                )
            
            return jsonify({
                "status": "success",
                "message": f"PDF download completed",
                "statistics": download_results['statistics'],
                "downloaded_files": download_results['downloaded_files'],
                "download_directory": str(Path(download_dir).absolute()),
                "report_file": download_results['report_file'],
                "subjects_found": list(set([f['subject'] for f in download_results['downloaded_files']]))
            }), 200
            
        except FileNotFoundError as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 404
        except Exception as e:
            print(f"❌ Error in PDF download: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"PDF download failed: {str(e)}"
            }), 500
    
    @web_scraping_bp.route('/api/download-status', methods=['GET'])
    def download_status():
        """Get download directory status and statistics"""
        download_dir = request.args.get('download_dir', 'downloaded_pdfs')
        
        try:
            base_dir = Path(download_dir)
            if not base_dir.exists():
                return jsonify({
                    "status": "success",
                    "message": "Download directory does not exist yet",
                    "directory": str(base_dir.absolute()),
                    "exists": False,
                    "total_files": 0,
                    "subjects": {}
                }), 200
            
            # Count files by subject
            subjects = {}
            total_files = 0
            total_size = 0
            
            for subject_dir in base_dir.iterdir():
                if subject_dir.is_dir():
                    pdf_files = list(subject_dir.glob("*.pdf"))
                    file_count = len(pdf_files)
                    subject_size = sum(f.stat().st_size for f in pdf_files)
                    
                    subjects[subject_dir.name] = {
                        "file_count": file_count,
                        "size_bytes": subject_size,
                        "size_mb": round(subject_size / (1024*1024), 2)
                    }
                    
                    total_files += file_count
                    total_size += subject_size
            
            # Find recent reports
            report_files = list(base_dir.glob("download_report_*.json"))
            recent_reports = sorted(report_files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            
            return jsonify({
                "status": "success",
                "directory": str(base_dir.absolute()),
                "exists": True,
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024*1024), 2),
                "subjects": subjects,
                "recent_reports": [str(r) for r in recent_reports]
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error checking download status: {e}"
            }), 500
    
    @web_scraping_bp.route('/api/analyze-pdf', methods=['POST'])
    def analyze_pdf_endpoint():
        """Endpoint for analyzing PDF page structure"""
        data = request.json
        url = data.get('url')# type: ignore
        
        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400
        
        try:
            return jsonify({
                "status": "success",
                "message": "PDF analysis endpoint - implementation needed",
                "url": url
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Analysis error: {e}"
            }), 500
    
    @web_scraping_bp.route('/api/crawl-pdf-only', methods=['POST'])
    def crawl_pdf_only():
        """Endpoint for PDF-only crawling"""
        data = request.json
        urls = data.get('urls', [])# type: ignore
        base_url = data.get('base_url')# type: ignore
        
        if not urls or not base_url:
            return jsonify({"status": "error", "message": "Missing URLs or base_url"}), 400
        
        try:
            # Normalize URLs to (title, url) format
            if isinstance(urls[0], str):
                detail_links = [(url, url) for url in urls]
            else:
                detail_links = urls
            
            return jsonify({
                "status": "success",
                "message": "PDF crawl endpoint - implementation needed",
                "urls_to_process": len(detail_links)
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"PDF crawl error: {e}"
            }), 500
    

    @web_scraping_bp.route('/api/crawl-hocmai', methods=['POST'])
    def crawl_hocmai_standalone():
        """Endpoint riêng để crawl HocMai"""
        data = request.json
        url_input = data.get('url', 'https://hocmai.vn/kho-tai-lieu/') # type: ignore
        max_lessons = data.get('max_lessons', 10) # type: ignore
        
        try:
            print(f"🎓 Standalone HocMai crawl: {url_input}")
            
            crawler_hocmai = HocMaiCrawler()
            result = crawler_hocmai.crawl_hocmai(url_input, max_lessons)
            
            return jsonify({
                "status": "success",
                "message": f"HocMai crawl completed: {result['successful']}/{result['total_lessons']} lessons",
                "summary": result
            }), 200
            
        except Exception as e:
            print(f"❌ Error crawling HocMai: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"HocMai crawl failed: {str(e)}"
            }), 500

    return web_scraping_bp


def extract_subject_from_url(url: str) -> str:
    """Extract subject from URL for categorization"""
    url_lower = url.lower()
    
    subjects = {
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
    
    for key, subject in subjects.items():
        if key in url_lower:
            return subject
    
    return 'Khác'