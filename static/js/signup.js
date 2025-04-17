document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');
    const password1 = document.querySelector('input[name="password1"]');
    const password2 = document.querySelector('input[name="password2"]');
  
    form.addEventListener('submit', (e) => {
      if (password1.value !== password2.value) {
        e.preventDefault();
        alert('Passwords do not match!');
      }
    });
  });
  