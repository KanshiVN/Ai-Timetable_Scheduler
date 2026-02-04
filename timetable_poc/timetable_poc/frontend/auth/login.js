async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;

    const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email: email,
            password: password,
            role: role
        })
    });

    const data = await res.json();

    if (res.ok) {
        localStorage.setItem("faculty_id", data.user_id);
        window.location.href = data.redirect;

    } else {
        document.getElementById("error").innerText = data.error;
    }
}
