async function validateToken() {
  const access = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');

  // Check if access token is available
  if (!access) {
    window.location.href = '/login/';
    return;
  }

  try {
    // Check if the access token is valid by making a protected API request
    let response = await fetch('/api/protected/', {
      headers: {
        'Authorization': 'Bearer ' + access
      }
    });

    // If token is expired, try to refresh it using the refresh token
    if (response.status === 401 && refresh) {
      const refreshResponse = await fetch('/api/token/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh })
      });

      if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        localStorage.setItem('access_token', data.access);
        return validateToken(); // Retry with new access token
      } else {
        localStorage.clear();  // Clear local storage if refresh fails
        window.location.href = '/login/';
        return;  // Stop execution after redirect
      }
    } else if (!response.ok) {
      localStorage.clear();  // Clear local storage if response is not OK
      window.location.href = '/login/';
      return;  // Stop execution after redirect
    } else {
      // Everything is okay, hide loading and show content
      document.getElementById("loading")?.style.display = "none";
      document.getElementById("dashboard-content")?.style.display = "block";
    }
  } catch (error) {
    console.error("Error during token validation:", error);
    localStorage.clear();
    window.location.href = '/login/';
  }
}

function logout() {
  localStorage.clear();
  window.location.href = "/login/";
}

document.addEventListener("DOMContentLoaded", () => {
  validateToken();
});
