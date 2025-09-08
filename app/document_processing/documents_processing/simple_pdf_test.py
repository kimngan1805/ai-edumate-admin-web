import fitz
from pathlib import Path

def test_pdf_simple(pdf_path):
    try:
        print(f"📄 Testing PDF: {pdf_path}")
        doc = fitz.open(str(pdf_path))
        print(f"📖 Pages: {len(doc)}")
        
        if len(doc) > 0:
            page = doc[0]
            text = page.get_text()
            print(f"📝 First page text length: {len(text)}")
            print(f"📖 First 200 chars: {text[:200]}...")
        
        doc.close()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Test
pdf_files = list(Path("test_data").glob("*.pdf"))
if pdf_files:
    test_pdf_simple(pdf_files[0])
else:
    print("No PDF files found")
