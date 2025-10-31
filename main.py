import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)
import sys
import asyncio
if sys.platform == "win32":
    import logging
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

import random
import string
import json
import os
from datetime import datetime
import sys
from faker import Faker
import pyautogui
import time
import math
import requests
import base64
import logging
import multiprocessing
from typing import Optional, Dict, List
import aiohttp
import asyncio
from concurrent.futures import ProcessPoolExecutor
import signal
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
import traceback
import urllib3
import subprocess
import socket
import socks
from http.server import HTTPServer, BaseHTTPRequestHandler
import select
import hashlib
import pygetwindow as gw
import warnings
# Kameleo SDK imports
from kameleo.local_api_client.kameleo_local_api_client import KameleoLocalApiClient
from kameleo.local_api_client.models.create_profile_request import CreateProfileRequest
from kameleo.local_api_client.models.proxy_choice import ProxyChoice
from kameleo.local_api_client.models.server import Server
from kameleo.local_api_client.models.proxy_connection_type import ProxyConnectionType
from kameleo.local_api_client.exceptions import ApiException, ServiceException
from multiprocessing import Manager

warnings.filterwarnings("ignore", category=ResourceWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hotmail_creator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class ProxyConfig:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = 'http'

class ProxyPool:
    def __init__(self, proxy_list: List[Dict[str, str]], manager):
        self.proxies = manager.list()
        self.lock = manager.Lock()
        self.proxy_usage_count = manager.dict()
        self.current_proxy_index = manager.Value('i', 0)
        self._load_proxies(proxy_list)
        
    def _load_proxies(self, proxy_list: List[Dict[str, str]]):
        logger.info(f"[DEBUG] Loading {len(proxy_list)} proxies...")
        for i, proxy in enumerate(proxy_list):
            try:
                logger.info(f"[DEBUG] Processing proxy {i+1}: {proxy}")
                # Handle different proxy formats
                if isinstance(proxy, str):
                    # Handle URL format like "socks5://user:pass@host:port" or "socks5://host:port:user:pass"
                    if '://' in proxy:
                        # Parse URL format
                        protocol_part, rest = proxy.split('://', 1)
                        protocol_part = protocol_part.strip().lstrip(';').strip()
                        logger.info(f"[DEBUG] URL format detected - protocol: {protocol_part}, rest: {rest}")
                        
                        # Check if it's the standard format with @ symbol
                        if '@' in rest:
                            # Standard format: socks5://username:password@host:port
                            auth_part, host_port = rest.rsplit('@', 1)
                            logger.info(f"[DEBUG] Standard format - auth: {auth_part}, host_port: {host_port}")
                            # Split auth_part on last : to handle passwords with colons
                            if ':' in auth_part:
                                username, password = auth_part.rsplit(':', 1)
                            else:
                                username = auth_part
                                password = None
                            host, port = host_port.split(':', 1)
                        else:
                            # Non-standard format: socks5://host:port:username:password
                            logger.info(f"[DEBUG] Non-standard format detected")
                            # Split on colons and handle the last two parts as username:password
                            parts = rest.split(':')
                            if len(parts) >= 4:
                                # Extract host, port, username, password
                                host = parts[0]
                                port = parts[1]
                                # Join all remaining parts except the last one as username
                                username = ':'.join(parts[2:-1])
                                password = parts[-1]
                            elif len(parts) == 3:
                                # Format: host:port:username (no password)
                                host, port, username = parts
                                password = None
                            elif len(parts) == 2:
                                # Format: host:port (no authentication)
                                host, port = parts
                                username = password = None
                            else:
                                logger.error(f"[DEBUG] Invalid proxy format: {proxy}")
                                continue
                        
                        proxy_config = ProxyConfig(
                            host=host.strip(),
                            port=int(port.strip()),
                            username=username.strip() if username else None,
                            password=password.strip() if password else None,
                            protocol=protocol_part.strip()
                        )
                        
                        logger.info(f"[DEBUG] Parsed proxy: {proxy_config.protocol}://{proxy_config.host}:{proxy_config.port} (user: {proxy_config.username}, pass: {'*' * len(proxy_config.password) if proxy_config.password else 'None'})")
                    else:
                        # Handle simple format like "host:port:user:pass"
                        logger.info(f"[DEBUG] Simple format detected: {proxy}")
                        parts = proxy.split(':')
                        if len(parts) >= 4: # Allow for colons in password
                            host = parts[0]
                            port = parts[1]
                            username = parts[2]
                            password = ':'.join(parts[3:]) # Join the rest for the password
                            proxy_config = ProxyConfig(
                                host=host.strip(),
                                port=int(port.strip()),
                                username=username.strip(),
                                password=password.strip(),
                                protocol='http'  # Default to HTTP
                            )
                        elif len(parts) == 2:
                            host, port = parts
                            proxy_config = ProxyConfig(
                                host=host.strip(),
                                port=int(port.strip()),
                                protocol='http'  # Default to HTTP
                            )
                        else:
                            logger.error(f"[DEBUG] Invalid proxy format: {proxy}")
                            continue
                elif isinstance(proxy, dict):
                    proxy_config = ProxyConfig(
                        host=proxy.get('host'),
                        port=int(proxy.get('port')),
                        username=proxy.get('username'),
                        password=proxy.get('password'),
                        protocol='http'  # <-- Use HTTP everywhere as all proxies are HTTP
                    )
                else:
                    logger.error(f"[DEBUG] Invalid proxy format: {proxy}")
                    continue
                
                self.proxies.append(proxy_config)
                logger.info(f"[DEBUG] Successfully loaded proxy {i+1}: {proxy_config.protocol}://{proxy_config.host}:{proxy_config.port}")
                
            except Exception as e:
                logger.error(f"[DEBUG] Error loading proxy {i+1} ({proxy}): {str(e)}")
                logger.error(f"[DEBUG] Error details: {traceback.format_exc()}")
        
        if not self.proxies:
            logger.warning("[DEBUG] No valid proxies loaded!")
        else:
            logger.info(f"[DEBUG] Successfully loaded {len(self.proxies)} proxies")
            for i, proxy in enumerate(self.proxies):
                logger.info(f"[DEBUG] Proxy {i+1}: {proxy.protocol}://{proxy.host}:{proxy.port} (user: {proxy.username}, pass: {'*' * len(proxy.password) if proxy.password else 'None'})")
    
    def get_all_proxies(self):
        with self.lock:
            return list(self.proxies)

    def is_empty(self):
        with self.lock:
            return len(self.proxies) == 0
    
    async def validate_proxy(self, proxy: ProxyConfig) -> bool:
        """Test if a proxy is working by making a test request"""
        try:
            import aiohttp
            
            # Create proxy URL
            if proxy.username and proxy.password:
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
            
            # Test with a simple request
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=False)
            
            # Custom headers to avoid 417 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
                async with session.get(
                    'http://httpbin.org/ip',
                    proxy=proxy_url,
                    timeout=timeout,
                    expect100=False
                ) as response:
                    if response.status == 200:
                        logger.info(f"Proxy {proxy.host}:{proxy.port} is working")
                        return True
                    else:
                        logger.warning(f"Proxy {proxy.host}:{proxy.port} returned status {response.status}")
                        return False
                        
        except Exception as e:
            logger.warning(f"Proxy {proxy.host}:{proxy.port} validation failed: {str(e)}")
            return False
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        with self.lock:
            if not self.proxies:
                return None
            
            import time
            current_time = time.time()
            failed_proxies = getattr(self, 'failed_proxies', {})
            retry_delay = 300  # Retry failed proxies after 5 minutes
            
            # Try to find a proxy that's not recently failed
            attempts = 0
            max_attempts = len(self.proxies) * 2  # Allow cycling through all proxies twice
            
            while attempts < max_attempts:
                # Round-robin rotation
                proxy = self.proxies[self.current_proxy_index.value]
                self.current_proxy_index.value = (self.current_proxy_index.value + 1) % len(self.proxies)
                
                proxy_id = f"{proxy.host}:{proxy.port}"
                
                # Check if this proxy was recently failed
                if proxy_id in failed_proxies:
                    time_since_failed = current_time - failed_proxies[proxy_id]
                    if time_since_failed < retry_delay:
                        attempts += 1
                        continue  # Try next proxy
                    else:
                        # Enough time passed, remove from failed list and use this proxy
                        del failed_proxies[proxy_id]
                
                # Track usage
                self.proxy_usage_count[proxy_id] = self.proxy_usage_count.get(proxy_id, 0) + 1
                
                return proxy
            
            # If all proxies are recently failed, just return the next one anyway
            # (Better to try a potentially failed proxy than to have no proxy at all)
            proxy = self.proxies[self.current_proxy_index.value]
            self.current_proxy_index.value = (self.current_proxy_index.value + 1) % len(self.proxies)
            
            proxy_id = f"{proxy.host}:{proxy.port}"
            self.proxy_usage_count[proxy_id] = self.proxy_usage_count.get(proxy_id, 0) + 1
            
            print(f"[PROXY POOL] All proxies recently failed, retrying proxy: {proxy.host}:{proxy.port}")
            return proxy
    
    def mark_proxy_failed(self, proxy: ProxyConfig):
        with self.lock:
            # DON'T REMOVE PROXIES - just mark them as temporarily failed
            # This ensures we always have proxies available for cycling
            proxy_id = f"{proxy.host}:{proxy.port}"
            if not hasattr(self, 'failed_proxies'):
                self.failed_proxies = {}
            
            import time
            self.failed_proxies[proxy_id] = time.time()
            logger.warning(f"Marked proxy as temporarily failed: {proxy.host}:{proxy.port} (will retry later)")
    
    def get_working_proxy(self) -> Optional[ProxyConfig]:
        """Get a working proxy by testing available ones"""
        with self.lock:
            if not self.proxies:
                logger.warning("[DEBUG] No proxies available in pool")
                return None
            
            logger.info(f"[DEBUG] Looking for working proxy from {len(self.proxies)} available proxies")
            
            # Try up to 3 proxies
            for attempt in range(min(3, len(self.proxies))):
                proxy = self.proxies[self.current_proxy_index.value]
                self.current_proxy_index.value = (self.current_proxy_index.value + 1) % len(self.proxies)
                
                logger.info(f"[DEBUG] Trying proxy {attempt + 1}: {proxy.protocol}://{proxy.host}:{proxy.port}")

                if proxy.protocol.lower() not in ['http', 'https']:
                    logger.warning(f"[DEBUG] Skipping proxy with unsupported protocol: {proxy.protocol}")
                    continue
                
                # Only test HTTP proxies
                try:
                    import requests
                    proxy_dict = {
                        'http': f'{proxy.protocol}://{proxy.host}:{proxy.port}',
                        'https': f'{proxy.protocol}://{proxy.host}:{proxy.port}'
                    }
                    if proxy.username and proxy.password:
                        proxy_dict['http'] = f'{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}'
                        proxy_dict['https'] = f'{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}'
                    
                    logger.info(f"[DEBUG] Testing HTTP proxy with dict: {proxy_dict}")
                    response = requests.get('https://httpbin.org/ip', proxies=proxy_dict, timeout=5, verify=False)
                    if response.status_code == 200:
                        logger.info(f"[DEBUG] Found working HTTP proxy: {proxy.host}:{proxy.port}")
                        logger.info(f"[DEBUG] Response: {response.text}")
                        return proxy
                    else:
                        logger.warning(f"[DEBUG] HTTP proxy {proxy.host}:{proxy.port} failed with status {response.status_code}")
                except Exception as e:
                    logger.warning(f"[DEBUG] HTTP proxy {proxy.host}:{proxy.port} test failed: {str(e)}")
                    continue
            
            logger.warning("[DEBUG] No working proxies found after testing")
            return None
    
    def reset_failed_proxies(self):
        """Reset failed proxy list to retry all proxies"""
        with self.lock:
            if hasattr(self, 'failed_proxies'):
                failed_count = len(self.failed_proxies)
                self.failed_proxies.clear()
                print(f"[PROXY POOL] Reset {failed_count} failed proxies - all proxies available again")
    
    def get_proxy_usage_stats(self) -> Dict:
        """Get detailed proxy usage statistics"""
        with self.lock:
            total_assignments = sum(self.proxy_usage_count.values())
            unique_proxies_used = len(self.proxy_usage_count)
            failed_count = len(getattr(self, 'failed_proxies', {}))
            return {
                "total_proxies": len(self.proxies),
                "total_assignments": total_assignments,
                "unique_proxies_used": unique_proxies_used,
                "failed_proxies": failed_count,
                "usage_per_proxy": dict(self.proxy_usage_count),
                "rotation_efficiency": (unique_proxies_used / total_assignments * 100) if total_assignments > 0 else 100
            }

class HotmailAccountCreator:
    def __init__(self, proxy_pool: Optional[ProxyPool] = None, use_proxies: bool = False, account_type: str = 'hotmail', headless: bool = False):
        self.fake = Faker()
        self.proxy_pool = proxy_pool
        self.use_proxies = use_proxies
        self.account_type = account_type
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.current_proxy = None
        self.kameleo_client = None
        self.kameleo_profile_id = None
        self.current_email = None
        self.current_password = None
        self.local_proxy_server = None
        self.local_proxy_port = None
        self.local_proxy_process = None
        self.max_retries = 3
        self.funcaptcha_server = "http://localhost:5000"
        self.account_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.port = None
        self.credentials_file = "accounts.json"
        self.headless = headless  # <-- Headless mode toggle
        self._focus_task = None   # <-- For periodic focus
        Path('credentials').mkdir(exist_ok=True)

    def find_free_port(self):
        """Find a free port for local proxy server"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def start_socks5_tunnel(self, socks5_proxy):
        """Start a SOCKS5-to-HTTP tunnel using external script"""
        try:
            # Find a free port for the tunnel
            self.local_proxy_port = self.find_free_port()
            
            logger.info(f"[DEBUG] Starting SOCKS5 tunnel on port {self.local_proxy_port}")
            logger.info(f"[DEBUG] SOCKS5 proxy details: {socks5_proxy.host}:{socks5_proxy.port}")
            logger.info(f"[DEBUG] Username: {socks5_proxy.username}")
            logger.info(f"[DEBUG] Password: {'*' * len(socks5_proxy.password) if socks5_proxy.password else 'None'}")
            
            # Start tunnel using external script
            tunnel_cmd = [
                sys.executable, 
                'socks5_tunnel.py',
                str(self.local_proxy_port),
                socks5_proxy.host,
                str(socks5_proxy.port),
                socks5_proxy.username,
                socks5_proxy.password
            ]
            
            logger.info(f"[DEBUG] Tunnel command: {' '.join(tunnel_cmd)}")
            
            self.local_proxy_process = subprocess.Popen(
                tunnel_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for tunnel to start
            time.sleep(3)
            
            # Check if tunnel process is still running
            if self.local_proxy_process.poll() is None:
                logger.info(f"[DEBUG] Tunnel process started successfully (PID: {self.local_proxy_process.pid})")
            else:
                stdout, stderr = self.local_proxy_process.communicate()
                logger.error(f"[DEBUG] Tunnel process failed to start")
                logger.error(f"[DEBUG] stdout: {stdout.decode()}")
                logger.error(f"[DEBUG] stderr: {stderr.decode()}")
                return False
            
            # Test the tunnel with a simple request
            try:
                import requests
                test_response = requests.get(
                    'http://httpbin.org/ip',
                    proxies={'http': f'http://localhost:{self.local_proxy_port}', 'https': f'http://localhost:{self.local_proxy_port}'},
                    timeout=10
                )
                logger.info(f"[DEBUG] Tunnel test response: {test_response.text}")
                if test_response.status_code == 200:
                    logger.info(f"[DEBUG] Tunnel test successful!")
                else:
                    logger.warning(f"[DEBUG] Tunnel test failed with status {test_response.status_code}")
            except Exception as e:
                logger.warning(f"[DEBUG] Tunnel test failed: {str(e)}")
            
            logger.info(f"Started SOCKS5-to-HTTP tunnel on port {self.local_proxy_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start SOCKS5 tunnel: {str(e)}")
            return False

    def stop_local_proxy_server(self):
        """Stop the local proxy server"""
        if self.local_proxy_process:
            try:
                self.local_proxy_process.terminate()
                self.local_proxy_process.wait(timeout=5)
                logger.info("Local proxy server stopped")
            except Exception as e:
                logger.warning(f"Error stopping local proxy server: {str(e)}")
                try:
                    self.local_proxy_process.kill()
                except:
                    pass
            finally:
                self.local_proxy_process = None
                self.local_proxy_port = None

    def get_random_fingerprint(self):
        """Generate a realistic, randomized browser fingerprint."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        ]
        timezones = ["America/New_York", "Europe/London", "Asia/Kolkata", "America/Los_Angeles"]
        locales = ["en-US", "en-GB", "en-CA", "en-AU"]
        viewports = [
            {"width": 1280, "height": 800},
            {"width": 1366, "height": 768},
            {"width": 1920, "height": 1080},
            {"width": 1536, "height": 864},
        ]
        return {
            "user_agent": random.choice(user_agents),
            "timezone": random.choice(timezones),
            "locale": random.choice(locales),
            "viewport": random.choice(viewports),
        }

    async def save_cookies(self, context, cookies_path):
        cookies = await context.cookies()
        with open(cookies_path, "w") as f:
            json.dump(cookies, f)

    async def load_cookies(self, context, cookies_path):
        if os.path.exists(cookies_path):
            with open(cookies_path, "r") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)

    def create_mostlogin_profile(self, assigned_proxy=None):
        """Create a new MostLogin profile directory"""
        try:
            # Generate unique profile ID
            import uuid
            profile_id = str(uuid.uuid4())
            profile_path = os.path.join(self.mostlogin_base_dir, f"profile_{profile_id}")
            
            # Create profile directory
            os.makedirs(profile_path, exist_ok=True)
            
            # Create basic Chrome profile structure
            os.makedirs(os.path.join(profile_path, "Default"), exist_ok=True)
            
            # Create preferences file with proxy settings if provided
            preferences = {
                "profile": {
                    "default_content_setting_values": {
                        "geolocation": 1,
                        "notifications": 2
                    },
                    "managed_user_id": "",
                    "name": f"Profile_{profile_id[:8]}"
                },
                "browser": {
                    "check_default_browser": False,
                    "show_home_button": False
                }
            }
            
            # Add proxy configuration if provided
            if assigned_proxy:
                # For Kameleo Playwright, proxy is handled via the Kameleo profile, not here
                pass
            
            # Save preferences
            prefs_path = os.path.join(profile_path, "Default", "Preferences")
            with open(prefs_path, 'w') as f:
                json.dump(preferences, f, indent=2)
            
            print(f"[MOSTLOGIN] Created profile directory: {profile_path}")
            return profile_path
            
        except Exception as e:
            print(f"[MOSTLOGIN] Error creating profile: {e}")
            return None

    async def test_proxy_connectivity(self, proxy: ProxyConfig, timeout=5) -> bool:
        """Test if a proxy is working by making a test request to https://httpbin.org/ip"""
        try:
            import aiohttp
            if proxy.username and proxy.password:
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
            
            print(f"[PROXY TEST] Testing proxy: {proxy_url}")
            
            # Use shorter timeout for faster failure detection
            timeout_obj = aiohttp.ClientTimeout(total=timeout, connect=3)
            connector = aiohttp.TCPConnector(ssl=False, limit=1, limit_per_host=1)
            
            # Custom headers to avoid 417 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            async with aiohttp.ClientSession(timeout=timeout_obj, connector=connector, headers=headers) as session:
                async with session.get('http://httpbin.org/ip', proxy=proxy_url, timeout=timeout_obj, expect100=False) as response:
                    if response.status == 200:
                        print(f"[PROXY TEST] ✅ Proxy {proxy.host}:{proxy.port} is working!")
                        return True
                    else:
                        print(f"[PROXY TEST] ❌ Proxy {proxy.host}:{proxy.port} returned status {response.status}")
                        return False
        except asyncio.TimeoutError:
            print(f"[PROXY TEST] ❌ Proxy {proxy.host}:{proxy.port} timed out")
            return False
        except Exception as e:
            print(f"[PROXY TEST] ❌ Proxy {proxy.host}:{proxy.port} failed: {str(e)[:100]}")
            return False

    async def setup_mostlogin_browser(self, assigned_proxy=None, profile_semaphore=None):
        """Setup MostLogin browser with Playwright via Kameleo (robust, official pattern)"""
        try:
            print(f"[MOSTLOGIN] 🚀 SETTING UP MOSTLOGIN BROWSER VIA KAMELEO SDK...")
            # --- ENFORCE USERNAME AND PASSWORD ---
            if not assigned_proxy or not assigned_proxy.username or not assigned_proxy.password:
                raise ValueError(f"Proxy {assigned_proxy.host}:{assigned_proxy.port} must have both username and password.")
            # --- PRE-KAMELEO PROXY TEST ---
            print(f"[PROXY TEST] Testing proxy before Kameleo profile creation: {assigned_proxy.protocol}://{assigned_proxy.host}:{assigned_proxy.port}")
            is_working = await self.test_proxy_connectivity(assigned_proxy)
            if not is_working:
                print(f"[PROXY TEST] Proxy {assigned_proxy.host}:{assigned_proxy.port} is not working. Skipping.")
                if self.proxy_pool:
                    self.proxy_pool.mark_proxy_failed(assigned_proxy)
                return False
            else:
                print(f"[PROXY TEST] Proxy {assigned_proxy.host}:{assigned_proxy.port} is working. Proceeding with Kameleo profile creation.")
            # --- END PRE-KAMELEO PROXY TEST ---

            # Ensure Playwright is initialized
            if not self.playwright:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()

            # Create Kameleo client
            from kameleo.local_api_client.kameleo_local_api_client import KameleoLocalApiClient
            from kameleo.local_api_client.models.create_profile_request import CreateProfileRequest
            client = KameleoLocalApiClient()

            # Search for a fingerprint
            fingerprints = client.fingerprint.search_fingerprints(device_type='desktop', browser_product='chrome')
            if not fingerprints:
                raise Exception("No fingerprints available")
            fingerprint = random.choice(fingerprints)
            print(f"[KAMELEO] Selected fingerprint: {fingerprint.id}")

            # Build proxy dict for Kameleo (with 'extra' field for compatibility)
            from kameleo.local_api_client.models.proxy_choice import ProxyChoice
            from kameleo.local_api_client.models.server import Server
            # Map protocol string to enum
            protocol_map = {
                "http": ProxyConnectionType.HTTP,
                "https": ProxyConnectionType.HTTP,  # HTTPS proxies are handled as HTTP in Kameleo
                "socks5": ProxyConnectionType.SOCKS5,
            }
            protocol = assigned_proxy.protocol.strip().lower() if assigned_proxy.protocol else "http"
            proxy_type = protocol_map.get(protocol, ProxyConnectionType.HTTP)  # Default to HTTP

            # Strip all string fields and ensure port is int
            host = assigned_proxy.host.strip() if assigned_proxy.host else None
            port = int(str(assigned_proxy.port).strip()) if assigned_proxy.port else None
            username = assigned_proxy.username.strip() if assigned_proxy.username else None
            password = assigned_proxy.password.strip() if assigned_proxy.password else None

            # Print debug info
            proxy = ProxyChoice(
                value=proxy_type,
                extra=Server(
                    host=host,
                    port=port,
                    id=username,
                    secret=password
                )
            )

            # Create the profile request
            create_profile_request = CreateProfileRequest(
                fingerprint_id=str(fingerprint.id),
                proxy=proxy
            )
            profile = client.profile.create_profile(create_profile_request)
            # Store references for cleanup
            self.kameleo_client = client
            self.kameleo_profile_id = profile.id

            # Start the profile
            client.profile.start_profile(profile.id)

            # Wait for profile to reach 'running' state, with timeout
            max_wait = 60  # seconds (increased from 30)
            interval = 2   # seconds
            waited = 0
            while waited < max_wait:
                profile_status = client.profile.read_profile(profile.id)
                lifetime_state = None
                if hasattr(profile_status, 'status') and hasattr(profile_status.status, 'lifetime_state'):
                    lifetime_state = profile_status.status.lifetime_state
                if (isinstance(lifetime_state, str) and lifetime_state == "running") or \
                   (hasattr(lifetime_state, 'value') and lifetime_state.value == "running") or \
                   (str(lifetime_state) == "ProfileLifetimeState.RUNNING"):
                    break
                await asyncio.sleep(interval)
                waited += interval
            else:
                try:
                    client.profile.delete_profile(profile.id)
                except Exception as e:
                    pass
                if self.proxy_pool and assigned_proxy:
                    self.proxy_pool.mark_proxy_failed(assigned_proxy)
                return False

            # Connect Playwright to the running profile
            playwright_url = f"ws://localhost:5050/playwright/{profile.id}"
            # Note: Kameleo's CDP connection does not support headless mode directly, but we keep the toggle for future use or for non-Kameleo flows.
            self.browser = await self.playwright.chromium.connect_over_cdp(playwright_url)
            self.context = self.browser
            self.page = await self.context.new_page()
            # Start periodic focus task
            if self._focus_task is None:
                self._focus_task = asyncio.create_task(self._periodic_focus())

            return True

        except Exception as e:
            return False

    async def _periodic_focus(self):
        try:
            while True:
                await asyncio.sleep(10)  # Every 10 seconds
                await self.ensure_window_focus()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            pass

    async def setup_browser(self, port=None):
        try:
            if self.current_proxy:
                proxy_id = f"{self.current_proxy.host}:{self.current_proxy.port}"
                # Store proxy info for verification
                self._browser_proxy_id = proxy_id
                self._browser_proxy_config = self.current_proxy
            else:
                self._browser_proxy_id = None
                self._browser_proxy_config = None
            
            # Create the browser with assigned proxy
            result = await self.setup_mostlogin_browser(self.current_proxy)
            
            return result
        except Exception as e:
            return False
    
    async def verify_proxy_assignment(self):
        """Verify that the browser is actually using the assigned proxy"""
        if not self.page or not self.current_proxy:
            return False
        
        try:
            # Test IP to verify proxy is working
            try:
                response = await self.page.goto("https://httpbin.org/ip", wait_until="domcontentloaded", timeout=15000)
                if response and response.ok:
                    ip_info = await self.page.evaluate("() => document.body.textContent")
                    current_ip = ip_info.strip()
                    return True
                else:
                    return False
            except Exception as e:
                return False
                
        except Exception as e:
            return False

    async def simulate_mouse_movements(self):
        if not self.page:
            return
        while True:
            try:
                viewport = await self.page.evaluate("""() => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    }
                }""")
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                await self.page.mouse.move(x, y)
                await self.random_sleep(0.5, 2)
            except Exception:
                break

    def generate_random_password(self, length=None):
        # Generate random length between 8-10 characters
        if length is None:
            length = random.randint(8, 10)
        
        # Use only alphanumeric characters (letters and numbers)
        characters = string.ascii_letters + string.digits
        
        # Generate password with alphanumeric characters only
        password = ''.join(random.choice(characters) for _ in range(length))
        
        # Add a small random number to ensure uniqueness without exceeding length limit
        unique_suffix = str(random.randint(0, 99)).zfill(2)
        password = password[:-2] + unique_suffix
        
        return password

    def generate_random_username(self):
        """Generate a random username that's more likely to be eligible"""
        first_names = ['john', 'jane', 'mike', 'sarah', 'david', 'emma', 'alex', 'lisa', 'tom', 'anna']
        words = ['happy', 'sunny', 'cool', 'smart', 'bright', 'quick', 'fast', 'wise', 'brave', 'calm']
        adjectives = ['super', 'mega', 'ultra', 'hyper', 'pro', 'elite', 'prime', 'alpha', 'beta', 'delta']
        
        # Generate random components
        random_name = random.choice(first_names)
        random_word = random.choice(words)
        random_adj = random.choice(adjectives)
        random_number = random.randint(100, 9999)
        random_letters = ''.join(random.choices(string.ascii_lowercase, k=random.randint(2, 4)))
        random_underscores = '__'  # Fixed two underscores
        
        # Create username patterns with two underscores
        username_patterns = [
            f"{random_name}{random_underscores}{random_word}{random_number}",
            f"{random_word}{random_underscores}{random_name}{random_number}",
            f"{random_adj}{random_underscores}{random_name}{random_number}",
            f"{random_name}{random_underscores}{random_adj}{random_number}",
            f"{random_word}{random_underscores}{random_adj}{random_number}",
            f"{random_adj}{random_underscores}{random_word}{random_number}",
            f"{random_name}{random_letters}{random_underscores}{random_number}",
            f"{random_word}{random_letters}{random_underscores}{random_number}",
            f"{random_adj}{random_letters}{random_underscores}{random_number}",
            f"{random_letters}{random_underscores}{random_name}{random_number}",
            f"{random_letters}{random_underscores}{random_word}{random_number}",
            f"{random_letters}{random_underscores}{random_adj}{random_number}",
            f"{random_name}{random_underscores}{random_letters}{random_number}",
            f"{random_word}{random_underscores}{random_letters}{random_number}",
            f"{random_adj}{random_underscores}{random_letters}{random_number}",
        ]
        
        # Add more complex patterns
        complex_patterns = [
            f"{random_name}{random_underscores}{random_word}{random_letters}{random_number}",
            f"{random_word}{random_underscores}{random_name}{random_letters}{random_number}",
            f"{random_adj}{random_underscores}{random_name}{random_letters}{random_number}",
            f"{random_name}{random_letters}{random_underscores}{random_word}{random_number}",
            f"{random_word}{random_letters}{random_underscores}{random_name}{random_number}",
            f"{random_adj}{random_letters}{random_underscores}{random_name}{random_number}",
        ]
        
        # Combine all patterns
        all_patterns = username_patterns + complex_patterns
        
        # Select a random pattern
        username = random.choice(all_patterns)
        
        # Ensure username length is between 5 and 20 characters
        while len(username) < 5 or len(username) > 20:
            username = random.choice(all_patterns)
        
        # Add timestamp to make it even more unique
        timestamp = int(time.time() * 1000) % 10000
        username = f"{username}{timestamp}"
        
        # Ensure final length is still within limits
        if len(username) > 20:
            username = username[:20]
        
        return username

    def save_credentials(self, email, password, client_id=None, refresh_token=None):
        """Save credentials in the format: email:password:creation_date"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            os.makedirs('credentials', exist_ok=True)
            if '@hotmail.com' in email:
                filename = 'hotmail_accounts.txt'
            elif '@outlook.com' in email:
                filename = 'outlook_accounts.txt'
            else:
                filename = 'other_accounts.txt'
            file_path = os.path.join('credentials', filename)
            # Save only email, password, and creation date
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"{email}:{password}:{created_at}\n")
                f.flush()
            print("saved")
            return True
        except Exception as e:
            return False

    async def random_sleep(self, min_seconds=0.2, max_seconds=0.5):
        """Optimized random sleep with shorter default delays (30% faster)"""
        min_s = min_seconds * 0.7
        max_s = max_seconds * 0.7
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def ensure_window_focus(self):
        """
        Ensure browser window stays focused for background automation.
        This is called before every major interaction and also periodically in the background.
        """
        try:
            if self.page:
                # Bring browser to front
                await self.page.bring_to_front()
                
                # Use JavaScript to maintain focus
                await self.page.evaluate("""
                    () => {
                        // Force window focus
                        window.focus();
                        
                        // Ensure document is visible and active (with error handling)
                        if (document.hidden) {
                            try {
                                Object.defineProperty(document, 'hidden', {
                                    get: () => false,
                                    configurable: true
                                });
                            } catch(e) {
                                // Property already defined, skip
                            }
                            
                            try {
                                Object.defineProperty(document, 'visibilityState', {
                                    get: () => 'visible',
                                    configurable: true
                                });
                            } catch(e) {
                                // Property already defined, skip
                            }
                        }
                        
                        // Dispatch focus events to ensure page knows it's active
                        window.dispatchEvent(new Event('focus'));
                        document.dispatchEvent(new Event('visibilitychange'));
                    }
                """)
                
                # Additional system-level window focusing (Windows specific)
                try:
                    import pygetwindow as gw
                    # Find MostLogin browser windows
                    windows = gw.getWindowsWithTitle('Chrome')
                    if windows:
                        for window in windows:
                            if not window.isMinimized:
                                window.activate()
                                break
                except Exception:
                    pass  # System-level focusing is optional
                    
        except Exception as e:
            # Don't let focusing issues stop the automation
            pass

    async def find_first_selector(self, selectors, frame=None, timeout=3000):
        if not self.page:
            pass
            return None
        search_context = frame if frame else self.page
        for selector in selectors:
            try:
                el = await search_context.wait_for_selector(selector, timeout=timeout)
                if el:
                    return el
            except Exception:
                continue
        return None

 

    async def handle_name_page(self):
        if not self.page:
            return
        try:
            # CRITICAL: Ensure window focus for background automation
            await self.ensure_window_focus()

            # Generate realistic names with validation
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            # OPTIMIZED: Quick page reading simulation
            await asyncio.sleep(random.uniform(1.0, 2.5))

            # Try multiple selectors for first name field
            first_name_selectors = [
                '#firstNameInput',
                'input[name="FirstName"]',
                'input[aria-label*="First name"]',
                'input[placeholder*="First name"]',
                'input[class*="first"]',
                'input[type="text"]',
                'input',
            ]

            first_name_field = await self.find_first_selector(first_name_selectors, timeout=8000)
            if not first_name_field:
                return False

            # --- Human-like label interaction ---
            await self.simulate_label_interaction(first_name_field, "first name", self.page)
            await asyncio.sleep(random.uniform(0.2, 0.4))

            # Type first name with human-like typing
            await self.human_type(first_name_field, first_name)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Simulate field validation (user checks what they typed)
            await self.simulate_field_validation_behavior(first_name_field, first_name, self.page)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Short pause between fields
            await asyncio.sleep(random.uniform(0.3, 0.7))

            # Try multiple selectors for last name field
            last_name_selectors = [
                '#lastNameInput',
                'input[name="LastName"]',
                'input[aria-label*="Last name"]',
                'input[placeholder*="Last name"]',
                'input[class*="last"]',
                'input[type="text"]',
                'input',
            ]

            last_name_field = await self.find_first_selector(last_name_selectors, timeout=5000)
            if not last_name_field:
                return False

            # --- Human-like label interaction ---
            await self.simulate_label_interaction(last_name_field, "last name", self.page)
            await asyncio.sleep(random.uniform(0.2, 0.4))

            # Type last name with human-like typing
            await self.human_type(last_name_field, last_name)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Simulate field validation (user checks what they typed)
            await self.simulate_field_validation_behavior(last_name_field, last_name, self.page)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Quick form review (mouse movement, micro-pause)
            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            for _ in range(random.randint(1, 2)):
                x = random.randint(50, viewport['width'] - 50)
                y = random.randint(200, viewport['height'] - 100)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))

            # Find next button
            next_button_selectors = [
                'button:has-text("Next")',
                '#iSignupAction',
                'button[type="submit"]',
                'button[class*="next"]',
                'button[class*="submit"]',
                'button[class*="primary"]',
                'input[type="submit"]',
            ]

            next_button = await self.find_first_selector(next_button_selectors, timeout=5000)
            if not next_button:
                return False

            # Quick pre-submission check (hover, micro-pause)
            box = await next_button.bounding_box()
            if box:
                await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                await asyncio.sleep(random.uniform(0.2, 0.4))

            # Click submit button
            await self.human_click(next_button)

            # Minimal post-submission waiting
            await asyncio.sleep(random.uniform(1.0, 2.0))

            # Handle the captcha
            if not await self.handle_captcha_page():
                return False

            return True

        except Exception as e:
            return False

    async def handle_country_and_date_fields(self):
        if not self.page:
            return
        try:
            # CRITICAL: Ensure window focus for background automation
            await self.ensure_window_focus()
            
            # Skip country selection since Nepal is default
            await self.random_sleep(0.2, 0.5)

            # Helper for selecting month and day (from auto_hotmail_creator10.py)
            async def select_month_and_day(page):
                try:
                    await page.wait_for_selector("#BirthMonthDropdown", timeout=10000)
                    await page.locator("#BirthMonthDropdown").scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    try:
                        await page.locator("#BirthMonthDropdown").click(force=True)
                    except Exception as e:
                        return False

                    await page.wait_for_selector("#fluent-option293", timeout=5000)
                    await page.locator("#fluent-option293").click(force=True)
                    await asyncio.sleep(0.5)

                    await page.wait_for_selector("#BirthDayDropdown", timeout=10000)
                    await page.locator("#BirthDayDropdown").scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    try:
                        await page.locator("#BirthDayDropdown").click(force=True)
                    except Exception as e:
                        return False

                    await page.wait_for_selector("#fluent-option305", timeout=5000)
                    await page.locator("#fluent-option305").click(force=True)
                    await asyncio.sleep(0.5)
                    return True
                except Exception as e:
                    return False

            # Select month and day
            if not await select_month_and_day(self.page):
                return False

            await self.random_sleep(1, 2)

            # Year input logic (from auto_hotmail_creator10.py)
            current_year = datetime.now().year
            birth_year = random.randint(current_year - 50, current_year - 20)
            year_input = await self.find_first_selector([
                'input#floatingLabelInput23',
                'input[name="BirthYear"]',
                'input[aria-label="Birth year"]',
                'input[type="number"]',
                'input[inputmode="numeric"]',
                'input[class*="fui-Input__input"]',
            ], timeout=5000)
            if year_input:
                try:
                    valid_year = max(1905, min(2025, birth_year))
                    await year_input.fill("")
                    await self.random_sleep(0.5, 1)
                    if hasattr(self, 'human_type'):
                        await self.human_type(year_input, str(valid_year))
                    else:
                        await year_input.type(str(valid_year))
                    input_value = await year_input.evaluate('el => el.value')
                    if str(input_value) != str(valid_year):
                        await year_input.evaluate(f'(el) => {{ el.value = "{valid_year}"; el.dispatchEvent(new Event("input")); el.dispatchEvent(new Event("change")); }}')
                        await self.random_sleep(1, 2)
                        input_value = await year_input.evaluate('el => el.value')
                        if str(input_value) != str(valid_year):
                            return False
                except Exception as e:
                    return False
            else:
                return False

            # After entering year, click the next button to proceed
            next_button_selectors = [
                '#iSignupAction',
                'button:has-text("Next")',
                'button[type="submit"]',
                'button[class*="next"]',
                'button[data-testid="next"]',
                'button[aria-label*="next"]',
                'button[aria-label*="Next"]',
                'button[title*="next"]',
                'button[title*="Next"]',
                'button[class*="submit"]',
                'button[class*="continue"]',
                'button[class*="primary"]',
                'button[id*="next"]',
                'button[id*="Next"]',
                'button[id*="submit"]',
                'button[id*="Submit"]',
            ]
            next_button = await self.find_first_selector(next_button_selectors, timeout=5000)
            if not next_button:
                return False
            try:
                await self.human_click(next_button)
            except Exception as e:
                return False
            await self.random_sleep(1, 2)

            return True

        except Exception as e:
            return False

    async def handle_captcha_page(self):
        if not self.page:
            return
        try:
            max_attempts = 3
            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                
                # Natural wait time for captcha to load
                await self.random_sleep(2.1, 4.7)
                
                # Try to find the iframe
                iframe_handle = await self.page.wait_for_selector('iframe[data-testid="humanCaptchaIframe"]', timeout=15000)
                if not iframe_handle:
                    if attempt == max_attempts:
                        pass
                    continue

                # Add a 3 second sleep after finding the iframe
               

                # Get iframe position and size for traditional positioning approach
                box = await iframe_handle.bounding_box()
                if not box:
                    if attempt == max_attempts:
                        pass
                    continue

                await asyncio.sleep(3)
                # Simulate realistic human behavior before clicking
                await self.simulate_human_browsing_behavior()
                
                # Use traditional positioning logic with modern enhancements
                # First click: 40% from top and 20% from left (same as traditional)
                click_x = box['x'] + (box['width'] * 0.2)  # 20% from left edge
                click_y = box['y'] + (box['height'] * 0.4)  # 40% from top edge
                
                # Perform first sophisticated click with traditional positioning
                if not await self.perform_sophisticated_click(click_x, click_y):
                    continue
                
                # Traditional timing: 8-10 seconds between clicks (same as original)
                await self.random_sleep(10, 12)
                
                # Second click: slightly to the right (same as traditional)
                second_click_x = click_x + (box['width'] * 0.1)  # 10% of iframe width to the right
                second_click_y = click_y  # Keep same vertical position
                
                # Perform second sophisticated click with traditional positioning
                if not await self.perform_sophisticated_click(second_click_x, second_click_y):
                    continue
                
                # Wait for page to change with realistic expectations
                try:
                    current_url = self.page.url

                    # Wait for any account.microsoft.com page
                    await self.page.wait_for_url(
                        lambda url: "account.microsoft.com" in url,
                        timeout=25000
                    )

                    # Handle OK button if present
                    ok_button = await self.find_first_selector([
                        'button:has-text("OK")',
                        'button:has-text("Ok")',
                        'button[class*="ok"]',
                        'button[class*="confirm"]',
                        'button:has-text("Accept")',
                        'button:has-text("Continue")',
                        'span:has-text("OK")',
                    ], timeout=10000)
                    if ok_button:
                        await self.human_click(ok_button)
                        return True
                    else:
                        return True

                except Exception:
                    continue
            return False
        except Exception as e:
            return False



    async def simulate_realistic_browsing(self, page):
        if not page:
            pass
            return
        """Simulate realistic browsing behavior on any page"""
        try:
            # Random scroll patterns like real users
            for _ in range(random.randint(2, 5)):
                scroll_amount = random.randint(-200, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.8, 2.3))
            
            # Random mouse movements
            for _ in range(random.randint(3, 8)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.2, 1.1))
                
            # Sometimes hover over elements
            if random.random() < 0.3:
                try:
                    links = await page.query_selector_all('a, button')
                    if links and len(links) > 0:
                        random_link = random.choice(links)
                        await random_link.hover()
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                except:
                    pass
                    
        except Exception as e:
            print(f"[STEALTH] Browsing simulation error: {e}")

    async def simulate_realistic_page_interaction(self, page):
        if not page:
            pass
            return
        try:
            print(f"[STEALTH] Simulating realistic page interaction...")
            
            # Look around the page like a real user
            await asyncio.sleep(random.uniform(2, 4))
            
            # Random scrolling to "read" the page
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(100, 300)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(1.2, 2.8))
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(1, 2))
            
            # Move mouse around like reading
            viewport = await page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            for _ in range(random.randint(5, 10)):
                x = random.randint(50, viewport['width'] - 50)
                y = random.randint(50, viewport['height'] - 50)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.3, 1.2))
            
            print(f"[STEALTH] Page interaction simulation completed")
            
        except Exception as e:
            print(f"[STEALTH] Page interaction error: {e}")

    async def simulate_human_browsing_behavior(self):
        if not self.page:
            return
        """Enhanced human behavior simulation for stealth"""
        try:
            # More realistic simulation patterns
            await asyncio.sleep(random.uniform(1.2, 3.5))
            
            # Realistic scroll patterns
            for _ in range(random.randint(1, 3)):
                scroll_amount = random.randint(-50, 150)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.8, 2.1))
            
            # Natural mouse movements
            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            for _ in range(random.randint(2, 5)):
                x = random.randint(50, viewport['width'] - 50)
                y = random.randint(50, viewport['height'] - 50)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.2, 0.9))
                
            await asyncio.sleep(random.uniform(0.5, 1.8))
            
        except Exception as e:
            pass  # Silent fail for robustness

    async def perform_sophisticated_click(self, target_x, target_y):
        if not self.page:
            return
        """Lightweight sophisticated click optimized for background execution - EXACT COPY FROM WORKING dhirendra.py"""
        try:
            # Minimal variance for traditional positioning
            variance_x = random.uniform(-2, 2)
            variance_y = random.uniform(-2, 2)
            final_x = target_x + variance_x
            final_y = target_y + variance_y
            
            # Simplified movement (reduced complexity for background)
            try:
                await self.page.mouse.move(final_x, final_y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            except:
                pass
            
            # Perform click with fallback methods
            click_success = False
            
            # Method 1: Direct mouse click
            try:
                await self.page.mouse.click(final_x, final_y, delay=random.randint(50, 120))
                click_success = True
            except:
                # Method 2: JavaScript click (fallback)
                try:
                    await self.page.evaluate(f"""
                        (() => {{
                            const event = new MouseEvent('click', {{
                                view: window,
                                bubbles: true,
                                cancelable: true,
                                clientX: {final_x},
                                clientY: {final_y}
                            }});
                            const element = document.elementFromPoint({final_x}, {final_y});
                            if (element) element.dispatchEvent(event);
                        }})();
                    """)
                    click_success = True
                except:
                    pass
            
            # Minimal post-click behavior
            if click_success:
                try:
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                    post_x = final_x + random.uniform(-2, 2)
                    post_y = final_y + random.uniform(-2, 2)
                    await self.page.mouse.move(post_x, post_y)
                except:
                    pass
            
            return click_success
            
        except Exception:
            return False





    async def handle_verification(self):
        if not self.page:
            return
        try:
            try:
                await self.page.wait_for_url(
                    lambda url: "privacynotice.account.microsoft.com" in url or "account.microsoft.com/notice" in url or "account.microsoft.com" in url,
                    timeout=60000
                )
            except Exception:
                return False

            # If the privacy notice dialog is displayed, click the "OK" button.
            try:
                max_attempts = 2  # Try twice: first attempt, then refresh and retry
                ok_button = None
                
                for attempt in range(max_attempts):
                    ok_button = await self.find_first_selector([
                        'button:has-text("OK")',
                        'span:has-text("OK")',
                        'button:has-text("Accept")',
                        'button:has-text("Continue")'
                    ], timeout=5000)

                    if ok_button:
                        await self.human_click(ok_button)
                        break
                    else:
                        if attempt < max_attempts - 1:  # If not the last attempt
                            try:
                                await self.page.reload(wait_until="domcontentloaded", timeout=20000)
                                await asyncio.sleep(2)  # Wait for page to fully load after refresh
                            except Exception as refresh_error:
                                break

            except Exception as e:
                pass

            # SAVE CREDENTIALS - After successful captcha verification
            if hasattr(self, 'current_email') and hasattr(self, 'current_password') and self.current_email and self.current_password:
                email = self.current_email
                password = self.current_password
                
                # Simple save - no complex error handling
                self.save_credentials(email, password)
                
                # Clear credentials from memory
                self.current_email = None
                self.current_password = None
                # Cleanup profile after saving credentials
                await self.cleanup()

            # Wait 5 seconds and return
            import asyncio
            await asyncio.sleep(5)
            return True

        except Exception as e:
            return False

    async def human_mouse_move(self, start, end, steps=20):
        if not self.page:
            return
        """Move mouse in a human-like way"""
        try:
            # Generate control points for the curve
            control_points = []
            for i in range(steps + 1):
                t = i / steps
                # Add some randomness to the path
                x = start[0] + (end[0] - start[0]) * t + random.uniform(-10, 10)
                y = start[1] + (end[1] - start[1]) * t + random.uniform(-10, 10)
                control_points.append((x, y))

            # Move through the control points
            for point in control_points:
                await self.page.mouse.move(point[0], point[1])
                await asyncio.sleep(random.uniform(0.01, 0.03))  # Small random delay between moves

        except Exception as e:
            print(f"Error during mouse movement: {str(e)}")
            # Fallback to direct movement if curve movement fails
            try:
                await self.page.mouse.move(end[0], end[1])
            except Exception as e:
                print(f"Error during fallback mouse movement: {str(e)}")

    async def restart_browser_with_new_proxy(self, port=None):
        if not self.page:
            return
        """Restart browser with a new proxy when current one fails"""
        logger.info("Restarting browser with new proxy...")
        
        # Clean up current browser
        await self.cleanup()
        
        # Try to setup browser with a new proxy
        return await self.setup_mostlogin_browser(self.current_proxy)

    async def create_account(self):
        if not self.page:
            return False
        success = False
        email = None
        password = None
        client_id = None
        refresh_token = None
        try:
            # The browser setup and navigation are now handled in the worker_process
            
            # Clear storage (do it AFTER the page is available)
            try:
                await self.page.evaluate("localStorage.clear(); sessionStorage.clear();")
            except Exception as e:
                print(f"Warning: Could not clear storage: {e}")
            
            # Make sure DOM is fully ready
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"Warning: Page load timeout: {str(e)}")
                print("Continuing anyway...")
            
            username = self.generate_random_username()
            password = self.generate_random_password()
            account_type = self.account_type
            email = f"{username}@{account_type}.com"
            self.current_email = email
            self.current_password = password
            
            # Generated credentials stored quietly

            # Enhanced page load waiting with realistic behavior
            try:
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                pass

            # Simple page interaction check
            try:
                # Simple check to ensure page is loaded and interactive
                page_ready = await self.page.evaluate("() => document.readyState === 'complete'")
                if not page_ready:
                    await asyncio.sleep(2)
            except Exception as e:
                pass

            # CRITICAL: Ensure window focus before starting form interactions
            await self.ensure_window_focus()

            # Enhanced email field selectors - most reliable ones first
            email_field_selectors = [
                'input[name="Email"]',
                '#MemberName',
                '#floatingLabelInput5',
                'input#MemberName',
                'input#floatingLabelInput5',
                'input[type="email"]',
                'input[aria-label*="Email"]' # Last resort
            ]

            email_field = None
            
            # Try the most reliable selectors first with longer timeout
            for i, selector in enumerate(email_field_selectors[:6]):
                try:
                    email_field = await self.page.wait_for_selector(selector, timeout=8000)
                    if email_field:
                        break
                except Exception:
                    continue

            # If not found, try remaining selectors with shorter timeout
            if not email_field:
                for i, selector in enumerate(email_field_selectors[6:], 7):
                    try:
                        email_field = await self.page.wait_for_selector(selector, timeout=3000)
                        if email_field:
                            break
                    except Exception:
                        continue

            if not email_field:
                try:
                    await self.page.reload(wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    # Retry all selectors again after refresh
                    for i, selector in enumerate(email_field_selectors[:6]):
                        try:
                            email_field = await self.page.wait_for_selector(selector, timeout=8000)
                            if email_field:
                                break
                        except Exception:
                            continue
                    if not email_field:
                        for i, selector in enumerate(email_field_selectors[6:], 7):
                            try:
                                email_field = await self.page.wait_for_selector(selector, timeout=3000)
                                if email_field:
                                    break
                            except Exception:
                                continue
                except Exception as e:
                    pass

            if not email_field:
                # Take screenshot for debugging
                try:
                    await self.page.screenshot(path="error_screenshot.png")
                except Exception as e:
                    pass
                return False

            # Realistic pause before typing email (like user reading the field label)
            await asyncio.sleep(random.uniform(1.5, 3.8))

            try:
                # Enhanced human-like email typing
                await self.human_type(email_field, email)
            except Exception as e:
                return False

            # Realistic pause after typing email (like user double-checking)
            await asyncio.sleep(random.uniform(1.8, 4.2))

            # Enhanced next button selectors - most reliable ones first
            next_button_selectors = [
                '#iSignupAction',
                'button:has-text("Next")',
                'button[type="submit"]',
                'button[class*="next"]',
                'button[class*="submit"]',
                'button[class*="primary"]',
                'button[class*="continue"]',
                'button[id*="next"]',
                'button[id*="Next"]',
                'button[id*="submit"]',
                'button[id*="Submit"]',
                'input[type="submit"]',
                'input[value*="Next"]',
            ]
            
            next_button = None
            
            # Try to find next button with patient search
            for i, selector in enumerate(next_button_selectors[:5]):
                try:
                    next_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if next_button:
                        break
                except Exception:
                    continue
            
            # If not found, try remaining selectors with shorter timeout
            if not next_button:
                for i, selector in enumerate(next_button_selectors[5:], 6):
                    try:
                        next_button = await self.page.wait_for_selector(selector, timeout=2000)
                        if next_button:
                            break
                    except Exception:
                        continue

            if not next_button:
                return False

            # Realistic pause before clicking (like user thinking/reviewing)
            await asyncio.sleep(random.uniform(2.1, 4.8))

            try:
                # Enhanced human-like click
                await self.human_click(next_button)
            except Exception as e:
                try:
                    # Fallback: Element click
                    await next_button.click(delay=random.randint(50, 150))
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                except Exception as e2:
                    try:
                        # Last resort: JavaScript click
                        await next_button.evaluate("el => el.click()")
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                    except Exception as e3:
                        return False

            # Execute all required steps
            if not await self.handle_password_page(password):
                return False

            if not await self.handle_country_and_date_fields():
                return False

            if not await self.handle_name_page():
                return False

            # After all the form filling steps, handle verification
            if not await self.handle_verification():
                return False

            # === OAuth2 flow to get client_id and refresh_token (stub) ===
            # TODO: Implement actual OAuth2 flow here and set client_id and refresh_token
            # Example:
            # client_id = YOUR_CLIENT_ID
            # refresh_token = await self.obtain_refresh_token(email, password, client_id)
            # For now, leave as None or set to real values if available
            # client_id = ...
            # refresh_token = ...

            # If we get here, verification was successful
            success = True
            # Remove duplicate save_credentials call here
            return True
        except Exception as e:
            print(f"Error during account creation: {str(e)}")
            return False
        finally:
            if not success:
                await self.cleanup()

    async def cleanup(self):
        """Optimized cleanup for background processes with aggressive resource management and robust Kameleo profile handling"""
        try:
            # Stop local proxy server if running
            self.stop_local_proxy_server()
            
            # Cancel mouse movement task if it exists (lightweight check)
            if hasattr(self, 'mouse_task') and self.mouse_task:
                try:
                    self.mouse_task.cancel()
                except Exception as e:
                    print(f"[CLEANUP] Error cancelling mouse task: {e}")
                finally:
                    self.mouse_task = None

            # Aggressive browser cleanup for background processes
            if self.page:
                try:
                    await asyncio.wait_for(self.page.close(), timeout=3.0)
                except Exception as e:
                    print(f"[CLEANUP] Error closing page: {e}")
                finally:
                    self.page = None

            if self.context:
                try:
                    await asyncio.wait_for(self.context.close(), timeout=3.0)
                except Exception as e:
                    print(f"[CLEANUP] Error closing context: {e}")
                finally:
                    self.context = None

            if self.browser:
                try:
                    await asyncio.wait_for(self.browser.close(), timeout=3.0)
                except Exception as e:
                    print(f"[CLEANUP] Error closing browser: {e}")
                finally:
                    self.browser = None

            # Quick MostLogin profile cleanup
            if hasattr(self, 'mostlogin_profile_path') and self.mostlogin_profile_path:
                try:
                    import shutil
                    if os.path.exists(self.mostlogin_profile_path):
                        shutil.rmtree(self.mostlogin_profile_path, ignore_errors=True)
                        print(f"[MOSTLOGIN] Cleaned up profile: {self.mostlogin_profile_path}")
                except Exception as e:
                    print(f"[CLEANUP] Error cleaning MostLogin profile: {e}")
                finally:
                    self.mostlogin_profile_path = None

            # Force garbage collection for better memory management
            import gc
            gc.collect()

        except Exception as e:
            print(f"[CLEANUP] General cleanup error: {e}")
        finally:
            # Ensure all references are cleared
            self.page = None
            self.context = None
            self.browser = None
            self.mouse_task = None

        # Robust Kameleo cleanup: always try to stop/delete if profile was created
        if getattr(self, 'kameleo_client', None) and getattr(self, 'kameleo_profile_id', None):
            try:
                print(f"[KAMELEO] Attempting to stop profile: {self.kameleo_profile_id}")
                try:
                    self.kameleo_client.profile.stop_profile(self.kameleo_profile_id)
                    print(f"[KAMELEO] Stopped profile: {self.kameleo_profile_id}")
                except Exception as stop_e:
                    print(f"[KAMELEO] Stop profile error (may be already stopped): {stop_e}")
                print(f"[KAMELEO] Attempting to delete profile: {self.kameleo_profile_id}")
                try:
                    self.kameleo_client.profile.delete_profile(self.kameleo_profile_id)
                    print(f"[KAMELEO] Deleted profile: {self.kameleo_profile_id}")
                except Exception as delete_e:
                    print(f"[KAMELEO] Delete profile error: {delete_e}")
            except Exception as cleanup_e:
                print(f"[KAMELEO] General Kameleo cleanup error: {cleanup_e}")
            finally:
                self.kameleo_profile_id = None

        # Cancel periodic focus task
        if self._focus_task:
            try:
                self._focus_task.cancel()
            except Exception as e:
                print(f"[CLEANUP] Error cancelling focus task: {e}")
            self._focus_task = None

    async def debug_blank_page(self, page, debug_name="blank_page"):
        """Comprehensive debug function for blank page issues"""
        try:
            print(f"\n[DEBUG] Starting comprehensive blank page analysis for {debug_name}...")
            
            # Basic page info
            current_url = page.url
            page_title = await page.title()
            print(f"[DEBUG] Current URL: {current_url}")
            print(f"[DEBUG] Page title: '{page_title}'")
            
            # Check page loading states
            load_state = await page.evaluate("() => document.readyState")
            print(f"[DEBUG] Document ready state: {load_state}")
            
            # Check for JavaScript errors
            js_errors = await page.evaluate("""
                () => {
                    const errors = window.jsErrors || [];
                    return errors.slice(0, 5); // Get first 5 errors
                }
            """)
            if js_errors:
                print(f"[DEBUG] JavaScript errors found: {js_errors}")
            else:
                print(f"[DEBUG] No JavaScript errors detected")
            
            # Check content details
            content_analysis = await page.evaluate("""
                () => {
                    const html = document.documentElement;
                    const body = document.body;
                    const head = document.head;
                    
                    return {
                        htmlExists: !!html,
                        bodyExists: !!body,
                        headExists: !!head,
                        bodyContent: body ? body.innerHTML.length : 0,
                        bodyText: body ? body.innerText.length : 0,
                        bodyVisible: body ? body.style.display !== 'none' : false,
                        scripts: document.scripts.length,
                        stylesheets: document.styleSheets.length,
                        bodyClasses: body ? body.className : '',
                        bodyStyle: body ? body.style.cssText : '',
                        metaTags: head ? head.querySelectorAll('meta').length : 0,
                        firstText: body ? body.innerText.slice(0, 200) : 'No body'
                    };
                }
            """)
            
            print(f"[DEBUG] Content analysis:")
            for key, value in content_analysis.items():
                print(f"  - {key}: {value}")
            
            # Check for common blocking elements
            blocking_elements = await page.evaluate("""
                () => {
                    const selectors = [
                        '[class*="loading"]',
                        '[class*="spinner"]',
                        '[id*="loading"]',
                        '[class*="overlay"]',
                        '[class*="modal"]',
                        '[style*="position: fixed"]',
                        '[style*="z-index"]'
                    ];
                    
                    const results = {};
                    selectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            results[selector] = elements.length;
                        }
                    });
                    
                    return results;
                }
            """)
            
            if len(blocking_elements) > 0:
                print(f"[DEBUG] Potential blocking elements found: {blocking_elements}")
            else:
                print(f"[DEBUG] No obvious blocking elements detected")
            
            # Check for iframes
            iframe_count = await page.evaluate("() => document.querySelectorAll('iframe').length")
            print(f"[DEBUG] iframes found: {iframe_count}")
            
            # Network request analysis
            try:
                # Check for failed requests
                failed_requests = await page.evaluate("""
                    () => {
                        if (window.performance && window.performance.getEntriesByType) {
                            const entries = window.performance.getEntriesByType('navigation');
                            return entries.length > 0 ? entries[0] : null;
                        }
                        return null;
                    }
                """)
                if failed_requests:
                    print(f"[DEBUG] Navigation timing available")
                else:
                    print(f"[DEBUG] No navigation timing data")
            except:
                print(f"[DEBUG] Could not check navigation timing")
            
            # Save debug screenshot and page source
            try:
                await page.screenshot(path=f"{debug_name}_debug.png", full_page=True)
                print(f"[DEBUG] Saved debug screenshot: {debug_name}_debug.png")
                
                page_source = await page.content()
                with open(f"{debug_name}_source.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                print(f"[DEBUG] Saved page source: {debug_name}_source.html")
                
                # Save a shorter version for quick analysis
                if len(page_source) > 1000:
                    with open(f"{debug_name}_source_short.txt", "w", encoding="utf-8") as f:
                        f.write(page_source[:2000] + "\n\n...[TRUNCATED]...\n\n" + page_source[-500:])
                    print(f"[DEBUG] Saved short page source: {debug_name}_source_short.txt")
                    
            except Exception as e:
                print(f"[DEBUG] Could not save debug files: {e}")
            
            # Recommendations
            print(f"\n[DEBUG] Recommendations:")
            if content_analysis['bodyText'] < 50:
                print(f"  - Page appears blank (very little text content)")
                print(f"  - Try refreshing the page or using different user agent")
                if content_analysis['scripts'] > 0:
                    print(f"  - Page has {content_analysis['scripts']} scripts - may need more time to load")
            
            if blocking_elements:
                print(f"  - Found potential blocking elements - page may be loading")
                print(f"  - Wait longer or try to dismiss overlays")
            
            if iframe_count > 0:
                print(f"  - Page has {iframe_count} iframes - content may be in iframe")
            
            print(f"[DEBUG] Analysis complete for {debug_name}\n")
            
        except Exception as e:
            print(f"[DEBUG] Error during blank page analysis: {e}")

    async def try_fix_blank_page(self, page):
        """Try various methods to fix a blank page"""
        try:
            print(f"[FIX] Attempting to fix blank page...")
            
            # Method 1: Wait longer for JavaScript
            print(f"[FIX] Method 1: Waiting for JavaScript execution...")
            await asyncio.sleep(5)
            content_after_wait = await page.evaluate("() => document.body ? document.body.innerText.length : 0")
            print(f"[FIX] Content after wait: {content_after_wait} characters")
            if content_after_wait > 100:
                print(f"[FIX] ✅ Page fixed by waiting!")
                return True
            
            # Method 2: Reload page
            print(f"[FIX] Method 2: Reloading page...")
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)
            content_after_reload = await page.evaluate("() => document.body ? document.body.innerText.length : 0")
            print(f"[FIX] Content after reload: {content_after_reload} characters")
            if content_after_reload > 100:
                print(f"[FIX] ✅ Page fixed by reloading!")
                return True
            
            # Method 3: Try disabling JavaScript and reload
            print(f"[FIX] Method 3: Trying with different settings...")
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Cache-Control': 'no-cache'
            })
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(4)
            content_after_headers = await page.evaluate("() => document.body ? document.body.innerText.length : 0")
            print(f"[FIX] Content after header change: {content_after_headers} characters")
            if content_after_headers > 100:
                print(f"[FIX] ✅ Page fixed by changing headers!")
                return True
            
            # Method 4: Try executing JavaScript to force content
            print(f"[FIX] Method 4: Trying to force content rendering...")
            await page.evaluate("""
                () => {
                    // Force reflow
                    document.body.style.display = 'none';
                    document.body.offsetHeight; // Trigger reflow
                    document.body.style.display = '';
                    
                    // Try to trigger any lazy loading
                    window.scrollTo(0, 100);
                    window.scrollTo(0, 0);
                    
                    // Dispatch events that might trigger content loading
                    window.dispatchEvent(new Event('resize'));
                    window.dispatchEvent(new Event('load'));
                }
            """)
            await asyncio.sleep(3)
            content_after_js = await page.evaluate("() => document.body ? document.body.innerText.length : 0")
            print(f"[FIX] Content after JavaScript fix: {content_after_js} characters")
            if content_after_js > 100:
                print(f"[FIX] ✅ Page fixed by JavaScript manipulation!")
                return True
            
            print(f"[FIX] ❌ Could not fix blank page with any method")
            return False
            
        except Exception as e:
            print(f"[FIX] Error while trying to fix blank page: {e}")
            return False

    async def test_signup_page_loading(self):
        if not self.page:
            return
        """Simple test function to verify signup page loads correctly"""
        try:
            # Setup browser
            if not await self.setup_browser():
                return False
            
            # Test each signup URL
            signup_urls = [
                "https://signup.live.com/signup",
                "https://signup.live.com/",
                "https://account.microsoft.com/account/signup",
            ]
            
            working_urls = []
            
            for i, url in enumerate(signup_urls):
                print(f"\n[TEST] Testing URL {i+1}: {url}")
                
                try:
                    # Navigate to URL
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Wait for content to load
                    await asyncio.sleep(5)
                    
                    # Check content
                    content_analysis = await self.page.evaluate("""
                        () => {
                            const body = document.body;
                            const emailInputs = document.querySelectorAll('input[type="email"], input[name*="email"], input[name*="Email"], input[name="MemberName"]');
                            const bodyText = body ? body.innerText : '';
                            
                            return {
                                bodyTextLength: bodyText.length,
                                hasEmailInputs: emailInputs.length > 0,
                                hasSignupKeywords: bodyText.toLowerCase().includes('signup') || 
                                                 bodyText.toLowerCase().includes('sign up') || 
                                                 bodyText.toLowerCase().includes('create account') ||
                                                 bodyText.toLowerCase().includes('email'),
                                visibleText: bodyText.slice(0, 300)
                            };
                        }
                    """)
                    
                    print(f"[TEST] Content analysis for {url}:")
                    print(f"  - Body text length: {content_analysis['bodyTextLength']}")
                    print(f"  - Has email inputs: {content_analysis['hasEmailInputs']}")
                    print(f"  - Has signup keywords: {content_analysis['hasSignupKeywords']}")
                    
                    if content_analysis['bodyTextLength'] < 50:
                        print(f"[TEST] ⚠️  Page appears blank!")
                        print(f"[TEST] Visible text: '{content_analysis['visibleText']}'")
                        
                        # Try to fix it
                        print(f"[TEST] Attempting to fix blank page...")
                        if await self.try_fix_blank_page(self.page):
                            print(f"[TEST] ✅ Page fixed!")
                            working_urls.append(url)
                        else:
                            print(f"[TEST] ❌ Could not fix page")
                    elif content_analysis['hasEmailInputs'] or content_analysis['hasSignupKeywords']:
                        print(f"[TEST] ✅ Page appears to be working correctly!")
                        working_urls.append(url)
                    else:
                        print(f"[TEST] ⚠️  Page loaded but may not be signup page")
                        print(f"[TEST] Visible text: '{content_analysis['visibleText']}'")
                
                except Exception as e:
                    print(f"[TEST] ❌ Error testing {url}: {e}")
            
            # Summary
            print(f"\n" + "="*60)
            print("📊 TEST RESULTS SUMMARY")
            print("="*60)
            print(f"Total URLs tested: {len(signup_urls)}")
            print(f"Working URLs: {len(working_urls)}")
            
            if working_urls:
                print(f"✅ SUCCESS: Found {len(working_urls)} working URL(s):")
                for url in working_urls:
                    print(f"  - {url}")
                print(f"\nThe blank page issue appears to be fixed!")
            else:
                print(f"❌ FAILURE: No working URLs found")
                print(f"The blank page issue persists. Check:")
                print(f"  1. Proxy configuration (if using proxies)")
                print(f"  2. MostLogin Local API Client is running")
                print(f"  3. Internet connection")
                print(f"  4. Generated debug files for more details")
            
            return len(working_urls) > 0
            
        except Exception as e:
            print(f"[TEST] ❌ Test failed with error: {e}")
            return False
        finally:
            await self.cleanup()

    async def simulate_reading_signup_form(self, page):
        if not page:
            pass
            return
        """Simulate extensive page reading before filling forms - CRITICAL for Microsoft detection"""
        try:
            # Simulating thorough page reading
            
            # Get viewport for realistic movements
            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            
            # Phase 1: Initial page scan (like real users read top to bottom)
            # Initial page scanning
            for scan in range(random.randint(3, 6)):
                # Simulate reading different sections of the page
                if scan == 0:
                    # Read header/title area
                    x = random.randint(200, viewport['width'] - 200)
                    y = random.randint(50, 150)
                elif scan == 1:
                    # Read form instructions
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(150, 300)
                else:
                    # Read form fields and labels
                    x = random.randint(150, viewport['width'] - 150)
                    y = random.randint(250, 500)
                
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(1.5, 4.2))  # Longer reading pauses
            
            # Phase 2: Detailed form field examination
            # Examining form fields
            try:
                # Look for and examine all input fields (like users scan the form)
                input_fields = await self.page.query_selector_all('input[type="text"], input[name*="Name"], input[placeholder*="name"]')
                for i, field in enumerate(input_fields[:4]):  # Limit to first 4 fields
                    try:
                        box = await field.bounding_box()
                        if box:
                            # Move to field area and "read" the label
                            await self.page.mouse.move(box['x'] - 20, box['y'])
                            await asyncio.sleep(random.uniform(0.8, 2.1))
                            
                            # Move over the field itself
                            await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            await asyncio.sleep(random.uniform(0.5, 1.3))
                    except:
                        continue
            except:
                pass
            
            # Phase 3: Scroll and look around (critical for detection avoidance)
            for scroll in range(random.randint(2, 4)):
                scroll_amount = random.randint(-150, 200)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(1.2, 3.8))
                
                # Move mouse while scrolling (natural behavior)
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.8, 2.1))
            
            # Phase 4: Final preparation pause with attention patterns
            await self.simulate_human_attention_patterns(page)
            await asyncio.sleep(random.uniform(2.5, 5.8))
            # Page reading simulation completed
            
        except Exception as e:
            pass

    async def simulate_label_interaction(self, field, field_name, page):
        if not page:
            pass
            return
        """Simulate clicking on field labels before typing - very human behavior"""
        try:
            print(f"[STEALTH] Simulating label interaction for {field_name}...")
            
            # Try to find the label associated with this field
            try:
                box = await field.bounding_box()
                if box:
                    # Move to label area (usually to the left or above the field)
                    label_x = max(50, box['x'] - random.randint(20, 80))
                    label_y = box['y'] + random.randint(-30, 10)
                    
                    await self.page.mouse.move(label_x, label_y)
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                    
                    # Sometimes click on the label area (very human)
                    if random.random() < 0.6:  # 60% chance
                        await self.page.mouse.click(label_x, label_y)
                        await asyncio.sleep(random.uniform(0.3, 0.8))
            except:
                pass
            
            # Move to the field itself with human-like movement
            await self.human_click(field)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"[STEALTH] Error in label interaction: {e}")

    async def enhanced_human_type(self, element, text: str, field_type: str = "text", page=None):
        if page is not None and not page:
            pass
            return
        """Enhanced human typing with corrections and natural patterns"""
        try:
            print(f"[STEALTH] Enhanced typing for {field_type}: {text}")
            
            # Click to focus the field first
            await element.click()
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Clear any existing content
            await element.press('Control+a')
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await element.press('Delete')
            await asyncio.sleep(random.uniform(0.2, 0.6))
            
            # Enhanced typing with human patterns
            if field_type == "name":
                # Names are typed more carefully
                for i, char in enumerate(text):
                    # Longer pauses for first character and after spaces
                    if i == 0 or (i > 0 and text[i-1] == ' '):
                        base_delay = random.randint(200, 400)
                    else:
                        base_delay = random.randint(80, 180)
                    
                    # Add variance
                    typing_delay = base_delay + random.randint(-30, 50)
                    
                    # Occasional hesitation (like thinking about spelling)
                    if random.random() < 0.15:  # 15% chance
                        await asyncio.sleep(random.uniform(0.3, 1.2))
                    
                    await element.type(char, delay=typing_delay)
                    
                    # Very occasional typo and correction (super human-like)
                    if random.random() < 0.05 and i < len(text) - 1:  # 5% chance
                        # Type wrong character
                        wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                        await element.type(wrong_char, delay=random.randint(100, 200))
                        await asyncio.sleep(random.uniform(0.2, 0.6))
                        # Correct it
                        await element.press('Backspace')
                        await asyncio.sleep(random.uniform(0.1, 0.4))
            else:
                # Regular typing for other fields
                await element.type(text, delay=random.randint(90, 200))
            
            # Final pause after typing
            await asyncio.sleep(random.uniform(0.5, 1.8))
            
        except Exception as e:
            print(f"[STEALTH] Error in enhanced typing: {e}")
            # Fallback to regular typing
            await element.fill(text)
            await asyncio.sleep(random.uniform(0.5, 1.2))

    async def simulate_field_validation_behavior(self, field, text, page):
        if not page:
            pass
            return
        """Simulate checking what was typed (critical human behavior)"""
        try:
            print(f"[STEALTH] Simulating field validation for: {text}")
            
            # Users often click elsewhere then back to check what they typed
            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            
            # Move mouse away from field
            away_x = random.randint(100, viewport['width'] - 100)
            away_y = random.randint(100, viewport['height'] - 100)
            await self.page.mouse.move(away_x, away_y)
            await asyncio.sleep(random.uniform(0.8, 2.1))
            
            # Move back to field to "check" what was typed
            await field.click()
            await asyncio.sleep(random.uniform(0.5, 1.2))
            
            # Simulate selecting text to verify (very human)
            if random.random() < 0.4:  # 40% chance
                await field.press('Control+a')
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await field.press('ArrowRight')  # Deselect
                await asyncio.sleep(random.uniform(0.2, 0.6))
            
            # Sometimes use arrow keys to navigate through the text
            if random.random() < 0.3:  # 30% chance
                for _ in range(random.randint(1, 3)):
                    await field.press('ArrowLeft' if random.random() < 0.5 else 'ArrowRight')
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            print(f"[STEALTH] Error in field validation: {e}")

    async def simulate_extensive_form_review(self, first_name_field, last_name_field, first_name, last_name, page):
        if not page:
            pass
            return
        """Simulate extensive form review - MOST CRITICAL for avoiding detection"""
        try:
            # Simulating extensive form review
            
            # Phase 1: Review first name
            await first_name_field.click()
            await asyncio.sleep(random.uniform(0.8, 2.1))
            
            # Select and check first name
            await first_name_field.press('Control+a')
            await asyncio.sleep(random.uniform(0.5, 1.3))
            current_first = await first_name_field.evaluate('el => el.value')
            print(f"[STEALTH] Verified first name: {current_first}")
            await first_name_field.press('ArrowRight')
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Pause between reviews
            await asyncio.sleep(random.uniform(1.2, 3.5))
            
            # Phase 2: Review last name
            # Reviewing last name
            await last_name_field.click()
            await asyncio.sleep(random.uniform(0.8, 2.1))
            
            # Select and check last name
            await last_name_field.press('Control+a')
            await asyncio.sleep(random.uniform(0.5, 1.3))
            current_last = await last_name_field.evaluate('el => el.value')
            # Verified last name
            await last_name_field.press('ArrowRight')
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Phase 3: Look around the form for other fields or requirements
            # Scanning for additional requirements
            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            
            for scan in range(random.randint(3, 6)):
                x = random.randint(50, viewport['width'] - 50)
                y = random.randint(200, viewport['height'] - 100)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(1.0, 2.8))
            
            # Phase 4: Final form completeness check with attention patterns
            # Final completeness check
            await self.simulate_human_attention_patterns(page)
            await self.add_human_micro_delay(1.0, 3.0, 2.5, page)
            await asyncio.sleep(random.uniform(2.5, 5.2))
            
        except Exception as e:
            print(f"[STEALTH] Error in form review: {e}")

    async def simulate_pre_submission_paranoia(self, first_name_field, last_name_field, next_button, page):
        if not page:
            pass
            return
        """Simulate paranoid checking before submission - CRITICAL anti-detection"""
        try:
            # Simulating pre-submission paranoia
            
            # Phase 1: Last-minute field checks (very human behavior)
            for field_name, field in [("first name", first_name_field), ("last name", last_name_field)]:
                # Final check of field
                
                await field.click()
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
                # Quick select-all to verify content
                await field.press('Control+a')
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await field.press('ArrowRight')
                await asyncio.sleep(random.uniform(0.2, 0.6))
                
                # Pause between field checks
                await asyncio.sleep(random.uniform(0.8, 2.1))
            
            # Phase 2: Look for any error messages or warnings
            # Checking for error messages
            try:
                # Look around the form for any red text or error indicators
                viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
                for error_check in range(random.randint(2, 4)):
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(200, 600)
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.8, 1.8))
            except:
                pass
            
            # Phase 3: Hover over next button and hesitate (super human)
            # Hovering over submit button
            try:
                box = await next_button.bounding_box()
                if box:
                    # Move towards button but don't click yet
                    button_x = box['x'] + box['width']/2
                    button_y = box['y'] + box['height']/2
                    
                    # Approach button slowly
                    await self.page.mouse.move(button_x - 20, button_y - 10)
                    await asyncio.sleep(random.uniform(1.2, 2.8))
                    
                    # Hover over button
                    await self.page.mouse.move(button_x, button_y)
                    await asyncio.sleep(random.uniform(2.5, 5.2))  # Long hesitation
                    
                    # Move away briefly (second thoughts)
                    if random.random() < 0.7:  # 70% chance of hesitation
                        await self.page.mouse.move(button_x - 30, button_y + 20)
                        await asyncio.sleep(random.uniform(1.0, 2.5))
                        # Move back to button
                        await self.page.mouse.move(button_x, button_y)
                        await asyncio.sleep(random.uniform(1.5, 3.2))
            except:
                pass
            
            # Phase 4: Final decision pause with realistic hesitation
            # Final decision pause
            await self.simulate_human_attention_patterns(page)
            await self.add_human_micro_delay(2.0, 4.0, 3.0, page)
            await asyncio.sleep(random.uniform(3.2, 7.5))
            
        except Exception as e:
            print(f"[STEALTH] Error in pre-submission paranoia: {e}")

    async def enhanced_form_submission(self, next_button, page):
        if not page:
            pass
            return
        """Enhanced form submission with natural behavior"""
        try:
            # Performing enhanced form submission
            
            # Phase 1: Final button approach
            box = await next_button.bounding_box()
            if box:
                button_x = box['x'] + box['width']/2 + random.uniform(-5, 5)
                button_y = box['y'] + box['height']/2 + random.uniform(-3, 3)
                
                # Slow approach to button
                await self.page.mouse.move(button_x, button_y)
                await asyncio.sleep(random.uniform(0.8, 1.8))
            
            # Phase 2: The actual click with human timing
            # Clicking submit button
            
            # Random delay before click (last second hesitation)
            await asyncio.sleep(random.uniform(0.5, 1.8))
            
            # Enhanced human click
            if not await self.human_click(next_button):
                return False
            
            # Phase 3: Post-click behavior (don't move mouse immediately)
            # Post-click behavior
            await asyncio.sleep(random.uniform(1.2, 3.2))
            
            # Small mouse movement after click (natural behavior)
            if box:
                post_x = box['x'] + box['width']/2 + random.uniform(-10, 10)
                post_y = box['y'] + box['height']/2 + random.uniform(-8, 8)
                await self.page.mouse.move(post_x, post_y)
            
            return True
            
        except Exception as e:
            print(f"[STEALTH] Error in enhanced form submission: {e}")
            return False

    async def simulate_post_submission_behavior(self, page):
        if not page:
            pass
            return
        """Simulate realistic waiting behavior after form submission"""
        try:
            # Simulating post-submission waiting behavior
            
            # Phase 1: Initial waiting (users expect immediate response)
            await asyncio.sleep(random.uniform(2.5, 4.8))
            
            # Phase 2: Looking around while waiting
            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            
            # Simulate impatient waiting behavior
            total_wait_chunks = random.randint(6, 10)
            chunk_duration = random.uniform(2.0, 4.0)
            
            for chunk in range(total_wait_chunks):
                print(f"[STEALTH] Waiting chunk {chunk+1}/{total_wait_chunks}...")
                
                # Random mouse movements (impatient waiting)
                if random.random() < 0.8:  # 80% chance
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(100, viewport['height'] - 100)
                    await self.page.mouse.move(x, y)
                
                # Occasional scrolling (looking for progress indicators)
                if random.random() < 0.4:  # 40% chance
                    scroll_amount = random.randint(-100, 150)
                    await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                
                # Sometimes hover over areas of the page
                if random.random() < 0.3:  # 30% chance
                    try:
                        # Look for loading indicators or form elements
                        elements = await self.page.query_selector_all('div, span, button')
                        if elements and len(elements) > 0:
                            random_element = random.choice(elements[:10])  # First 10 elements
                            try:
                                await random_element.hover()
                                await asyncio.sleep(random.uniform(0.5, 1.2))
                            except:
                                pass
                    except:
                        pass
                
                await asyncio.sleep(chunk_duration)
            
            # Post-submission behavior completed
            
        except Exception as e:
            pass

    async def add_human_micro_delay(self, base_min=0.1, base_max=0.3, variation_factor=2.0, page=None):
        if page is not None and not page:
            pass
            return
        """Add human-like micro delays with natural variation"""
        # Create realistic timing patterns
        delay = random.uniform(base_min, base_max)
        
        # Add occasional longer pauses (like humans getting distracted)
        if random.random() < 0.1:  # 10% chance
            delay *= variation_factor
        
        await asyncio.sleep(delay)

    async def simulate_human_attention_patterns(self, page):
        if not page:
            pass
            return
        """Simulate human attention and distraction patterns"""
        try:
            # Humans sometimes get distracted and look away
            if random.random() < 0.15:  # 15% chance
                # Simulating momentary distraction
                
                # Move mouse to random location (looking away)
                viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
                distraction_x = random.randint(50, viewport['width'] - 50)
                distraction_y = random.randint(50, viewport['height'] - 50)
                
                await self.page.mouse.move(distraction_x, distraction_y)
                await asyncio.sleep(random.uniform(1.5, 4.2))
                
                # Sometimes small scroll during distraction
                if random.random() < 0.5:
                    scroll_amount = random.randint(-100, 100)
                    await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            pass  # Silent fail for robustness

# Quick test function for standalone testing
async def test_blank_page_fix():
    """Standalone function to test blank page fixes"""
    print("🧪 Quick Test: Signup Page Blank Page Fix")
    print("This will test if the signup page loads correctly...")
    
    creator = HotmailAccountCreator(use_proxies=False)
    
    try:
        result = await creator.test_signup_page_loading()
        if result:
            print("\n🎉 SUCCESS: Blank page fix appears to be working!")
        else:
            print("\n❌ FAILURE: Blank page issue still exists.")
            print("Check the debug files generated for more information.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

def worker_process(worker_id: int, num_accounts: int, num_processes: int, config: Dict, profile_semaphore=None, proxy_pool=None):
    """Optimized worker process for background execution with enhanced proxy debugging and per-account profile lifecycle."""
    try:
        # Set minimal logging for background processes
        logging.getLogger().setLevel(logging.WARNING)

        async def worker_async():
            assigned_proxy = None

            # Track credentials for this worker
            worker_credentials = []
            successful_accounts = 0
            failed_accounts = 0

            # Account distribution - ensure all accounts are covered
            base = num_accounts // num_processes
            extra = num_accounts % num_processes
            start_account = worker_id * base + min(worker_id, extra)
            end_account = start_account + base + (1 if worker_id < extra else 0)
            
            accounts_to_process = end_account - start_account
            print(f"[WORKER {worker_id}] Assigned accounts {start_account+1} to {end_account} ({accounts_to_process} accounts total)")
            print(f"[WORKER {worker_id}] Will process ALL {accounts_to_process} accounts regardless of individual failures")

            # ENSURE PROXY AVAILABILITY - Exit worker if no proxy pool when proxies are required
            if config.get('use_proxies', False) and not proxy_pool:
                print(f"[WORKER {worker_id}] ERROR: Proxies are required but proxy pool is not available. Worker cannot continue.")
                return

            # Process accounts with per-account profile lifecycle
            for i in range(start_account, end_account):
                account_num = i + 1
                print(f"Started creating account {account_num}")

                successful_creator = None

                # ACQUIRE SEMAPHORE BEFORE ANY PROFILE CREATION
                if profile_semaphore:
                    profile_semaphore.acquire()

                try:
                    # --- Browser Setup Stage with GUARANTEED Proxy Assignment ---
                    max_proxy_retries = 10  # Increased retries to cycle through all proxies
                    successful_creator = None
                    
                    for attempt in range(max_proxy_retries):
                        assigned_proxy = None
                        
                        if config.get('use_proxies', False):
                            # ALWAYS get a proxy - cycle through all available proxies
                            assigned_proxy = proxy_pool.get_next_proxy()
                            
                            if not assigned_proxy:
                                print(f"[WORKER {worker_id}] CRITICAL: No proxy available! This should never happen.")
                                # Wait a bit and try again
                                await asyncio.sleep(5)
                                continue
                            
                            print(f"[WORKER {worker_id}] Account {account_num} - Using proxy: {assigned_proxy.host}:{assigned_proxy.port} (attempt {attempt + 1})")
                        
                        # NEVER create browser without proxy when proxies are enabled
                        if config.get('use_proxies', False) and not assigned_proxy:
                            print(f"[WORKER {worker_id}] Skipping account {account_num} - no proxy available")
                            continue

                        creator = HotmailAccountCreator(
                            proxy_pool=proxy_pool,
                            use_proxies=config.get('use_proxies', False),
                            account_type=config.get('account_type', 'hotmail')
                        )
                        creator.current_proxy = assigned_proxy

                        if await creator.setup_mostlogin_browser(assigned_proxy):
                            successful_creator = creator
                            print(f"[WORKER {worker_id}] Browser setup successful with proxy: {assigned_proxy.host}:{assigned_proxy.port}")
                            break # Success, exit proxy retry loop
                        else:
                            # Mark this proxy as failed and try next one
                            if assigned_proxy and proxy_pool:
                                proxy_pool.mark_proxy_failed(assigned_proxy)
                                print(f"[WORKER {worker_id}] Browser setup failed with proxy: {assigned_proxy.host}:{assigned_proxy.port}, trying next proxy...")
                            
                            # Cleanup of the failed profile is handled inside setup_mostlogin_browser
                            await asyncio.sleep(2)

                    # --- Account Creation Stage ---
                    try:
                        if successful_creator:
                            try:
                                # Navigation
                                print("Processing...")
                                signup_url = "https://signup.live.com/signup"
                                await successful_creator.page.goto(signup_url, wait_until="domcontentloaded", timeout=45000)

                                # Actual account creation
                                account_credentials = None
                                if await successful_creator.create_account():
                                    print("Created successfully")
                                    successful_accounts += 1
                                    if hasattr(successful_creator, 'current_email') and hasattr(successful_creator, 'current_password'):
                                        if successful_creator.current_email and successful_creator.current_password:
                                            account_credentials = {
                                                'email': successful_creator.current_email,
                                                'password': successful_creator.current_password,
                                                'account_num': account_num,
                                                'status': 'success'
                                            }
                                            worker_credentials.append(account_credentials)
                                else:
                                    print("Failed to create")

                            except Exception as e:
                                if successful_creator.current_proxy and proxy_pool:
                                    proxy_pool.mark_proxy_failed(successful_creator.current_proxy)
                                failed_accounts += 1
                                print("Failed to create")
                            finally:
                                # Always cleanup after each account
                                await successful_creator.cleanup()
                        else:
                            failed_accounts += 1
                            print(f"[WORKER {worker_id}] Failed to create account {account_num} - browser setup failed after {max_proxy_retries} proxy attempts")
                            if config.get('use_proxies', False):
                                print(f"[WORKER {worker_id}] All proxies failed for account {account_num}. Will retry with fresh proxy cycle for next account.")
                            else:
                                print(f"[WORKER {worker_id}] Browser setup failed for account {account_num}.")
                    finally:
                        # ALWAYS RELEASE SEMAPHORE AFTER ACCOUNT COMPLETION AND CLEANUP
                        if profile_semaphore:
                            profile_semaphore.release()
                except Exception as e:
                    if profile_semaphore:
                        profile_semaphore.release()

            # Save credentials quietly
            successful_creds = [c for c in worker_credentials if c['status'] == 'success']
            if successful_creds:
                # Save all credentials to a worker-specific summary file
                try:
                    import os
                    summary_file = os.path.join('credentials', f'worker_{worker_id}_summary.txt')
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        f.write(f"Worker {worker_id} Summary Report\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Total processed: {end_account - start_account}\n")
                        f.write(f"Successful: {successful_accounts}\n")
                        f.write(f"Failed: {failed_accounts}\n\n")
                        f.write("Successful Credentials:\n")
                        for cred in successful_creds:
                            f.write(f"{cred['email']}:{cred['password']}:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                except Exception as e:
                    pass

            # Worker completion summary
            total_processed = successful_accounts + failed_accounts
            print(f"[WORKER {worker_id}] ✅ COMPLETED: Processed {total_processed}/{accounts_to_process} accounts")
            print(f"[WORKER {worker_id}] ✅ SUCCESS: {successful_accounts} accounts created")
            print(f"[WORKER {worker_id}] ❌ FAILED: {failed_accounts} attempts failed")
            
            if total_processed == accounts_to_process:
                print(f"[WORKER {worker_id}] 🎯 ALL ASSIGNED ACCOUNTS PROCESSED SUCCESSFULLY!")
            else:
                print(f"[WORKER {worker_id}] ⚠️  WARNING: Only {total_processed}/{accounts_to_process} accounts were processed")

        # Run with timeout for background processes
        try:
            asyncio.run(asyncio.wait_for(worker_async(), timeout=36000))  # 10 hours max per worker (for large batches)
        except asyncio.TimeoutError:
            logger.warning(f"[WORKER {worker_id}] Worker process timed out after 10 hours.")
            pass  # Silent timeout for background processes
        except Exception as e:
            logger.error(f"[WORKER {worker_id}] Unhandled exception in worker_async: {e}")
            logger.error(traceback.format_exc())
            pass  # Silent error handling for background
    finally:
        # Force cleanup any remaining resources
        import gc
        gc.collect()

def get_user_input() -> Dict:
    """Gets user input for account creation settings."""
    print("\n=== Microsoft Account Creator Configuration ===")
    
    # Account type selection
    while True:
        try:
            account_type = input("\nChoose account type (1 for Hotmail, 2 for Outlook): ")
            if account_type in ['1', '2']:
                account_type = 'hotmail' if account_type == '1' else 'outlook'
                break
            print("Please enter 1 for Hotmail or 2 for Outlook")
        except ValueError:
            print("Please enter a valid number")
    
    # Number of accounts
    while True:
        try:
            num_accounts = int(input("\nHow many accounts do you want to create? (1-50000): "))
            if 1 <= num_accounts <= 50000:
                break
            print("Please enter a number between 1 and 50000")
        except ValueError:
            print("Please enter a valid number")
    
    # Number of processes
    while True:
        try:
            num_processes = int(input("\nHow many parallel processes? (1-20): "))
            if 1 <= num_processes <= 20:
                break
            print("Please enter a number between 1 and 20")
        except ValueError:
            print("Please enter a valid number")
    
    # Ask if user wants to use proxies
    use_proxies = input("\nDo you want to use proxies? (y/n): ").lower() == 'y'
    
    # Load proxies if requested
    proxy_list = []
    if use_proxies:
        try:
            with open('Hotmail automation/proxies', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            # Handle different proxy formats
                            if '://' in line:
                                # URL format like "socks5://user:pass@host:port"
                                proxy_list.append(line)
                            else:
                                # Parse proxy in format host:port:username:password
                                parts = line.split(':')
                                if len(parts) == 4:
                                    host, port, username, password = parts
                                    proxy_list.append({
                                        "host": host.strip(),
                                        "port": port.strip(),
                                        "username": username.strip(),
                                        "password": password.strip()
                                    })
                                elif len(parts) == 2:
                                    host, port = parts
                                    proxy_list.append({
                                        "host": host.strip(),
                                        "port": port.strip()
                                    })
                                else:
                                    print(f"Invalid proxy format: {line}")
                                    continue
                        except Exception as e:
                            print(f"Error parsing proxy line: {line} - {str(e)}")
                            continue
            
            if proxy_list:
                print(f"\nSuccessfully loaded {len(proxy_list)} proxies")
            else:
                print("No valid proxies found in file")
                use_proxies = False
        except Exception as e:
            print(f"Error reading proxies file: {str(e)}")
            use_proxies = False
    
    # Save configuration
    config = {
        "account_type": account_type,
        "num_accounts": num_accounts,
        "num_processes": num_processes,
        "use_proxies": use_proxies,
        "proxy_list": proxy_list if use_proxies else []
    }
    
    # Save to file
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        print("\nConfiguration saved to config.json")
    except Exception as e:
        print(f"\nWarning: Could not save configuration: {str(e)}")
    
    return config

def validate_proxy_config(config: Dict) -> bool:
    """Validate proxy configuration before starting"""
    if not config.get('use_proxies', False):
        return True
    
    proxy_list = config.get('proxy_list', [])
    num_processes = config.get('num_processes', 1)
    
    if not proxy_list:
        print("Error: Proxy usage is enabled but no proxies are configured!")
        print("Please add proxies to your configuration or disable proxy usage.")
        return False
    
    # Check if we have enough proxies for the number of processes
    if len(proxy_list) < num_processes:
        print(f"Warning: You have {len(proxy_list)} proxies but {num_processes} processes.")
        print(f"Some processes will share proxies (round-robin assignment).")
    else:
        print(f"Good: You have {len(proxy_list)} proxies for {num_processes} processes.")
    
    print(f"Testing up to 3 HTTP/S proxies from your list of {len(proxy_list)} before starting...")
    proxy_pool = ProxyPool(proxy_list)
    working_count = 0
    tested_http_proxies = 0

    for proxy in proxy_pool.proxies:
        # Stop if we've already tested 3 HTTP/S proxies
        if tested_http_proxies >= 3:
            break

        if proxy.protocol.lower() not in ['http', 'https']:
            print(f"[SKIP] Skipping proxy with unsupported protocol: {proxy.protocol}://{proxy.host}:{proxy.port}")
            continue

        # We found an HTTP/S proxy, so we'll test it
        tested_http_proxies += 1
        try:
            import requests
            print(f"Testing HTTP/S proxy: {proxy.protocol}://{proxy.host}:{proxy.port}")
            if getattr(proxy, 'username', None) and getattr(proxy, 'password', None):
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
            proxy_dict = {
                'http': proxy_url,
                'https': proxy_url
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get('http://httpbin.org/ip', proxies=proxy_dict, timeout=5, verify=False, headers=headers)
            if response.status_code == 200:
                working_count += 1
                print(f"[OK] HTTP proxy {proxy.host}:{proxy.port} is working")
            else:
                print(f"[FAIL] HTTP proxy {proxy.host}:{proxy.port} failed (status: {response.status_code})")
        except Exception as e:
            print(f"[FAIL] HTTP proxy {proxy.host}:{proxy.port} test failed: {str(e)}")

    if working_count == 0:
        print("\nNo working HTTP/S proxies found!")
        print("Please check your proxy configuration or disable proxy usage.")
        return False
    else:
        print(f"\n[OK] Found {working_count} working HTTP/S proxies. Proceeding with account creation.")
        return True

def run_account_creation(config: Dict):
    """Main function to run the account creation process with multiprocessing."""
    num_accounts = config['num_accounts']
    num_processes = config['num_processes']
    use_proxies = config['use_proxies']

    print("\n" + "="*43)
    print(f"Creating {num_accounts} {config['account_type']} accounts using {num_processes} processes...")
    print(f"Proxy usage: {'Enabled' if use_proxies else 'Disabled'}")
    print("="*43 + "\n")

    if use_proxies:
        proxy_list = config.get('proxy_list', [])
        if not proxy_list:
            print("ERROR: Proxies are enabled, but the proxy list is empty.")
            return

        print("=== ENHANCED PROXY ROTATION STRATEGY ===")
        print("📊 PROXY CONFIGURATION:")
        print(f"  Total proxies available: {len(proxy_list)}")
        print(f"  Total accounts to create: {num_accounts}")
        print(f"  Worker processes: {num_processes}")
        print("\n🔄 ROTATION STRATEGY:")
        print("  ✅ Each account = Different proxy (GUARANTEED)")
        print("  ✅ Each browser profile = Unique proxy assignment")
        print("  ✅ Round-robin rotation through all proxies")
        print("  ✅ Perfect proxy isolation for maximum anonymity")

        if len(proxy_list) < num_accounts:
            print("\n📈 DISTRIBUTION:")
            print(f"  ⚠️  WARNING: Fewer proxies ({len(proxy_list)}) than accounts ({num_accounts})")
            print("  ⚠️  Proxies will be reused, but still rotated for each new account.")
        else:
            print("\n📈 DISTRIBUTION:")
            print("  🎯 PERFECT: More proxies than accounts!")
            print("  🎯 Each account will use a completely different proxy")
        print("="*40)

    # Use a multiprocessing Manager to share state
    with multiprocessing.Manager() as manager:
        proxy_pool = None
        if use_proxies:
            proxy_list = config.get('proxy_list', [])
            if not proxy_list:
                print("ERROR: Proxies are enabled, but the proxy list is empty.")
                return
            
            proxy_pool = ProxyPool(proxy_list, manager)

        # Use a semaphore to limit concurrent browser profile creation
        profile_semaphore = manager.Semaphore(num_processes)

        processes = []
        for i in range(num_processes):
            p = multiprocessing.Process(
                target=worker_process,
                args=(i, num_accounts, num_processes, config, profile_semaphore, proxy_pool)
            )
            processes.append(p)
            p.start()
            print(f"✅ Started worker process {i} (PID: {p.pid})")

        print(f"🚀 All {num_processes} worker processes started successfully!")
        print("🔍 Monitoring processes to ensure they all stay active...")

        try:
            import time
            while True:
                # Check if all processes are still alive
                alive_processes = [p for p in processes if p.is_alive()]
                
                if len(alive_processes) != num_processes:
                    dead_count = num_processes - len(alive_processes)
                    print(f"⚠️  WARNING: {dead_count} processes have stopped! This should not happen.")
                    print(f"Active processes: {len(alive_processes)}/{num_processes}")
                
                # Check if all processes are done (normal completion)
                if all(not p.is_alive() for p in processes):
                    print("✅ All worker processes completed their work normally")
                    break
                
                # Status update every 2 minutes
                time.sleep(120)
                active_count = len([p for p in processes if p.is_alive()])
                print(f"📊 Status: {active_count}/{num_processes} processes still active")
                
        except KeyboardInterrupt:
            print("\n⏹️  Process interrupted by user")
            for p in processes:
                if p.is_alive():
                    p.terminate()
                    p.join()

    print("\n" + "="*50)
    print("🎯 ACCOUNT CREATION SUMMARY")
    print("="*50)
    print(f"✅ Total accounts requested: {num_accounts}")
    print(f"⚙️  Processes used: {num_processes}")
    print(f"🔄 Proxy usage: {'Enabled' if use_proxies else 'Disabled'}")
    
    # Try to read worker summary files for detailed stats
    try:
        import os
        import glob
        total_successful = 0
        total_failed = 0
        
        summary_files = glob.glob('credentials/worker_*_summary.txt')
        if summary_files:
            print(f"\n📊 WORKER PERFORMANCE:")
            for summary_file in summary_files:
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract stats from summary file
                        if 'Successful:' in content and 'Failed:' in content:
                            worker_id = summary_file.split('worker_')[1].split('_summary')[0]
                            successful_line = [line for line in content.split('\n') if 'Successful:' in line][0]
                            failed_line = [line for line in content.split('\n') if 'Failed:' in line][0]
                            successful = int(successful_line.split('Successful:')[1].strip())
                            failed = int(failed_line.split('Failed:')[1].strip())
                            total_successful += successful
                            total_failed += failed
                            print(f"  Worker {worker_id}: ✅ {successful} successful, ❌ {failed} failed")
                except Exception:
                    continue
            
            print(f"\n🎯 OVERALL RESULTS:")
            print(f"  ✅ Total successful accounts: {total_successful}")
            print(f"  ❌ Total failed attempts: {total_failed}")
            if total_successful + total_failed > 0:
                success_rate = (total_successful / (total_successful + total_failed)) * 100
                print(f"  📈 Success rate: {success_rate:.1f}%")
        else:
            print("📋 No worker summary files found. Check credentials folder for individual account files.")
            
    except Exception as e:
        print("📋 Could not generate detailed summary. Check credentials folder for results.")
    
    print("="*50)
    print("✅ All workers finished.")

def main():
    """Main entry point optimized for background execution"""
    try:
        # Check if running in background mode (no TTY)
        import sys
        background_mode = not sys.stdin.isatty()
        
        if background_mode:
            # Background mode: load config silently
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                print("Background mode: Using existing configuration")
            except:
                # Default background config
                config = {
                    "account_type": "hotmail",
                    "num_accounts": 10,
                    "num_processes": 2,
                    "use_proxies": False,
                    "proxy_list": []
                }
                print("Background mode: Using default configuration")
        else:
            # Interactive mode
            print("\n=== Hotmail Account Creator ===")
            print("1. Start new session")
            print("2. Load previous configuration")
            print("3. Exit")
            
            while True:
                try:
                    choice = int(input("\nChoose an option (1-3): "))
                    if 1 <= choice <= 3:
                        break
                    print("Please enter a number between 1 and 3")
                except ValueError:
                    print("Please enter a valid number")
            
            if choice == 3:
                print("\nGoodbye!")
                return
            
            if choice == 2:
                try:
                    with open('config.json', 'r') as f:
                        config = json.load(f)
                    print("\nLoaded previous configuration:")
                    print(f"Accounts to create: {config['num_accounts']}")
                    print(f"Number of processes: {config['num_processes']}")
                    print(f"Number of proxies: {len(config['proxy_list'])}")
                    
                    use_previous = input("\nUse this configuration? (y/n): ").lower() == 'y'
                    if not use_previous:
                        config = get_user_input()
                except FileNotFoundError:
                    print("\nNo previous configuration found")
                    config = get_user_input()
                except Exception as e:
                    print(f"\nError loading configuration: {str(e)}")
                    config = get_user_input()
            else:
                config = get_user_input()
        
        # Run the main process
        run_account_creation(config)
    except KeyboardInterrupt:
        if not background_mode:
            print("\nProcess interrupted by user")
    except Exception as e:
        if not background_mode:
            print(f"\nError in main process: {str(e)}")
    finally:
        # Quick cleanup for background processes
        try:
            for p in multiprocessing.active_children():
                p.terminate()
                p.join(timeout=5)  # 5 second timeout
        except:
            pass

if __name__ == "__main__":
    # Check if this is being run as a test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running blank page fix test...")
        asyncio.run(test_blank_page_fix())
    else:
        # Set up multiprocessing start method
        multiprocessing.set_start_method('spawn', force=True)
        main()
