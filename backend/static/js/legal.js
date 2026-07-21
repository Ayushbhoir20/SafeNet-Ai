/**
 * SAFENET AI - LEGAL PAGES JAVASCRIPT
 * Lightweight handler for theme toggle & navbar on legal pages
 */

// ============================================
// THEME TOGGLE
// ============================================

const themeToggle = document.getElementById('themeToggle');
const body = document.body;

// Load saved theme on page load
const savedTheme = localStorage.getItem('theme') || 'dark';
if (savedTheme === 'light') {
    body.classList.add('light-theme');
}
updateThemeIcon(savedTheme);

if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        body.classList.toggle('light-theme');
        const newTheme = body.classList.contains('light-theme') ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });
}

function updateThemeIcon(theme) {
    if (!themeToggle) return;
    const icon = themeToggle.querySelector('i');
    if (icon) {
        icon.className = theme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// ============================================
// NAVBAR SCROLL EFFECT
// ============================================

const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    if (!navbar) return;
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// ============================================
// NEWSLETTER SUBSCRIBE HANDLER
// ============================================

function handleNewsletterSubmit(e) {
    e.preventDefault();
    const input = e.target.querySelector('.footer-newsletter-input');
    const btn = e.target.querySelector('.footer-newsletter-btn');
    if (!btn || !input) return;
    const originalText = btn.textContent;
    btn.textContent = '✓ Subscribed!';
    btn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
    input.value = '';
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
    }, 3000);
}
