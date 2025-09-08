# app/web_searching/content_scraper.py
"""
Two-Stage Intelligent Content Scraper
Stage 1: Fast pre-filtering (basic checks)
Stage 2: AI quality analysis (Gemini)
"""

import os
import time
import threading
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import trafilatura
import re
import json


class TwoStageContentScraper:
    """Two-stage content scraper với pre-filtering và AI analysis"""
    
    def __init__(self, base_path="data", gemini_api_key=None):
        self.base_path = Path(base_path)
        self.setup_directories()
        self.setup_session()
        self.processed_links = set()
        self.rejected_links = set()
        self.prefilter_rejected = set()  # Links bị loại ở stage 1
        self.running = False
        self.thread = None
        
        # AI Configuration
        self.gemini_api_key = gemini_api_key or "AIzaSyAxyew-YwI4QfOzFHJQhGSaG0T1uMj6ALo"
        self.setup_gemini()
        
        # Paths
        self.detail_links_base = self.base_path / "scraped_data" / "detail_link"
        self.single_detail_file = self.detail_links_base / "single_detail_link.txt"
        self.multi_detail_links_path = self.detail_links_base / "multi_detail_link"
        self.output_path = self.base_path / "links_md"
        self.processed_links_file = self.output_path / "processed_links.txt"
        self.rejected_links_file = self.output_path / "rejected_links.txt"
        self.prefilter_rejected_file = self.output_path / "prefilter_rejected.txt"
        self.quality_log_file = self.output_path / "quality_analysis.json"
        
        # Load processed/rejected links
        self.load_processed_links()
        self.load_rejected_links()
        self.load_prefilter_rejected()
        
        # Quality thresholds
        self.min_content_length = 300
        self.min_educational_score = 7
        
        # Pre-filter configuration
        self.prefilter_config = {
            'min_raw_content_length': 150,  # Tối thiểu 150 ký tự raw
            'max_link_density': 0.6,        # Tối đa 60% là links
            'min_text_lines': 5,            # Tối thiểu 5 dòng text
            'blocked_patterns': [
                'chỉ có link', 'only links', 'danh sách link',
                'download file', 'tải file', 'file đính kèm',
                'liên hệ mua', 'thanh toán', 'gửi phí',
                'đăng nhập để xem', 'đăng ký để tải'
            ],
            'required_educational_keywords': [
                'bài tập', 'đề thi', 'lời giải', 'phân tích',
                'lý thuyết', 'công thức', 'ví dụ', 'giải thích',
                'soạn bài', 'tóm tắt', 'nội dung', 'chương',
                'học sinh', 'giáo viên', 'môn học'
            ]
        }
        
    def setup_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            self.base_path / "links_md",
            self.base_path / "scraped_data" / "detail_link",
            self.base_path / "scraped_data" / "detail_link" / "multi_detail_link"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def setup_session(self):
        """Setup session với headers"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session.headers.update(self.headers)
    
    def setup_gemini(self):
        """Setup Gemini AI"""
        self.gemini_model = None
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                
                available_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']
                for model_name in available_models:
                    try:
                        self.gemini_model = genai.GenerativeModel(
                            model_name,
                            generation_config={
                                'temperature': 0.1,
                                'top_p': 0.8,
                                'max_output_tokens': 1024,  # type: ignore # Giảm để tiết kiệm
                            }
                        )
                        print(f"✅ Gemini AI initialized with model: {model_name}")
                        break
                    except Exception:
                        continue
                        
                if not self.gemini_model:
                    print("❌ No Gemini model available")
                    
            except ImportError:
                print("⚠️ google-generativeai not installed. AI quality check disabled.")
        else:
            print("⚠️ No Gemini API key provided. AI quality check disabled.")
    
    def load_processed_links(self):
        """Load danh sách links đã xử lý"""
        if self.processed_links_file.exists():
            try:
                with open(self.processed_links_file, 'r', encoding='utf-8') as f:
                    self.processed_links = set(line.strip() for line in f if line.strip())
                print(f"📋 Loaded {len(self.processed_links)} processed links")
            except Exception as e:
                print(f"⚠️ Error loading processed links: {e}")
                self.processed_links = set()
        else:
            self.processed_links = set()
    
    def load_rejected_links(self):
        """Load danh sách links bị từ chối ở stage 2"""
        if self.rejected_links_file.exists():
            try:
                with open(self.rejected_links_file, 'r', encoding='utf-8') as f:
                    self.rejected_links = set(line.strip().split(' | ')[0] for line in f if line.strip())
                print(f"🚫 Loaded {len(self.rejected_links)} AI-rejected links")
            except Exception as e:
                print(f"⚠️ Error loading rejected links: {e}")
                self.rejected_links = set()
        else:
            self.rejected_links = set()
    
    def load_prefilter_rejected(self):
        """Load danh sách links bị từ chối ở stage 1"""
        if self.prefilter_rejected_file.exists():
            try:
                with open(self.prefilter_rejected_file, 'r', encoding='utf-8') as f:
                    self.prefilter_rejected = set(line.strip().split(' | ')[0] for line in f if line.strip())
                print(f"🔍 Loaded {len(self.prefilter_rejected)} pre-filter rejected links")
            except Exception as e:
                print(f"⚠️ Error loading prefilter rejected links: {e}")
                self.prefilter_rejected = set()
        else:
            self.prefilter_rejected = set()
    
    def save_prefilter_rejected(self, url, reason=""):
        """Lưu link bị từ chối ở stage 1"""
        self.prefilter_rejected.add(url)
        try:
            with open(self.prefilter_rejected_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{url} | {reason} | {timestamp}\n")
        except Exception as e:
            print(f"⚠️ Error saving prefilter rejected link: {e}")
    
    def get_page_content_lightweight(self, url):
        """Lấy nội dung nhanh cho pre-filtering"""
        try:
            response = self.session.get(url, timeout=15)  # Timeout ngắn hơn
            response.raise_for_status()
            
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = 'utf-8'
            
            return response.text
        except Exception as e:
            print(f"   ❌ Pre-filter load error: {e}")
            return None
    
    def extract_content_fast(self, html_content, url):
        """Extract nội dung nhanh cho pre-filtering"""
        if not html_content:
            return None
        
        try:
            # Quick extraction with trafilatura
            extracted = trafilatura.extract(
                html_content,
                output_format="text",  # Plain text để nhanh hơn
                include_links=False,
                favor_precision=True,  # Ưu tiên tốc độ
                url=url
            )
            
            if extracted:
                return extracted.strip()
                
            # Fallback to simple BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove scripts, styles
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # Get text from main content areas
            main_selectors = ['article', '.content', '.post-content', '.entry-content', 'main']
            for selector in main_selectors:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
            
            # Fallback to body
            body = soup.find('body')
            if body:
                return body.get_text(strip=True)
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Fast extract error: {e}")
            return None
    
    def prefilter_analysis(self, content, url):
        """Stage 1: Pre-filtering analysis (nhanh, không dùng AI)"""
        if not content:
            return {
                'passed': False,
                'reason': 'No content extracted',
                'score': 0
            }
        
        content_lower = content.lower()
        content_length = len(content)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Check 1: Minimum content length
        if content_length < self.prefilter_config['min_raw_content_length']:
            return {
                'passed': False,
                'reason': f'Too short: {content_length} chars',
                'score': 1
            }
        
        # Check 2: Minimum text lines
        if len(lines) < self.prefilter_config['min_text_lines']:
            return {
                'passed': False,
                'reason': f'Too few lines: {len(lines)}',
                'score': 1
            }
        
        # Check 3: Blocked patterns
        for pattern in self.prefilter_config['blocked_patterns']:
            if pattern in content_lower:
                return {
                    'passed': False,
                    'reason': f'Contains blocked pattern: {pattern}',
                    'score': 2
                }
        
        # Check 4: Link density (approximation)
        link_indicators = content_lower.count('http') + content_lower.count('www.') + content_lower.count('.html')
        text_words = len(content.split())
        link_density = link_indicators / max(text_words, 1)
        
        if link_density > self.prefilter_config['max_link_density']:
            return {
                'passed': False,
                'reason': f'High link density: {link_density:.2f}',
                'score': 2
            }
        
        # Check 5: Educational keywords
        educational_keyword_count = sum(1 for keyword in self.prefilter_config['required_educational_keywords'] 
                                      if keyword in content_lower)
        
        if educational_keyword_count < 2:  # Cần ít nhất 2 từ khóa giáo dục
            return {
                'passed': False,
                'reason': f'Too few educational keywords: {educational_keyword_count}',
                'score': 3
            }
        
        # Check 6: Simple answer patterns
        simple_answer_patterns = ['đáp án:', 'answer:', 'a)', 'b)', 'c)', 'd)']
        simple_answers = sum(1 for pattern in simple_answer_patterns if pattern in content_lower)
        
        if simple_answers > len(lines) * 0.5:  # Hơn 50% là đáp án đơn giản
            return {
                'passed': False,
                'reason': f'Mostly simple answers: {simple_answers}/{len(lines)}',
                'score': 3
            }
        
        # Calculate pre-filter score
        score = 5  # Base score
        
        # Bonus points
        if content_length > 500:
            score += 1
        if educational_keyword_count >= 5:
            score += 1
        if len(lines) >= 10:
            score += 1
        
        return {
            'passed': True,
            'reason': f'Pre-filter passed: {educational_keyword_count} edu keywords, {content_length} chars',
            'score': min(score, 8)  # Max 8 for pre-filter
        }
    
    def stage1_prefilter(self, url):
        """Stage 1: Pre-filtering một URL"""
        print(f"   🔍 STAGE 1: Pre-filtering...")
        
        # Get content quickly
        html_content = self.get_page_content_lightweight(url)
        if not html_content:
            self.save_prefilter_rejected(url, "Failed to load page")
            return None
        
        # Extract content fast
        raw_content = self.extract_content_fast(html_content, url)
        if not raw_content:
            self.save_prefilter_rejected(url, "No content extracted")
            return None
        
        # Pre-filter analysis
        prefilter_result = self.prefilter_analysis(raw_content, url)
        
        print(f"   📊 Pre-filter score: {prefilter_result['score']}/8")
        print(f"   📝 Reason: {prefilter_result['reason']}")
        
        if not prefilter_result['passed']:
            print(f"   🚫 STAGE 1 REJECTED: {prefilter_result['reason']}")
            self.save_prefilter_rejected(url, prefilter_result['reason'])
            return None
        
        print(f"   ✅ STAGE 1 PASSED: Ready for AI analysis")
        return {
            'raw_content': raw_content,
            'prefilter_score': prefilter_result['score'],
            'prefilter_reason': prefilter_result['reason']
        }
    
    def stage2_ai_analysis(self, content, url):
        """Stage 2: AI analysis với Gemini"""
        if not self.gemini_model:
            return {
                'is_quality': True,  # Default pass nếu không có AI
                'score': 6,
                'reason': 'AI not available - passed pre-filter',
                'content_type': 'unknown'
            }
        
        try:
            print(f"   🤖 STAGE 2: AI analysis...")
            
            # Compact prompt to save tokens
            prompt = f"""Analyze this educational content. Return JSON only:
{{
    "is_quality": true/false,
    "score": 1-10,
    "reason": "brief reason",
    "content_type": "full_lesson|partial_content|test_answers|advertisement"
}}

CRITERIA:
✅ HIGH QUALITY (8-10): Complete lessons, detailed explanations, full exercises
❌ LOW QUALITY (1-4): Only links, simple answers, advertisements

CONTENT (first 1500 chars):
{content[:1500]}

JSON:"""

            response = self.gemini_model.generate_content(prompt)
            
            if response.text:
                try:
                    json_text = response.text.strip()
                    if json_text.startswith('```json'):
                        json_text = json_text[7:-3]
                    elif json_text.startswith('```'):
                        json_text = json_text[3:-3]
                    
                    analysis = json.loads(json_text.strip())
                    
                    if all(field in analysis for field in ['is_quality', 'score', 'reason']):
                        print(f"   🧠 AI Score: {analysis['score']}/10 - {analysis.get('content_type', 'unknown')}")
                        return analysis
                        
                except json.JSONDecodeError:
                    print(f"   ⚠️ AI response parse error")
            
            # Fallback
            return {
                'is_quality': True,
                'score': 6,
                'reason': 'AI analysis failed - using fallback',
                'content_type': 'partial_content'
            }
            
        except Exception as e:
            print(f"   ❌ AI analysis error: {e}")
            return {
                'is_quality': True,
                'score': 6,
                'reason': f'AI error: {str(e)[:50]}',
                'content_type': 'unknown'
            }
    
    def process_single_url_two_stage(self, url):
        """Xử lý một URL với 2-stage filtering"""
        print(f"\n🔄 Processing: {url}")
        
        try:
            # STAGE 1: Pre-filtering
            stage1_result = self.stage1_prefilter(url)
            if not stage1_result:
                return None  # Rejected at stage 1
            
            # STAGE 2: AI Analysis
            ai_analysis = self.stage2_ai_analysis(stage1_result['raw_content'], url)
            
            # Combine scores
            combined_score = (stage1_result['prefilter_score'] + ai_analysis['score']) / 2
            
            print(f"   📊 Combined score: {combined_score:.1f}/10 (Pre: {stage1_result['prefilter_score']}, AI: {ai_analysis['score']})")
            
            # Final quality check
            if not ai_analysis['is_quality'] or combined_score < 6:
                reason = f"Low combined score: {combined_score:.1f} - {ai_analysis['reason']}"
                print(f"   🚫 STAGE 2 REJECTED: {reason}")
                self.save_rejected_link(url, reason)
                return None
            
            # STAGE 3: Full content extraction for saving
            print(f"   📄 STAGE 3: Full content extraction...")
            html_content = self.get_page_content_advanced(url)
            if not html_content:
                return None
            
            full_content = self.extract_content_advanced(html_content, url)
            if not full_content:
                return None
            
            cleaned_content = self.advanced_content_cleaning(full_content)
            if not cleaned_content or len(cleaned_content) < self.min_content_length:
                return None
            
            print(f"   ✅ TWO-STAGE PASSED: Final content {len(cleaned_content)} chars")
            
            return {
                'url': url,
                'content': cleaned_content,
                'quality_analysis': {
                    'score': round(combined_score, 1),
                    'prefilter_score': stage1_result['prefilter_score'],
                    'ai_score': ai_analysis['score'],
                    'content_type': ai_analysis.get('content_type', 'unknown'),
                    'reason': f"Pre-filter: {stage1_result['prefilter_reason']} | AI: {ai_analysis['reason']}"
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"   ❌ Two-stage error: {e}")
            return None
    
    def save_processed_link(self, url):
        """Lưu link đã xử lý thành công"""
        self.processed_links.add(url)
        try:
            with open(self.processed_links_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")
        except Exception as e:
            print(f"⚠️ Error saving processed link: {e}")
    
    def save_rejected_link(self, url, reason=""):
        """Lưu link bị từ chối ở stage 2"""
        self.rejected_links.add(url)
        try:
            with open(self.rejected_links_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{url} | {reason} | {timestamp}\n")
        except Exception as e:
            print(f"⚠️ Error saving rejected link: {e}")
    
    def get_links_from_files(self):
        """Lấy links chưa xử lý"""
        all_links = []
        
        # Single file
        if self.single_detail_file.exists():
            links_data = self.read_links_from_file(self.single_detail_file)
            if links_data:
                all_links.append({
                    'file_path': self.single_detail_file,
                    'links': links_data
                })
        
        # Multi files  
        if self.multi_detail_links_path.exists():
            txt_files = list(self.multi_detail_links_path.glob("*.txt"))
            for txt_file in txt_files:
                links_data = self.read_links_from_file(txt_file)
                if links_data:
                    all_links.append({
                        'file_path': txt_file,
                        'links': links_data
                    })
        
        return all_links
    
    def read_links_from_file(self, file_path):
        """Đọc links chưa processed/rejected"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return []
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            valid_links = []
            
            for line in lines:
                url = line
                if ' | ' in line:
                    parts = line.split(' | ')
                    url = parts[-1].strip()
                
                if (url.startswith('http') and 
                    not url.lower().endswith('.pdf') and
                    url not in self.processed_links and 
                    url not in self.rejected_links and
                    url not in self.prefilter_rejected):
                    valid_links.append(url)
            
            return valid_links
            
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
            return []
    
    # Include all other necessary methods from previous implementation
    def get_page_content_advanced(self, url):
        """Advanced page loading for stage 3"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                    response.encoding = 'utf-8'
                return response.text
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"   ❌ Final load error: {e}")
                    return None
                time.sleep(2)
        return None
    
    def extract_content_advanced(self, html_content, url):
        """Advanced content extraction for final stage"""
        try:
            extracted = trafilatura.extract(
                html_content,
                output_format="markdown",
                with_metadata=True,
                include_images=True,
                include_links=False,
                include_tables=True,
                favor_recall=True,
                url=url
            )
            
            if extracted and len(extracted.strip()) > 100:
                return self.clean_extracted_markdown(extracted)
                
            return self.custom_extract_with_bs4(html_content)
            
        except Exception:
            return self.custom_extract_with_bs4(html_content)
    
    def clean_extracted_markdown(self, markdown_text):
        """Clean markdown text"""
        if not markdown_text:
            return markdown_text
        
        lines = markdown_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if not line.strip():
                cleaned_lines.append('')
                continue
            
            line = re.sub(r'\[([^\]]+)\]\([^)]*\.html[^)]*\)', r'\1', line)
            line = re.sub(r'\[([^\]]+)\]\(https?://[^)]+\)', r'\1', line)
            line = re.sub(r'https?://[^\s]+\.html\S*', '', line)
            line = re.sub(r'\s+', ' ', line).strip()
            
            if line and len(line) > 3:
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    
    def custom_extract_with_bs4(self, html_content):
        """BeautifulSoup extraction fallback"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                unwanted.decompose()
            
            content_selectors = [
                '.entry-content', '.post-content', '.content',
                'article', 'main', '.main-content', '.post-body'
            ]
            
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element and len(element.get_text().strip()) > 200:
                    markdown_content = md(
                        str(element),
                        heading_style="ATX",
                        bullets="*",
                        strip=['script', 'style'],
                        convert=['img'],
                        escape_misc=False
                    )
                    return self.clean_extracted_markdown(markdown_content)
            
            return None
            
        except Exception:
            return None
    
    def advanced_content_cleaning(self, text):
        """Advanced content cleaning"""
        if not text:
            return text
        
        lines = text.split('\n')
        cleaned_lines = []
        
        skip_patterns = [
            'chỉ từ', 'mua trọn bộ', 'gửi phí', 'tk:', 'tài khoản',
            'ngân hàng', 'chuyển khoản', 'thanh toán',
            'với bộ', 'sẽ giúp học sinh', 'được biên soạn',
            'xin gửi tới', 'mời các bạn', 'download', 'tải về',
            'xem thêm', 'liên hệ', 'facebook', 'zalo',
            'đáp án: a', 'đáp án: b', 'đáp án: c', 'đáp án: d'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if len(line_lower) < 3:
                if line.strip() == '':
                    cleaned_lines.append('')
                continue
            
            skip = any(pattern in line_lower for pattern in skip_patterns)
            
            if not skip and line.strip():
                digit_count = sum(c.isdigit() for c in line)
                if digit_count > len(line) * 0.4 and len(line.strip()) < 50:
                    skip = True
            
            if not skip and line.strip():
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    
    def save_content_to_md_enhanced(self, content_data):
        """Lưu content với metadata chi tiết"""
        try:
            url = content_data['url']
            domain = url.split('/')[2].replace('www.', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            quality_score = content_data['quality_analysis']['score']
            safe_url = re.sub(r'[^\w\-.]', '_', url.split('/')[-1])[:40]
            filename = f"{domain}_s{quality_score}_{safe_url}_{timestamp}.md"
            
            filepath = self.output_path / filename
            
            # Enhanced markdown với 2-stage info
            md_content = f"""# {url}

**Scraped at:** {content_data['timestamp']}
**Source:** {url}
**Combined Score:** {quality_score}/10
**Pre-filter Score:** {content_data['quality_analysis']['prefilter_score']}/8
**AI Score:** {content_data['quality_analysis']['ai_score']}/10
**Content Type:** {content_data['quality_analysis']['content_type']}

---

{content_data['content']}

---

*Two-Stage Analysis: {content_data['quality_analysis']['reason']}*
"""
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            print(f"💾 Saved: {filename}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving content: {e}")
            return None
    
    def update_file_remove_link(self, file_path, processed_url):
        """Xóa link đã xử lý khỏi file gốc"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            updated_lines = []
            for line in lines:
                if processed_url not in line.strip():
                    updated_lines.append(line)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
                
        except Exception as e:
            print(f"⚠️ Error updating file {file_path}: {e}")
    
    def process_all_links_two_stage(self, max_links_per_session=200):
        """Xử lý links với 2-stage filtering system"""
        print("\n🚀 STARTING TWO-STAGE INTELLIGENT CONTENT SCRAPING")
        print("=" * 70)
        
        # Configuration display
        print(f"🔍 STAGE 1 - Pre-filtering:")
        print(f"   • Min content length: {self.prefilter_config['min_raw_content_length']} chars")
        print(f"   • Min text lines: {self.prefilter_config['min_text_lines']}")
        print(f"   • Max link density: {self.prefilter_config['max_link_density']*100}%")
        print(f"   • Required edu keywords: {len(self.prefilter_config['required_educational_keywords'])}")
        
        print(f"\n🤖 STAGE 2 - AI Analysis:")
        print(f"   • Model: {'✅ ' + (self.gemini_model._model_name if self.gemini_model else 'None')}")
        print(f"   • Min AI score: {self.min_educational_score}/10")
        
        print(f"\n🎯 Processing Settings:")
        print(f"   • Max links per session: {max_links_per_session}")
        print(f"   • Output: {self.output_path}")
        
        # Get links
        link_files = self.get_links_from_files()
        if not link_files:
            print("\n📂 No new links to process")
            return
        
        # Flatten and limit links
        all_links_flat = []
        for file_data in link_files:
            for url in file_data['links']:
                all_links_flat.append({
                    'url': url,
                    'file_path': file_data['file_path']
                })
        
        total_available = len(all_links_flat)
        
        # Apply session limit
        if total_available > max_links_per_session:
            print(f"\n⚠️ SESSION LIMITING ENABLED")
            print(f"   📊 Total available: {total_available:,}")
            print(f"   🎯 Processing: {max_links_per_session}")
            print(f"   ⏭️ Remaining after: {total_available - max_links_per_session:,}")
            
            links_to_process = all_links_flat[:max_links_per_session]
            
            # Estimate filtering
            print(f"\n📈 EXPECTED FILTERING:")
            print(f"   🔍 Stage 1 (pre-filter): ~70-80% rejection")
            print(f"   🤖 Stage 2 (AI): ~30-50% rejection of passed")
            print(f"   ✅ Final success: ~10-20% of total ({max_links_per_session * 0.15:.0f} links)")
            
            confirm = input(f"\n❓ Process {max_links_per_session} links now? (y/N): ").strip().lower()
            if confirm != 'y':
                print("🛑 Processing cancelled")
                return
        else:
            links_to_process = all_links_flat
        
        total_links = len(links_to_process)
        print(f"\n📄 Processing {total_links} links")
        
        # Processing stats
        processed_count = 0
        stage1_passed = 0
        stage2_passed = 0
        final_success = 0
        stage1_rejected = 0
        stage2_rejected = 0
        errors = 0
        
        # Time estimation
        estimated_seconds = total_links * 3  # 3 giây/link trung bình với pre-filter
        print(f"⏱️ Estimated time: {estimated_seconds/60:.0f} minutes")
        
        start_time = time.time()
        
        # Process each link
        for idx, link_data in enumerate(links_to_process, 1):
            try:
                url = link_data['url']
                file_path = link_data['file_path']
                
                print(f"\n{'='*80}")
                print(f"🔍 [{idx}/{total_links}] Processing...")
                print(f"🌐 URL: {url}")
                
                # Two-stage processing
                content_data = self.process_single_url_two_stage(url)
                
                if content_data:
                    # Successful processing
                    saved_file = self.save_content_to_md_enhanced(content_data)
                    if saved_file:
                        self.save_processed_link(url)
                        self.update_file_remove_link(file_path, url)
                        final_success += 1
                        stage1_passed += 1
                        stage2_passed += 1
                        
                        print(f"✅ FINAL SUCCESS: High-quality content saved")
                        print(f"   📊 Combined Score: {content_data['quality_analysis']['score']}/10")
                        print(f"   📄 Content Length: {len(content_data['content'])}")
                        print(f"   💾 File: {saved_file.name}")
                    else:
                        errors += 1
                        print(f"❌ Save error")
                else:
                    # Check which stage rejected it
                    if url in self.prefilter_rejected:
                        stage1_rejected += 1
                        print(f"🚫 STAGE 1 REJECTED")
                    elif url in self.rejected_links:
                        stage1_passed += 1
                        stage2_rejected += 1
                        print(f"🚫 STAGE 2 REJECTED")
                    else:
                        errors += 1
                        print(f"❌ PROCESSING ERROR")
                
                processed_count += 1
                
                # Progress report every 10 links
                if processed_count % 10 == 0 or processed_count == total_links:
                    elapsed = time.time() - start_time
                    progress = (processed_count / total_links) * 100
                    avg_time = elapsed / processed_count
                    remaining_time = (total_links - processed_count) * avg_time
                    
                    print(f"\n📈 PROGRESS REPORT [{processed_count}/{total_links}] ({progress:.1f}%)")
                    print(f"   🔍 Stage 1 passed: {stage1_passed} ({stage1_passed/processed_count*100:.1f}%)")
                    print(f"   🤖 Stage 2 passed: {stage2_passed} ({stage2_passed/max(stage1_passed,1)*100:.1f}%)")
                    print(f"   ✅ Final success: {final_success} ({final_success/processed_count*100:.1f}%)")
                    print(f"   ⏱️ Avg time/link: {avg_time:.1f}s | ETA: {remaining_time/60:.0f}min")
                
                # Adaptive delay based on success rate
                if processed_count >= 20:
                    success_rate = final_success / processed_count
                    if success_rate > 0.3:  # High success rate - can speed up
                        delay = 1
                    elif success_rate > 0.15:  # Normal success rate
                        delay = 2
                    else:  # Low success rate - slow down for quality
                        delay = 3
                else:
                    delay = 2  # Default delay
                
                if processed_count < total_links:
                    print(f"⏳ Waiting {delay}s...")
                    time.sleep(delay)
                
            except KeyboardInterrupt:
                print(f"\n🛑 Processing interrupted by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                processed_count += 1
                errors += 1
                continue
        
        # Final comprehensive summary
        total_time = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"🎉 TWO-STAGE PROCESSING COMPLETE!")
        print(f"{'='*80}")
        
        print(f"📊 DETAILED STATISTICS:")
        print(f"   📄 Total processed: {processed_count}")
        print(f"   ⏱️ Total time: {total_time/60:.1f} minutes")
        print(f"   🚀 Avg speed: {total_time/processed_count:.1f} seconds/link")
        
        print(f"\n🔍 STAGE 1 (Pre-filtering):")
        print(f"   ✅ Passed: {stage1_passed} ({stage1_passed/processed_count*100:.1f}%)")
        print(f"   🚫 Rejected: {stage1_rejected} ({stage1_rejected/processed_count*100:.1f}%)")
        
        print(f"\n🤖 STAGE 2 (AI Analysis):")
        if stage1_passed > 0:
            print(f"   ✅ Passed: {stage2_passed} ({stage2_passed/stage1_passed*100:.1f}%)")
            print(f"   🚫 Rejected: {stage2_rejected} ({stage2_rejected/stage1_passed*100:.1f}%)")
        else:
            print(f"   ✅ Passed: {stage2_passed}")
            print(f"   🚫 Rejected: {stage2_rejected}")
        
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   ✅ Successfully saved: {final_success} ({final_success/processed_count*100:.1f}%)")
        print(f"   ❌ Errors: {errors} ({errors/processed_count*100:.1f}%)")
        
        print(f"\n📁 OUTPUT LOCATIONS:")
        print(f"   💾 Content: {self.output_path}")
        print(f"   🔍 Pre-filter rejected: {self.prefilter_rejected_file}")
        print(f"   🤖 AI rejected: {self.rejected_links_file}")
        print(f"   ✅ Processed: {self.processed_links_file}")
        
        # Efficiency analysis
        if processed_count > 0:
            efficiency = final_success / processed_count
            if efficiency > 0.2:
                print(f"\n🎊 EXCELLENT EFFICIENCY: {efficiency*100:.1f}% success rate!")
            elif efficiency > 0.1:
                print(f"\n👍 GOOD EFFICIENCY: {efficiency*100:.1f}% success rate")
            else:
                print(f"\n🔧 LOW EFFICIENCY: {efficiency*100:.1f}% - consider adjusting filters")
        
        # Remaining work estimate
        remaining = total_available - processed_count
        if remaining > 0:
            remaining_time_est = remaining * (total_time / processed_count) / 3600  # hours
            print(f"\n⏭️ REMAINING WORK:")
            print(f"   📊 Links left: {remaining:,}")
            print(f"   ⏱️ Est. time: {remaining_time_est:.1f} hours")
            print(f"   💡 Tip: Run again with max_links_per_session={max_links_per_session}")
    
    def get_statistics(self):
        """Lấy thống kê chi tiết cho cả 2 stages"""
        stats = {
            'processed_links': len(self.processed_links),
            'prefilter_rejected': len(self.prefilter_rejected),
            'ai_rejected': len(self.rejected_links),
            'total_handled': len(self.processed_links) + len(self.prefilter_rejected) + len(self.rejected_links)
        }
        
        # Calculate filtering efficiency
        if stats['total_handled'] > 0:
            stats['stage1_pass_rate'] = (len(self.processed_links) + len(self.rejected_links)) / stats['total_handled']
            stats['final_success_rate'] = len(self.processed_links) / stats['total_handled']
        
        return stats
    
    def print_statistics(self):
        """In thống kê chi tiết"""
        stats = self.get_statistics()
        
        print(f"\n📊 TWO-STAGE SCRAPER STATISTICS")
        print(f"{'='*60}")
        print(f"✅ Successfully processed: {stats['processed_links']}")
        print(f"🔍 Pre-filter rejected: {stats['prefilter_rejected']}")
        print(f"🤖 AI rejected: {stats['ai_rejected']}")
        print(f"📄 Total handled: {stats['total_handled']}")
        
        if stats['total_handled'] > 0:
            print(f"\n📈 EFFICIENCY METRICS:")
            print(f"   🔍 Stage 1 pass rate: {stats.get('stage1_pass_rate', 0)*100:.1f}%")
            print(f"   🎯 Final success rate: {stats.get('final_success_rate', 0)*100:.1f}%")
            
            # Filtering effectiveness
            total_rejected = stats['prefilter_rejected'] + stats['ai_rejected']
            print(f"   🛡️ Total filtered out: {total_rejected} ({total_rejected/stats['total_handled']*100:.1f}%)")


# Backward compatibility
IntegratedContentScraper = TwoStageContentScraper

def main():
    """Test function với two-stage processing"""
    print("🧪 TESTING TWO-STAGE CONTENT SCRAPER")
    print("=" * 50)
    
    scraper = TwoStageContentScraper()
    
    # Show current statistics
    scraper.print_statistics()
    
    # Debug file existence
    print(f"\n🔍 File existence check:")
    print(f"   Single file exists: {scraper.single_detail_file.exists()}")
    print(f"   Multi folder exists: {scraper.multi_detail_links_path.exists()}")
    
    if scraper.multi_detail_links_path.exists():
        txt_files = list(scraper.multi_detail_links_path.glob("*.txt"))
        print(f"   Files in multi folder: {[f.name for f in txt_files]}")
    
    # Get link count
    link_files = scraper.get_links_from_files()
    total_new_links = sum(len(file_data['links']) for file_data in link_files)
    
    if total_new_links > 0:
        print(f"\n📄 Found {total_new_links:,} NEW links to process")
        
        # Suggest batch size
        if total_new_links > 1000:
            suggested_batch = min(500, total_new_links)
            print(f"💡 Suggested batch size: {suggested_batch}")
        else:
            suggested_batch = total_new_links
        
        batch_size = input(f"🎯 Enter batch size (default {suggested_batch}): ").strip()
        if not batch_size:
            batch_size = suggested_batch
        else:
            batch_size = int(batch_size)
        
        confirm = input(f"❓ Start two-stage processing for {batch_size} links? (y/N): ").strip().lower()
        if confirm == 'y':
            scraper.process_all_links_two_stage(max_links_per_session=batch_size)
        else:
            print("🛑 Processing cancelled")
    else:
        print("\n✅ No new links to process")


if __name__ == "__main__":
    main()