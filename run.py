import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

# Import đối tượng 'app' từ app.server
from app.server import app
from utils.minio_connection import MinIOConnection
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://triennd23ai:k2vKW7uw0FUcdX3J@eduagentcluster.do87h7i.mongodb.net/?retryWrites=true&w=majority&appName=EduAgentCluster")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "edu_agent_db")
MONGO_COLLECTION_NAME = "lectures"  # or "chunks"

class BackgroundPDFProcessor:
    """Background PDF processor that runs alongside Flask server"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.processed_files = set()  # Track processed files
        
        # Configuration
        self.gemini_api_key = "AIzaSyAxyew-YwI4QfOzFHJQhGSaG0T1uMj6ALo"
        self.minio_config = {
            'endpoint': 'localhost:9000',
            'access_key': 'minioadmin',
            'secret_key': 'minioadmin',
            'bucket_name': 'ai-education',
            'secure': False
        }
        self.pdf_folder = "downloaded_pdfs"
        self.check_interval = 30  # Check every 30 seconds
        
        self.processor = None
        self.last_check_time = 0
        
        # Initialize MinIO connection
        self.minio_client = MinIOConnection()
        if not self.minio_client.connect():
            print("❌ Failed to connect to MinIO")
        else:
            print("✅ MinIO connected successfully")
    
    def initialize_processor(self):
        """Initialize PDF processor if libraries are available"""
        try:
            from app.web_scarching.pdf_metadata_processor import PDFMetadataProcessor
            self.processor = PDFMetadataProcessor(self.gemini_api_key, self.minio_config)
            print("✅ Background PDF processor initialized")
            return True
        except ImportError as e:
            print(f"⚠️ PDF processor libraries not available: {e}")
            print("   Install: pip install google-generativeai PyPDF2 minio unidecode")
            return False
        except Exception as e:
            print(f"⚠️ Failed to initialize PDF processor: {e}")
            return False
    
    def get_pdf_files(self):
        """Get list of PDF files in folder"""
        if not Path(self.pdf_folder).exists():
            return []
        return list(Path(self.pdf_folder).glob("**/*.pdf"))
    
    def get_minio_files(self):
        """Get list of files already in MinIO"""
        try:
            if not self.minio_client.client:
                return set()
            
            objects = self.minio_client.client.list_objects(
                bucket_name=self.minio_config['bucket_name'],
                recursive=True
            )
            
            # Extract just the filename from the full path
            return set(os.path.basename(obj.object_name) for obj in objects if not obj.is_dir) # type: ignore
        except Exception as e:
            print(f"⚠️ Error checking MinIO files: {e}")
            return set()
    
    def process_new_files(self):
        """Process any new PDF files - STRICT VERSION with AUTO DELETE"""
        if not self.processor:
            return
        
        try:
            # Get current PDF files
            pdf_files = self.get_pdf_files()
            if not pdf_files:
                return
            
            # Get files already in MinIO
            minio_files = self.get_minio_files()
            
            # Find new files to process
            new_files = []
            files_to_delete = []  # Files already in MinIO
            
            for pdf_file in pdf_files:
                filename = pdf_file.name
                if filename in minio_files:
                    files_to_delete.append(pdf_file)
                elif filename not in self.processed_files:
                    new_files.append(pdf_file)
            
            # Delete files that already exist in MinIO
            if files_to_delete:
                print(f"\n🗑️ Cleaning up {len(files_to_delete)} files already in MinIO")
                for pdf_file in files_to_delete:
                    try:
                        pdf_file.unlink()
                        print(f"  🗑️ Deleted (already in MinIO): {pdf_file.name}")
                    except Exception as e:
                        print(f"  ❌ Failed to delete {pdf_file.name}: {e}")
            
            if new_files:
                print(f"\n📄 Found {len(new_files)} new PDF files to process")
                print("🔍 STRICT MODE: Only well-analyzed educational content will be uploaded")
                print("🗑️ AUTO DELETE: Files will be deleted after processing")
                
                for i, pdf_file in enumerate(new_files, 1):
                    try:
                        filename = pdf_file.name
                        print(f"📥 [{i}/{len(new_files)}] Processing: {filename}")
                        
                        # STRICT: Use analyze_pdf_metadata with strict validation
                        metadata = self.processor.analyze_pdf_metadata(str(pdf_file), filename)
                        
                        if metadata is None:
                            print(f"  ❌ Analysis failed or not educational content - DELETING local file")
                            try:
                                pdf_file.unlink()
                                print(f"  🗑️ Deleted non-educational file: {filename}")
                            except Exception as e:
                                print(f"  ❌ Failed to delete: {e}")
                            continue
                        
                        # STRICT: Get paths and validate
                        level_path = metadata.get("gpt_educational_level", "khac")
                        subject_path = metadata.get("gpt_subject", "tong-hop")
                        doc_type_path = metadata.get("gpt_content_type", "tai-lieu-khac")
                        
                        # STRICT: Final validation - reject generic classifications
                        if (level_path in ["khac", "khong-xac-dinh"] or 
                            subject_path in ["tong-hop", "khac", "khong-xac-dinh"] or
                            doc_type_path in ["tai-lieu-khac", "khac"]):
                            print(f"  ❌ Generic classification detected - DELETING local file")
                            print(f"    Level: {level_path} | Subject: {subject_path} | Type: {doc_type_path}")
                            try:
                                pdf_file.unlink()
                                print(f"  🗑️ Deleted generic file: {filename}")
                            except Exception as e:
                                print(f"  ❌ Failed to delete: {e}")
                            continue
                        
                        object_name = f"{level_path}/{subject_path}/{doc_type_path}/{filename}"
                        
                        # FIXED: Upload to MinIO using direct client like server.py
                        if self.minio_client.client:
                            try:
                                self.minio_client.client.fput_object(
                                    bucket_name=self.minio_config['bucket_name'],
                                    object_name=object_name,
                                    file_path=str(pdf_file),
                                    content_type='application/pdf'
                                )
                                print(f"  ✅ Uploaded: {object_name}")
                                self.processed_files.add(filename)
                                
                                # DELETE local file after successful upload
                                try:
                                    pdf_file.unlink()
                                    print(f"  🗑️ Deleted local file after upload: {filename}")
                                except Exception as e:
                                    print(f"  ❌ Failed to delete after upload: {e}")
                                    
                            except Exception as e:
                                print(f"  ❌ Upload failed: {e}")
                        else:
                            print(f"  ❌ MinIO client not connected")
                        
                        # STRICT: Longer delay for AI rate limiting
                        time.sleep(8)  # Increased from 3 to 8 seconds
                        
                    except Exception as e:
                        print(f"  ❌ Error processing {pdf_file.name}: {e}")
                        continue
                
                print(f"✅ Background processing complete with strict validation and auto-delete")
            else:
                # Only print this occasionally to avoid spam
                current_time = time.time()
                if current_time - self.last_check_time > 300:  # Every 5 minutes
                    print(f"📂 No new PDF files to process (checked {len(pdf_files)} files)")
                    self.last_check_time = current_time
        
        except Exception as e:
            print(f"❌ Error in background processing: {e}")
    
    def background_worker(self):
        """Background worker thread"""
        print(f"🔄 Background PDF processor started (checking every {self.check_interval}s)")
        
        while self.running:
            try:
                self.process_new_files()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ Background worker error: {e}")
                time.sleep(self.check_interval)
    
    def start(self):
        """Start background processing"""
        if self.running:
            return
        
        # Try to initialize processor
        if not self.initialize_processor():
            print("⚠️ Background PDF processing disabled due to missing dependencies")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.background_worker, daemon=True)
        self.thread.start()
        print("🚀 Background PDF processor started")
    
    def stop(self):
        """Stop background processing"""
        if self.running:
            self.running = False
            print("🛑 Background PDF processor stopped")


def test_minio_connection():
    """Test kết nối MinIO trước khi chạy server"""
    print("🔌 Đang test kết nối MinIO...")
    minio_conn = MinIOConnection()
    if minio_conn.connect():
        print("✅ MinIO connection OK!")
        return True
    else:
        print("⚠️ MinIO connection failed - ứng dụng sẽ chạy nhưng các tính năng liên quan đến MinIO có thể không hoạt động.")
        return False


def open_browser_after_delay(port):
    """Mở trình duyệt sau một khoảng thời gian ngắn."""
    time.sleep(3)  # Đợi 3 giây để server Flask khởi động hoàn chỉnh
    try:
        webbrowser.open(f"http://localhost:{port}/")
        print(f"🌐 Đã mở trình duyệt tại: http://localhost:{port}/")
    except Exception as e:
        print(f"⚠️ Không thể mở trình duyệt: {e}")


def check_data_folder_status():
    """Kiểm tra trạng thái các folder data"""
    print("\n📁 CHECKING DATA FOLDER STATUS")
    print("=" * 50)
    
    # Check PDF folder
    PDF_FOLDER = "downloaded_pdfs"
    if not Path(PDF_FOLDER).exists():
        print(f"❌ PDF Folder not found: {PDF_FOLDER}")
        print("💡 Run the web scraper first to download PDFs")
    else:
        pdf_files = list(Path(PDF_FOLDER).glob("**/*.pdf"))
        print(f"📄 Found {len(pdf_files)} PDF files in: {PDF_FOLDER}")
        if pdf_files:
            total_size = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)  # MB
            print(f"📊 Total PDF size: {total_size:.1f} MB")
    
    # Check MinIO status
    print(f"\n☁️ MinIO STATUS")
    print("-" * 20)
    try:
        minio_conn = MinIOConnection()
        if minio_conn.connect():
            print("✅ MinIO connection: OK")
        else:
            print("❌ MinIO connection: Failed")
    except Exception as e:
        print(f"❌ MinIO error: {e}")


def run_flask_server_with_background():
    """Chạy Flask server với background PDF processing"""
    print("\n🌐 STARTING FLASK SERVER WITH BACKGROUND PROCESSING")
    print("=" * 60)
    
    # Global background processor
    global bg_pdf_processor
    bg_pdf_processor = BackgroundPDFProcessor()
    
    try:
        # Test MinIO connection trước
        minio_status = test_minio_connection()
        print()
        
        # Cấu hình server Flask
        flask_port = 8000
        
        # Kiểm tra thư mục templates và static
        if not os.path.exists("templates"):
            print(f"❌ Không tìm thấy thư mục 'templates'")
            print("📁 Vui lòng tạo thư mục templates và đặt file index.html vào đó")
            return
        
        if not os.path.exists("static"):
            print(f"❌ Không tìm thấy thư mục 'static'")
            print("📁 Vui lòng tạo thư mục static và đặt file CSS/JS vào đó")
            return
        
        index_file = os.path.join("templates", "index.html")
        if not os.path.exists(index_file):
            print(f"❌ Không tìm thấy file 'index.html' trong thư mục 'templates'")
            print("📄 Vui lòng đặt file index.html vào thư mục templates")
            return
        
        print(f"✅ Tìm thấy file HTML: {index_file}")
        print(f"🌐 Ứng dụng Flask sẽ chạy trên port: {flask_port}")
        print(f"💾 MinIO Status: {'✅ Connected' if minio_status else '❌ Disconnected'}")
        
        # Check data folders status
        pdf_files = []
        if Path("downloaded_pdfs").exists():
            pdf_files = list(Path("downloaded_pdfs").glob("**/*.pdf"))
            print(f"📄 PDF Files: {len(pdf_files)} found")
        else:
            print(f"📄 PDF Folder: Not found (will be created when scraping)")
        
        print()
        
        # Start background processor
        print("🔄 Starting background PDF processor...")
        bg_pdf_processor.start()
        print()
        
        # Khởi động trình duyệt trong một thread riêng
        browser_thread = threading.Thread(target=open_browser_after_delay, args=(flask_port,))
        browser_thread.daemon = True
        browser_thread.start()
        
        print(f"🚀 Flask server starting at: http://localhost:{flask_port}/")
        print(f"📱 Background PDF processing is running")
        print(f"⏹️ Press Ctrl+C to stop server and all background processing")
        print()
        
        # Chạy ứng dụng Flask
        app.run(host='0.0.0.0', port=flask_port, debug=False)  # debug=False để tránh reload
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping server and background processing...")
        bg_pdf_processor.stop()
        print("👋 Tạm biệt!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        bg_pdf_processor.stop()
        sys.exit(1)

#  processing pdf manual
def run_manual_pdf_processor():
    """Chạy PDF processor manual (one-time)"""
    print("\n🚀 MANUAL PDF PROCESSING")
    print("=" * 40)
    
    try:
        from app.web_scarching.pdf_metadata_processor import PDFMetadataProcessor
        
        # Configuration
        GEMINI_API_KEY = "AIzaSyAxyew-YwI4QfOzFHJQhGSaG0T1uMj6ALo"
        MINIO_CONFIG = {
            'endpoint': 'localhost:9000',
            'access_key': 'minioadmin',
            'secret_key': 'minioadmin',
            'bucket_name': 'ai-education',
            'secure': False
        }
        PDF_FOLDER = "downloaded_pdfs"
        
        if not Path(PDF_FOLDER).exists():
            print(f"❌ Folder not found: {PDF_FOLDER}")
            return
        
        pdf_files = list(Path(PDF_FOLDER).glob("**/*.pdf"))
        if not pdf_files:
            print("⚠️ No PDF files found")
            return
        
        print(f"📄 Found {len(pdf_files)} PDF files")
        confirm = input(f"❓ Process all files? (y/N): ").lower().strip()
        if confirm != 'y':
            return
        
        # Process files
        processor = PDFMetadataProcessor(GEMINI_API_KEY, MINIO_CONFIG)
        results = processor.process_pdf_folder(PDF_FOLDER, skip_existing=True)
        
        stats = results['statistics']
        print(f"\n✅ Processing complete!")
        print(f"   Uploaded: {stats['uploaded']}")
        print(f"   Skipped: {stats['skipped']}")
        print(f"   Errors: {stats['errors']}")
        
    except ImportError as e:
        print(f"❌ Missing libraries: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


# === MongoDB Utility ===
def get_mongo_collection():
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        return collection
    except Exception as e:
        print(f"❌ Lỗi kết nối MongoDB: {e}")
        return None


def check_db():
    print("🔌 Đang kiểm tra kết nối MongoDB...")
    collection = get_mongo_collection()
    # Chỉ so sánh với None, không dùng truthy test
    if collection is not None:
        print(f"✅ Đã kết nối tới MongoDB collection: {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")
        doc_count = collection.count_documents({})
        print(f"📊 Collection hiện có {doc_count} documents.")
    else:
        print("❌ Không thể kết nối tới MongoDB.")

def main():
    """Hàm chính của chương trình"""
    try:
        # Kiểm tra command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "server":
                run_flask_server_with_background()
            elif sys.argv[1] == "pdf":
                run_manual_pdf_processor()
            elif sys.argv[1] == "status":
                check_data_folder_status()
            else:
                print("❌ Invalid argument. Use: server, pdf, or status")
                print("📖 Commands:")
                print("   server  - Run Flask server with background processing")
                print("   pdf     - Manual PDF processing")
                print("   status  - Check data folder status")
        else:
            # Default: Run server with background processing
            run_flask_server_with_background()
            
    except KeyboardInterrupt:
        print("\n👋 Tạm biệt!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_db()
    main()