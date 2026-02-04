document.addEventListener("DOMContentLoaded", () => {

    // ==================================================
    // SESSION HANDLING (FINAL & CORRECT)
    // ==================================================
    const faculty_id = localStorage.getItem("faculty_id");

    if (!faculty_id) {
        alert("Session expired. Please login again.");
        window.location.href = "/";
        return;
    }

    // ==================================================
    // LOAD SUBJECTS BASED ON YEAR + SEMESTER
    // ==================================================
    function loadSubjects(year, semester, prefIds) {
        if (!semester) return;

        fetch(`/api/hod/subjects-by-semester?year=${year}&semester=${semester}`)
            .then(res => res.json())
            .then(subjects => {
                prefIds.forEach(id => {
                    const sel = document.getElementById(id);
                    sel.innerHTML = `<option value="">Select</option>`;

                    subjects.forEach(s => {
                        const opt = document.createElement("option");
                        opt.value = s.subject_name;
                        opt.textContent = s.subject_name;
                        sel.appendChild(opt);
                    });
                });
            })
            .catch(() => {
                alert("Failed to load subjects");
            });
    }

    // ==================================================
    // SEMESTER CHANGE HANDLERS
    // ==================================================
    document.getElementById("se_sem").addEventListener("change", e =>
        loadSubjects("SE", e.target.value, ["se_pref1", "se_pref2", "se_pref3"])
    );

    document.getElementById("te_sem").addEventListener("change", e =>
        loadSubjects("TE", e.target.value, ["te_pref1", "te_pref2", "te_pref3"])
    );

    document.getElementById("be_sem").addEventListener("change", e =>
        loadSubjects("BE", e.target.value, ["be_pref1", "be_pref2", "be_pref3"])
    );

    // ==================================================
    // FORM SUBMISSION
    // ==================================================
    document.getElementById("prefForm").addEventListener("submit", async e => {
        e.preventDefault();

        const facultyName = faculty_name.value.trim();
        const shortName = document.getElementById("short_name").value.trim();
        const designationVal = designation.value;

        if (!facultyName || !shortName || !designationVal) {
            alert("Please fill all required fields");
            return;
        }

        const payload = {
            faculty_id: faculty_id,
            faculty_name: facultyName,
            short_name: shortName,
            designation: designationVal,
            willing_for_practical: practical.checked,

            SE: {
                semester: se_sem.value,
                prefs: [se_pref1.value, se_pref2.value, se_pref3.value]
            },
            TE: {
                semester: te_sem.value,
                prefs: [te_pref1.value, te_pref2.value, te_pref3.value]
            },
            BE: {
                semester: be_sem.value,
                prefs: [be_pref1.value, be_pref2.value, be_pref3.value]
            }
        };

        try {
            const res = await fetch("/api/faculty/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            document.getElementById("msg").innerText =
                data.message || "Preferences submitted successfully";
            document.getElementById("msg").style.color = "green";

            document.getElementById("prefForm").reset();

        } catch (err) {
            alert("Failed to submit preferences");
        }
    });
});
