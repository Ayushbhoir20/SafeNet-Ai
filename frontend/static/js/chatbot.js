/**
 * Premium Cybersecurity Chatbot - JavaScript (ALWAYS VISIBLE)
 * ============================================================
 * Chatbot is visible on page load in neutral state
 * Updates dynamically based on scan results
 */

// ============================================
// GLOBAL STATE
// ============================================

let chatbotState = {
    currentScanId: null,      // Current active scan ID
    isOpen: false,
    isVisible: true,          // Always visible
    scanResult: null,         // "Legitimate", "Phishing", "Suspicious", or null
    scanCompleted: false,
    messages: [],
    isInitialized: false,
    isIdle: true              // True when no scan has been performed
};

// ============================================
// DOM ELEMENTS
// ============================================

const chatbotIcon = document.getElementById('chatbotIcon');
const chatbotWindow = document.getElementById('chatbotWindow');
const chatbotClose = document.getElementById('chatbotClose');
const chatbotMessages = document.getElementById('chatbotMessages');
const chatbotInput = document.getElementById('chatbotInput');
const chatbotSendBtn = document.getElementById('chatbotSendBtn');
const typingIndicator = document.getElementById('typingIndicator');

// ============================================
// INITIALIZATION ON PAGE LOAD
// ============================================

/**
 * Initialize chatbot in neutral idle state
 * Called automatically when page loads
 */
function initializeChatbot() {


    // Show chatbot icon immediately
    chatbotIcon.classList.add('active');
    chatbotState.isVisible = true;
    chatbotState.isIdle = true;
    chatbotState.isInitialized = true;

    // Apply neutral theme
    applyTheme('neutral');

    // Show idle welcome message
    setTimeout(() => {
        showIdleMessage();
    }, 500);


}

/**
 * Show idle welcome message
 */
function showIdleMessage() {
    const message = `👋 **Welcome to SafeNet AI Security Assistant**

I'm here to help you understand URL scan results and answer cybersecurity questions.

**What I can do:**
• Explain scan results in detail
• Answer phishing-related questions
• Provide security recommendations
• Help you stay safe online

**Scan a URL to get started!** 🔍`;

    addBotMessage(message, 'info');
}

// ============================================
// COMPLETE STATE RESET (FOR NEW SCAN)
// ============================================

/**
 * Reset chatbot for a new scan (keeps it visible)
 */
function resetChatbotForScan() {


    // Reset state (but keep visible)
    chatbotState.currentScanId = null;
    chatbotState.scanResult = null;
    chatbotState.scanCompleted = false;
    chatbotState.messages = [];
    chatbotState.isIdle = false;

    // Clear all messages from DOM
    if (chatbotMessages) {
        chatbotMessages.innerHTML = '';
    }

    // Clear input
    if (chatbotInput) {
        chatbotInput.value = '';
    }

    // Hide typing indicator
    if (typingIndicator) {
        typingIndicator.classList.remove('active');
    }

    // Apply neutral theme during scan
    applyTheme('neutral');

    // Add "analyzing" message
    addBotMessage('🔍 **Analyzing URL...**\n\nPlease wait while I scan this website for security threats.', 'info');

    // Show typing indicator
    showTyping();


}

/**
 * Reset to idle state (when page is refreshed or no scan)
 */
function resetToIdle() {


    chatbotState = {
        currentScanId: null,
        isOpen: false,
        isVisible: true,
        scanResult: null,
        scanCompleted: false,
        messages: [],
        isInitialized: true,
        isIdle: true
    };

    // Clear messages
    if (chatbotMessages) {
        chatbotMessages.innerHTML = '';
    }

    // Apply neutral theme
    applyTheme('neutral');

    // Show idle message
    showIdleMessage();


}

// ============================================
// CHATBOT ACTIVATION (AFTER SCAN)
// ============================================

/**
 * Activate chatbot with scan results
 * @param {string} scanId - Unique scan identifier
 * @param {string} result - "Legitimate", "Phishing", or "Suspicious"
 * @param {object} scanData - Full scan data (optional)
 */
function activateChatbot(scanId, result, scanData = null) {


    // Check if this is a duplicate activation
    if (chatbotState.currentScanId === scanId && chatbotState.scanCompleted) {

        return;
    }

    // Set new scan session
    chatbotState.currentScanId = scanId;
    chatbotState.scanResult = result;
    chatbotState.scanCompleted = true;
    chatbotState.isIdle = false;

    // Hide typing indicator
    hideTyping();

    // Clear "analyzing" message
    chatbotMessages.innerHTML = '';
    chatbotState.messages = [];

    // Apply theme with animation
    applyThemeWithAnimation(result);

    // Expand chatbot if minimized
    if (!chatbotState.isOpen) {
        setTimeout(() => {
            openChatbot();
        }, 300);
    }

    // Send auto-response after animation
    setTimeout(() => {
        sendAutoResponse(result, scanData);
    }, 600);
}

/**
 * Apply theme with smooth animation
 * @param {string} result - "Legitimate", "Phishing", "Suspicious", or "neutral"
 */
function applyThemeWithAnimation(result) {
    // Shrink animation
    chatbotWindow.style.transform = 'scale(0.95)';

    setTimeout(() => {
        // Apply new theme
        applyTheme(result);

        // Expand animation
        chatbotWindow.style.transform = 'scale(1.02)';

        setTimeout(() => {
            chatbotWindow.style.transform = 'scale(1)';
        }, 150);
    }, 150);
}

/**
 * Apply theme color based on scan result
 * @param {string} result - "Legitimate", "Phishing", "Suspicious", or "neutral"
 */
function applyTheme(result) {
    // Remove all theme classes
    chatbotWindow.classList.remove('theme-green', 'theme-red', 'theme-orange', 'theme-neutral');

    // Apply new theme
    if (result === 'Legitimate') {
        chatbotWindow.classList.add('theme-green');
    } else if (result === 'Phishing') {
        chatbotWindow.classList.add('theme-red');
    } else if (result === 'Suspicious') {
        chatbotWindow.classList.add('theme-orange');
    } else {
        chatbotWindow.classList.add('theme-neutral');
    }


}

/**
 * Send automatic response based on scan result
 * @param {string} result - "Legitimate", "Phishing", or "Suspicious"
 * @param {object} scanData - Full scan data (optional)
 */
function sendAutoResponse(result, scanData = null) {
    let message = '';
    let type = 'info';

    if (result === 'Legitimate') {
        type = 'safe';
        message = `✅ **This website appears safe.**

**Security Analysis:**
• No phishing indicators detected
• Domain appears legitimate
• HTTPS encryption verified

**Security Tips:**
• Always verify the exact domain spelling
• Look for the HTTPS lock icon
• Enable 2FA when available
• Never share OTP or passwords
• Bookmark trusted websites

Feel free to ask me any cybersecurity questions! 🔐`;
    } else if (result === 'Phishing') {
        type = 'warning';
        message = `🚨 **WARNING: Strong Phishing Indicators Detected**

**This website is likely a phishing attempt!**

**Immediate Actions:**
• ❌ Do NOT enter any credentials
• ❌ Do NOT click any links on this page
• ❌ Close the page immediately
• ✓ Report to Google Safe Browsing
• ✓ Clear browser cookies if you interacted
• ✓ Monitor your bank/email accounts

**Need help?** Ask me:
• "What should I do if I clicked a phishing link?"
• "How to identify phishing websites?"
• "What is phishing?"`;
    } else if (result === 'Suspicious') {
        type = 'warning';
        message = `⚠️ **Caution: Suspicious Indicators Detected**

**This website shows some risk factors.**

**Recommendations:**
• 🔍 Proceed with extreme caution
• ❌ Avoid entering sensitive data
• ✓ Double-check the domain age
• ✓ Verify it's the official company domain
• ✓ Use another security tool for confirmation
• ✓ Contact the company directly if unsure

**Security Questions?**
• "How to verify website safety?"
• "What are phishing red flags?"
• "Is HTTPS always safe?"`;
    }

    // Add bot message with typing effect
    addBotMessage(message, type);
}

// ============================================
// CHATBOT UI CONTROLS
// ============================================

/**
 * Open chatbot window
 */
function openChatbot() {
    chatbotWindow.classList.add('active');
    chatbotState.isOpen = true;
    chatbotInput.focus();

}

/**
 * Close chatbot window
 */
function closeChatbot() {
    chatbotWindow.classList.remove('active');
    chatbotState.isOpen = false;

}

/**
 * Toggle chatbot window
 */
function toggleChatbot() {
    if (chatbotState.isOpen) {
        closeChatbot();
    } else {
        openChatbot();
    }
}

// ============================================
// MESSAGE HANDLING
// ============================================

/**
 * Add bot message to chat
 * @param {string} text - Message text
 * @param {string} type - Message type: 'info', 'warning', 'safe'
 */
function addBotMessage(text, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chatbot-message bot';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar bot';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';

    const content = document.createElement('div');
    content.className = `message-content ${type}`;

    // Convert markdown-style formatting to HTML
    const formattedText = formatMessage(text);
    content.innerHTML = formattedText;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatbotMessages.appendChild(messageDiv);

    // Scroll to bottom
    scrollToBottom();

    // Store message
    chatbotState.messages.push({
        type: 'bot',
        text: text,
        messageType: type,
        timestamp: new Date(),
        scanId: chatbotState.currentScanId
    });
}

/**
 * Add user message to chat
 * @param {string} text - Message text
 */
function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chatbot-message user';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar user';
    avatar.innerHTML = '<i class="fas fa-user"></i>';

    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = text;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatbotMessages.appendChild(messageDiv);

    // Scroll to bottom
    scrollToBottom();

    // Store message
    chatbotState.messages.push({
        type: 'user',
        text: text,
        timestamp: new Date(),
        scanId: chatbotState.currentScanId
    });
}

/**
 * Format message text (convert markdown-style to HTML)
 * @param {string} text - Raw message text
 * @returns {string} - Formatted HTML
 */
function formatMessage(text) {
    // Convert **bold** to <strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert line breaks to <br>
    text = text.replace(/\n/g, '<br>');

    // Convert bullet points
    text = text.replace(/^• /gm, '&bull; ');

    return text;
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}

/**
 * Show typing indicator
 */
function showTyping() {
    typingIndicator.classList.add('active');
    scrollToBottom();
}

/**
 * Hide typing indicator
 */
function hideTyping() {
    typingIndicator.classList.remove('active');
}

// ============================================
// SEND MESSAGE TO BACKEND
// ============================================

/**
 * Send user message to chatbot backend
 * @param {string} message - User's message
 */
async function sendMessage(message) {
    if (!message.trim()) return;

    // Add user message to UI
    addUserMessage(message);

    // Clear input
    chatbotInput.value = '';

    // Disable send button
    chatbotSendBtn.disabled = true;

    // Show typing indicator
    showTyping();

    try {
        // Send to backend
        const response = await fetch('/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                scan_result: chatbotState.scanResult,
                scan_id: chatbotState.currentScanId
            })
        });

        const data = await response.json();

        // Hide typing indicator
        hideTyping();

        if (data.success) {
            // Add bot response with slight delay for natural feel
            setTimeout(() => {
                addBotMessage(data.reply, data.type || 'info');
            }, 300);
        } else {
            // Error response
            setTimeout(() => {
                addBotMessage('Sorry, I encountered an error. Please try again.', 'warning');
            }, 300);
        }

    } catch (error) {
        console.error('Chatbot error:', error);
        hideTyping();

        setTimeout(() => {
            addBotMessage('Sorry, I\'m having trouble connecting. Please try again.', 'warning');
        }, 300);
    } finally {
        // Re-enable send button
        chatbotSendBtn.disabled = false;
        chatbotInput.focus();
    }
}

// ============================================
// EVENT LISTENERS
// ============================================

// Toggle chatbot on icon click
if (chatbotIcon) {
    chatbotIcon.addEventListener('click', toggleChatbot);
}

// Close chatbot
if (chatbotClose) {
    chatbotClose.addEventListener('click', closeChatbot);
}

// Send message on button click
if (chatbotSendBtn) {
    chatbotSendBtn.addEventListener('click', () => {
        const message = chatbotInput.value.trim();
        if (message) {
            sendMessage(message);
        }
    });
}

// Send message on Enter key
if (chatbotInput) {
    chatbotInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = chatbotInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        }
    });
}

// ============================================
// INTEGRATION WITH SCAN RESULTS
// ============================================

/**
 * Called from script.js after a scan is completed
 */
window.activateChatbotAfterScan = function (scanId, scanResult, scanData) {

    activateChatbot(scanId, scanResult, scanData);
};

/**
 * Called from script.js BEFORE making the scan API call
 */
window.resetChatbotForNewScan = function () {

    resetChatbotForScan();
};

/**
 * Reset to idle state (for page refresh)
 */
window.resetChatbotToIdle = function () {
    resetToIdle();
};

// ============================================
// AUTO-INITIALIZATION
// ============================================

// Initialize chatbot when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChatbot);
} else {
    // DOM already loaded
    initializeChatbot();
}


