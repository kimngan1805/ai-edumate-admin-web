import json
import os
from datetime import datetime
from typing import List, Dict, Any
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MongoDBChunkStorage:
    def __init__(self):
        self.MONGO_URI = "mongodb+srv://triennd23ai:k2vKW7uw0FUcdX3J@eduagentcluster.do87h7i.mongodb.net/?retryWrites=true&w=majority&appName=EduAgentCluster"
        self.MONGO_DB_NAME = "edu_agent_db"
        self.COLLECTION_NAME = "lectures"
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            logger.info("Connecting to MongoDB...")
            self.client = MongoClient(self.MONGO_URI)
            self.db = self.client[self.MONGO_DB_NAME]
            self.collection = self.db[self.COLLECTION_NAME]
            
            # Test connection
            self.client.admin.command('ismaster')
            logger.info("✓ Connected to MongoDB successfully!")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def load_chunks_from_file(self, file_path: str) -> List[Dict]:
        """Load chunks from JSON file"""
        try:
            logger.info(f"Reading JSON file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            logger.info(f"Found {len(chunks)} chunks to process")
            return chunks
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
    
    def transform_chunk(self, chunk: Dict, index: int) -> Dict:
        """Transform chunk to MongoDB document format"""
        current_time = int(datetime.now().timestamp() * 1000)
        
        # Generate ID if not exists
        chunk_id = chunk.get('id', f"chunk_{current_time}_{index}")
        
        # Estimate token count (simple word count estimation)
        content = chunk.get('content', '')
        token_count = len(content.split()) if content else 0
        
        # Get metadata or use defaults
        metadata = chunk.get('metadata', {})
        
        document = {
            '_id': chunk_id,
            'chunk_id': chunk_id,
            'content': content,
            'token_count': token_count,
            'method': metadata.get('chunking_strategy', 'hybrid_sentence_aware'),
            'source_file': metadata.get('source_file', 'unknown'),
            'source_url': metadata.get('source_url'),
            'retrieved_from': 'file_upload',
            'char_count': metadata.get('char_count', len(content)),
            'keywords': metadata.get('keywords', []),
            'coherence_score': metadata.get('coherence_score', 1.0),
            'completeness_score': metadata.get('completeness_score', 1.0),
            'metadata': {
                'chunk_index': metadata.get('chunk_index', index),
                'word_count': metadata.get('word_count', token_count),
                'language_confidence': metadata.get('language_confidence', 1.0),
                'chunking_strategy': metadata.get('chunking_strategy', 'hybrid_sentence_aware'),
                **metadata  # Include all original metadata
            },
            'embedding': chunk.get('embedding', [])
        }
        
        return document
    
    def save_chunks_bulk(self, chunks: List[Dict]) -> bool:
        """Save chunks using bulk insert (faster)"""
        try:
            if not chunks:
                logger.warning("No chunks to save")
                return False
            
            # Transform chunks to documents
            documents = [self.transform_chunk(chunk, i) for i, chunk in enumerate(chunks)]
            
            logger.info("Inserting documents into MongoDB using bulk insert...")
            
            # Bulk insert with ordered=False to continue on errors
            result = self.collection.insert_many(documents, ordered=False)
            
            logger.info(f"✓ Successfully inserted {len(result.inserted_ids)} documents")
            logger.info(f"Inserted IDs: {list(result.inserted_ids)[:5]}...")  # Show first 5 IDs
            
            return True
            
        except BulkWriteError as e:
            # Handle bulk write errors (e.g., duplicate keys)
            logger.warning(f"Bulk write completed with some errors: {e.details}")
            successful_inserts = len(e.details.get('writeErrors', [])) 
            total_attempts = len(chunks)
            logger.info(f"Successfully inserted {total_attempts - successful_inserts}/{total_attempts} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error during bulk insert: {e}")
            return False
    
    def save_chunks_one_by_one(self, chunks: List[Dict]) -> bool:
        """Save chunks one by one (better error handling)"""
        try:
            if not chunks:
                logger.warning("No chunks to save")
                return False
            
            success_count = 0
            error_count = 0
            
            for i, chunk in enumerate(chunks):
                try:
                    document = self.transform_chunk(chunk, i)
                    
                    self.collection.insert_one(document)
                    success_count += 1
                    
                    if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                        logger.info(f"Progress: {i + 1}/{len(chunks)} chunks processed")
                        
                except DuplicateKeyError:
                    error_count += 1
                    logger.warning(f"Duplicate key for chunk {i + 1}: {chunk.get('id', 'unknown')}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to insert chunk {i + 1}: {e}")
            
            logger.info(f"\nSummary: {success_count} successful, {error_count} errors")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error during one-by-one insert: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test MongoDB connection and list collections"""
        try:
            logger.info("Testing MongoDB connection...")
            
            if not self.connect():
                return False
            
            # List collections
            collections = self.db.list_collection_names()
            logger.info(f"✓ Connection successful!")
            logger.info(f"Available collections: {collections}")
            
            # Check if lectures collection exists
            if self.COLLECTION_NAME in collections:
                count = self.collection.count_documents({})
                logger.info(f"'{self.COLLECTION_NAME}' collection has {count} documents")
            else:
                logger.info(f"'{self.COLLECTION_NAME}' collection will be created on first insert")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            return False
        finally:
            self.disconnect()
    
    def get_collection_stats(self):
        """Get statistics about the lectures collection"""
        try:
            if not self.collection:
                logger.error("Not connected to database")
                return
            
            total_docs = self.collection.count_documents({})
            logger.info(f"Total documents in '{self.COLLECTION_NAME}': {total_docs}")
            
            # Sample document
            sample_doc = self.collection.find_one()
            if sample_doc:
                logger.info("Sample document structure:")
                sample_keys = list(sample_doc.keys())
                logger.info(f"Document keys: {sample_keys}")
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")

def main():
    """Main function to run the chunk upload process"""
    # Configuration/Users/kimngan/IdeaProjects/ai-education/app/document_processing/data_embedding/embedding_output/result_hybrid_20250722_204214_chunks_embedded.json
    json_file_path = "./app/document_processing/data_embedding/embedding_output/Ch1_B1_Menh_de_a59ac_result_embedded.json"  # Change this to your JSON file path
    use_bulk_insert = True  # Set to False for one-by-one insert
    
    # Initialize storage handler
    storage = MongoDBChunkStorage()
    
    try:
        # Test connection first
        if not storage.test_connection():
            logger.error("Connection test failed. Exiting...")
            return
        
        # Connect for actual work
        if not storage.connect():
            logger.error("Failed to connect. Exiting...")
            return
        
        # Load chunks from file
        chunks = storage.load_chunks_from_file(json_file_path)
        if not chunks:
            logger.error("No chunks loaded. Exiting...")
            return
        
        # Save chunks to MongoDB
        if use_bulk_insert:
            success = storage.save_chunks_bulk(chunks)
        else:
            success = storage.save_chunks_one_by_one(chunks)
        
        if success:
            logger.info("✓ Chunk upload completed successfully!")
            # Get final stats
            storage.get_collection_stats()
        else:
            logger.error("✗ Chunk upload failed!")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    finally:
        storage.disconnect()


def test_only():
    """Function to only test the connection"""
    storage = MongoDBChunkStorage()
    storage.test_connection()


if __name__ == "__main__":
    # Uncomment the function you want to run:
    
    # Run full upload process
    main()
    
    # Or just test connection
    # test_only()