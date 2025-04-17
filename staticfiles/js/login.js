document.addEventListener('DOMContentLoaded', function () {
  // If already logged in, redirect to the dashboard
  if (localStorage.getItem('access_token')) {
    window.location.href = '/dashboard/';
    return; // Prevent further code execution
  }

  const form = document.getElementById('login-form');
  const errorMsg = document.getElementById('error-msg');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    // Clear any previous error message
    errorMsg.style.display = "none";

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
      // Attempt to get tokens from the API
      const response = await fetch('/api/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (response.ok) {
        // If login is successful, store tokens and redirect to dashboard
        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        window.location.href = '/dashboard/';
      } else {
        // If login fails, show the error message
        const result = await response.json();
        errorMsg.textContent = result.detail || "Invalid username or password.";
        errorMsg.style.display = "block";
      }
    } catch (error) {
      // Handle any network errors
      console.error("Error during login:", error);
      errorMsg.textContent = "An error occurred. Please try again.";
      errorMsg.style.display = "block";
    }
  });
});
