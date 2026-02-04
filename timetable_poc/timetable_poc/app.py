from flask import Flask, request, jsonify, send_from_directory, render_template_string
import psycopg2
import os
from dotenv import load_dotenv
from collections import defaultdict
from generator import generate_timetable

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# =====================================================
# DATABASE
# =====================================================

def get_connection():
    """Establish Supabase database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=os.getenv("SUPABASE_DB_PORT", "5432"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD")
    )

# =====================================================
# STATIC FILES
# =====================================================

@app.route("/auth/<path:path>")
def auth_files(path):
    return send_from_directory("frontend/auth", path)

@app.route("/faculty/<path:path>")
def faculty_files(path):
    return send_from_directory("frontend/faculty", path)

@app.route("/hod/<path:path>")
def hod_files(path):
    return send_from_directory("frontend/hod", path)

@app.route("/landing.css")
def serve_landing_css():
    return send_from_directory("frontend", "landing.css")

# =====================================================
# LANDING & LOGIN
# =====================================================

@app.route("/")
def landing_page():
    return send_from_directory("frontend", "index.html")

@app.route("/login")
def login_page():
    return send_from_directory("frontend/auth", "login.html")

@app.route("/public/timetable")
def public_timetable_view():
    return send_from_directory("frontend/public", "public_view.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, role
        FROM users
        WHERE email=%s AND password=%s AND role=%s
    """, (data["email"], data["password"], data["role"]))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    user_id, role = user

    return jsonify({
        "user_id": user_id,
        "redirect": "/hod/dashboard" if role == "HOD"
        else f"/faculty/dashboard?uid={user_id}"
    })

# =====================================================
# FACULTY UI
# =====================================================

FACULTY_LAYOUT = open("frontend/faculty/layout.html", encoding='utf-8').read()

@app.route("/faculty/dashboard")
def faculty_dashboard():
    with open("frontend/faculty/faculty_dashboard.html", encoding='utf-8') as f:
        return render_template_string(
            FACULTY_LAYOUT,
            title="Dashboard",
            content=f.read()
        )

@app.route("/faculty/subject-preferences")
def faculty_preferences_page():
    with open("frontend/faculty/subject_preferences.html", encoding='utf-8') as f:
        return render_template_string(
            FACULTY_LAYOUT,
            title="Preferences",
            content=f.read()
        )

@app.route("/faculty/view-timetable")
def faculty_view_timetable():
    with open("frontend/faculty/view_timetable.html", encoding='utf-8') as f:
        return render_template_string(
            FACULTY_LAYOUT,
            title="View Timetable",
            content=f.read()
        )

# =====================================================
# HOD UI
# =====================================================

HOD_LAYOUT = open("frontend/hod/layout.html", encoding='utf-8').read()

@app.route("/hod/dashboard")
def hod_dashboard():
    with open("frontend/hod/hod_dashboard.html", encoding='utf-8') as f:
        return render_template_string(HOD_LAYOUT, title="Dashboard", content=f.read())

@app.route("/hod/allot")
def hod_allot():
    with open("frontend/hod/allot_subjects.html", encoding='utf-8') as f:
        return render_template_string(
            HOD_LAYOUT,
            title="Allot Subjects",
            content=f.read()
        )

@app.route("/hod/data-input")
def hod_data_input():
    with open("frontend/hod/data_input.html", encoding='utf-8') as f:
        return render_template_string(HOD_LAYOUT, title="Data Input", content=f.read())

# =====================================================
# SUBJECT LOAD CONFIG (PHASE 2) ✅ FIXED
# =====================================================

@app.route("/api/hod/subjects-by-semester")
def subjects_by_semester():
    year = request.args.get("year")
    semester = request.args.get("semester")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.subject_id, s.subject_name, s.is_lab,
               c.weekly_theory_load, c.weekly_practical_load
        FROM subject_load_config c
        JOIN subjects s ON s.subject_id = c.subject_id
        WHERE c.year_level=%s AND c.semester=%s
        ORDER BY s.subject_name
    """, (year, semester))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "subject_id": r[0],
            "subject_name": r[1],
            "is_lab": r[2],
            "weekly_theory_load": r[3],
            "weekly_practical_load": r[4]
        }
        for r in rows
    ])

@app.route("/api/hod/add-subject-with-load", methods=["POST"])
def add_subject_with_load():
    d = request.json
    conn = get_connection()
    cur = conn.cursor()

    is_lab = d["is_lab"]

    # 🔒 ENFORCE CORRECT LOAD LOGIC
    weekly_theory = d["weekly_theory_load"]
    weekly_practical = d["weekly_practical_load"]

    if is_lab:
        weekly_theory = 0
    else:
        weekly_practical = 0

    cur.execute("""
        INSERT INTO subjects (subject_name, department, is_lab)
        VALUES (%s, %s, %s)
        ON CONFLICT (subject_name) DO NOTHING
        RETURNING subject_id
    """, (d["subject_name"], "Computer Engg", is_lab))

    row = cur.fetchone()
    if not row:
        cur.execute(
            "SELECT subject_id FROM subjects WHERE subject_name=%s",
            (d["subject_name"],)
        )
        row = cur.fetchone()

    subject_id = row[0]

    cur.execute("""
        INSERT INTO subject_load_config
        (subject_id, year_level, semester,
         weekly_theory_load, weekly_practical_load)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (subject_id, year_level, semester)
        DO UPDATE SET
          weekly_theory_load = EXCLUDED.weekly_theory_load,
          weekly_practical_load = EXCLUDED.weekly_practical_load
    """, (
        subject_id,
        d["year_level"],
        d["semester"],
        weekly_theory,
        weekly_practical
    ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Subject load saved correctly"})

# =====================================================
# FACULTY SUBJECT PREFERENCES (PHASE 1)
# =====================================================

@app.route("/api/faculty/preferences", methods=["POST"])
def save_faculty_preferences():
    try:
        data = request.json
        conn = get_connection()
        cur = conn.cursor()

        # TEMP FIX: auto-increment faculty_id for testing
        cur.execute("SELECT COALESCE(MAX(faculty_id), 0) + 1 FROM faculty_subject_preferences")
        faculty_id = cur.fetchone()[0]

        for year in ["SE", "TE", "BE"]:
            cur.execute("""
                INSERT INTO faculty_subject_preferences (
                    faculty_id,
                    faculty_name,
                    designation,
                    class_name,
                    pref_1,
                    pref_2,
                    pref_3,
                    allocated_subject,
                    status,
                    short_name,
                    created_time,
                    semester,
                    willing_for_practical,
                    year_level
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    NOW(), %s, %s, %s
                )
            """, (
                faculty_id,
                data["faculty_name"],
                data["designation"],
                None,                                  # class_name (later)
                data[year]["prefs"][0],
                data[year]["prefs"][1],
                data[year]["prefs"][2],
                None,                                  # allocated_subject
                "PENDING",
                data["short_name"],                   # ✅ short name
                int(data[year]["semester"]),
                data["willing_for_practical"],
                year
            ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Preferences submitted successfully"})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500


# =====================================================
# HOD – APPROVED TEACHERS FOR SUBJECT
# =====================================================

@app.route("/api/hod/approved-teachers")
def approved_teachers():
    year = request.args.get("year")
    semester = request.args.get("semester")
    subject = request.args.get("subject")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT faculty_id, faculty_name
        FROM faculty_subject_preferences
        WHERE status = 'APPROVED'
          AND year_level = %s
          AND semester = %s
          AND allocated_subject = %s
    """, (year, semester, subject))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"teacher_id": r[0], "teacher_name": r[1]}
        for r in rows
    ])


# =====================================================
# HOD VIEW + APPROVE PREFERENCES (PHASE 3A)
# =====================================================

# =====================================================
# HOD – ALLOT PRACTICALS UI
# =====================================================

@app.route("/hod/allot-practicals")
def hod_allot_practicals():
    with open("frontend/hod/allot_practicals.html", encoding='utf-8') as f:
        return render_template_string(
            HOD_LAYOUT,
            title="Allot Practicals",
            content=f.read()
        )

@app.route("/api/hod/preferences")
def hod_preferences():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, faculty_id, faculty_name,
               year_level, semester,
               pref_1, pref_2, pref_3
        FROM faculty_subject_preferences
        WHERE status='PENDING'
        ORDER BY faculty_name, year_level
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "faculty_id": r[1],
            "faculty_name": r[2],
            "year_level": r[3],
            "semester": r[4],
            "preferences": [r[5], r[6], r[7]]
        }
        for r in rows
    ])

@app.route("/api/hod/approve-preferences", methods=["POST"])
def approve_preferences():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    try:
        for a in data["approvals"]:
            preference_id = a["preference_id"]
            allocated_subject = a["allocated_subject"]

            # ---------------------------------------------
            # 1. Approve preference
            # ---------------------------------------------
            cur.execute("""
                UPDATE faculty_subject_preferences
                SET allocated_subject = %s,
                    status = 'APPROVED'
                WHERE id = %s
                  AND status = 'PENDING'
                RETURNING faculty_id, faculty_name
            """, (allocated_subject, preference_id))

            row = cur.fetchone()
            if not row:
                continue

            faculty_id, faculty_name = row

            # ---------------------------------------------
            # 2. AUTO INSERT INTO TEACHERS TABLE ✅
            # ---------------------------------------------
            cur.execute("""
                INSERT INTO teachers
                (teacher_id, teacher_name, department,
                 max_lectures_per_day, max_practicals_per_day, max_lectures_per_week)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (teacher_id) DO NOTHING
            """, (
                faculty_id,
                faculty_name,
                "Computer Engg",
                4,   # default max lectures/day
                8,   # default max practicals/day
                15   # default max lectures/week
            ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Preferences approved and teachers synced"})

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print("APPROVE ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/hod/delete-preference/<int:pref_id>", methods=["DELETE"])
def delete_preference(pref_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM faculty_subject_preferences
        WHERE id = %s
    """, (pref_id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Preference deleted"})

# =====================================================
# HOD – GET ALLOCATED TEACHER FOR SUBJECT (READ-ONLY)
# =====================================================

@app.route("/api/hod/allocated-teacher")
def get_allocated_teacher():
    subject_id = request.args.get("subject_id")
    class_id = request.args.get("class_id")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.teacher_id, t.teacher_name
        FROM teacher_subject_allocation tsa
        JOIN teachers t ON t.teacher_id = tsa.teacher_id
        WHERE tsa.subject_id = %s
          AND tsa.class_id = %s
        LIMIT 1
    """, (subject_id, class_id))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({})

    return jsonify({
        "teacher_id": row[0],
        "teacher_name": row[1]
    })



# =====================================================
# HOD – SUBJECTS FOR DIVISION ALLOCATION
# =====================================================

@app.route("/api/hod/subjects-for-allocation")
def subjects_for_allocation():
    year = request.args.get("year")
    semester = request.args.get("semester")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.subject_id, s.subject_name
        FROM subject_load_config c
        JOIN subjects s ON s.subject_id = c.subject_id
        WHERE c.year_level = %s
          AND c.semester = %s
        ORDER BY s.subject_name
    """, (year, semester))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"subject_id": r[0], "subject_name": r[1]}
        for r in rows
    ])


@app.route("/api/hod/division-allocation", methods=["POST"])
def save_division_allocation():
    try:
        d = request.json
        conn = get_connection()
        cur = conn.cursor()

        teacher_id = d["teacher_id"]
        subject_id = d["subject_id"]
        class_id = d["class_id"]

        # --------------------------------------------------
        # 1. Get year & semester for the subject
        # --------------------------------------------------
        cur.execute("""
            SELECT year_level, semester
            FROM subject_load_config
            WHERE subject_id = %s
            LIMIT 1
        """, (subject_id,))

        row = cur.fetchone()
        if not row:
            raise Exception("Year / Semester not found for subject")

        year, semester = row

        # --------------------------------------------------
        # 2. Prevent duplicate allocation
        # --------------------------------------------------
        cur.execute("""
            SELECT 1
            FROM teacher_subject_allocation
            WHERE teacher_id = %s
              AND subject_id = %s
              AND class_id = %s
        """, (teacher_id, subject_id, class_id))

        if cur.fetchone():
            return jsonify({"message": "Already allocated"}), 200

        # --------------------------------------------------
        # 3. Insert FINAL teacher–subject–class allocation
        # --------------------------------------------------
        cur.execute("""
            INSERT INTO teacher_subject_allocation
            (teacher_id, subject_id, class_id)
            VALUES (%s, %s, %s)
        """, (teacher_id, subject_id, class_id))

        # --------------------------------------------------
        # 4. Insert weekly load
        # --------------------------------------------------
        cur.execute("""
            SELECT weekly_theory_load, weekly_practical_load
            FROM subject_load_config
            WHERE subject_id = %s
              AND year_level = %s
              AND semester = %s
        """, (subject_id, year, semester))

        theory, practical = cur.fetchone()

        cur.execute("""
            INSERT INTO teacher_weekly_load
            (teacher_id, subject_id, class_id,
             weekly_theory_load, weekly_practical_load)
            VALUES (%s, %s, %s, %s, %s)
        """, (teacher_id, subject_id, class_id, theory, practical))

        # --------------------------------------------------
        # 5. ✅ UPDATE faculty_subject_preferences (IMPORTANT)
        # --------------------------------------------------
        cur.execute("""
            UPDATE faculty_subject_preferences
            SET
                subject_id = %s,
                class_name = (
                    SELECT class_name
                    FROM classes
                    WHERE class_id = %s
                )
            WHERE faculty_id = %s
              AND allocated_subject = (
                  SELECT subject_name
                  FROM subjects
                  WHERE subject_id = %s
              )
              AND year_level = %s
              AND semester = %s
        """, (
            subject_id,
            class_id,
            teacher_id,
            subject_id,
            year,
            semester
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Division allocated successfully"})

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print("DIVISION ALLOCATION ERROR:", e)
        return jsonify({"error": str(e)}), 500



@app.route("/api/hod/lab-subjects")
def hod_lab_subjects():
    year = request.args.get("year")
    semester = request.args.get("semester")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.subject_id, s.subject_name
        FROM subject_load_config c
        JOIN subjects s ON s.subject_id = c.subject_id
        WHERE s.is_lab = true
          AND c.year_level = %s
          AND c.semester = %s
        ORDER BY s.subject_name
    """, (year, semester))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "subject_id": r[0],
            "subject_name": r[1]
        }
        for r in rows
    ])



@app.route("/api/hod/willing-practical-faculty")
def hod_willing_practical_faculty():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT faculty_id, faculty_name, short_name
        FROM faculty_subject_preferences
        WHERE willing_for_practical = true
          AND status = 'APPROVED'
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "faculty_id": r[0],
            "faculty_name": r[1],
            "short_name": r[2]
        }
        for r in rows
    ])


# =====================================================
# GENERATE TIMETABLE ✅ FIXED
# =====================================================

@app.route("/api/hod/generate-timetable", methods=["POST"])
def api_generate_timetable():
    LOGICAL_SLOT_TIME = {
        1: ("08:30", "09:30"),
        2: ("09:30", "10:30"),
        3: ("10:45", "11:45"),
        4: ("11:45", "12:45"),
        5: ("13:30", "14:30"),
        6: ("14:30", "15:30"),
    }
    
    try:
        conn = get_connection()
        cur = conn.cursor()

        # =====================================================
        # 1. FETCH ACTIVE CLASSES
        # =====================================================
        cur.execute("""
            SELECT class_id, class_name
            FROM classes
            WHERE class_name IN (
                'SE-A','SE-B','SE-C',
                'TE-A','TE-B',
                'BE-A','BE-B'
            )
            ORDER BY class_name
        """)
        class_rows = cur.fetchall()
        class_map = {c[0]: c[1] for c in class_rows}

        # =====================================================
        # 2. FETCH TEACHERS
        # =====================================================
        cur.execute("""
            SELECT teacher_id, teacher_name, max_lectures_per_day
            FROM teachers
        """)
        teachers = cur.fetchall()

        teacher_limits = {
            t[0]: t[2]   # teacher_id → max_lectures_per_day
            for t in teachers
        }

        # =====================================================
        # 3. FETCH WEEKLY LOAD (SOURCE OF TRUTH)
        # =====================================================
        cur.execute("""
            SELECT
                teacher_id,
                subject_id,
                class_id,
                weekly_theory_load,
                weekly_practical_load
            FROM teacher_weekly_load
        """)
        weekly_loads = cur.fetchall()

        weekly_load_map = {
            (t, s, c): {
                "weekly_theory_load": th,
                "weekly_practical_load": pr
            }
            for t, s, c, th, pr in weekly_loads
        }

        # =====================================================
        # 4. THEORY ALLOCATIONS
        # =====================================================
        cur.execute("""
            SELECT teacher_id, subject_id, class_id
            FROM teacher_subject_allocation
        """)
        allocation_set = set(cur.fetchall())

        # =====================================================
        # 5. PRACTICAL (BATCH) ALLOCATIONS
        # =====================================================
        cur.execute("""
            SELECT teacher_id, subject_id, class_id, batch_id
            FROM teacher_batch_subject_allocation
        """)
        batch_allocations = cur.fetchall()
        batch_allocation_set = set(batch_allocations)

        # =====================================================
        # 6. PREPARE GENERATOR INPUT
        # =====================================================
        data = {
            "teachers": teachers,
            "weekly_loads": weekly_loads,
            "batch_allocations": batch_allocations,
            "class_map": class_map,
            "teacher_limits": teacher_limits,
            "allocation_set": allocation_set,
            "batch_allocation_set": batch_allocation_set
        }

        # =====================================================
        # 7. GENERATE TIMETABLE ✅ Using the imported function
        # =====================================================
        final_timetable = generate_timetable(data)

        # =====================================================
        # 8. VALIDATE (OPTIONAL - already done in generator)
        # =====================================================
        from constraints import validate_timetable
        
        if not validate_timetable(
            final_timetable,
            weekly_load_map,
            teacher_limits,
            allocation_set,
            batch_allocation_set
        ):
            raise Exception("Constraint validation failed")

        # =====================================================
        # 9. SAVE TO DATABASE
        # =====================================================
        cur.execute("TRUNCATE timetable")

        cur.executemany("""
            INSERT INTO timetable
            (class_id, subject_id, teacher_id, batch_id, is_lab, day, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            (
                e["class_id"],
                e["subject_id"],
                e["teacher_id"],
                e.get("batch_id"),
                e["is_lab"],
                e["day"],
                LOGICAL_SLOT_TIME[e["slot_id"]][0],
                LOGICAL_SLOT_TIME[e["slot_id"]][1]
            )
            for e in final_timetable
        ])

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Timetable generated successfully",
            "total_entries": len(final_timetable)
        })

    except Exception as e:
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass

        print("TIMETABLE GENERATION ERROR:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# VIEW TIMETABLE ✅ COMPLETELY FIXED
# =====================================================

@app.route("/api/hod/timetable")
def hod_timetable():
    class_id = request.args.get("class_id")

    conn = get_connection()
    cur = conn.cursor()

    # JOIN with faculty_subject_preferences to get the assigned short_name
    cur.execute("""
        SELECT
            t.day,
            t.start_time,
            t.end_time,
            s.subject_name,
            COALESCE(pref.short_name, LEFT(te.teacher_name, 3)) as short_name,
            t.is_lab,
            t.batch_id
        FROM timetable t
        JOIN subjects s ON s.subject_id = t.subject_id
        JOIN teachers te ON te.teacher_id = t.teacher_id
        LEFT JOIN faculty_subject_preferences pref 
            ON pref.faculty_id = t.teacher_id 
            AND pref.year_level = (SELECT LEFT(class_name, 2) FROM classes WHERE class_id = %s)
            AND pref.allocated_subject = s.subject_name
        WHERE t.class_id = %s
        ORDER BY 
            CASE 
                WHEN t.day IN ('Monday', 'Mon') THEN 1
                WHEN t.day IN ('Tuesday', 'Tue') THEN 2
                WHEN t.day IN ('Wednesday', 'Wed') THEN 3
                WHEN t.day IN ('Thursday', 'Thu') THEN 4
                WHEN t.day IN ('Friday', 'Fri') THEN 5
                ELSE 6
            END,
            t.start_time
    """, (class_id, class_id))

    rows = cur.fetchall()
    result = []
    
    for row in rows:
        day, start_time, end_time, subject, short_name, is_lab, batch_id = row
        
        if is_lab and batch_id:
            cur.execute("SELECT batch_name FROM class_batches WHERE batch_id = %s", (batch_id,))
            batch_row = cur.fetchone()
            batch_name = batch_row[0] if batch_row else f"B{batch_id}"
            display = f"{subject} ({short_name})<br>{batch_name}"
        else:
            display = f"{subject} ({short_name})"

        result.append({
            "day": day,
            "start_time": str(start_time),
            "end_time": str(end_time),
            "display": display
        })
    
    cur.close()
    conn.close()
    return jsonify(result)


# =====================================================
# FACULTY TIMETABLE
# =====================================================

@app.route("/api/timetable")
def faculty_timetable():
    """Get timetable entries for a specific teacher"""
    teacher_id = request.args.get("teacher_id")
    
    conn = get_connection()
    cur = conn.cursor()

    if teacher_id:
        # Get specific teacher's timetable
        cur.execute("""
            SELECT
                c.class_name,
                s.subject_name,
                t.teacher_name,
                tt.day,
                tt.start_time,
                tt.end_time,
                s.is_lab,
                cb.batch_name
            FROM timetable tt
            JOIN classes c ON c.class_id = tt.class_id
            JOIN subjects s ON s.subject_id = tt.subject_id
            JOIN teachers t ON t.teacher_id = tt.teacher_id
            LEFT JOIN class_batches cb ON cb.batch_id = tt.batch_id
            WHERE tt.teacher_id = %s
            ORDER BY 
                CASE 
                    WHEN tt.day IN ('Monday', 'Mon') THEN 1
                    WHEN tt.day IN ('Tuesday', 'Tue') THEN 2
                    WHEN tt.day IN ('Wednesday', 'Wed') THEN 3
                    WHEN tt.day IN ('Thursday', 'Thu') THEN 4
                    WHEN tt.day IN ('Friday', 'Fri') THEN 5
                    ELSE 6
                END,
                tt.start_time
        """, (teacher_id,))
    else:
        # Get all timetable entries
        cur.execute("""
            SELECT
                c.class_name,
                s.subject_name,
                t.teacher_name,
                tt.day,
                tt.start_time,
                tt.end_time,
                s.is_lab,
                cb.batch_name
            FROM timetable tt
            JOIN classes c ON c.class_id = tt.class_id
            JOIN subjects s ON s.subject_id = tt.subject_id
            JOIN teachers t ON t.teacher_id = tt.teacher_id
            LEFT JOIN class_batches cb ON cb.batch_id = tt.batch_id
            ORDER BY 
                CASE 
                    WHEN tt.day IN ('Monday', 'Mon') THEN 1
                    WHEN tt.day IN ('Tuesday', 'Tue') THEN 2
                    WHEN tt.day IN ('Wednesday', 'Wed') THEN 3
                    WHEN tt.day IN ('Thursday', 'Thu') THEN 4
                    WHEN tt.day IN ('Friday', 'Fri') THEN 5
                    ELSE 6
                END,
                tt.start_time
        """)

    rows = cur.fetchall()
    result = []
    
    for row in rows:
        class_name, subject, teacher, day, start_time, end_time, is_lab, batch_name = row
        
        result.append({
            "class": class_name,
            "subject": subject,
            "teacher": teacher,
            "day": day,
            "start_time": str(start_time),
            "end_time": str(end_time),
            "type": "LAB" if is_lab else "LECTURE",
            "batch": batch_name
        })
    
    cur.close()
    conn.close()
    return jsonify(result)


# =====================================================
# CLASSES & BATCHES
# =====================================================

@app.route("/api/classes")
def get_classes():
    year = request.args.get("year")  # SE / TE / BE

    conn = get_connection()
    cur = conn.cursor()

    if year:
        cur.execute("""
            SELECT class_id, class_name
            FROM classes
            WHERE class_name LIKE %s
            ORDER BY class_name
        """, (f"{year}-%",))
    else:
        cur.execute("""
            SELECT class_id, class_name
            FROM classes
            ORDER BY class_name
        """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"class_id": r[0], "class_name": r[1]}
        for r in rows
    ])


@app.route("/api/class-batches")
def get_class_batches():
    class_id = request.args.get("class_id")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT batch_id, batch_name
        FROM class_batches
        WHERE class_id = %s
        ORDER BY batch_name
    """, (class_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"batch_id": r[0], "batch_name": r[1]}
        for r in rows
    ])


@app.route("/api/hod/allot-practical", methods=["POST"])
def allot_practical():
    try:
        d = request.json

        conn = get_connection()
        cur = conn.cursor()

        # ---------------------------------------------
        # 1. Prevent duplicate allocation
        # ---------------------------------------------
        cur.execute("""
            SELECT 1
            FROM teacher_batch_subject_allocation
            WHERE teacher_id = %s
              AND subject_id = %s
              AND class_id = %s
              AND batch_id = %s
        """, (
            d["faculty_id"],
            d["subject_id"],
            d["class_id"],
            d["batch_id"]
        ))

        if cur.fetchone():
            return jsonify({"message": "Already allotted"}), 200

        # ---------------------------------------------
        # 2. Insert allocation
        # ---------------------------------------------
        cur.execute("""
            INSERT INTO teacher_batch_subject_allocation
            (teacher_id, subject_id, class_id, batch_id)
            VALUES (%s, %s, %s, %s)
        """, (
            d["faculty_id"],
            d["subject_id"],
            d["class_id"],
            d["batch_id"]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Practical allotted successfully"})

    except Exception as e:
        print("ALLOT PRACTICAL ERROR:", e)
        return jsonify({"error": "Failed to allot practical"}), 500



# =====================================================
# HELPER / INTERNAL
# =====================================================

@app.route("/api/hod/configured-years")
def configured_years():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT year_level, semester
        FROM subject_load_config
        ORDER BY year_level, semester
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"year_level": r[0], "semester": r[1]}
        for r in rows
    ])

@app.route("/api/internal/subject-load-map")
def subject_load_map():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT subject_id, year_level, semester,
               weekly_theory_load, weekly_practical_load
        FROM subject_load_config
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "subject_id": r[0],
            "year_level": r[1],
            "semester": r[2],
            "theory": r[3],
            "practical": r[4]
        }
        for r in rows
    ])

@app.route("/api/hod/recalculate-weekly-load", methods=["POST"])
def recalculate_weekly_load():
    try:
        conn = get_connection()
        cur = conn.cursor()

        # =====================================================
        # 1. RESET WEEKLY LOAD TABLE
        # =====================================================
        cur.execute("TRUNCATE teacher_weekly_load")

        # =====================================================
        # 2. INSERT THEORY LOADS (ONE ROW PER SUBJECT)
        # =====================================================
        cur.execute("""
            INSERT INTO teacher_weekly_load (
                teacher_id,
                subject_id,
                class_id,
                weekly_theory_load,
                weekly_practical_load
            )
            SELECT
                tsa.teacher_id,
                tsa.subject_id,
                tsa.class_id,
                slc.weekly_theory_load,
                0
            FROM teacher_subject_allocation tsa
            JOIN subject_load_config slc
              ON slc.subject_id = tsa.subject_id
        """)

        # =====================================================
        # 3. MERGE PRACTICAL LOADS (AGGREGATED PER SUBJECT)
        # =====================================================
        cur.execute("""
            INSERT INTO teacher_weekly_load (
                teacher_id,
                subject_id,
                class_id,
                weekly_theory_load,
                weekly_practical_load
            )
            SELECT
                tbsa.teacher_id,
                tbsa.subject_id,
                tbsa.class_id,
                0,
                MAX(slc.weekly_practical_load)
            FROM teacher_batch_subject_allocation tbsa
            JOIN subject_load_config slc
              ON slc.subject_id = tbsa.subject_id
            GROUP BY
                tbsa.teacher_id,
                tbsa.subject_id,
                tbsa.class_id
            ON CONFLICT (teacher_id, subject_id, class_id)
            DO UPDATE
            SET weekly_practical_load = EXCLUDED.weekly_practical_load
        """)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Weekly load recalculated successfully"
        })

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print("RECALC LOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500



@app.route("/hod/generate-timetable")
def hod_generate_timetable():
    with open("frontend/hod/generate_timetable.html", encoding='utf-8') as f:
        return render_template_string(
            HOD_LAYOUT,
            title="Generate Timetable",
            content=f.read()
        )

@app.route("/hod/view-timetable")
def hod_view_timetable():
    with open("frontend/hod/view_timetable.html", encoding='utf-8') as f:
        return render_template_string(
            HOD_LAYOUT,
            title="View Timetable",
            content=f.read()
        )

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)