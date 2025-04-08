// Add password visibility toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const passwordField = document.getElementById('password');
    const togglePassword = document.getElementById('togglePassword');

    togglePassword.addEventListener('click', function (e) {
        // toggle the type attribute
        const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordField.setAttribute('type', type);
        // toggle the eye / eye slash icon
        this.querySelector('i').classList.toggle('fa-eye');
        this.querySelector('i').classList.toggle('fa-eye-slash');
    });
});

// ...existing code...