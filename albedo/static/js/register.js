// Add password visibility toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const passwordField1 = document.getElementById('password1');
    const togglePassword1 = document.getElementById('togglePassword1');
    const passwordField2 = document.getElementById('password2');
    const togglePassword2 = document.getElementById('togglePassword2');

    togglePassword1.addEventListener('click', function (e) {
        const type = passwordField1.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordField1.setAttribute('type', type);
        this.querySelector('i').classList.toggle('fa-eye');
        this.querySelector('i').classList.toggle('fa-eye-slash');
    });

    togglePassword2.addEventListener('click', function (e) {
        const type = passwordField2.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordField2.setAttribute('type', type);
        this.querySelector('i').classList.toggle('fa-eye');
        this.querySelector('i').classList.toggle('fa-eye-slash');
    });
});

// ...existing code...