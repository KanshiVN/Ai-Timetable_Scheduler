# fetch_data.py
# =====================================================
# Centralized data loader for timetable engine
# Supports:
# - Class-level lectures
# - Batch-level practicals
# =====================================================

from db import get_connection


# -------------------------------
# CLASSES
# -------------------------------
def fetch_classes(cursor):
    cursor.execute("""
        SELECT class_id, class_name
        FROM classes
        ORDER BY class_name
    """)
    return cursor.fetchall()


# -------------------------------
# SUBJECTS
# -------------------------------
def fetch_subjects(cursor):
    cursor.execute("""
        SELECT subject_id, subject_name,
               lectures_per_week,
               is_lab,
               practicals_per_week
        FROM subjects
    """)
    return cursor.fetchall()


# -------------------------------
# TEACHERS
# -------------------------------
def fetch_teachers(cursor):
    cursor.execute("""
        SELECT teacher_id, teacher_name,
               max_lectures_per_day,
               max_practicals_per_day,
               max_lectures_per_week
        FROM teachers
    """)
    return cursor.fetchall()


# -------------------------------
# LECTURE ALLOCATIONS (CLASS LEVEL)
# -------------------------------
def fetch_allocations(cursor):
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id
        FROM teacher_subject_allocation
    """)
    return cursor.fetchall()


# -------------------------------
# WEEKLY LOAD (HOURS)
# -------------------------------
def fetch_weekly_load(cursor):
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id,
               weekly_theory_load,
               weekly_practical_load
        FROM teacher_weekly_load
    """)
    return cursor.fetchall()


# -------------------------------
# CLASS BATCHES
# -------------------------------
def fetch_batches(cursor):
    cursor.execute("""
        SELECT batch_id, class_id, batch_name
        FROM class_batches
        ORDER BY class_id, batch_name
    """)
    return cursor.fetchall()


# -------------------------------
# BATCH-WISE PRACTICAL ALLOCATIONS
# -------------------------------
def fetch_batch_allocations(cursor):
    cursor.execute("""
        SELECT teacher_id, subject_id, class_id, batch_id
        FROM teacher_batch_subject_allocation
    """)
    return cursor.fetchall()


# -------------------------------
# MASTER LOADER
# -------------------------------
def load_all_data(cursor):
    """
    Master loader used by main.py
    """
    return {
        "classes": fetch_classes(cursor),
        "subjects": fetch_subjects(cursor),
        "teachers": fetch_teachers(cursor),
        "allocations": fetch_allocations(cursor),          # lectures
        "weekly_loads": fetch_weekly_load(cursor),
        "batches": fetch_batches(cursor),
        "batch_allocations": fetch_batch_allocations(cursor)
    }
