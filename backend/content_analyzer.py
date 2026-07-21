"""
Lightweight Content Analyzer Module
====================================
Performs lightweight content analysis on suspicious URLs without full crawling.

Analyzes:
- Page title keywords (login, verify, secure, update)
- Password input fields
- Form tags
- Brand keyword impersonation

Does NOT perform:
- Deep JavaScript execution
- Screenshot analysis
- Full page crawling
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import time


class ContentAnalyzer:
    """
    Lightweight content analyzer for suspicious URLs.
    """
    
    def __init__(self):
        """
        Initialize the content analyzer.
        """
        self.timeout = 10  # Maximum time to wait for page load
        self.max_content_size = 500000  # 500KB max content size
        
        # Suspicious keywords in page title/content
        self.suspicious_keywords = [
            'login', 'verify', 'account', 'update', 'secure', 'banking',
            'confirm', 'password', 'signin', 'suspended', 'locked',
            'validate', 'authentication', 'credential', 'urgent', 'alert',
            'expire', 'renew', 'restore', 'recover', 'reset'
        ]
        
        # Brand keywords for impersonation detection
        self.brand_keywords = [
            'paypal', 'amazon', 'google', 'microsoft', 'apple', 'facebook',
            'netflix', 'instagram', 'twitter', 'linkedin', 'ebay', 'walmart',
            'paytm', 'phonepe', 'gpay', 'sbi', 'hdfc', 'icici', 'axis',
            'kotak', 'bank', 'payment', 'wallet'
        ]
    
    def analyze_content(self, url):
        """
        Perform lightweight content analysis on a URL.
        
        Args:
            url (str): URL to analyze
            
        Returns:
            dict: {
                'success': bool,
                'risk_score': int (0-100),
                'indicators': list of suspicious indicators found,
                'details': dict with analysis details
            }
        """
        print(f"\n[CONTENT ANALYZER] Analyzing {url}...")
        
        try:
            # Fetch page content with safety measures
            html_content = self._fetch_page_safely(url)
            
            if not html_content:
                return {
                    'success': False,
                    'risk_score': 0,
                    'indicators': [],
                    'details': {'error': 'Failed to fetch page content'}
                }
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Perform analysis
            indicators = []
            details = {}
            risk_score = 0
            
            # 1. Check page title for suspicious keywords
            title_result = self._check_title(soup)
            if title_result['is_suspicious']:
                indicators.append(f"Suspicious title: {title_result['keywords_found']}")
                risk_score += 20
                details['title'] = title_result
            
            # 2. Check for password input fields
            password_result = self._check_password_fields(soup)
            if password_result['has_password_field']:
                indicators.append(f"Password field detected ({password_result['count']} fields)")
                risk_score += 25
                details['password_fields'] = password_result
            
            # 3. Check for form tags
            form_result = self._check_forms(soup)
            if form_result['has_forms']:
                indicators.append(f"Form detected ({form_result['count']} forms)")
                risk_score += 15
                details['forms'] = form_result
            
            # 4. Check for brand impersonation
            brand_result = self._check_brand_impersonation(soup, url)
            if brand_result['is_impersonating']:
                indicators.append(f"Brand impersonation: {brand_result['brands_found']}")
                risk_score += 30
                details['brand_impersonation'] = brand_result
            
            # 5. Check for suspicious meta tags
            meta_result = self._check_meta_tags(soup)
            if meta_result['is_suspicious']:
                indicators.append(f"Suspicious meta tags: {meta_result['issues']}")
                risk_score += 10
                details['meta_tags'] = meta_result
            
            # Cap risk score at 100
            risk_score = min(risk_score, 100)
            
            print(f"[CONTENT ANALYZER] Risk Score: {risk_score}/100")
            print(f"[CONTENT ANALYZER] Indicators: {len(indicators)} found")
            
            return {
                'success': True,
                'risk_score': risk_score,
                'indicators': indicators,
                'details': details
            }
            
        except Exception as e:
            print(f"[CONTENT ANALYZER] Error: {str(e)}")
            return {
                'success': False,
                'risk_score': 0,
                'indicators': [],
                'details': {'error': str(e)}
            }
    
    def _fetch_page_safely(self, url):
        """
        Safely fetch page content with timeout and size limits.
        
        Args:
            url (str): URL to fetch
            
        Returns:
            str: HTML content or None
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Stream response to check size
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                stream=True,
                allow_redirects=True,
                verify=False  # Skip SSL verification for phishing sites
            )
            
            # Check content size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_content_size:
                print(f"[CONTENT ANALYZER] Content too large ({content_length} bytes), skipping")
                return None
            
            # Read content with size limit
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.max_content_size:
                    print(f"[CONTENT ANALYZER] Content exceeded limit, truncating")
                    break
            
            return content.decode('utf-8', errors='ignore')
            
        except requests.Timeout:
            print(f"[CONTENT ANALYZER] Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"[CONTENT ANALYZER] Error fetching {url}: {str(e)}")
            return None
    
    def _check_title(self, soup):
        """
        Check page title for suspicious keywords.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            dict: Analysis result
        """
        title_tag = soup.find('title')
        if not title_tag:
            return {'is_suspicious': False, 'keywords_found': []}
        
        title_text = title_tag.get_text().lower()
        keywords_found = [kw for kw in self.suspicious_keywords if kw in title_text]
        
        return {
            'is_suspicious': len(keywords_found) > 0,
            'keywords_found': keywords_found,
            'title': title_text[:100]  # First 100 chars
        }
    
    def _check_password_fields(self, soup):
        """
        Check for password input fields.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            dict: Analysis result
        """
        password_fields = soup.find_all('input', {'type': 'password'})
        
        return {
            'has_password_field': len(password_fields) > 0,
            'count': len(password_fields)
        }
    
    def _check_forms(self, soup):
        """
        Check for form tags.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            dict: Analysis result
        """
        forms = soup.find_all('form')
        
        # Check if forms have suspicious action URLs
        suspicious_actions = []
        for form in forms:
            action = form.get('action', '')
            if action and ('login' in action.lower() or 'signin' in action.lower()):
                suspicious_actions.append(action)
        
        return {
            'has_forms': len(forms) > 0,
            'count': len(forms),
            'suspicious_actions': suspicious_actions
        }
    
    def _check_brand_impersonation(self, soup, url):
        """
        Check for brand keyword impersonation.
        
        Args:
            soup: BeautifulSoup object
            url: str - Original URL
            
        Returns:
            dict: Analysis result
        """
        # Get page text content
        page_text = soup.get_text().lower()
        
        # Extract domain from URL
        domain = urlparse(url).netloc.lower()
        
        # Find brand keywords in page content
        brands_in_content = [brand for brand in self.brand_keywords if brand in page_text]
        
        # Check if brand is in content but NOT in domain (impersonation)
        impersonating_brands = []
        for brand in brands_in_content:
            if brand not in domain:
                impersonating_brands.append(brand)
        
        return {
            'is_impersonating': len(impersonating_brands) > 0,
            'brands_found': impersonating_brands,
            'brands_in_content': brands_in_content
        }
    
    def _check_meta_tags(self, soup):
        """
        Check meta tags for suspicious patterns.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            dict: Analysis result
        """
        issues = []
        
        # Check meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            content = meta_desc.get('content', '').lower()
            suspicious_in_desc = [kw for kw in self.suspicious_keywords if kw in content]
            if suspicious_in_desc:
                issues.append(f"Suspicious keywords in description: {suspicious_in_desc}")
        
        # Check for refresh/redirect meta tags (common in phishing)
        meta_refresh = soup.find('meta', {'http-equiv': 'refresh'})
        if meta_refresh:
            issues.append("Auto-refresh meta tag detected")
        
        return {
            'is_suspicious': len(issues) > 0,
            'issues': issues
        }


# Singleton instance
_content_analyzer = None

def get_content_analyzer():
    """
    Get or create the content analyzer instance.
    
    Returns:
        ContentAnalyzer: Singleton instance
    """
    global _content_analyzer
    if _content_analyzer is None:
        _content_analyzer = ContentAnalyzer()
    return _content_analyzer


# Example usage
if __name__ == "__main__":
    analyzer = ContentAnalyzer()
    
    # Test with a URL
    test_url = "https://www.google.com"
    result = analyzer.analyze_content(test_url)
    
    print("\n" + "=" * 80)
    print("CONTENT ANALYSIS RESULT")
    print("=" * 80)
    print(f"URL: {test_url}")
    print(f"Success: {result['success']}")
    print(f"Risk Score: {result['risk_score']}/100")
    print(f"Indicators: {result['indicators']}")
    print("=" * 80)
