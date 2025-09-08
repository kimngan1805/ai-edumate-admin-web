# register_processors.py
from base import ProcessorFactory, DocumentFormat

# Register all processors
def register_all_processors():
    try:
        # PDF processor
        from pdf_processor import PDFProcessor
        ProcessorFactory.register_processor(DocumentFormat.PDF, PDFProcessor)
        
        # Office processors  
        from office_processor import DOCXProcessor, PPTXProcessor, XLSXProcessor
        ProcessorFactory.register_processor(DocumentFormat.DOCX, DOCXProcessor)
        ProcessorFactory.register_processor(DocumentFormat.PPTX, PPTXProcessor)
        ProcessorFactory.register_processor(DocumentFormat.XLSX, XLSXProcessor)
        
        # Image processor
        from image_processor import ImageProcessor
        ProcessorFactory.register_processor(DocumentFormat.IMAGE, ImageProcessor)
        
        print("✅ All processors registered successfully")
        return True
        
    except ImportError as e:
        print(f"⚠️ Failed to register processors: {e}")
        return False

# Auto register when imported
register_all_processors()