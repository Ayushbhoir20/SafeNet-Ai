/**
 * PHISHING DETECTION SYSTEM - HOME PAGE JAVASCRIPT
 * Handles animations, theme toggle, and smooth transitions
 */

// ============================================
// THEME TOGGLE
// ============================================

const themeToggle = document.getElementById('themeToggle');
const body = document.body;

// Load saved theme from localStorage
const savedTheme = localStorage.getItem('theme') || 'dark';
if (savedTheme === 'light') {
    body.classList.add('light-theme');
    if (themeToggle) themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
}

// Toggle theme on button click
if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        body.classList.toggle('light-theme');

        if (body.classList.contains('light-theme')) {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            localStorage.setItem('theme', 'light');
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            localStorage.setItem('theme', 'dark');
        }
    });
}

// ============================================
// TYPING ANIMATION
// ============================================

const typingText = document.getElementById('typingText');
const messages = [
    'Protect users from phishing attacks with real-time URL analysis',
    'Powered by Machine Learning, WHOIS data, and Blacklist detection',
    'Industry-grade tiered detection for maximum accuracy',
    'Analyze URLs instantly with 95%+ accuracy'
];

let messageIndex = 0;
let charIndex = 0;
let isDeleting = false;
let typingSpeed = 50;

function typeWriter() {
    if (!typingText) return;
    const currentMessage = messages[messageIndex];

    if (isDeleting) {
        // Deleting characters
        typingText.textContent = currentMessage.substring(0, charIndex - 1);
        charIndex--;
        typingSpeed = 30;
    } else {
        // Typing characters
        typingText.textContent = currentMessage.substring(0, charIndex + 1);
        charIndex++;
        typingSpeed = 50;
    }

    // Check if message is complete
    if (!isDeleting && charIndex === currentMessage.length) {
        // Pause at end of message
        typingSpeed = 2000;
        isDeleting = true;
    } else if (isDeleting && charIndex === 0) {
        // Move to next message
        isDeleting = false;
        messageIndex = (messageIndex + 1) % messages.length;
        typingSpeed = 500;
    }

    setTimeout(typeWriter, typingSpeed);
}

// Start typing animation only if element exists
if (typingText) setTimeout(typeWriter, 1000);

// ============================================
// COUNTER ANIMATION
// ============================================

const counters = document.querySelectorAll('.stat-number');
let hasAnimated = false;

function animateCounters() {
    if (hasAnimated) return;

    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const increment = target / 100;
        let current = 0;

        const updateCounter = () => {
            current += increment;

            if (current < target) {
                counter.textContent = Math.ceil(current) + (target === 95 || target === 100 ? '%' : '');
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target + (target === 95 || target === 100 ? '%' : '');
            }
        };

        updateCounter();
    });

    hasAnimated = true;
}

// Trigger counter animation when hero section is visible
const heroSection = document.querySelector('.hero-section');
if (heroSection) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
            }
        });
    }, { threshold: 0.5 });
    observer.observe(heroSection);
}

// ============================================
// GET STARTED BUTTON - REDIRECT TO SCAN PAGE
// ============================================

const getStartedBtn = document.getElementById('getStartedBtn');

if (getStartedBtn) {
    getStartedBtn.addEventListener('click', () => {
        // Add click animation
        getStartedBtn.style.transform = 'scale(0.95)';

        setTimeout(() => {
            // Smooth page transition
            document.body.style.opacity = '0';
            document.body.style.transition = 'opacity 0.5s ease';

            setTimeout(() => {
                window.location.href = '/scan';
            }, 500);
        }, 100);
    });
}

// ============================================
// SMOOTH SCROLL FOR NAVIGATION LINKS
// ============================================

const navLinks = document.querySelectorAll('.nav-link');

navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        const href = link.getAttribute('href');

        // Only handle internal anchor links
        if (href.startsWith('#')) {
            e.preventDefault();

            const targetId = href.substring(1);
            const targetSection = document.getElementById(targetId);

            if (targetSection) {
                // Remove active class from all links
                navLinks.forEach(l => l.classList.remove('active'));

                // Add active class to clicked link
                link.classList.add('active');

                // Smooth scroll to section
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });
});

// ============================================
// UPDATE ACTIVE NAV LINK ON SCROLL
// ============================================

const sections = document.querySelectorAll('section[id]');

window.addEventListener('scroll', () => {
    let current = '';

    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;

        if (window.pageYOffset >= sectionTop - 200) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('active');
        }
    });
});

// ============================================
// SCROLL ANIMATIONS FOR CARDS
// ============================================

const animateOnScroll = () => {
    const cards = document.querySelectorAll('.feature-card, .about-card, .timeline-item');

    const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        cardObserver.observe(card);
    });
};

// Initialize scroll animations
animateOnScroll();

// ============================================
// NAVBAR BACKGROUND ON SCROLL
// ============================================

const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    if (window.scrollY > 100) {
        navbar.style.background = body.classList.contains('light-theme')
            ? 'rgba(255, 255, 255, 0.95)'
            : 'rgba(10, 14, 39, 0.95)';
        navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
    } else {
        navbar.style.background = body.classList.contains('light-theme')
            ? 'rgba(255, 255, 255, 0.9)'
            : 'rgba(10, 14, 39, 0.9)';
        navbar.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.2)';
    }
});

// ============================================
// PAGE LOAD ANIMATION
// ============================================

// Page is visible by default - no opacity tricks needed




// ============================================
// FOOTER ANIMATION ON SCROLL
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

