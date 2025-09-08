# ===== app/web_scraping/pdf_metadata_processor.py (MODIFIED FOR IMAGE-BASED PDFs, KEEPING YOUR STRICT LOGIC) =====
"""
Process downloaded PDF files: analyze metadata and upload to MinIO - FIXED VERSION
"""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from unidecode import unidecode
import re
import logging # Thêm import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import libraries
try:
    import google.generativeai as genai
    import PyPDF2
    from minio import Minio
    LIBRARIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Required libraries not installed: {e}")
    logger.error("Install: pip install google-generativeai PyPDF2 minio unidecode")
    LIBRARIES_AVAILABLE = False

# Import MinIO connection from utils
try:
    from utils.minio_connection import MinIOConnection
except ImportError:
    logger.error("❌ MinIOConnection not found. Please ensure utils/minio_connection.py exists")
    MinIOConnection = None


class PDFMetadataProcessor:
    """Process PDF files for metadata analysis and MinIO upload"""
    
    def __init__(self, gemini_api_key: str, minio_config: Dict[str, Any]):
        if not LIBRARIES_AVAILABLE:
            raise ImportError("Required libraries not available")
        
        # Gemini API setup
        self.gemini_api_key = gemini_api_key
        try:
            genai.configure(api_key=gemini_api_key)# type: ignore
            # Use stable model with higher quota instead of experimental
            self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')# type: ignore
            logger.info("✅ Gemini API initialized with gemini-1.5-flash")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini API: {e}")
            raise
        
        # MinIO setup using utils.minio_connection
        try:
            if MinIOConnection:
                self.minio_connection = MinIOConnection()
                if self.minio_connection.connect():
                    self.minio_client = self.minio_connection.client
                    logger.info("✅ MinIO connected via MinIOConnection")
                else:
                    raise Exception("Failed to connect to MinIO")
            else:
                # Fallback to direct Minio client
                self.minio_client = Minio(# type: ignore
                    minio_config['endpoint'],
                    access_key=minio_config['access_key'],
                    secret_key=minio_config['secret_key'],
                    secure=minio_config.get('secure', False)
                )
                logger.info("✅ MinIO connected via direct client")
            
            self.minio_bucket = minio_config['bucket_name']
            
            # Check if bucket exists, create if not
            if not self.minio_client.bucket_exists(self.minio_bucket):# type: ignore
                self.minio_client.make_bucket(self.minio_bucket)# type: ignore
                logger.info(f"✅ Created MinIO bucket: {self.minio_bucket}")
            else:
                logger.info(f"✅ MinIO bucket exists: {self.minio_bucket}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize MinIO: {e}")
            raise
        
        # Statistics
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "analyzed": 0,
            "uploaded": 0,
            "skipped": 0,
            "errors": 0
        }
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file.
        Returns an empty string if no text is found or an error occurs.
        """
        try:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)# type: ignore
                max_pages = min(3, len(reader.pages))
                for i in range(max_pages):
                    page_text = reader.pages[i].extract_text()
                    if page_text: # Only append if text is found on page
                        text += page_text + " "
            
            # Limit text length for API
            return text[:8000].strip() # Use .strip() to handle all whitespace
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract text from {file_path}: {e}. This is common for image-based PDFs.")
            return "" # Return empty string on failure

    def analyze_pdf_metadata(self, file_path: str, filename: str) -> Optional[Dict[str, Any]]: # Changed return type to Optional
        """Analyze PDF metadata using Gemini AI"""
        logger.info(f"🤖 Analyzing: {filename}")
        
        # Extract text from PDF
        text_content = self.extract_text_from_pdf(file_path) # Changed var name to avoid conflict
        
        # --- MODIFICATION START ---
        # Do not skip if no text. Instead, prepare prompt based on text availability.
        if not text_content:
            logger.info("  ℹ️ No text content found in PDF. Analyzing based on filename.")
            # If no text, limit the content passed to AI to just the filename prompt
            content_for_ai = "" 
            text_analysis_note = "\nLưu ý: Không tìm thấy nội dung văn bản trong PDF. Hãy phân tích CHÍNH XÁC dựa trên tên file và cấu trúc chung của tài liệu giáo dục."
        else:
            content_for_ai = f"\nNội dung: {text_content[:3000]}" # Use the extracted text
            text_analysis_note = ""
        # --- MODIFICATION END ---
            
        # Try AI analysis with multiple attempts
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"  🔄 Analysis attempt {attempt + 1}/{max_retries}")
                
                # Enhanced prompt for better accuracy, adapted for text or no text
                prompt = f"""
                Bạn là chuyên gia phân tích tài liệu giáo dục Việt Nam. Phân tích KỸ CÀNG tên file và {('nội dung' if text_content else '')} để xác định CHÍNH XÁC:

                QUAN TRỌNG: CHỈ phân tích các tài liệu DẠY HỌC (bài học, đề thi, bài tập của học sinh). 
                LOẠI TRỪ: công văn, thông báo, CV, học bổng, fellowship, tuyển dụng.

                Tên file: `{filename}`
                {content_for_ai}
                {text_analysis_note}

                Phân tích và trả về JSON:
                {{
                    "is_educational": true/false,
                    "mon_hoc": "Toán",
                    "cap_do": "THPT", 
                    "loai_tai_lieu": "Bài giảng",
                    "confidence": 0.8,
                    "reason": "Chi tiết lý do"
                }}

                CHỈ CHỌN 1 GIÁ TRỊ DUY NHẤT:
                - mon_hoc: Toán | Ngữ văn | Vật lý | Hóa học | Sinh học | Lịch sử | Địa lý | Tiếng Anh | GDCD | Tin học
                - cap_do: Tiểu học | THCS | THPT
                - loai_tai_lieu: Đề thi | Bài tập | Bài giảng | Tài liệu | Đề cương

                QUY TẮC:
                1. is_educational = false nếu KHÔNG phải bài học trực tiếp hoặc không thể xác định.
                2. confidence >= 0.8 mới chấp nhận.
                3. CHỈ chọn 1 môn học duy nhất, không liệt kê nhiều môn.
                4. Nếu không chắc chắn -> is_educational = false.
                """
                
                response = self.gemini_client.generate_content(
                    contents=[prompt],
                    generation_config=genai.GenerationConfig(# type: ignore
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                
                # Parse response
                # Ensure response.text is a string
                response_text = response.text
                if isinstance(response_text, list): # This might happen with some API versions or unusual responses
                    response_text = response_text[0] if response_text else "{}"
                
                # Check for empty response text
                if not response_text.strip():
                    logger.warning(f"  ⚠️ Gemini returned empty response for {filename}. Retrying...")
                    continue # Retry if response is empty

                # Attempt to parse JSON
                try:
                    ai_result = json.loads(response_text)
                    if isinstance(ai_result, list): # Handle if AI returns a list of JSON objects
                        ai_result = ai_result[0] if ai_result else {}
                except json.JSONDecodeError as e:
                    logger.error(f"  ❌ Failed to parse JSON from Gemini response for {filename}: {e}. Response: {response_text}")
                    # If JSON parsing fails, it's a critical error for this attempt, try again
                    if attempt < max_retries - 1:
                        time.sleep(5) # Wait before retry
                        continue
                    else:
                        return None


                # Check if educational content
                if not ai_result.get("is_educational", False):
                    logger.warning(f"  ❌ Not educational content (is_educational: false) - SKIPPING")
                    return None
                
                # Check confidence level  
                confidence = ai_result.get("confidence", 0.0)
                if confidence < 0.8:  # Increased from 0.7 to 0.8
                    logger.warning(f"  ⚠️ Low confidence ({confidence}) - Retry {attempt + 1}")
                    continue
                
                # Extract and validate results
                subject_raw = ai_result.get("mon_hoc", "").strip()
                level_raw = ai_result.get("cap_do", "").strip()
                content_raw = ai_result.get("loai_tai_lieu", "").strip()
                
                # Handle multi-subject responses - take first one only
                if "," in subject_raw:
                    subject_raw = subject_raw.split(",")[0].strip()
                if "|" in subject_raw:
                    subject_raw = subject_raw.split("|")[0].strip()
                
                # Validate all fields are properly filled
                valid_subjects = ["Toán", "Ngữ văn", "Vật lý", "Hóa học", "Sinh học", 
                                "Lịch sử", "Địa lý", "Tiếng Anh", "GDCD", "Tin học"]
                valid_levels = ["Tiểu học", "THCS", "THPT"]
                valid_contents = ["Đề thi", "Bài tập", "Bài giảng", "Tài liệu", "Đề cương"]
                
                if (subject_raw not in valid_subjects or 
                    level_raw not in valid_levels or 
                    content_raw not in valid_contents):
                    logger.warning(f"  ⚠️ Invalid classification - Retry {attempt + 1}")
                    logger.warning(f"    Subject: {subject_raw} | Level: {level_raw} | Content: {content_raw}")
                    continue # Retry if classification is invalid
                
                # Generate clean path names
                gpt_subject_for_path = unidecode(subject_raw).replace(" ", "-").lower()
                gpt_level_for_path = unidecode(level_raw).replace(" ", "-").lower()
                gpt_content_type_for_path = unidecode(content_raw).replace(" ", "-").lower()
                
                logger.info(f"  ✅ AI Success: {subject_raw} | {level_raw} | {content_raw} (confidence: {confidence})")
                
                return {
                    "method": "ai",
                    "original_filename": filename,
                    "status": "success",
                    "confidence": confidence,
                    "inferred_topic_gpt": f"{content_raw} môn {subject_raw} {level_raw}".strip(),
                    "gpt_subject_raw": subject_raw,
                    "gpt_educational_level_raw": level_raw,
                    "gpt_content_type_raw": content_raw,
                    "gpt_subject": gpt_subject_for_path,
                    "gpt_educational_level": gpt_level_for_path,
                    "gpt_content_type": gpt_content_type_for_path,
                    "gpt_analysis": ai_result.get("reason", "AI analysis completed"),
                    "possible_language": "vi"
                }
                
            except Exception as e:
                logger.error(f"  ❌ AI attempt {attempt + 1} failed: {e}")
                
                # Handle rate limiting specifically
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning(f"  ⏰ Rate limit hit, waiting 70 seconds...")
                    time.sleep(70)  # Wait longer for rate limit reset
                elif attempt == max_retries - 1:
                    logger.error(f"  ❌ All AI attempts failed - SKIPPING file")
                    return None
                else:
                    time.sleep(5)  # Wait before retry for other errors
        
        return None
    
    def upload_to_minio(self, file_path: str, object_name: str) -> bool:
        """Upload file to MinIO - FIXED VERSION matching server.py"""
        try:
            logger.info(f"📤 Uploading to: {object_name}")
            
            # Upload file using the same method as server.py
            self.minio_client.fput_object(# type: ignore
                bucket_name=self.minio_bucket,
                object_name=object_name,
                file_path=file_path,
                content_type='application/pdf'
            )
            
            logger.info(f"  ✅ Uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Upload failed: {e}")
            return False
    
    def process_pdf_folder(self, folder_path: str, skip_existing: bool = True) -> Dict[str, Any]:
        """Process all PDF files in a folder - STRICT VERSION"""
        folder = Path(folder_path)
        
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Find all PDF files
        pdf_files = list(folder.glob("**/*.pdf"))
        self.stats["total_files"] = len(pdf_files)
        
        logger.info(f"🚀 Processing {len(pdf_files)} PDF files from: {folder_path}")
        logger.info("🔍 STRICT MODE: Only well-analyzed educational content will be uploaded")
        logger.info("=" * 60)
        
        processed_files = []
        
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                filename = pdf_file.name
                logger.info(f"\n📄 [{i}/{len(pdf_files)}] {filename}")
                
                # Check if already exists in MinIO
                if skip_existing:
                    try:
                        existing_objects = list(self.minio_client.list_objects(# type: ignore
                            self.minio_bucket, 
                            recursive=True
                        ))
                        
                        # Check if filename already exists anywhere in bucket
                        if any(filename in obj.object_name for obj in existing_objects):# type: ignore
                            logger.info(f"  ⏭️ Already exists in MinIO, skipping")
                            self.stats["skipped"] += 1
                            continue
                    except Exception:
                        pass  # Object doesn't exist, continue processing
                
                # Analyze metadata with strict validation
                metadata = self.analyze_pdf_metadata(str(pdf_file), filename)
                
                if metadata is None:
                    # Log message changed to reflect the new behavior
                    logger.warning(f"  ❌ Analysis failed (due to strict rules or AI error) - SKIPPING upload")
                    self.stats["errors"] += 1
                    continue
                
                self.stats["analyzed"] += 1
                
                # Upload to MinIO using the same structure as server.py
                level_path = metadata.get("gpt_educational_level", "khac")
                subject_path = metadata.get("gpt_subject", "tong-hop")
                doc_type_path = metadata.get("gpt_content_type", "tai-lieu-khac")
                
                # Final validation - make sure no "khac" or generic values
                if (level_path in ["khac", "khong-xac-dinh"] or 
                    subject_path in ["tong-hop", "khac", "khong-xac-dinh"] or
                    doc_type_path in ["tai-lieu-khac", "khac"]):
                    logger.warning(f"  ❌ Generic classification detected - SKIPPING upload")
                    logger.warning(f"    Level: {level_path} | Subject: {subject_path} | Type: {doc_type_path}")
                    self.stats["errors"] += 1
                    continue
                
                object_name = f"{level_path}/{subject_path}/{doc_type_path}/{filename}"
                
                success = self.upload_to_minio(str(pdf_file), object_name)
                
                if success:
                    self.stats["uploaded"] += 1
                    processed_files.append({
                        "filename": filename,
                        "local_path": str(pdf_file),
                        "object_name": object_name,
                        "metadata": metadata
                    })
                    logger.info(f"  ✅ Successfully uploaded with proper classification")
                else:
                    self.stats["errors"] += 1
                
                self.stats["processed"] += 1
                
                # Rate limiting - longer delay to avoid quota issues
                time.sleep(8)  # Increased from 2 to 8 seconds
                
            except Exception as e:
                logger.error(f"  ❌ Error processing {pdf_file.name}: {e}")
                self.stats["errors"] += 1
                continue
        
        # Final summary
        logger.info(f"\n🎉 STRICT PROCESSING COMPLETE!")
        logger.info(f"📊 Statistics:")
        logger.info(f"   📄 Total files: {self.stats['total_files']}")
        logger.info(f"   ✅ Processed: {self.stats['processed']}")
        logger.info(f"   🤖 Analyzed: {self.stats['analyzed']}")
        logger.info(f"   📤 Uploaded: {self.stats['uploaded']}")
        logger.info(f"   ⏭️ Skipped: {self.stats['skipped']}")
        logger.info(f"   ❌ Rejected: {self.stats['errors']}") # Renamed from 'errors' to 'rejected' for clarity on skipped items
        
        success_rate = (self.stats['uploaded'] / max(self.stats['total_files'], 1)) * 100
        logger.info(f"   🎯 Success rate: {success_rate:.1f}%")
        logger.info(f"   📈 Quality: Only properly classified educational content uploaded")
        
        return {
            "statistics": self.stats,
            "processed_files": processed_files
        }
    
    def list_minio_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in MinIO bucket"""
        try:
            objects = self.minio_client.list_objects( # type: ignore
                self.minio_bucket,
                prefix=prefix,
                recursive=True
            )
            
            files = []
            for obj in objects:
                if not obj.object_name.endswith('/'):  # Skip directories# type: ignore
                    files.append({
                        "name": os.path.basename(obj.object_name),# type: ignore
                        "path": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"❌ Error listing MinIO files: {e}")
            return []


# ===== MAIN SCRIPT =====
def main():
    """Main script to process downloaded PDFs"""
    
    # Configuration
    # CHÚ Ý: BẠN PHẢI THAY THẾ KHÓA NÀY BẰNG KHÓA THẬT CỦA BẠN!
    GEMINI_API_KEY = "AIzaSyAxyew-YwI4QfOzFHJQhGSaG0T1uMj6ALo" # <--- THAY THẾ Ở ĐÂY
    
    MINIO_CONFIG = {
        'endpoint': 'localhost:9000',
        'access_key': 'minioadmin',
        'secret_key': 'minioadmin',
        'bucket_name': 'ai-education',
        'secure': False
    }
    
    PDF_FOLDER = "downloaded_pdfs"
    
    logger.info("🚀 PDF METADATA PROCESSOR")
    logger.info("=" * 50)
    
    try:
        # Initialize processor
        processor = PDFMetadataProcessor(GEMINI_API_KEY, MINIO_CONFIG)
        
        # Process all PDFs in folder
        results = processor.process_pdf_folder(
            folder_path=PDF_FOLDER,
            skip_existing=True
        )
        
        # Show MinIO contents
        logger.info(f"\n☁️ Files in MinIO bucket:")
        minio_files = processor.list_minio_files()
        
        if minio_files:
            # Group by subject
            by_subject = {}
            for file_info in minio_files:
                subject = file_info['path'].split('/')[0]
                if subject not in by_subject:
                    by_subject[subject] = []
                by_subject[subject].append(file_info)
            
            for subject, files in by_subject.items():
                logger.info(f"   📚 {subject}: {len(files)} files")
                for file_info in files[:3]:  # Show first 3
                    logger.info(f"      📄 {file_info['name']}")
                if len(files) > 3:
                    logger.info(f"      ... and {len(files) - 3} more")
        else:
            logger.info("   No files found")
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()