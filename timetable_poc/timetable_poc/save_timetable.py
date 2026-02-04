# save_timetable.py
# =====================================================
# Persist generated timetable into database (FINAL, SAFE)
# =====================================================

from db import get_connection
from constraints import infer_lab_window

# -----------------------------------------------------
# SLOT ACCESS (slot / slot_id SAFE)
# -----------------------------------------------------
def get_slot(e):
    return e.get("slot_id") or e.get("slot")


# -------------------------------
# Single-slot lecture timings
# -------------------------------
SLOT_TIME_MAP = {
    1: ("08:30", "09:30"),
    2: ("09:30", "10:30"),
    3: ("10:45", "11:45"),
    4: ("11:45", "12:45"),
    5: ("13:30", "14:30"),
    6: ("14:30", "15:30"),
}

# -------------------------------
# Lab window → time mapping
# -------------------------------
LAB_WINDOW_TIME_MAP = {
    (1, 2): ("08:30", "10:30"),
    (3, 4): ("10:45", "12:45"),
    (5, 6): ("13:30", "15:30"),
}


def save_timetable(timetable):
    conn = get_connection()
    cursor = conn.cursor()

    # Clear old timetable
    cursor.execute("DELETE FROM timetable")

    for e in timetable:
        slot = get_slot(e)

        if slot is None:
            raise KeyError("❌ Timetable entry missing slot/slot_id")

        # ---------------------------
        # Determine start & end time
        # ---------------------------
        if e["is_lab"]:
            lab_window = infer_lab_window(slot)
            start_time, end_time = LAB_WINDOW_TIME_MAP[lab_window]
        else:
            start_time, end_time = SLOT_TIME_MAP[slot]

        # ---------------------------
        # Insert row
        # ---------------------------
        cursor.execute("""
            INSERT INTO timetable (
                class_id,
                subject_id,
                teacher_id,
                batch_id,
                is_lab,
                day,
                start_time,
                end_time
            )
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
    cursor.close()
    conn.close()

    print("💾 Timetable saved to database successfully")