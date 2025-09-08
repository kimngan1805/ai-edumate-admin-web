# modules/rag_module/data_embedding/embedding_processor.py

from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
import torch
from typing import List, Dict, Any

class VietnameseEmbeddingProcessor:
    def __init__(self, model_name: str = "VoVanPhuc/sup-SimCSE-VietNamese-phobert-base", device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SentenceTransformer(model_name, device=self.device) # <--- Dòng này tạo ra self.model
        print(f"✅ Loaded embedding model: {model_name} on {self.device}")

    def load_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        # Kiểm tra phần mở rộng của file
        if Path(file_path).suffix == ".md":
            print(f"📖 Reading Markdown file: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # Giả định toàn bộ nội dung Markdown là một chunk
            # Trong thực tế, bạn sẽ cần logic phức tạp hơn để chia Markdown thành nhiều chunk
            return [{"content": markdown_content, "metadata": {"source_file": Path(file_path).name}}]
        elif Path(file_path).suffix == ".json":
            print(f"📄 Reading JSON file: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported file type: {Path(file_path).suffix}. Only .md and .json are supported.")

    def save_chunks(self, chunks: List[Dict[str, Any]], output_path: str): # <--- Hàm này phải nằm trong lớp
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    def run(self, file_path: str, save_results: bool = False, output_path: str = None) -> Dict[str, Any]:
        chunks = self.load_chunks(file_path)
        total_chunks = len(chunks)
        successful = 0

        print(f"🧠 Processing {total_chunks} chunks...")

        for i, chunk in enumerate(chunks):
            text = chunk.get("content", "").strip()

            if not text:
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["embedding"] = []
                continue

            try:
                embedding = self.model.encode(text, convert_to_numpy=True).tolist() # <--- Dòng này cần self.model
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["embedding"] = embedding
                successful += 1
            except Exception as e:
                print(f"❌ Error embedding chunk {i}: {e}")
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["embedding"] = []

            # Progress
            if (i + 1) % 50 == 0 or (i + 1) == total_chunks:
                print(f"📊 Progress: {i + 1}/{total_chunks} chunks")

        print(f"✅ Completed: {successful}/{total_chunks} chunks embedded successfully")

        if save_results:
            output_dir = Path("embedding_output")
            output_dir.mkdir(exist_ok=True)

            if output_path:
                out_path = output_dir / Path(output_path).name
            else:
                out_path = output_dir / f"{Path(file_path).stem}_embedded.json"

            self.save_chunks(chunks, str(out_path)) # <--- Dòng này cần self.save_chunks
            print(f"💾 Saved embedded chunks to: {out_path}")
        else:
            print("⚠️ Results not saved (save_results=False)")

        return {
            "statistics": {
                "total_chunks": total_chunks,
                "successful_embeddings": successful
            },
            "chunks": chunks
        }