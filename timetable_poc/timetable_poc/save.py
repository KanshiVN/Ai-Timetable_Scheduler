from db import get_connection

def save_timetable(timetable):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM timetable")

    for entry in timetable:
        cur.execute("""
            INSERT INTO timetable (class_id, subject_id, teacher_id, slot_id)
            VALUES (%s, %s, %s, %s)
        """, (
            entry["class_id"],
            entry["subject_id"],
            entry["teacher_id"],
            entry["slot_id"]
        ))

    conn.commit()
    conn.close()
