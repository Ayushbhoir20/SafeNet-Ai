/**
 * Login Page JavaScript
 * Handles form submission, validation, and theme toggling
 */

// Theme Toggle Functionality
const themeToggle = document.getElementById('themeToggle');
const htmlElement = document.documentElement;

// Load saved theme preference (default to dark)
const savedTheme = localStorage.getItem('theme') || 'dark';
htmlElement.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    htmlElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    const icon = themeToggle.querySelector('i');
    icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
}

// Password Toggle Functionality
const passwordInput = document.getElementById('password');
const passwordToggle = document.getElementById('passwordToggle');

passwordToggle.addEventListener('click', () => {
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;

    const icon = passwordToggle.querySelector('i');
    icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
});

// Login Form Submission
const loginForm = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const loginBtn = document.getElementById('loginBtn');

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Clear previous errors
    hideError();

    // Get form values
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // Basic validation
    if (!username || !password) {
        showError('Please enter both username and password.');
        return;
    }

    // Disable button and show loading state
    loginBtn.disabled = true;
    const btnText = loginBtn.querySelector('.btn-text');
    const originalText = btnText.textContent;
    btnText.textContent = 'Signing in...';

    try {
        // Send login request
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            // Success - redirect based on role
            btnText.textContent = 'Success!';
            setTimeout(() => {
                // Use redirect URL from server if available, otherwise default to home
                const redirectUrl = data.redirect || '/';
                window.location.href = redirectUrl;
            }, 500);
        } else {
            // Show error message
            showError(data.message || 'Invalid credentials. Please try again.');
            loginBtn.disabled = false;
            btnText.textContent = originalText;
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('An error occurred. Please try again.');
        loginBtn.disabled = false;
        btnText.textContent = originalText;
    }
});

// Error Display Functions
function showError(message) {
    errorText.textContent = message;
    errorMessage.style.display = 'flex';
    errorMessage.classList.add('shake');

    setTimeout(() => {
        errorMessage.classList.remove('shake');
    }, 500);
}

function hideError() {
    errorMessage.style.display = 'none';
    errorText.textContent = '';
}

// Add enter key support for form fields
document.getElementById('username').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('password').focus();
    }
});

// Google Login Button Handler
const googleLoginBtn = document.getElementById('googleLoginBtn');

googleLoginBtn.addEventListener('click', () => {
    // Redirect to Google OAuth endpoint
    window.location.href = '/auth/google';
});

// Check for OAuth errors in URL parameters
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    
    if (error) {
        let errorMsg = 'An error occurred during Google login.';
        
        switch(error) {
            case 'oauth_failed':
                errorMsg = 'Google authentication failed. Please try again.';
                break;
            case 'no_email':
                errorMsg = 'Could not retrieve email from Google account.';
                break;
            case 'oauth_error':
                errorMsg = 'An error occurred during Google login. Please try again or use email/password.';
                break;
        }
        
        showError(errorMsg);
        
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});
