# from modules.rag_module.data_embedding.embedding_processor import VietnameseEmbeddingProcessor
from embedding_processor import VietnameseEmbeddingProcessor
processor = VietnameseEmbeddingProcessor()

# Xử lý file
chunks_file = "../documents_processing/processing_output/CD1_B1_HE_PHUONG_TRINH_BAC_NHAT_BA_AN_VA_UNG_DUNG_122cd_result.md"
result = processor.run(chunks_file, save_results=True)