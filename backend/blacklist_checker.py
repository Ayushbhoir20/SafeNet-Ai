"""
External Blacklist Checker Module
==================================
Checks URLs against external phishing databases:
1. PhishTank (free, no API key required)
2. Google Safe Browsing API (optional, requires API key)

This module provides fast blacklist verification without opening URLs.
"""

import requests
import hashlib
import time
from urllib.parse import urlparse, quote
import json


class BlacklistChecker:
    """
    Check URLs against external phishing blacklists.
    """
    
    def __init__(self, google_api_key=None):
        """
        Initialize the blacklist checker.
        
        Args:
            google_api_key (str): Optional Google Safe Browsing API key
        """
        self.google_api_key = google_api_key
        self.phishtank_url = "https://checkurl.phishtank.com/checkurl/"
        self.cache = {}  # Simple cache to avoid repeated checks
        self.cache_timeout = 3600  # 1 hour cache
        
    def check_url(self, url):
        """
        Check URL against all available blacklists.
        
        Args:
            url (str): URL to check
            
        Returns:
            dict: {
                'is_blacklisted': bool,
                'source': str (PhishTank/Google/None),
                'details': str
            }
        """
        # Check cache first
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.cache:
            cached_time, cached_result = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                print(f"[CACHE HIT] Blacklist result for {url}")
                return cached_result
        
        # Try PhishTank first (free, no API key needed)
        phishtank_result = self._check_phishtank(url)
        if phishtank_result['is_blacklisted']:
            self.cache[cache_key] = (time.time(), phishtank_result)
            return phishtank_result
        
        # Try Google Safe Browsing if API key is available
        if self.google_api_key:
            google_result = self._check_google_safe_browsing(url)
            if google_result['is_blacklisted']:
                self.cache[cache_key] = (time.time(), google_result)
                return google_result
        
        # Not found in any blacklist
        result = {
            'is_blacklisted': False,
            'source': None,
            'details': 'URL not found in blacklists'
        }
        self.cache[cache_key] = (time.time(), result)
        return result
    
    def _check_phishtank(self, url):
        """
        Check URL against PhishTank database.
        
        Args:
            url (str): URL to check
            
        Returns:
            dict: Blacklist check result
        """
        try:
            print(f"[PHISHTANK] Checking {url}...")
            
            # PhishTank API endpoint
            # Note: PhishTank requires POST request with specific format
            headers = {
                'User-Agent': 'phishtank/PhishingDetectionSystem'
            }
            
            data = {
                'url': url,
                'format': 'json',
                'app_key': ''  # Optional: Register for API key at phishtank.com
            }
            
            # Use timeout to prevent hanging
            response = requests.post(
                self.phishtank_url,
                data=data,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # PhishTank returns results with 'in_database' field
                if result.get('results', {}).get('in_database'):
                    is_phishing = result['results'].get('valid', False)
                    
                    if is_phishing:
                        print(f"[PHISHTANK] ⚠️ URL found in PhishTank database as PHISHING")
                        return {
                            'is_blacklisted': True,
                            'source': 'PhishTank',
                            'details': f"PhishTank ID: {result['results'].get('phish_id', 'Unknown')}"
                        }
            
            print(f"[PHISHTANK] URL not found in database")
            return {
                'is_blacklisted': False,
                'source': None,
                'details': 'Not in PhishTank database'
            }
            
        except requests.Timeout:
            print(f"[PHISHTANK] Timeout - skipping check")
            return {'is_blacklisted': False, 'source': None, 'details': 'Timeout'}
        except Exception as e:
            print(f"[PHISHTANK] Error: {str(e)}")
            return {'is_blacklisted': False, 'source': None, 'details': f'Error: {str(e)}'}
    
    def _check_google_safe_browsing(self, url):
        """
        Check URL against Google Safe Browsing API.
        
        Args:
            url (str): URL to check
            
        Returns:
            dict: Blacklist check result
        """
        if not self.google_api_key:
            return {'is_blacklisted': False, 'source': None, 'details': 'No API key'}
        
        try:
            print(f"[GOOGLE SAFE BROWSING] Checking {url}...")
            
            api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={self.google_api_key}"
            
            payload = {
                "client": {
                    "clientId": "phishing-detection-system",
                    "clientVersion": "1.0.0"
                },
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url}]
                }
            }
            
            response = requests.post(api_url, json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'matches' in result and len(result['matches']) > 0:
                    threat_type = result['matches'][0].get('threatType', 'UNKNOWN')
                    print(f"[GOOGLE SAFE BROWSING] ⚠️ URL flagged as {threat_type}")
                    
                    return {
                        'is_blacklisted': True,
                        'source': 'Google Safe Browsing',
                        'details': f"Threat Type: {threat_type}"
                    }
            
            print(f"[GOOGLE SAFE BROWSING] URL is safe")
            return {
                'is_blacklisted': False,
                'source': None,
                'details': 'Not flagged by Google Safe Browsing'
            }
            
        except requests.Timeout:
            print(f"[GOOGLE SAFE BROWSING] Timeout - skipping check")
            return {'is_blacklisted': False, 'source': None, 'details': 'Timeout'}
        except Exception as e:
            print(f"[GOOGLE SAFE BROWSING] Error: {str(e)}")
            return {'is_blacklisted': False, 'source': None, 'details': f'Error: {str(e)}'}


# Singleton instance
_blacklist_checker = None

def get_blacklist_checker(google_api_key=None):
    """
    Get or create the blacklist checker instance.
    
    Args:
        google_api_key (str): Optional Google Safe Browsing API key
        
    Returns:
        BlacklistChecker: Singleton instance
    """
    global _blacklist_checker
    if _blacklist_checker is None:
        _blacklist_checker = BlacklistChecker(google_api_key)
    return _blacklist_checker


# Example usage
if __name__ == "__main__":
    checker = BlacklistChecker()
    
    # Test with known phishing URL (example)
    test_url = "http://example-phishing-site.com"
    result = checker.check_url(test_url)
    
    print("\n" + "=" * 80)
    print("BLACKLIST CHECK RESULT")
    print("=" * 80)
    print(f"URL: {test_url}")
    print(f"Is Blacklisted: {result['is_blacklisted']}")
    print(f"Source: {result['source']}")
    print(f"Details: {result['details']}")
    print("=" * 80)
