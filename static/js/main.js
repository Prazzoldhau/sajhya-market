// Global Functions for Authentication Pages

// Toggle password visibility
function togglePasswordVisibility(icon) {
    const passwordField = icon.previousElementSibling;
    const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordField.setAttribute('type', type);
    icon.classList.toggle('fa-eye');
    icon.classList.toggle('fa-eye-slash');
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    // Auto dismiss alerts (only actual flash messages, not static alert-styled content boxes)
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert.alert-dismissible');
        alerts.forEach(function(alert) {
            if (alert && bootstrap && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
    
    // Add password toggle to all password fields automatically
    document.querySelectorAll('input[type="password"]').forEach(function(passwordField) {
        // Check if already wrapped
        if (!passwordField.closest('.password-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'password-wrapper';
            passwordField.parentNode.insertBefore(wrapper, passwordField);
            wrapper.appendChild(passwordField);
            
            const eyeIcon = document.createElement('i');
            eyeIcon.className = 'fas fa-eye toggle-password';
            eyeIcon.onclick = function() { togglePasswordVisibility(this); };
            wrapper.appendChild(eyeIcon);
        }
    });
});

// Form validation helper
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    let isValid = true;
    const inputs = form.querySelectorAll('input[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// // Show loading state on submit
// document.addEventListener('submit', function(e) {
//     const submitBtn = e.target.querySelector('button[type="submit"]');
//     if (submitBtn && !submitBtn.disabled) {
//         submitBtn.disabled = true;
//         submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Please wait...';
        
//         // Re-enable if form submission fails (timeout)
//         setTimeout(() => {
//             submitBtn.disabled = false;
//             submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || submitBtn.innerHTML;
//         }, 5000);
//     }
// });

// // Store original button text
// document.querySelectorAll('button[type="submit"]').forEach(btn => {
//     btn.setAttribute('data-original-text', btn.innerHTML);
// });