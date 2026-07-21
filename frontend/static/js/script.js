/**
 * JavaScript for Phishing Detection System
 * ==========================================
 * Handles theme toggling, form submission, API communication, and result display
 */

// ============================================
// Theme Management
// ============================================

const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;

// Load saved theme preference or default to light
const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

// Theme toggle event listener
themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    const icon = themeToggle.querySelector('i');
    icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
}

// ============================================
// Form Handling
// ============================================

const urlForm = document.getElementById('urlForm');
const urlInput = document.getElementById('urlInput');
const checkBtn = document.getElementById('checkBtn');
const loader = document.getElementById('loader');
const resultContainer = document.getElementById('resultContainer');

// ============================================
// Credit State Management (SINGLE SOURCE OF TRUTH)
// ============================================

let userCredits = {
    credits_remaining: 0,
    has_credits: false,
    total_credits: 0,
    credits_used: 0
};

// Fetch user credits from backend on page load
async function fetchUserCredits() {
    try {
        const response = await fetch('/api/user/credits');
        const data = await response.json();

        if (data.success) {
            userCredits = {
                credits_remaining: data.credits_remaining,
                has_credits: data.has_credits,
                total_credits: data.total_credits,
                credits_used: data.credits_used
            };



            // Update button state based on credits
            updateScanButtonState();
        } else {
            console.error('Failed to fetch credits:', data.message);
        }
    } catch (error) {
        console.error('Error fetching credits:', error);
        // On error, assume user has credits (fail-safe)
        userCredits.has_credits = true;
        updateScanButtonState();
    }
}

// Update scan button state based on credits
function updateScanButtonState() {
    const btnText = checkBtn.querySelector('.btn-text');

    if (userCredits.has_credits) {
        // User has credits - enable scanning
        checkBtn.disabled = false;
        checkBtn.classList.remove('btn-disabled-tooltip');
        checkBtn.removeAttribute('data-tooltip');
        btnText.textContent = 'Analyze URL';

    } else {
        // User has NO credits - disable scanning
        checkBtn.disabled = true;
        checkBtn.classList.add('btn-disabled-tooltip');
        checkBtn.setAttribute('data-tooltip', 'No credits remaining');
        btnText.textContent = 'No Credits';


        // Show credits exhausted message
        showCreditsExhaustedMessage();
    }
}

// Show credits exhausted message
function showCreditsExhaustedMessage() {
    resultContainer.innerHTML = `
        <div class="credits-exhausted-card">
            <div class="credits-error-icon">
                <i class="fas fa-exclamation-circle"></i>
            </div>
            <h2 class="credits-error-title">Credits Exhausted</h2>
            <p class="credits-error-description">
                You've used all your available credits.<br>
                Upgrade your plan to continue scanning URLs.
            </p>
            <div class="credits-error-actions">
                <a href="/pricing" class="credits-btn-primary">
                    <i class="fas fa-rocket"></i>
                    Upgrade Plan
                </a>
                <a href="/dashboard" class="credits-btn-secondary">
                    <i class="fas fa-chart-line"></i>
                    View My Credits
                </a>
            </div>
        </div>
    `;
    showResult();
}

// Initialize credits on page load
fetchUserCredits();

// Form submission handler
urlForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = urlInput.value.trim();

    if (!url) {
        showError('Please enter a URL to check.');
        return;
    }

    // ============================================
    // RESET CHATBOT FOR NEW SCAN (CRITICAL)
    // ============================================

    // Completely destroy previous chatbot session before starting new scan
    if (typeof window.resetChatbotForNewScan === 'function') {
        window.resetChatbotForNewScan();
    }

    // Show loader and hide previous results
    showLoader();
    hideResult();

    try {
        // Make API request
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        // Hide loader
        hideLoader();

        if (data.success) {
            // Update local credit state from response
            if (data.credits_remaining !== undefined) {
                userCredits.credits_remaining = data.credits_remaining;
                userCredits.credits_used = data.credits_used || userCredits.credits_used;
                userCredits.total_credits = data.total_credits || userCredits.total_credits;
                userCredits.has_credits = data.has_credits !== undefined ? data.has_credits : (data.credits_remaining > 0);



                // Update button state
                updateScanButtonState();
            }

            // Display results
            displayResult(data);
        } else {
            // Show error message with error data for credits detection
            showError(data.message || 'An error occurred while analyzing the URL.', data);
        }

    } catch (error) {
        hideLoader();
        showError('Failed to connect to the server. Please try again.');
        console.error('Error:', error);
    }
});

// ============================================
// UI State Management
// ============================================

function showLoader() {
    loader.classList.add('active');
    checkBtn.disabled = true;
    checkBtn.querySelector('.btn-text').textContent = 'Analyzing...';
}

function hideLoader() {
    loader.classList.remove('active');
    checkBtn.disabled = false;
    checkBtn.querySelector('.btn-text').textContent = 'Analyze URL';
}

function showResult() {
    resultContainer.classList.add('active');
}

function hideResult() {
    resultContainer.classList.remove('active');
    resultContainer.innerHTML = '';
}

function showError(message, errorData = {}) {
    // Check if this is a credits exhausted error
    if (errorData.upgrade_required || message.toLowerCase().includes('credits exhausted')) {
        // Show premium credits exhausted UI
        resultContainer.innerHTML = `
            <div class="credits-exhausted-card">
                <div class="credits-error-icon">
                    <i class="fas fa-exclamation-circle"></i>
                </div>
                <h2 class="credits-error-title">Credits Exhausted</h2>
                <p class="credits-error-description">
                    You've used all your available credits.<br>
                    Upgrade your plan to continue scanning URLs.
                </p>
                <div class="credits-error-actions">
                    <a href="/pricing" class="credits-btn-primary">
                        <i class="fas fa-rocket"></i>
                        Upgrade Plan
                    </a>
                    <a href="/dashboard" class="credits-btn-secondary">
                        <i class="fas fa-chart-line"></i>
                        View My Credits
                    </a>
                </div>
            </div>
        `;

        // Disable the scan button and add tooltip
        const checkBtn = document.getElementById('checkBtn');
        checkBtn.disabled = true;
        checkBtn.classList.add('btn-disabled-tooltip');
        checkBtn.setAttribute('data-tooltip', 'No credits remaining');
        checkBtn.querySelector('.btn-text').textContent = 'No Credits';
    } else {
        // Show regular error message
        resultContainer.innerHTML = `
            <div class="result-header phishing">
                <div class="result-icon">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <h2 class="result-title">Error</h2>
                <p class="result-confidence">${message}</p>
            </div>
        `;
    }
    showResult();
}

// ============================================
// Result Display
// ============================================

function displayResult(data) {
    const isPhishing = data.prediction === 'Phishing';
    const resultClass = isPhishing ? 'phishing' : 'legitimate';
    const icon = isPhishing ? 'fa-shield-xmark' : 'fa-shield-check';
    const title = isPhishing ? 'Phishing Detected!' : 'Legitimate Website';

    // Determine detection method badge styling
    const detectionMethod = data.detection_method || 'ML Prediction';
    let methodBadgeClass = 'badge-ml';
    if (detectionMethod.includes('Rule-Based')) {
        methodBadgeClass = 'badge-rule';
    } else if (detectionMethod.includes('Hybrid')) {
        methodBadgeClass = 'badge-hybrid';
    }

    // Build warnings HTML if warnings exist
    let warningsHTML = '';
    if (data.warnings && data.warnings.length > 0) {
        const warningItems = data.warnings.map(warning =>
            `<div class="warning-item">⚠️ ${escapeHtml(warning)}</div>`
        ).join('');

        warningsHTML = `
            <div class="warnings-section">
                <h3 style="color: #f59e0b; margin: 0 0 10px 0; font-size: 14px;">
                    <i class="fas fa-exclamation-triangle"></i> Security Warnings
                </h3>
                ${warningItems}
            </div>
        `;
    }

    const html = `
        <!-- Result Header -->
        <div class="result-header ${resultClass}">
            <div class="result-icon">
                <i class="fas ${icon}"></i>
            </div>
            <h2 class="result-title">${title}</h2>
            <p class="result-confidence">Confidence: ${data.confidence}%</p>
            <div style="margin-top: 10px;">
                <span class="detection-badge ${methodBadgeClass}">
                    ${detectionMethod}
                </span>
            </div>
        </div>
        
        ${warningsHTML}
        
        <!-- URL Display -->
        <div class="result-url">
            <strong>Analyzed URL:</strong><br>
            ${isPhishing ?
            `<span style="color: var(--text-secondary); word-break: break-all;">${escapeHtml(data.url)}</span>` :
            `<a href="${escapeHtml(data.url)}" target="_blank" rel="noopener noreferrer" 
                   style="color: #10b981; text-decoration: none; word-break: break-all; 
                          transition: all 0.2s ease; display: inline-flex; align-items: center; gap: 6px;"
                   onmouseover="this.style.textDecoration='underline'; this.style.color='#059669';"
                   onmouseout="this.style.textDecoration='none'; this.style.color='#10b981';">
                    ${escapeHtml(data.url)}
                    <i class="fas fa-external-link-alt" style="font-size: 12px; opacity: 0.7;"></i>
                </a>`
        }
        </div>
        
        <!-- Recommendation -->
        <div class="info-section">
            <h3>
                <i class="fas fa-lightbulb"></i>
                Recommendation
            </h3>
            <div class="info-item">
                <p style="margin: 0; color: var(--text-secondary); line-height: 1.6;">
                    ${getRecommendation(isPhishing, data.confidence)}
                </p>
            </div>
        </div>
    `;

    resultContainer.innerHTML = html;
    showResult();

    // Scroll to results
    resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // ============================================
    // ACTIVATE CHATBOT AFTER SCAN (IMMEDIATE)
    // ============================================

    // Extract scan_id from response (CRITICAL for session management)
    const scanId = data.scan_id || `scan_${Date.now()}`;

    // Determine scan result category for chatbot
    let scanResultCategory = data.prediction; // "Phishing" or "Legitimate"

    // Check if it's suspicious (moderate confidence)
    if (data.confidence >= 35 && data.confidence <= 65) {
        scanResultCategory = "Suspicious";
    }



    // Activate chatbot immediately with scan data
    if (typeof window.activateChatbotAfterScan === 'function') {
        window.activateChatbotAfterScan(scanId, scanResultCategory, data);
    } else {
        console.error('❌ [SCAN] Chatbot activation function not found');
    }
}

// ============================================
// Helper Functions
// ============================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDomainAge(days) {
    if (days < 0) {
        return 'Not Available';
    } else if (days < 30) {
        return `${days} days (New)`;
    } else if (days < 365) {
        const months = Math.floor(days / 30);
        return `${months} month${months > 1 ? 's' : ''}`;
    } else {
        const years = Math.floor(days / 365);
        const remainingDays = days % 365;
        return `${years} year${years > 1 ? 's' : ''}, ${remainingDays} days`;
    }
}

function getRecommendation(isPhishing, confidence) {
    if (isPhishing) {
        if (confidence > 90) {
            return '⚠️ <strong>High Risk:</strong> This URL shows strong indicators of being a phishing website. Do not enter any personal information, passwords, or financial details. Close this page immediately and report it if possible.';
        } else if (confidence > 70) {
            return '⚠️ <strong>Moderate Risk:</strong> This URL has several suspicious characteristics. Exercise extreme caution and verify the legitimacy through official channels before proceeding.';
        } else {
            return '⚠️ <strong>Potential Risk:</strong> Some phishing indicators detected. Verify the URL carefully and ensure you\'re on the official website before entering any sensitive information.';
        }
    } else {
        if (confidence > 90) {
            return '✅ <strong>Appears Safe:</strong> This URL shows characteristics of a legitimate website. However, always verify the URL matches the official domain and look for HTTPS encryption.';
        } else if (confidence > 70) {
            return '✅ <strong>Likely Safe:</strong> This URL appears legitimate, but remain vigilant. Always double-check URLs and be cautious with sensitive information.';
        } else {
            return '✅ <strong>Possibly Safe:</strong> While this URL doesn\'t show strong phishing indicators, exercise normal internet safety practices and verify the website\'s authenticity.';
        }
    }
}

// ============================================
// Input Validation
// ============================================

urlInput.addEventListener('input', (e) => {
    // Remove any leading/trailing whitespace as user types
    e.target.value = e.target.value.trim();
});

// ============================================
// Keyboard Shortcuts
// ============================================

document.addEventListener('keydown', (e) => {
    // Alt + T to toggle theme
    if (e.altKey && e.key === 't') {
        e.preventDefault();
        themeToggle.click();
    }

    // Escape to clear results
    if (e.key === 'Escape') {
        hideResult();
        urlInput.value = '';
        urlInput.focus();
    }
});

// ============================================
// Initialize
// ============================================



// ============================================
// Footer Animation on Scroll
// ============================================

const footer = document.getElementById('footer');

if (footer) {
    const footerObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                footer.classList.add('visible');
                footerObserver.unobserve(footer); // Only animate once
            }
        });
    }, {
        threshold: 0.1 // Trigger when 10% of footer is visible
    });

    footerObserver.observe(footer);
}

