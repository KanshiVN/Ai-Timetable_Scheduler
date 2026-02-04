// ================= SEMESTER MAP =================
const SEMESTER_MAP = {
  SE: [3, 4],
  TE: [5, 6],
  BE: [7, 8]
};

// ================= TOGGLE UI =================
function showLoadConfig() {
  document.getElementById("loadConfigSection").style.display = "block";
  document.getElementById("divisionAllocationSection").style.display = "none";
}

function showDivisionAllocation() {
  document.getElementById("loadConfigSection").style.display = "none";
  document.getElementById("divisionAllocationSection").style.display = "block";
}

// ================= SUBJECT LOAD CONFIG =================
const yearSelect = document.getElementById("yearSelect");
const semesterSelect = document.getElementById("semesterSelect");

yearSelect.addEventListener("change", () =>
  populateSemesters(yearSelect, semesterSelect)
);

function populateSemesters(yearSel, semSel) {
  semSel.innerHTML = `<option value="">Select</option>`;
  if (!yearSel.value) return;

  SEMESTER_MAP[yearSel.value].forEach(s => {
    semSel.innerHTML += `<option value="${s}">Semester ${s}</option>`;
  });
}

// ================= LOAD TYPE TOGGLE =================
function toggleLoadInputs() {
  const type = document.getElementById("subjectType").value;
  document.getElementById("lectureLoad").style.display =
    type === "lecture" ? "inline" : "none";
  document.getElementById("practicalLoad").style.display =
    type === "lab" ? "inline" : "none";
}

// ================= ADD SUBJECT =================
function addSubject() {
  if (!yearSelect.value || !semesterSelect.value) {
    alert("Select year and semester");
    return;
  }

  const subjectName = document.getElementById("subjectName").value.trim();
  const subjectType = document.getElementById("subjectType").value;

  if (!subjectName) {
    alert("Enter subject name");
    return;
  }

  const payload = {
    subject_name: subjectName,
    is_lab: subjectType === "lab",
    year_level: yearSelect.value,
    semester: semesterSelect.value,
    weekly_theory_load:
      subjectType === "lecture"
        ? Number(document.getElementById("lectureLoad").value)
        : 0,
    weekly_practical_load:
      subjectType === "lab"
        ? Number(document.getElementById("practicalLoad").value)
        : 0
  };

  fetch("/api/hod/add-subject-with-load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(() => location.reload())
    .catch(() => alert("Failed to add subject"));
}

// ================= DIVISION ALLOCATION =================
const allocYear = document.getElementById("allocYear");
const allocSemester = document.getElementById("allocSemester");

allocYear.addEventListener("change", () =>
  populateSemesters(allocYear, allocSemester)
);

function loadAllocationTable() {
  const year = allocYear.value;
  const semester = allocSemester.value;
  const tbody = document.getElementById("allocationTable");

  if (!year || !semester) {
    alert("Select year and semester");
    return;
  }

  fetch(`/api/hod/subjects-for-allocation?year=${year}&semester=${semester}`)
    .then(res => res.json())
    .then(subjects => {
      tbody.innerHTML = "";

      if (!subjects.length) {
        tbody.innerHTML =
          `<tr><td colspan="4" align="center">No subjects</td></tr>`;
        return;
      }

      subjects.forEach(s => {
        const row = document.createElement("tr");

        row.innerHTML = `
          <td>${s.subject_name}</td>
          <td>
            <select class="teacherSelect">
              <option value="">Loading...</option>
            </select>
          </td>
          <td>
            <select class="divisionSelect"></select>
          </td>
          <td>
            <button onclick="saveAllocation(this, ${s.subject_id})">Save</button>
          </td>
        `;

        tbody.appendChild(row);

        loadTeacherDropdown(
          year,
          semester,
          s.subject_name,
          row.querySelector(".teacherSelect")
        );

        loadDivisions(year, row.querySelector(".divisionSelect"));
      });
    });
}

// ================= LOAD APPROVED TEACHERS DROPDOWN =================
function loadTeacherDropdown(year, semester, subjectName, select) {
  fetch(
    `/api/hod/approved-teachers?year=${year}&semester=${semester}&subject=${subjectName}`
  )
    .then(res => res.json())
    .then(teachers => {
      select.innerHTML = `<option value="">Select Teacher</option>`;

      if (!teachers.length) {
        select.innerHTML = `<option value="">No teachers</option>`;
        return;
      }

      teachers.forEach(t => {
        select.innerHTML += `
          <option value="${t.teacher_id}">
            ${t.teacher_name}
          </option>
        `;
      });
    })
    .catch(() => {
      select.innerHTML = `<option value="">Error</option>`;
    });
}

// ================= LOAD DIVISIONS =================
function loadDivisions(year, select) {
  fetch(`/api/classes?year=${year}`)
    .then(res => res.json())
    .then(classes => {
      select.innerHTML = "";
      classes.forEach(c => {
        select.innerHTML +=
          `<option value="${c.class_id}">${c.class_name}</option>`;
      });
    });
}

// ================= SAVE DIVISION ALLOCATION =================
function saveAllocation(btn, subjectId) {
  const row = btn.closest("tr");
  const teacherSelect = row.querySelector(".teacherSelect");
  const classId = row.querySelector(".divisionSelect").value;

  if (!teacherSelect.value) {
    alert("Select a teacher");
    return;
  }

  fetch("/api/hod/division-allocation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      teacher_id: Number(teacherSelect.value),
      subject_id: subjectId,
      class_id: Number(classId)
    })
  })
    .then(res => res.json())
    .then(d => alert(d.message || "Saved"))
    .catch(() => alert("Failed"));
}
