/**
 * Register Page JavaScript
 * Handles user registration functionality
 */

// Theme Toggle
const themeToggle = document.getElementById('themeToggle');
const body = document.body;

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'dark';
body.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    const icon = themeToggle.querySelector('i');
    if (theme === 'dark') {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    }
}

// Password Toggle
const passwordToggle = document.getElementById('passwordToggle');
const passwordInput = document.getElementById('password');
const confirmPasswordToggle = document.getElementById('confirmPasswordToggle');
const confirmPasswordInput = document.getElementById('confirmPassword');

passwordToggle.addEventListener('click', () => {
    togglePasswordVisibility(passwordInput, passwordToggle);
});

confirmPasswordToggle.addEventListener('click', () => {
    togglePasswordVisibility(confirmPasswordInput, confirmPasswordToggle);
});

function togglePasswordVisibility(input, button) {
    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);

    const icon = button.querySelector('i');
    if (type === 'password') {
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}

// Register Form Submission
const registerForm = document.getElementById('registerForm');
const registerBtn = document.getElementById('registerSubmitBtn');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const successMessage = document.getElementById('successMessage');
const successText = document.getElementById('successText');

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Hide previous messages
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';

    // Get form values
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    // Validate email
    if (!email || !isValidEmail(email)) {
        showError('Please enter a valid email address');
        return;
    }

    // Validate password
    if (!password || password.length < 6) {
        showError('Password must be at least 6 characters long');
        return;
    }

    // Check if passwords match
    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }

    // Disable button and show loading
    registerBtn.disabled = true;
    registerBtn.innerHTML = '<span class="btn-text">Creating Account...</span><i class="fas fa-spinner fa-spin btn-icon"></i>';

    try {
        // Send registration request
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            // Show success message
            showSuccess(data.message || 'Account created successfully! Redirecting...');

            // Clear form
            registerForm.reset();

            // Redirect to the URL provided by backend (home page)
            setTimeout(() => {
                window.location.href = data.redirect || '/';
            }, 1500);
        } else {
            showError(data.message || 'Registration failed. Please try again.');
            resetButton();
        }
    } catch (error) {
        console.error('Registration error:', error);
        showError('An error occurred. Please try again.');
        resetButton();
    }
});

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showError(message) {
    errorText.textContent = message;
    errorMessage.style.display = 'flex';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function showSuccess(message) {
    successText.textContent = message;
    successMessage.style.display = 'flex';
}

function resetButton() {
    registerBtn.disabled = false;
    registerBtn.innerHTML = '<span class="btn-text">Create Account</span><i class="fas fa-user-plus btn-icon"></i>';
}
