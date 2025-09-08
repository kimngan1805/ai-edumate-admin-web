# utils/minio_connection.py
import os
from minio import Minio
from minio.error import S3Error
import logging
from typing import Optional, List

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinIOConnection:
    """Class để quản lý kết nối với MinIO"""
    
    def __init__(self, endpoint="127.000.1:9000", access_key="minioadmin", secret_key="minioadmin", secure=False):
        """
        Khởi tạo kết nối MinIO
        
        Args:
            endpoint (str): MinIO endpoint
            access_key (str): Access key
            secret_key (str): Secret key  
            secure (bool): Sử dụng HTTPS hay không
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client: Optional[Minio] = None
        
    def connect(self):
        """Tạo kết nối với MinIO server"""
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            logger.info(f"✅ Kết nối thành công tới MinIO server: {self.endpoint}")
            return True
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối MinIO: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test kết nối bằng cách list buckets"""
        if not self.client:
            logger.error("❌ Chưa có kết nối MinIO. Vui lòng gọi connect() trước")
            return False
            
        try:
            # Explicit type check để tránh IDE warning
            client: Minio = self.client
            
            # List all buckets
            buckets = client.list_buckets()
            
            print("\n" + "="*50)
            print("🗂️  DANH SÁCH BUCKETS TRONG MINIO")
            print("="*50)
            
            if buckets:
                for bucket in buckets:
                    print(f"📁 Bucket: {bucket.name}")
                    print(f"   📅 Tạo lúc: {bucket.creation_date}")
                    print(f"   🔗 Endpoint: {self.endpoint}")
                    print("-" * 30)
            else:
                print("📭 Không có bucket nào trong MinIO")
                
            print("="*50)
            print(f"✅ Kết nối thành công! Tổng cộng {len(buckets)} bucket(s)")
            return True
            
        except S3Error as e:
            logger.error(f"❌ Lỗi S3: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định: {e}")
            return False
    
    def create_bucket(self, bucket_name: str) -> bool:
        """Tạo bucket mới"""
        if not self.client:
            logger.error("❌ Chưa có kết nối MinIO")
            return False
            
        try:
            # Explicit type check để tránh IDE warning
            client: Minio = self.client
            
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                logger.info(f"✅ Tạo bucket '{bucket_name}' thành công")
                return True
            else:
                logger.info(f"ℹ️  Bucket '{bucket_name}' đã tồn tại")
                return True
        except Exception as e:
            logger.error(f"❌ Lỗi tạo bucket: {e}")
            return False
    
    def list_objects(self, bucket_name: str, prefix: str = "") -> List[str]:
        """List objects trong bucket"""
        if not self.client:
            logger.error("❌ Chưa có kết nối MinIO")
            return []
            
        try:
            # Explicit type check để tránh IDE warning
            client: Minio = self.client
            objects = client.list_objects(bucket_name, prefix=prefix)
            object_list = []
            
            print(f"\n📂 Objects trong bucket '{bucket_name}':")
            print("-" * 40)
            
            for obj in objects:
                print(f"📄 {obj.object_name} (Size: {obj.size} bytes)")
                object_list.append(obj.object_name)
                
            return object_list
            
        except Exception as e:
            logger.error(f"❌ Lỗi list objects: {e}")
            return []
        
    # --- ĐÂY LÀ VỊ TRÍ ĐÚNG CỦA HÀM list_common_prefixes ---
    # Đảm bảo hàm này được thụt vào đúng cấp độ của các phương thức khác trong class MinIOConnection
    def list_common_prefixes(self, bucket_name: str, prefix: str = "") -> List[str]:
        """
        List common prefixes (simulating folders) within a bucket using a fallback method
        if 'delimiter' is not supported.
        This method is less efficient for large buckets.
        """
        if not self.client:
            logger.error("❌ Chưa có kết nối MinIO.")
            return []

        try:
            client: Minio = self.client

            # --- THAY THẾ LOGIC LIST FOLDERS Ở ĐÂY ---
            # Cố gắng sử dụng delimiter trước, nếu lỗi thì dùng fallback
            try:
                # Đây là cách ưu tiên, cho phiên bản Minio 7.x.x
                objects_iterator = client.list_objects(bucket_name, prefix=prefix, delimiter='/') # type: ignore
                folders = []
                for obj in objects_iterator:
                    if obj.is_dir: # obj.is_dir chỉ có sẵn khi dùng delimiter
                        folders.append(obj.object_name)
                
                logger.info(f"✅ Đã tải danh sách common prefixes/folders từ bucket '{bucket_name}' dưới prefix '{prefix}' bằng delimiter. Tìm thấy {len(folders)}.")
                return folders

            except TypeError as te:
                # Nếu TypeError xuất hiện (do 'delimiter' không được hỗ trợ)
                if "unexpected keyword argument 'delimiter'" in str(te):
                    logger.warning(f"⚠️ Phiên bản MinIO client không hỗ trợ 'delimiter' cho list_objects. Đang dùng phương pháp fallback. Lỗi: {te}")
                    
                    # Phương pháp fallback: Liệt kê tất cả objects và tự phân tích prefixes
                    all_objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
                    found_prefixes = set()
                    
                    for obj in all_objects:
                        # object_name ví dụ: "thpt/toan/detai/file.pdf"
                        # Cần tìm tiền tố ngay sau 'prefix' ban đầu
                        relative_name = obj.object_name[len(prefix):] # type: ignore
                        if '/' in relative_name:
                            # Lấy phần trước dấu '/' đầu tiên
                            first_slash_index = relative_name.find('/')
                            top_level_prefix = relative_name[:first_slash_index + 1] # Cộng 1 để giữ dấu '/'
                            found_prefixes.add(prefix + top_level_prefix)
                    
                    folders = sorted(list(found_prefixes))
                    logger.info(f"✅ Đã tải danh sách common prefixes/folders từ bucket '{bucket_name}' dưới prefix '{prefix}' bằng fallback. Tìm thấy {len(folders)}.")
                    return folders
                else:
                    raise te # Nếu là TypeError khác, thì re-raise

        except S3Error as e:
            logger.error(f"❌ Lỗi S3 khi lấy danh sách folder: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi lấy danh sách folder: {e}")
            return []
def main():
    """Hàm test kết nối MinIO"""
    print("🔌 TESTING MINIO CONNECTION")
    print("=" * 50)
    
    # Khởi tạo kết nối
    minio_conn = MinIOConnection()
    
    # Kết nối
    if minio_conn.connect():
        # Test kết nối
        minio_conn.test_connection()
        
        # Tạo bucket demo (optional)
        demo_bucket = "ai-education-demo"
        minio_conn.create_bucket(demo_bucket)
        
        # List objects trong bucket (nếu có)
        minio_conn.list_objects(demo_bucket)
        
    else:
        print("❌ Không thể kết nối tới MinIO server")
        print("📋 Kiểm tra lại:")
        print("   - MinIO server đang chạy chưa?")
        print("   - Endpoint có đúng không?")
        print("   - Access key và secret key có đúng không?")

if __name__ == "__main__":
    main()