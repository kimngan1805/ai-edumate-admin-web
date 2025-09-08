from pathlib import Path
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO)

from main_processor import EduMateDocumentProcessor
from base import ProcessingConfig, ProcessingMode

def test_with_light_config():
    """Test với config nhẹ để tránh segfault"""
    
    # Đường dẫn file
    path = Path("./test_data/Ch1_B1_Menh_de_a59ac.pdf")
    
    if not path.exists():
        print(f"❌ File không tồn tại: {path}")
        return
    
    # Tạo thư mục output
    output_dir = Path("./processing_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 Testing file: {path}")
    print(f"📏 File size: {path.stat().st_size / 1024:.2f} KB")
    
    try:
        # Tạo config nhẹ - DISABLE các features nặng
        light_config = ProcessingConfig(
            mode=ProcessingMode.FAST,      # Dùng FAST thay vì BALANCED
            use_gpu=False,                  # Tắt GPU
            enable_ocr=True,               # Giữ OCR
            extract_images=False,          # Tắt extract images (gây crash)
            extract_tables=True,           # Giữ tables
            extract_formulas=False,        # Tắt formulas (gây crash ở bboxes)
            parallel_processing=False,     # Tắt multiprocessing
            max_workers=1,                 # Chỉ 1 worker
            use_llm_enhancement=False,     # Tắt LLM
            preserve_layout=True
        )
        
        # Tạo processor với config nhẹ
        from main_processor import DocumentProcessingSystem
        processor_system = DocumentProcessingSystem(light_config)
        processor = EduMateDocumentProcessor(processor_system)
        
        print(f"📚 Supported formats: {processor.get_supported_formats()}")
        
        # Xử lý file
        print(f"\n🔄 Processing file with LIGHT config...")
        print("⚠️  Disabled: GPU, Images, Formulas, Multiprocessing")
        
        result = processor.process_file(path)
        
        print(f"\n✅ Processing completed!")
        print(f"📊 Success: {result.success}")
        
        if result.success:
            print(f"📝 Content length: {len(result.content)} characters")
            print(f"📐 Formulas found: {len(result.formulas) if result.formulas else 0}")
            print(f"📊 Tables found: {len(result.tables) if result.tables else 0}")
            print(f"🖼️ Images found: {len(result.images) if result.images else 0}")
            
            # In một phần nội dung để kiểm tra
            if result.content:
                print(f"\n📖 First 500 characters of content:")
                print(f"{result.content[:500]}...")
                
                # Lưu kết quả
                json_file = output_dir / f"{path.stem}_light_result.json"
                processor.save_results(result, json_file, format="json")
                print(f"📄 JSON saved to: {json_file}")
                
                md_file = output_dir / f"{path.stem}_light_result.md"
                processor.save_results(result, md_file, format="markdown")
                print(f"📝 Markdown saved to: {md_file}")
            else:
                print(f"\n⚠️ No content extracted!")
                
        else:
            print(f"❌ Processing failed: {result.error_message}")
            
    except Exception as e:
        print(f"💥 Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_light_config()