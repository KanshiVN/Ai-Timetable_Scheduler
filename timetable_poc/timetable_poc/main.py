# main.py
# =====================================================
# ENTRY POINT – COMPLETE TIMETABLE GENERATION WITH VALIDATION
# =====================================================

import psycopg2
import os
from dotenv import load_dotenv
from generator import generate_timetable
from constraints import validate_timetable

# Load environment variables from .env file
load_dotenv()


def get_connection():
    """Establish Supabase database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=os.getenv("SUPABASE_DB_PORT", "5432"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD")
    )


def load_all_data(cursor):
    """Load all necessary data from database"""
    
    # Weekly loads
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id,
               weekly_theory_load, weekly_practical_load
        FROM teacher_weekly_load
    """)
    weekly_loads = cursor.fetchall()

    # Batch allocations
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id, batch_id
        FROM teacher_batch_subject_allocation
    """)
    batch_allocations = cursor.fetchall()

    # Classes
    cursor.execute("""
        SELECT class_id, class_name
        FROM classes
        ORDER BY class_name
    """)
    classes = cursor.fetchall()
    class_map = dict(classes)

    # Teachers with limits
    cursor.execute("""
        SELECT teacher_id, teacher_name, max_lectures_per_day
        FROM teachers
    """)
    teachers = cursor.fetchall()
    teacher_limits = {
        t_id: max_lec
        for t_id, _, max_lec in teachers
    }

    # Subjects
    cursor.execute("""
        SELECT subject_id, subject_name
        FROM subjects
        ORDER BY subject_name
    """)
    subjects = cursor.fetchall()

    # Batches
    cursor.execute("""
        SELECT batch_id, batch_name
        FROM class_batches
        ORDER BY batch_name
    """)
    batches = cursor.fetchall()

    # Theory allocations (teacher-subject-class)
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id
        FROM teacher_subject_allocation
    """)
    allocation_set = set(cursor.fetchall())

    # Practical allocations (teacher-subject-class-batch)
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id, batch_id
        FROM teacher_batch_subject_allocation
    """)
    batch_allocation_set = set(cursor.fetchall())

    return {
        "weekly_loads": weekly_loads,
        "batch_allocations": batch_allocations,
        "classes": classes,
        "class_map": class_map,
        "teachers": teachers,
        "teacher_limits": teacher_limits,
        "subjects": subjects,
        "batches": batches,
        "allocation_set": allocation_set,
        "batch_allocation_set": batch_allocation_set
    }


def run_generator():
    """Main function to generate and save timetable"""
    
    conn = get_connection()
    cur = conn.cursor()

    print("📥 Loading data from database...")
    data = load_all_data(cur)
    print("✅ Data loaded successfully")

    # Build weekly load map for validation
    weekly_load_map = {
        (t, s, c): {
            "weekly_theory_load": th,
            "weekly_practical_load": pr
        }
        for t, s, c, th, pr in data["weekly_loads"]
    }

    print("\n🔧 Generating timetable...")
    try:
        timetable = generate_timetable(data)
        print(f"✅ Generated {len(timetable)} timetable entries")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        cur.close()
        conn.close()
        raise

    # Validate before saving
    print("\n🔍 Validating timetable...")
    is_valid = validate_timetable(
        timetable,
        weekly_load_map,
        data["teacher_limits"],
        data["allocation_set"],
        data["batch_allocation_set"]
    )

    if not is_valid:
        print("❌ Validation failed - timetable not saved")
        cur.close()
        conn.close()
        raise Exception("Timetable validation failed")

    # Save to database
    print("\n💾 Saving timetable to database...")
    cur.execute("TRUNCATE TABLE timetable")

    # Slot time mapping
    LOGICAL_SLOT_TIME = {
        1: ("08:30", "09:30"),
        2: ("09:30", "10:30"),
        3: ("10:45", "11:45"),
        4: ("11:45", "12:45"),
        5: ("13:30", "14:30"),
        6: ("14:30", "15:30"),
    }

    for e in timetable:
        slot_id = e.get("slot_id") or e.get("slot")
        start_time, end_time = LOGICAL_SLOT_TIME.get(slot_id, ("00:00", "00:00"))
        
        cur.execute("""
            INSERT INTO timetable
            (class_id, subject_id, teacher_id, batch_id, is_lab, day, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            e["class_id"],
            e["subject_id"],
            e["teacher_id"],
            e.get("batch_id"),
            e["is_lab"],
            e["day"],
            start_time,
            end_time
        ))

    conn.commit()
    print(f"✅ Saved {len(timetable)} entries to database")

    # Print summary
    print("\n📊 TIMETABLE SUMMARY:")
    print(f"  Total entries: {len(timetable)}")
    
    lab_count = sum(1 for e in timetable if e["is_lab"])
    lecture_count = len(timetable) - lab_count
    print(f"  Lab entries: {lab_count}")
    print(f"  Lecture entries: {lecture_count}")
    
    # Count by class
    from collections import Counter
    class_counts = Counter(e["class_name"] for e in timetable)
    print("\n  Entries per class:")
    for class_name, count in sorted(class_counts.items()):
        print(f"    {class_name}: {count}")

    cur.close()
    conn.close()

    print("\n✅ Timetable generation completed successfully!")
    return timetable


if __name__ == "__main__":
    run_generator()