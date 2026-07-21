/**
 * Global Keyboard Shortcuts
 * ==========================
 * Provides keyboard shortcuts that work across all pages
 * 
 * Shortcuts:
 * - Ctrl+P: Go to Pricing page
 * - Ctrl+S: Go to Scan page
 * - Ctrl+D: Go to Dashboard
 * - Ctrl+C: Go to Contact page
 * - Ctrl+H: Go to Home page
 * - Ctrl+L: Go to Login page (if not logged in)
 * - Ctrl+/: Show shortcuts help
 */

(function() {
    'use strict';

    // Keyboard shortcut configuration
    const shortcuts = {
        'p': '/pricing',           // Ctrl+P -> Pricing
        's': '/scan',              // Ctrl+S -> Scan
        'd': '/dashboard',         // Ctrl+D -> Dashboard
        'c': '/contact',           // Ctrl+C -> Contact
        'h': '/',                  // Ctrl+H -> Home
        'l': '/login',             // Ctrl+L -> Login
        'f': '/faq',               // Ctrl+F -> FAQ
    };

    // Listen for keyboard events
    document.addEventListener('keydown', function(e) {
        // Check if Ctrl (or Cmd on Mac) is pressed
        const isCtrlPressed = e.ctrlKey || e.metaKey;
        
        // Ctrl+/ to show help
        if (isCtrlPressed && e.key === '/') {
            e.preventDefault();
            toggleShortcutsHelp();
            return;
        }
        
        if (!isCtrlPressed) return;

        // Get the pressed key in lowercase
        const key = e.key.toLowerCase();

        // Check if this key has a shortcut
        if (shortcuts.hasOwnProperty(key)) {
            // Prevent default browser behavior
            e.preventDefault();
            e.stopPropagation();

            const targetUrl = shortcuts[key];

            // Show visual feedback
            showShortcutFeedback(key, targetUrl);

            // Navigate to the page after a brief delay for feedback
            setTimeout(() => {
                window.location.href = targetUrl;
            }, 200);
        }
    });

    // Show visual feedback when shortcut is pressed
    function showShortcutFeedback(key, url) {
        // Remove any existing feedback
        const existingFeedback = document.getElementById('shortcut-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        // Create feedback element
        const feedback = document.createElement('div');
        feedback.id = 'shortcut-feedback';
        feedback.innerHTML = `
            <div class="shortcut-feedback-content">
                <i class="fas fa-keyboard"></i>
                <span>Ctrl+${key.toUpperCase()}</span>
                <i class="fas fa-arrow-right"></i>
                <span>${getPageName(url)}</span>
            </div>
        `;

        // Add to body
        document.body.appendChild(feedback);

        // Trigger animation
        setTimeout(() => {
            feedback.classList.add('show');
        }, 10);

        // Remove after animation
        setTimeout(() => {
            feedback.classList.remove('show');
            setTimeout(() => {
                feedback.remove();
            }, 300);
        }, 1500);
    }

    // Toggle shortcuts help modal
    function toggleShortcutsHelp() {
        let helpModal = document.getElementById('shortcuts-help-modal');
        
        if (helpModal) {
            // Close if already open
            helpModal.remove();
        } else {
            // Create and show help modal
            helpModal = document.createElement('div');
            helpModal.id = 'shortcuts-help-modal';
            helpModal.innerHTML = `
                <div class="shortcuts-help-overlay"></div>
                <div class="shortcuts-help-content">
                    <div class="shortcuts-help-header">
                        <h2><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h2>
                        <button class="shortcuts-help-close" onclick="document.getElementById('shortcuts-help-modal').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="shortcuts-help-body">
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>P</kbd>
                            <span>Go to Pricing</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>S</kbd>
                            <span>Go to Scan Page</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>D</kbd>
                            <span>Go to Dashboard</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>C</kbd>
                            <span>Go to Contact</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>H</kbd>
                            <span>Go to Home</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>F</kbd>
                            <span>Go to FAQ</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>/</kbd>
                            <span>Show this help</span>
                        </div>
                    </div>
                    <div class="shortcuts-help-footer">
                        <p>Press <kbd>Esc</kbd> to close</p>
                    </div>
                </div>
            `;
            
            document.body.appendChild(helpModal);
            
            // Close on overlay click
            helpModal.querySelector('.shortcuts-help-overlay').addEventListener('click', () => {
                helpModal.remove();
            });
            
            // Close on Escape key
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    helpModal.remove();
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
        }
    }

    // Get friendly page name from URL
    function getPageName(url) {
        const pageNames = {
            '/': 'Home',
            '/pricing': 'Pricing',
            '/scan': 'Scan',
            '/dashboard': 'Dashboard',
            '/contact': 'Contact',
            '/login': 'Login',
            '/faq': 'FAQ'
        };
        return pageNames[url] || url;
    }

    // Add CSS for feedback animation and help modal
    const style = document.createElement('style');
    style.textContent = `
        #shortcut-feedback {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(99, 102, 241, 0.4);
            z-index: 10000;
            opacity: 0;
            transform: translateY(-20px) scale(0.9);
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: none;
        }

        #shortcut-feedback.show {
            opacity: 1;
            transform: translateY(0) scale(1);
        }

        .shortcut-feedback-content {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            font-weight: 600;
            white-space: nowrap;
        }

        .shortcut-feedback-content i {
            font-size: 16px;
        }

        .shortcut-feedback-content .fa-arrow-right {
            font-size: 12px;
            opacity: 0.7;
        }

        /* Shortcuts Help Modal */
        #shortcuts-help-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 10001;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .shortcuts-help-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
            animation: fadeIn 0.2s ease;
        }

        .shortcuts-help-content {
            position: relative;
            background: var(--bg-primary, #1e293b);
            border-radius: 16px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .shortcuts-help-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 24px;
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
        }

        .shortcuts-help-header h2 {
            margin: 0;
            font-size: 20px;
            color: var(--text-primary, #fff);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .shortcuts-help-close {
            background: none;
            border: none;
            color: var(--text-secondary, #94a3b8);
            font-size: 20px;
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        .shortcuts-help-close:hover {
            background: rgba(99, 102, 241, 0.2);
            color: var(--text-primary, #fff);
        }

        .shortcuts-help-body {
            padding: 24px;
            max-height: 60vh;
            overflow-y: auto;
        }

        .shortcut-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            margin-bottom: 8px;
            background: rgba(99, 102, 241, 0.05);
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        .shortcut-item:hover {
            background: rgba(99, 102, 241, 0.1);
            transform: translateX(4px);
        }

        .shortcut-item kbd {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
            min-width: 40px;
            text-align: center;
        }

        .shortcut-item span {
            color: var(--text-secondary, #94a3b8);
            font-size: 14px;
        }

        .shortcuts-help-footer {
            padding: 16px 24px;
            border-top: 1px solid rgba(99, 102, 241, 0.2);
            text-align: center;
        }

        .shortcuts-help-footer p {
            margin: 0;
            color: var(--text-secondary, #94a3b8);
            font-size: 13px;
        }

        .shortcuts-help-footer kbd {
            background: rgba(99, 102, 241, 0.2);
            color: var(--text-primary, #fff);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        /* Mobile - hide shortcuts */
        @media (max-width: 768px) {
            #shortcut-feedback {
                display: none;
            }
        }
    `;
    document.head.appendChild(style);

    // Log shortcuts to console for user reference
    console.log('%c⌨️ Keyboard Shortcuts Available', 'color: #6366f1; font-size: 16px; font-weight: bold;');
    console.log('%cCtrl+P → Pricing', 'color: #8b5cf6; font-size: 14px;');
    console.log('%cCtrl+S → Scan', 'color: #8b5cf6; font-size: 14px;');
    console.log('%cCtrl+D → Dashboard', 'color: #8b5cf6; font-size: 14px;');
    console.log('%cCtrl+C → Contact', 'color: #8b5cf6; font-size: 14px;');
    console.log('%cCtrl+H → Home', 'color: #8b5cf6; font-size: 14px;');
    console.log('%cCtrl+/ → Show Help', 'color: #8b5cf6; font-size: 14px;');

})();
