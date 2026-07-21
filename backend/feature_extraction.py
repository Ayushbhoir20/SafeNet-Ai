"""
Feature Extraction Module for Phishing Detection (Production-Ready)
====================================================================
This module extracts comprehensive features from URLs for phishing detection.

Enhanced Features (20+ total):
1. URL Lexical Features: length, dots, hyphens, special chars, uppercase ratio, etc.
2. HTTPS and IP Detection: Protocol security and IP address usage
3. Domain Features: subdomain count, domain length, TLD analysis
4. Path/Query Features: path length, query parameters
5. Entropy and Randomness: URL entropy, digit ratio, letter ratio
6. Suspicious Patterns: suspicious words, URL shorteners, typosquatting
7. WHOIS Features: domain age, registration length, privacy protection, registrar reputation
8. Advanced Lexical: consecutive consonants, uppercase ratio, TLD reputation
"""

import re
import math
import whois
import validators
import tldextract
from datetime import datetime
from urllib.parse import urlparse
import socket


def extract_url_features(url):
    """
    Extract all features from a given URL.
    
    Args:
        url (str): The URL to analyze
        
    Returns:
        dict: Dictionary containing all extracted features
    """
    features = {}
    
    try:
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        # Basic URL features
        features['url_length'] = len(url)
        features['num_dots'] = url.count('.')
        features['num_hyphens'] = url.count('-')
        features['num_underscores'] = url.count('_')
        features['num_slashes'] = url.count('/')
        features['num_questionmarks'] = url.count('?')
        features['num_equals'] = url.count('=')
        features['num_at'] = url.count('@')
        features['num_ampersand'] = url.count('&')
        features['num_exclamation'] = url.count('!')
        features['num_tilde'] = url.count('~')
        features['num_percent'] = url.count('%')
        
        # NEW: Total special characters count
        features['num_special_chars_total'] = sum([
            features['num_hyphens'], features['num_underscores'],
            features['num_at'], features['num_ampersand'],
            features['num_exclamation'], features['num_tilde'],
            features['num_percent']
        ])
        
        # HTTPS check
        features['has_https'] = 1 if url.startswith('https://') else 0
        
        # IP address detection
        features['has_ip'] = check_ip_address(url)
        
        # Parse URL components
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Extract domain information
        ext = tldextract.extract(url)
        features['subdomain_count'] = len(ext.subdomain.split('.')) if ext.subdomain else 0
        
        # Domain length
        features['domain_length'] = len(domain)
        
        # Path length
        features['path_length'] = len(parsed.path)
        
        # Query length
        features['query_length'] = len(parsed.query) if parsed.query else 0
        
        # Special character ratio
        special_chars = sum([features['num_hyphens'], features['num_underscores'], 
                           features['num_at'], features['num_ampersand']])
        features['special_char_ratio'] = special_chars / len(url) if len(url) > 0 else 0
        
        # URL entropy (randomness measure)
        features['url_entropy'] = calculate_entropy(url)
        
        # Digit ratio
        digit_count = sum(c.isdigit() for c in url)
        features['digit_ratio'] = digit_count / len(url) if len(url) > 0 else 0
        
        # Letter ratio
        letter_count = sum(c.isalpha() for c in url)
        features['letter_ratio'] = letter_count / len(url) if len(url) > 0 else 0
        
        # NEW: Uppercase ratio (phishing URLs often use mixed case for obfuscation)
        uppercase_count = sum(c.isupper() for c in url)
        features['uppercase_ratio'] = uppercase_count / letter_count if letter_count > 0 else 0
        
        # NEW: Consecutive consonants (detect random strings like "xkzpqr")
        features['consecutive_consonants_max'] = calculate_max_consecutive_consonants(domain)
        
        # NEW: Suspicious TLD detection
        features['tld_suspicious'] = check_suspicious_tld(ext.suffix)
        
        # Suspicious words detection
        suspicious_words = ['login', 'verify', 'account', 'update', 'secure', 
                          'banking', 'confirm', 'password', 'signin']
        features['has_suspicious_words'] = any(word in url.lower() for word in suspicious_words)
        features['has_suspicious_words'] = 1 if features['has_suspicious_words'] else 0
        
        # Enhanced WHOIS features
        whois_data = get_whois_info(domain)
        features['domain_age_days'] = whois_data['domain_age_days']
        features['registration_length_days'] = whois_data['registration_length_days']
        features['privacy_protection_flag'] = whois_data['privacy_protection_flag']
        features['registrar_reputation'] = whois_data['registrar_reputation']
        
        # Shortening service detection - STRICT domain matching only
        # Extract the actual domain to avoid false positives
        ext_for_shortener = tldextract.extract(url)
        full_domain = f"{ext_for_shortener.domain}.{ext_for_shortener.suffix}".lower()
        
        shortening_services = [
            'bit.ly', 'goo.gl', 'tinyurl.com', 't.co', 'ow.ly', 
            'cutt.ly', 'tiny.cc', 'is.gd', 'buff.ly', 'rebrand.ly'
        ]
        features['is_shortened'] = 1 if full_domain in shortening_services else 0
        
    except Exception as e:
        print(f"Error extracting features from {url}: {str(e)}")
        # Return default features on error
        return get_default_features()
    
    return features


def check_ip_address(url):
    """
    Check if URL contains an IP address instead of domain name.
    
    Args:
        url (str): URL to check
        
    Returns:
        int: 1 if IP address found, 0 otherwise
    """
    try:
        # Extract domain from URL
        domain = urlparse(url).netloc
        # Remove port if present
        domain = domain.split(':')[0]
        
        # Check if it's an IP address
        socket.inet_aton(domain)
        return 1
    except:
        return 0


def calculate_entropy(string):
    """
    Calculate Shannon entropy of a string (measure of randomness).
    Higher entropy = more random = potentially suspicious
    
    Args:
        string (str): String to calculate entropy for
        
    Returns:
        float: Entropy value
    """
    if not string:
        return 0
    
    # Calculate frequency of each character
    freq = {}
    for char in string:
        freq[char] = freq.get(char, 0) + 1
    
    # Calculate entropy
    entropy = 0
    length = len(string)
    for count in freq.values():
        probability = count / length
        entropy -= probability * math.log2(probability)
    
    return entropy


def calculate_max_consecutive_consonants(string):
    """
    Calculate the maximum number of consecutive consonants in a string.
    High values indicate random/suspicious domain names.
    
    Args:
        string (str): String to analyze
        
    Returns:
        int: Maximum consecutive consonants count
    """
    if not string:
        return 0
    
    consonants = 'bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ'
    max_consecutive = 0
    current_consecutive = 0
    
    for char in string:
        if char in consonants:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    return max_consecutive


def check_suspicious_tld(tld):
    """
    Check if the TLD (top-level domain) is commonly used for phishing.
    
    Args:
        tld (str): Top-level domain (e.g., 'com', 'tk', 'ml')
        
    Returns:
        int: 1 if suspicious TLD, 0 otherwise
    """
    # Free TLDs commonly abused for phishing
    suspicious_tlds = ['tk', 'ml', 'ga', 'cf', 'gq', 'pw', 'cc', 'info', 'xyz']
    return 1 if tld.lower() in suspicious_tlds else 0


def get_whois_info(domain):
    """
    Get comprehensive WHOIS information for a domain.
    Uses WhoisXML API as primary source, falls back to python-whois library.
    
    Args:
        domain (str): Domain name to lookup
        
    Returns:
        dict: Dictionary with domain_age_days, registration_length_days, 
              privacy_protection_flag, registrar_reputation, registrar, expiry_date,
              creation_date, domain_name
    """
    import os
    import requests
    
    # Default values for failed lookups - using "Not Available" instead of "Unknown"
    default_result = {
        'domain_age_days': -1,
        'registration_length_days': -1,
        'privacy_protection_flag': 0,
        'registrar_reputation': 0,
        'registrar': 'Not Available',
        'expiry_date': 'Not Available',
        'creation_date': 'Not Available',
        'domain_name': 'Not Available'
    }
    
    try:
        # Remove port and subdomain - get clean domain
        ext = tldextract.extract(domain)
        clean_domain = f"{ext.domain}.{ext.suffix}"
        
        # Try WhoisXML API first (if API key is set)
        whoisxml_api_key = os.getenv('WHOISXML_API_KEY', '')
        
        if whoisxml_api_key and whoisxml_api_key != 'your_whoisxml_api_key_here':
            try:
                api_url = f"https://www.whoisxmlapi.com/whoisserver/WhoisService"
                params = {
                    'apiKey': whoisxml_api_key,
                    'domainName': clean_domain,
                    'outputFormat': 'JSON'
                }
                response = requests.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    whois_record = data.get('WhoisRecord', {})
                    
                    # Extract registrar info
                    registrar_name = whois_record.get('registrarName', 'Not Available')
                    
                    # Extract dates
                    created_date_str = whois_record.get('createdDate', '')
                    expires_date_str = whois_record.get('expiresDate', '')
                    
                    # Parse creation date
                    creation_date = None
                    creation_display = 'Not Available'
                    if created_date_str:
                        try:
                            creation_date = datetime.strptime(created_date_str[:10], '%Y-%m-%d')
                            creation_display = creation_date.strftime('%b %d, %Y')
                        except:
                            creation_display = created_date_str[:10] if len(created_date_str) >= 10 else 'Not Available'
                    
                    # Parse expiry date
                    expiry_date = None
                    expiry_display = 'Not Available'
                    if expires_date_str:
                        try:
                            expiry_date = datetime.strptime(expires_date_str[:10], '%Y-%m-%d')
                            expiry_display = expiry_date.strftime('%b %d, %Y')
                        except:
                            expiry_display = expires_date_str[:10] if len(expires_date_str) >= 10 else 'Not Available'
                    
                    # Calculate domain age
                    domain_age = -1
                    if creation_date:
                        domain_age = (datetime.now() - creation_date).days
                    
                    # Calculate registration length
                    registration_length = -1
                    if creation_date and expiry_date:
                        registration_length = (expiry_date - creation_date).days
                    
                    # Check privacy protection
                    privacy_flag = 0
                    privacy_keywords = ['privacy', 'private', 'protection', 'proxy', 'whoisguard', 'redacted']
                    if registrar_name and registrar_name != 'Not Available':
                        registrar_lower = registrar_name.lower()
                        privacy_flag = 1 if any(keyword in registrar_lower for keyword in privacy_keywords) else 0
                    
                    return {
                        'domain_age_days': domain_age,
                        'registration_length_days': registration_length,
                        'privacy_protection_flag': privacy_flag,
                        'registrar_reputation': calculate_registrar_reputation(registrar_name),
                        'registrar': registrar_name if registrar_name else 'Not Available',
                        'expiry_date': expiry_display,
                        'creation_date': creation_display,
                        'domain_name': clean_domain
                    }
            except Exception as api_error:
                print(f"WhoisXML API error for {clean_domain}: {str(api_error)}")
        
        # Fallback to python-whois library
        w = whois.whois(clean_domain)
        
        # Get creation date
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        
        # Calculate domain age
        age = -1
        creation_display = 'Not Available'
        if creation_date:
            age = (datetime.now() - creation_date).days
            creation_display = creation_date.strftime('%b %d, %Y')
        
        # Get registrar
        registrar = w.registrar if hasattr(w, 'registrar') and w.registrar else 'Not Available'
        
        # Get expiry date
        expiry_date = w.expiration_date
        if isinstance(expiry_date, list):
            expiry_date = expiry_date[0]
        
        # Calculate registration length
        registration_length = -1
        if creation_date and expiry_date:
            registration_length = (expiry_date - creation_date).days
        
        expiry_display = expiry_date.strftime('%b %d, %Y') if expiry_date else 'Not Available'
        
        # Check for privacy protection
        privacy_flag = 0
        privacy_keywords = ['privacy', 'private', 'protection', 'proxy', 'whoisguard', 'redacted']
        if registrar and registrar != 'Not Available':
            registrar_lower = registrar.lower()
            privacy_flag = 1 if any(keyword in registrar_lower for keyword in privacy_keywords) else 0
        
        return {
            'domain_age_days': age,
            'registration_length_days': registration_length,
            'privacy_protection_flag': privacy_flag,
            'registrar_reputation': calculate_registrar_reputation(registrar),
            'registrar': registrar,
            'expiry_date': expiry_display,
            'creation_date': creation_display,
            'domain_name': clean_domain
        }
        
    except Exception as e:
        print(f"WHOIS lookup failed for {domain}: {str(e)}")
        return default_result


def calculate_registrar_reputation(registrar):
    """
    Calculate reputation score for a domain registrar.
    
    Args:
        registrar (str): Registrar name
        
    Returns:
        int: Reputation score (1=reputable, 0=unknown, -1=suspicious)
    """
    if not registrar or registrar == 'Unknown':
        return 0
    
    registrar_lower = registrar.lower()
    
    # Reputable registrars
    reputable = ['godaddy', 'namecheap', 'google', 'cloudflare', 'amazon', 
                 'network solutions', 'tucows', 'enom', 'gandi', 'hover']
    
    # Suspicious indicators (privacy services, free registrars)
    suspicious = ['privacy', 'private', 'whoisguard', 'proxy', 'protection']
    
    # Check for reputable registrars
    for rep in reputable:
        if rep in registrar_lower:
            return 1
    
    # Check for suspicious indicators
    for sus in suspicious:
        if sus in registrar_lower:
            return -1
    
    # Unknown registrar
    return 0


def get_default_features():
    """
    Return default feature values when extraction fails.
    
    Returns:
        dict: Dictionary with default feature values (includes all 24 features)
    """
    return {
        'url_length': 0,
        'num_dots': 0,
        'num_hyphens': 0,
        'num_underscores': 0,
        'num_slashes': 0,
        'num_questionmarks': 0,
        'num_equals': 0,
        'num_at': 0,
        'num_ampersand': 0,
        'num_exclamation': 0,
        'num_tilde': 0,
        'num_percent': 0,
        'num_special_chars_total': 0,  # NEW
        'has_https': 0,
        'has_ip': 0,
        'subdomain_count': 0,
        'domain_length': 0,
        'path_length': 0,
        'query_length': 0,
        'special_char_ratio': 0,
        'url_entropy': 0,
        'digit_ratio': 0,
        'letter_ratio': 0,
        'uppercase_ratio': 0,  # NEW
        'consecutive_consonants_max': 0,  # NEW
        'tld_suspicious': 0,  # NEW
        'has_suspicious_words': 0,
        'domain_age_days': -1,
        'registration_length_days': -1,  # NEW
        'privacy_protection_flag': 0,  # NEW
        'registrar_reputation': 0,  # NEW
        'is_shortened': 0
    }


def validate_url(url):
    """
    Validate if a string is a valid URL.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    return validators.url(url)


# Example usage and testing
if __name__ == "__main__":
    # Test with sample URLs
    test_urls = [
        "https://www.google.com",
        "http://192.168.1.1/login",
        "https://secure-banking-verify-account.com/update",
        "http://bit.ly/abc123"
    ]
    
    print("=" * 80)
    print("FEATURE EXTRACTION TEST")
    print("=" * 80)
    
    for url in test_urls:
        print(f"\nURL: {url}")
        print("-" * 80)
        
        if validate_url(url):
            features = extract_url_features(url)
            for key, value in features.items():
                print(f"{key:25s}: {value}")
        else:
            print("Invalid URL!")
        
        print("-" * 80)
