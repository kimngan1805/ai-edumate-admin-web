# ===== app/web_scraping/config.py =====
"""
Configuration settings for web scraping
"""
import os
from enum import Enum
from pathlib import Path


class CrawlType(Enum):
    SINGLE_PAGE = 'single_page'  # Crawl one specific page
    LIST_PAGE = 'list_page'
    HOCMAI_SPECIAL = 'hocmai_special'      # Crawl aggregate page, can follow child links


# Base directories - Fix path resolution
BASE_DIR = Path(__file__).parent.parent.parent.absolute()  # Go to project root
DATA_DIR = BASE_DIR / 'data'
SCRAPED_DATA_DIR = DATA_DIR / 'scraped_data'
DETAIL_LINK_DIR = SCRAPED_DATA_DIR / 'detail_link'

# File paths
ALLOWED_DOMAINS_FILE = DATA_DIR / 'allowed_domains.txt'
SINGLE_DETAIL_LINK_FILE = DETAIL_LINK_DIR / 'single_detail_link.txt'
MULTI_DETAIL_LINK_DIR = DETAIL_LINK_DIR / 'multi_detail_link'
PDF_BASE_DIR = MULTI_DETAIL_LINK_DIR / 'pdf'

# Create directories
for directory in [DATA_DIR, SCRAPED_DATA_DIR, DETAIL_LINK_DIR, MULTI_DETAIL_LINK_DIR, PDF_BASE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Default domain configuration
DEFAULT_DOMAIN_CONFIG = {
    "detail_link_pattern": r'.*',
    "intermediate_link_pattern": r'^/$',
    "content_div_selector": [
        'body', 'main', 'article', 'div.content-main', 
        'div#main-content', 'div.entry-content', 'div.post-content', 
        'div.article-body', 'div[itemprop="articleBody"]'
    ],
    "junk_patterns": [
        r'©\s*\w+\.com', r'Bài viết liên quan:', r'Xem thêm:', 
        r'Bạn có thể tham khảo thêm', r'Quảng cáo', r'Đọc thêm', 
        r'Bình luận', r'Liên hệ'
    ]
}

# Specific domain configurations
SPECIFIC_DOMAIN_CONFIGS = {
    "loigiaihay.com": {
        "intermediate_link_pattern": r"^/$|/(?:lop|mon-hoc|bai-hoc|chuong|giai-bai-tap|cau-hoi|giai-sach|giai-voc|sbt|sgk|toan|van|tieng-anh|chuyen-de|ket-noi|canh-diep|chan-troi)-[a-z0-9\-]+(?:-c\d+)?\.html(?:/?)$",
        "detail_link_pattern": r"/(?:bai|ly-thuyet|de-thi|giai-bai-tap|cau-hoi|giai-sach|giai-voc|soan-van|giai-voc)-[a-z0-9\-]+(?:-c\d+)?-a\d+\.html$",
        "content_div_selector": ['div.content-wrap', 'div.article-body', 'div[itemprop="articleBody"]', 'div.main-content'],
        "junk_patterns": [r'©\s*loigiaihay\.com', r'Bài viết liên quan:', r'Xem thêm:', r'Bạn có thể tham khảo thêm']
    },
    "vietjack.com": {
        "intermediate_link_pattern": r"^/$|/[a-z0-9\-]+/(?:index|lop-\d+|mon-hoc|chu-de|khoa-hoc|hoidap|giai-bai-tap-sgk|giai-sbt)\.jsp$",
        "detail_link_pattern": r"/[a-z0-9\-]+/(?:bai|giai|de|tom-tat|cong-thuc|phuong-phap|tac-pham|van-mau|hoc-bai|hoi-dap|bai-tap|soan-van|trac-nghiem|cau-hoi|giai-vbt|giai-sbt|giai-sgk)-[a-z0-9\-]*\.jsp$",
        "content_div_selector": ['div.post-content', 'div.entry-content', 'div.main-content', 'div#content'],
        "junk_patterns": [r'©\s*vietjack\.com', r'Xem thêm:', r'Xem chi tiết:', r'Bài viết liên quan:', r'Mục lục', r'Video bài giảng']
    },
    "vndoc.com": {
        "intermediate_link_pattern": r"^/$|/(?:lop-\d+|chuyen-muc|mon-hoc|de-thi|giai-bai-tap|tai-lieu|bai-viet|toan-lop\d+|van-lop\d+|anh-lop\d+|ly-lop\d+|hoa-lop\d+|sinh-lop\d+|su-lop\d+|dia-lop\d+|giai-toan-lop\d+|tai-lieu-hoc-tap-lop\d+|nguphap-tieng-anh|tu-vung-tieng-anh|trac-nghiem|violympic|test-mon|kiem-tra|mam-non|tieu-hoc|thcs|thpt|thi-vao-lop-\d+|thi-tot-nghiep|dai-hoc|giao-duc|hoc-tap|ren-luyen)[a-z0-9\-/]*$",
        "detail_link_pattern": r"/[a-z0-9\-]+-\d+$",
        "exclude_keywords": [
            "giao-an", "powerpoint", "ppt", "slide", "word", "excel", 
            "pdf-download", "tai-ve", "download", "file-", ".doc", ".docx", ".ppt", ".pptx"
        ],
        "content_div_selector": ["div.content-detail", "div.entry-content", "div#main-content", "div.article-content"],
        "junk_patterns": ["©\\s*Vndoc\\.com", "Bài viết cùng chủ đề:", "Tải file tài liệu", "Xem thêm:", "Bạn đang xem tài liệu"]
    },
    "thpttamnongdongthap.edu.vn": {
        "intermediate_link_pattern": r"^/$|/(?:udcntt|giao-an)/(?:giao-an-dien-tu/?|mon-[a-z\-]+/?|[a-z\-]+-\d+/?)$",
        "detail_link_pattern": r"/udcntt/giao-an-dien-tu/mon-[a-z\-]+/[a-z\-0-9]+/[a-z\-0-9\-]+.*\.html$|/upload/.*\.pdf$",
        "pdf_download": True,
        "content_div_selector": ["div.content", "div.main-content", "body"],
        "junk_patterns": []
    },
    "*.edu.vn": {
        "intermediate_link_pattern": r"^/$|/(?:udcntt|giao-an|tai-lieu|hoc-tap|upload)[a-z0-9\-/]*$",
        "detail_link_pattern": r"/upload/.*\.pdf$",
        "pdf_download": True,
        "content_div_selector": ["div.content", "div.main-content", "body"],
        "junk_patterns": []
    }
}
