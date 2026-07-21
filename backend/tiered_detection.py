"""
Tiered/Hybrid Detection Engine
================================
Industry-grade phishing detection using a three-layer approach:

Layer 1: Fast ML Detection (Random Forest with probability-based classification)
Layer 2: External Blacklist Check (PhishTank, Google Safe Browsing)
Layer 3: Lightweight Content Analysis (only for suspicious URLs)

Classification Levels:
- Safe: Low phishing probability, not blacklisted
- Suspicious: Medium probability or some risk indicators
- Phishing: High probability, blacklisted, or strong evidence

Performance:
- Fast: Most URLs classified in Layer 1 + Layer 2 (< 1 second)
- Selective: Only suspicious URLs undergo content analysis
- Secure: No full crawling or JavaScript execution
"""

import time
from blacklist_checker import get_blacklist_checker
from content_analyzer import get_content_analyzer


class TieredDetectionEngine:
    """
    Three-layer tiered detection engine for phishing URL analysis.
    """
    
    def __init__(self, model, scaler, google_api_key=None):
        """
        Initialize the tiered detection engine.
        
        Args:
            model: Trained ML model
            scaler: Feature scaler
            google_api_key (str): Optional Google Safe Browsing API key
        """
        self.model = model
        self.scaler = scaler
        self.blacklist_checker = get_blacklist_checker(google_api_key)
        self.content_analyzer = get_content_analyzer()
        
        # Thresholds for classification
        self.SAFE_THRESHOLD = 0.25  # Below this = Safe
        self.PHISHING_THRESHOLD = 0.55  # Above this = Phishing
        # Between 0.25 and 0.55 = Suspicious (needs content analysis)
        
        # Store model class order for prediction mapping
        # self.model.classes_ contains [0, 1] where 0=legitimate, 1=phishing
    
    def detect(self, url, features, feature_vector_scaled):
        """
        Perform tiered detection on a URL.
        
        Args:
            url (str): URL to analyze
            features (dict): Extracted URL features
            feature_vector_scaled: Scaled feature vector for ML model
            
        Returns:
            dict: Complete detection result with all layer outputs
        """
        start_time = time.time()
        
        print("\n" + "=" * 80)
        print("TIERED DETECTION ENGINE - STARTING ANALYSIS")
        print("=" * 80)
        
        # ========== LAYER 1: FAST ML DETECTION ==========
        layer1_result = self._layer1_ml_detection(feature_vector_scaled)
        
        # ========== LAYER 2: EXTERNAL BLACKLIST CHECK ==========
        layer2_result = self._layer2_blacklist_check(url)
        
        # If blacklisted, immediately return as Phishing
        if layer2_result['is_blacklisted']:
            final_classification = "Phishing"
            final_confidence = 95.0
            content_analysis_performed = False
            layer3_result = None
            
            print(f"\n[FINAL DECISION] {final_classification} (Blacklisted)")
            
        else:
            # ========== LAYER 3: CONTENT ANALYSIS (CONDITIONAL) ==========
            # Only perform content analysis if ML result is "Suspicious"
            if layer1_result['classification'] == "Suspicious":
                layer3_result = self._layer3_content_analysis(url)
                content_analysis_performed = True
                
                # Make final decision based on ML + Content analysis
                final_classification, final_confidence = self._make_final_decision(
                    layer1_result, layer3_result
                )
            else:
                # ML result is Safe or Phishing, no content analysis needed
                final_classification = layer1_result['classification']
                final_confidence = layer1_result['confidence']
                content_analysis_performed = False
                layer3_result = None
                
                print(f"\n[LAYER 3] Skipped (ML classification: {final_classification})")
                print(f"[FINAL DECISION] {final_classification} (ML only)")
        
        # Calculate total processing time
        processing_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
        
        print("=" * 80)
        print(f"DETECTION COMPLETE - {processing_time}ms")
        print("=" * 80 + "\n")
        
        # Return comprehensive result
        return {
            'final_classification': final_classification,
            'final_confidence': final_confidence,
            'processing_time_ms': processing_time,
            'layers': {
                'layer1_ml': layer1_result,
                'layer2_blacklist': layer2_result,
                'layer3_content': layer3_result if content_analysis_performed else None
            },
            'content_analysis_performed': content_analysis_performed,
            'detection_path': self._get_detection_path(
                layer1_result, layer2_result, content_analysis_performed
            )
        }
    
    def _layer1_ml_detection(self, feature_vector_scaled):
        """
        Layer 1: Fast ML-based detection using Random Forest.
        
        Args:
            feature_vector_scaled: Scaled feature vector
            
        Returns:
            dict: ML detection result
        """
        print("\n[LAYER 1] ML Detection (Random Forest)")
        print("-" * 80)
        
        # Get probability predictions
        prediction_proba = self.model.predict_proba(feature_vector_scaled)[0]
        
        # Debug: Print raw probabilities and class order
        print(f"[DEBUG] Model classes: {self.model.classes_}")
        print(f"[DEBUG] Raw probabilities: {prediction_proba}")
        
        # Dynamically map probabilities based on model.classes_
        # Find indices for legitimate (0) and phishing (1) classes
        class_to_idx = {cls: idx for idx, cls in enumerate(self.model.classes_)}
        
        # Get probabilities for each class
        # The model might have classes as [0, 1] or [1, 0] or ['legitimate', 'phishing'], etc.
        if 0 in class_to_idx:
            legitimate_idx = class_to_idx[0]
            legitimate_prob = float(prediction_proba[legitimate_idx])
        elif 'legitimate' in class_to_idx:
            legitimate_idx = class_to_idx['legitimate']
            legitimate_prob = float(prediction_proba[legitimate_idx])
        else:
            # Fallback: assume first class is legitimate
            legitimate_prob = float(prediction_proba[0])
        
        if 1 in class_to_idx:
            phishing_idx = class_to_idx[1]
            phishing_prob = float(prediction_proba[phishing_idx])
        elif 'phishing' in class_to_idx:
            phishing_idx = class_to_idx['phishing']
            phishing_prob = float(prediction_proba[phishing_idx])
        else:
            # Fallback: assume second class is phishing
            phishing_prob = float(prediction_proba[1])
        
        # Debug: Print mapped probabilities
        print(f"[DEBUG] Mapped - Legitimate: {legitimate_prob:.4f}, Phishing: {phishing_prob:.4f}")
        
        # Classify based on thresholds
        if phishing_prob < self.SAFE_THRESHOLD:
            classification = "Safe"
            confidence = legitimate_prob * 100
        elif phishing_prob > self.PHISHING_THRESHOLD:
            classification = "Phishing"
            confidence = phishing_prob * 100
        else:
            classification = "Suspicious"
            confidence = 50.0 + (phishing_prob - 0.5) * 100  # Scale to 50-100
        
        print(f"Probabilities: Legitimate={legitimate_prob:.4f}, Phishing={phishing_prob:.4f}")
        print(f"Thresholds: Safe<{self.SAFE_THRESHOLD}, Phishing>{self.PHISHING_THRESHOLD}")
        print(f"Classification: {classification} (Confidence: {confidence:.2f}%)")
        
        return {
            'classification': classification,
            'confidence': confidence,
            'legitimate_prob': legitimate_prob,
            'phishing_prob': phishing_prob
        }
    
    def _layer2_blacklist_check(self, url):
        """
        Layer 2: Check against external blacklists.
        
        Args:
            url (str): URL to check
            
        Returns:
            dict: Blacklist check result
        """
        print("\n[LAYER 2] External Blacklist Check")
        print("-" * 80)
        
        result = self.blacklist_checker.check_url(url)
        
        if result['is_blacklisted']:
            print(f"⚠️  BLACKLISTED by {result['source']}")
            print(f"Details: {result['details']}")
        else:
            print(f"✓ Not found in blacklists")
        
        return result
    
    def _layer3_content_analysis(self, url):
        """
        Layer 3: Lightweight content analysis for suspicious URLs.
        
        Args:
            url (str): URL to analyze
            
        Returns:
            dict: Content analysis result
        """
        print("\n[LAYER 3] Lightweight Content Analysis")
        print("-" * 80)
        print("⚠️  URL marked as Suspicious - performing content scan...")
        
        result = self.content_analyzer.analyze_content(url)
        
        if result['success']:
            print(f"Risk Score: {result['risk_score']}/100")
            print(f"Indicators Found: {len(result['indicators'])}")
            for indicator in result['indicators']:
                print(f"  - {indicator}")
        else:
            print(f"Content analysis failed: {result['details'].get('error', 'Unknown error')}")
        
        return result
    
    def _make_final_decision(self, layer1_result, layer3_result):
        """
        Make final classification decision based on ML + Content analysis.
        
        Args:
            layer1_result (dict): ML detection result
            layer3_result (dict): Content analysis result
            
        Returns:
            tuple: (classification, confidence)
        """
        ml_classification = layer1_result['classification']
        ml_phishing_prob = layer1_result['phishing_prob']
        
        if not layer3_result or not layer3_result['success']:
            # Content analysis failed, rely on ML only
            return ml_classification, layer1_result['confidence']
        
        content_risk_score = layer3_result['risk_score']
        
        # Decision logic:
        # - ML = Suspicious + Content Risk >= 60 → Phishing
        # - ML = Suspicious + Content Risk < 40 → Safe
        # - ML = Suspicious + Content Risk 40-60 → Suspicious
        
        if content_risk_score >= 60:
            # High content risk → Phishing
            classification = "Phishing"
            confidence = min(95.0, 70 + content_risk_score * 0.3)
            print(f"\n[DECISION LOGIC] ML=Suspicious + High Content Risk → Phishing")
            
        elif content_risk_score < 40:
            # Low content risk → Safe
            classification = "Safe"
            confidence = max(60.0, 100 - content_risk_score)
            print(f"\n[DECISION LOGIC] ML=Suspicious + Low Content Risk → Safe")
            
        else:
            # Medium content risk → Suspicious
            classification = "Suspicious"
            confidence = 50 + content_risk_score * 0.5
            print(f"\n[DECISION LOGIC] ML=Suspicious + Medium Content Risk → Suspicious")
        
        return classification, confidence
    
    def _get_detection_path(self, layer1_result, layer2_result, content_analysis_performed):
        """
        Get a human-readable detection path description.
        
        Args:
            layer1_result (dict): ML result
            layer2_result (dict): Blacklist result
            content_analysis_performed (bool): Whether content analysis was done
            
        Returns:
            str: Detection path description
        """
        path = f"ML: {layer1_result['classification']}"
        
        if layer2_result['is_blacklisted']:
            path += f" → Blacklist: {layer2_result['source']}"
        else:
            path += " → Blacklist: Clean"
        
        if content_analysis_performed:
            path += " → Content: Analyzed"
        else:
            path += " → Content: Skipped"
        
        return path


# Example usage
if __name__ == "__main__":
    print("Tiered Detection Engine - Example Usage")
    print("=" * 80)
    print("\nThis module requires:")
    print("1. Trained ML model and scaler")
    print("2. blacklist_checker.py")
    print("3. content_analyzer.py")
    print("\nIntegrate with app.py for full functionality.")
    print("=" * 80)
