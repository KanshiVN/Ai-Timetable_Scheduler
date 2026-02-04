document.addEventListener("DOMContentLoaded", () => {

  const classSelect = document.getElementById("class_id");
  const subjectSelect = document.getElementById("subject_id");
  const teacherSelect = document.getElementById("teacher_id");
  const loadInput = document.getElementById("weekly_theory_load");
  const msg = document.getElementById("msg");

  // ------------------ LOAD CLASSES ------------------
  fetch("/api/classes")
    .then(res => res.json())
    .then(data => {
      data.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.class_id;
        opt.textContent = c.class_name;
        classSelect.appendChild(opt);
      });
    });

  // ------------------ LOAD SUBJECTS ------------------
  fetch("/api/subjects/all")
    .then(res => res.json())
    .then(data => {
      data.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.subject_id;
        opt.textContent = s.subject_name;
        subjectSelect.appendChild(opt);
      });
    });

  // ------------------ LOAD TEACHERS ------------------
  fetch("/api/teachers")
    .then(res => res.json())
    .then(data => {
      data.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t.teacher_id;
        opt.textContent = t.teacher_name;
        teacherSelect.appendChild(opt);
      });
    });

  // ------------------ FETCH LOAD ------------------
  subjectSelect.addEventListener("change", () => {
    const subject_id = subjectSelect.value;
    const class_id = classSelect.value;

    if (!subject_id || !class_id) return;

    fetch(`/api/hod/subject-load?subject_id=${subject_id}&class_id=${class_id}`)
      .then(res => res.json())
      .then(d => {
        loadInput.value = d.weekly_theory_load || 0;
      });
  });

  // ------------------ SUBMIT ------------------
  document.getElementById("lectureForm").addEventListener("submit", e => {
    e.preventDefault();

    fetch("/api/hod/lecture-allocation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        class_id: classSelect.value,
        subject_id: subjectSelect.value,
        teacher_id: teacherSelect.value
      })
    })
    .then(res => res.json())
    .then(d => {
      msg.textContent = d.message;
      msg.style.color = "green";
    })
    .catch(() => {
      msg.textContent = "Failed to allocate lecture";
      msg.style.color = "red";
    });
  });

});
