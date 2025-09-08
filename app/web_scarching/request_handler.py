# ===== app/web_scraping/request_handler.py =====
"""
HTTP request handling with retry logic
"""
import requests
import time
import urllib3
from typing import Optional

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestHandler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        }
    
    def robust_get_request(self, url: str, max_retries: int = 3, base_delay: int = 10) -> Optional[requests.Response]:
        """Make HTTP request with retry logic for slow websites"""
        timeout_configs = [120, 180, 240]
        
        for attempt in range(max_retries):
            timeout = timeout_configs[min(attempt, len(timeout_configs)-1)]
            
            try:
                print(f"🔄 Attempt {attempt + 1}/{max_retries} with timeout {timeout}s: {url}")
                
                # Try HTTPS first if URL is HTTP
                if url.startswith('http://'):
                    https_url = url.replace('http://', 'https://')
                    try:
                        print(f"  🔒 Trying HTTPS...")
                        response = requests.get(
                            https_url, 
                            headers=self.headers, 
                            timeout=timeout, 
                            verify=False,
                            allow_redirects=True
                        )
                        if response.status_code == 200:
                            print(f"✅ HTTPS successful after {timeout}s!")
                            return response
                    except Exception as e:
                        print(f"  ⚠️ HTTPS failed: {e}")
                
                print(f"  🌐 Trying HTTP...")
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    timeout=timeout,
                    allow_redirects=True
                )
                if response.status_code == 200:
                    print(f"✅ HTTP successful after {timeout}s!")
                    return response
                else:
                    print(f"  ❌ HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"  ⏰ Timeout after {timeout}s")
            except requests.exceptions.ConnectionError as e:
                print(f"  🔌 Connection error: {e}")
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Request error: {e}")
            except Exception as e:
                print(f"  ❌ Other error: {e}")
            
            if attempt < max_retries - 1:
                delay = base_delay * (attempt + 2)
                print(f"  😴 Waiting {delay}s before retry...")
                time.sleep(delay)
        
        print(f"❌ All {max_retries} attempts failed for {url}")
        return None