# ===== app/web_scraping/hocmai_crawler.py (MODIFIED: ONLY CRAWL & MOVE) =====
"""
HocMai crawler: Chỉ crawl và tạo PDF, sau đó chuyển sang folder cho BackgroundPDFProcessor xử lý.
Không còn xử lý metadata và upload MinIO trực tiếp trong file này.
"""
import requests
from bs4 import BeautifulSoup
import os
import img2pdf
from urllib.parse import urljoin
import time
from pathlib import Path
import json
import logging
import shutil # Import shutil để di chuyển file

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# KHÔNG CÒN IMPORT PDFMetadataProcessor Ở ĐÂY NỮA
# (Vì việc xử lý metadata đã được chuyển sang BackgroundPDFProcessor trong run.py)

class HocMaiCrawler:
    def __init__(self, base_output_dir: Path = None): # type: ignore # Không cần gemini_api_key, minio_config ở đây nữa
        # Thư mục gốc cho tất cả các output của HocMai Crawler
        if base_output_dir is None:
            try:
                from .config import MULTI_DETAIL_LINK_DIR
            except ImportError:
                logger.warning("❌ config.py not found or MULTI_DETAIL_LINK_DIR not defined. Using default 'crawled_output'.")
                MULTI_DETAIL_LINK_DIR = Path("crawled_output") 
                
            self.base_output_dir = MULTI_DETAIL_LINK_DIR / "hocmai_crawls" 
        else:
            self.base_output_dir = base_output_dir
            
        os.makedirs(self.base_output_dir, exist_ok=True)
        
        # Thư mục TRUNG GIAN để lưu PDF TẠM THỜI sau khi crawl
        # Sau đó sẽ được chuyển sang downloaded_pdfs
        self.temp_pdf_dir = self.base_output_dir / "pdfs_from_hocmai"
        os.makedirs(self.temp_pdf_dir, exist_ok=True) 
        
        # Thư mục đích cuối cùng cho PDF, nơi BackgroundPDFProcessor sẽ giám sát
        self.final_pdf_destination_dir = Path("downloaded_pdfs")
        os.makedirs(self.final_pdf_destination_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.current_crawl_output_dir = self.base_output_dir / f"crawl_session_{timestamp}"
        
        self.save_images = self.current_crawl_output_dir / "images"
        
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        os.makedirs(self.current_crawl_output_dir, exist_ok=True)
        os.makedirs(self.save_images, exist_ok=True)
        
        logger.info(f"📁 Base output directory for reports/images: {self.base_output_dir}")
        logger.info(f"📁 Temporary PDF directory: {self.temp_pdf_dir}")
        logger.info(f"📁 Final PDF destination for processing: {self.final_pdf_destination_dir}")

        # KHÔNG CÒN KHỞI TẠO PDFMetadataProcessor Ở ĐÂY NỮA
        self.pdf_processor = None # Đảm bảo là None để không có lỗi gọi
        logger.info("ℹ️ PDFMetadataProcessor initialization is now handled by BackgroundPDFProcessor in run.py.")


    def get_all_links(self, base_url=None):
        """
        Lấy danh sách link bài học từ trang chủ, các danh mục và các trang phân trang.
        Sử dụng BFS để duyệt các link một cách chủ động và sâu hơn.
        """
        initial_url = base_url or "https://hocmai.vn/kho-tai-lieu/"
        logger.info(f"🔍 Đang lấy links từ: {initial_url}")
        
        all_lesson_links = set() # Dùng set để tránh trùng lặp ((title, url))
        visited_urls = set()
        urls_to_visit = [initial_url]
        
        MAX_PAGES_TO_CRAWL = 50 # Giới hạn trang để cào sâu, có thể điều chỉnh
        pages_crawled = 0

        while urls_to_visit and pages_crawled < MAX_PAGES_TO_CRAWL:
            current_url = urls_to_visit.pop(0)
            if current_url in visited_urls:
                continue
            
            logger.info(f"  Đang thăm trang: {current_url} (Trang {pages_crawled+1}/{MAX_PAGES_TO_CRAWL})")
            visited_urls.add(current_url)
            pages_crawled += 1

            try:
                r = requests.get(current_url, headers=self.headers, timeout=15) 
                r.raise_for_status() 
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Bước 1: Tìm các link bài học (có 'read.php?id=') trên trang hiện tại
                for a in soup.find_all("a", href=True):
                    href = a["href"]  # type: ignore
                    full_link = urljoin(current_url, href)  # type: ignore

                    if "read.php?id=" in full_link:
                        title = a.get_text(strip=True)
                        if title and full_link not in [item[1] for item in all_lesson_links]: 
                            all_lesson_links.add((title, full_link))
                            
                    # Bước 2: Tìm các link danh mục và link phân trang để thêm vào hàng đợi duyệt
                    if "/kho-tai-lieu/" in full_link and \
                       ("lop-" in full_link or "mon-hoc/" in full_link or \
                        "de-thi-" in full_link or "thi-vao-lop-" in full_link or \
                        "/page-" in full_link) and \
                       "read.php?id=" not in full_link: 
                        
                        if full_link not in visited_urls and full_link not in urls_to_visit:
                            urls_to_visit.append(full_link)
                            logger.debug(f"    Tìm thấy danh mục/phân trang mới: {full_link}")
                            
            except requests.exceptions.Timeout:
                logger.warning(f"  ⚠️ Timeout khi lấy links từ: {current_url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"  ❌ Lỗi mạng hoặc HTTP khi lấy links từ {current_url}: {e}")
            except Exception as e:
                logger.error(f"  ❌ Lỗi khi phân tích HTML hoặc lấy links từ {current_url}: {e}")
            
            time.sleep(1) # Nghỉ giữa các request lấy link để tránh bị chặn

        logger.info(f"✅ Tìm thấy {len(all_lesson_links)} bài học (sau khi duyệt {pages_crawled} trang)")
        return list(all_lesson_links)

    def download_images_and_make_pdf(self, title, url):
        """Tải ảnh và tạo PDF - lưu vào thư mục TẠM THỜI"""
        logger.info(f"📥 Đang xử lý: {title}")

        try:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(" ", "_")[:100]
            
            if not safe_title:
                safe_title = f"untitled_{int(time.time())}"

            folder_name_for_images = self.save_images / safe_title 
            os.makedirs(folder_name_for_images, exist_ok=True)

            r = requests.get(url, headers=self.headers, timeout=20) 
            r.raise_for_status() 
            soup = BeautifulSoup(r.text, "html.parser")
            carousel = soup.find("div", id="khotailieu")
            imgs = carousel.find_all("img") if carousel else []  # type: ignore

            img_urls = []
            for img in imgs:
                src = img.get("src") or img.get("data-src") # type: ignore
                if src and "/documents/" in src: 
                    img_urls.append(src)

            if not img_urls:
                logger.warning(f"❌ No images found for {title} at {url}")
                return {"status": "error", "message": "No images found", "pdf_path": None}

            logger.info(f"📸 Tìm thấy {len(img_urls)} ảnh cho {title}")

            image_paths = []
            for i, img_url in enumerate(img_urls, start=1):
                try:
                    full_img_url = urljoin(url, img_url)
                    img_data = requests.get(full_img_url, headers=self.headers, timeout=15).content 
                    img_path = folder_name_for_images / f"page_{i}.png" 
                    
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    image_paths.append(str(img_path))
                except requests.exceptions.Timeout:
                    logger.warning(f"  ⚠️ Timeout khi tải ảnh {i} từ: {full_img_url}") # type: ignore
                except requests.exceptions.RequestException as e:
                    logger.warning(f"  ⚠️ Lỗi tải ảnh {i} (mạng/HTTP): {e}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Lỗi tải ảnh {i}: {e}")

            if not image_paths:
                logger.warning(f"❌ Không có ảnh nào được tải thành công cho {title}")
                return {"status": "error", "message": "No images downloaded successfully", "pdf_path": None}

            # Lưu PDF vào thư mục TẠM THỜI (self.temp_pdf_dir)
            pdf_path = self.temp_pdf_dir / f"{safe_title}.pdf"
            try:
                with open(pdf_path, "wb") as f:
                    if image_paths:
                        f.write(img2pdf.convert(image_paths))
                    else:
                        raise ValueError("No images to convert to PDF.")
                
                logger.info(f"✅ PDF created: {pdf_path}")
                
                return {
                    "status": "success",
                    "title": title,
                    "images_count": len(image_paths),
                    "pdf_path": str(pdf_path) # Trả về đường dẫn PDF tạm thời
                }
            except Exception as e:
                logger.error(f"❌ Lỗi khi tạo PDF từ ảnh cho {title}: {e}")
                return {"status": "error", "message": f"Failed to create PDF: {e}", "pdf_path": None}
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout khi xử lý {title}: {url}")
            return {"status": "error", "message": "Timeout during processing", "pdf_path": None}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Lỗi mạng hoặc HTTP khi xử lý {title}: {e}")
            return {"status": "error", "message": str(e), "pdf_path": None}
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý {title}: {e}")
            return {"status": "error", "message": str(e), "pdf_path": None}

    def crawl_hocmai(self, base_url=None, max_lessons=None):
        """Main function - Chỉ crawl và tạo PDF, sau đó chuyển file"""
        logger.info("🚀 Bắt đầu crawl HocMai...")
        
        links = self.get_all_links(base_url)
        if not links:
            logger.info("❌ Không tìm thấy bài học nào để cào.")
            return {"status": "error", "message": "Không tìm thấy bài học nào", 
                    "total_lessons_crawled": 0, "successful_downloads": 0, "failed_downloads": 0,
                    "minio_upload_summary": {"status": "skipped", "reason": "No PDFs processed in this module"}}
        
        if max_lessons:
            links = links[:max_lessons]
        
        logger.info(f"Found {len(links)} lessons to process (potentially limited by max_lessons)")
        
        results = []
        success_count = 0
        
        # Danh sách các file PDF đã tạo thành công trong phiên này
        created_pdf_paths = [] 

        for i, (title, link) in enumerate(links, 1):
            logger.info(f"\n[{i}/{len(links)}] Processing: {title} - {link}")
            
            result = self.download_images_and_make_pdf(title, link)
            result["lesson_number"] = i
            result["url"] = link
            
            if result["status"] == "success":
                success_count += 1
                created_pdf_paths.append(Path(result["pdf_path"])) # Thêm vào danh sách để di chuyển sau
            
            results.append(result)
            
            time.sleep(1) # Nghỉ giữa các request tải bài học
        
        # --- Di chuyển các file PDF đã tạo sang thư mục đích cuối cùng ---
        logger.info("\n" + "=" * 60)
        logger.info(f"📦 Đang di chuyển các file PDF từ {self.temp_pdf_dir} sang {self.final_pdf_destination_dir}...")
        moved_count = 0
        for pdf_file_path in created_pdf_paths:
            try:
                if pdf_file_path.exists():
                    shutil.move(str(pdf_file_path), str(self.final_pdf_destination_dir / pdf_file_path.name))
                    moved_count += 1
                    logger.info(f"  ✅ Đã di chuyển: {pdf_file_path.name}")
                else:
                    logger.warning(f"  ⚠️ File không tồn tại để di chuyển: {pdf_file_path.name}")
            except Exception as e:
                logger.error(f"  ❌ Lỗi khi di chuyển {pdf_file_path.name}: {e}")
        logger.info(f"✅ Đã di chuyển {moved_count}/{len(created_pdf_paths)} file PDF.")
        logger.info("=" * 60)

        # Cập nhật summary để phản ánh việc không xử lý metadata ở đây
        summary = {
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_lessons_crawled": len(links), 
            "successful_downloads": success_count, 
            "failed_downloads": len(links) - success_count,
            "moved_pdfs_count": moved_count,
            "download_results": results,
            "download_folders": {
                "base_output_dir": str(self.base_output_dir), 
                "temporary_pdfs_dir": str(self.temp_pdf_dir), # Đổi tên thành tạm thời
                "final_pdfs_destination_dir": str(self.final_pdf_destination_dir), # Thêm thư mục đích
                "current_session_images_dir": str(self.save_images) 
            },
            "minio_upload_summary": {"status": "delegated", "reason": "Processing handled by BackgroundPDFProcessor in run.py"} 
        }
        
        report_file = self.current_crawl_output_dir / f"hocmai_report_{int(time.time())}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"\n🎉 Hoàn thành! {success_count}/{len(links)} bài học thành công")
        logger.info(f"📊 Báo cáo: {report_file}")
        
        return summary

# ===== MAIN SCRIPT TO RUN CRAWLER (Ví dụ cách gọi) =====
if __name__ == "__main__":
    # Lưu ý: Khi gọi từ api.py, các tham số này sẽ được truyền từ đó.
    # Khi chạy file này trực tiếp, các tham số này sẽ được sử dụng.
    # Không cần Gemini API key hoặc MinIO config ở đây nữa.
    
    BASE_CRAWLER_OUTPUT_DIR = Path("hocmai_output_all") 

    crawler = HocMaiCrawler(
        base_output_dir=BASE_CRAWLER_OUTPUT_DIR
    )
    
    crawl_summary = crawler.crawl_hocmai(max_lessons=None) 

    logger.info("\n--- Tóm tắt cuối cùng ---")
    logger.info(json.dumps(crawl_summary, indent=2, ensure_ascii=False))