from db import get_connection

def save_timetable(allocations):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM timetable")

    for a in allocations:
        cur.execute("""
            INSERT INTO timetable (class_id, subject_id, teacher_id, slot_id)
            VALUES (%s,%s,%s,%s)
        """, (a["class_id"], a["subject_id"], a["teacher_id"], a["slot_id"]))

    conn.commit()
    cur.close()
    conn.close()
