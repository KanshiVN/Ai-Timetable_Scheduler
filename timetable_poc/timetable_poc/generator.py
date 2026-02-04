# generator.py
# =====================================================
# GLOBAL LAB-FIRST TIMETABLE GENERATOR
# WITH FALLBACK + PARALLEL BATCH SAFETY + DAY SAFETY
# =====================================================

from slot_maps import get_lab_slot_groups, get_lecture_slots
from collections import defaultdict

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def build_weekly_load_map(weekly_loads):
    """Maps (teacher, subject, class) to their load requirements"""
    return {
        (t, s, c): {
            "weekly_theory_load": th,
            "weekly_practical_load": pr
        }
        for t, s, c, th, pr in weekly_loads
    }


def build_batch_allocations(batch_allocs):
    """Groups batches by (teacher, subject, class)"""
    m = defaultdict(list)
    for t, s, c, b in batch_allocs:
        m[(t, s, c)].append(b)
    return m


def infer_lab_window(slot):
    """Determines the 2-slot window for a given slot ID"""
    if slot in (1, 2):
        return (1, 2)
    if slot in (3, 4):
        return (3, 4)
    if slot in (5, 6):
        return (5, 6)
    return None


# -----------------------------------------------------
# PHASE 1: GLOBAL LAB SCHEDULING
# -----------------------------------------------------
def generate_all_labs(data, global_teacher_busy):
    """
    Generate ALL lab sessions globally before any lectures.
    Ensures no teacher-subject-class has multiple lab sessions on same day.
    """
    timetable = []

    weekly_load = build_weekly_load_map(data["weekly_loads"])
    batch_allocs = build_batch_allocations(data["batch_allocations"])

    lab_sessions = []

    # Expand practical load into sessions (each session = 1 practical load unit)
    for (t, s, c), load in weekly_load.items():
        if load["weekly_practical_load"] <= 0:
            continue

        batches = batch_allocs.get((t, s, c), [])
        if not batches:
            class_name = data["class_map"][c]
            raise Exception(
                f"❌ No batch allocation for practical:\n"
                f"Teacher {t}, Subject {s}, Class {class_name}"
            )

        # Each practical load unit = 1 lab session
        total_sessions = int(load["weekly_practical_load"])
        for i in range(total_sessions):
            lab_sessions.append({
                "teacher": t,
                "subject": s,
                "class_id": c,
                "batch": batches[i % len(batches)]
            })

    # Sort by constraints (harder constraints first)
    lab_sessions.sort(key=lambda x: (x["teacher"], x["class_id"]))

    # Track parallel subjects: (day, class_id, lab_window) -> set of subjects
    parallel_subjects = defaultdict(set)

    # 🚨 CRITICAL: Track used lab days per teacher-subject-class
    # (teacher, subject, class, day) -> prevents multiple sessions same day
    used_lab_days = set()

    for lab in lab_sessions:
        class_name = data["class_map"][lab["class_id"]]
        lab_windows = get_lab_slot_groups(class_name)

        placed = False

        for window in lab_windows:
            for day in DAYS:
                # ❌ SAME TEACHER–SUBJECT–CLASS SAME DAY NOT ALLOWED
                day_key = (
                    lab["teacher"],
                    lab["subject"],
                    lab["class_id"],
                    day
                )
                if day_key in used_lab_days:
                    continue

                # Teacher must be free in both slots
                if any(
                    lab["teacher"] in global_teacher_busy.get((day, slot), set())
                    for slot in window
                ):
                    continue

                # Parallel batch subject safety
                # Same subject cannot run in parallel windows for same class
                key = (day, lab["class_id"], window)
                if lab["subject"] in parallel_subjects[key]:
                    continue

                # ✅ PLACE LAB
                for slot in window:
                    timetable.append({
                        "day": day,
                        "slot_id": slot,
                        "class_id": lab["class_id"],
                        "class_name": class_name,
                        "batch_id": lab["batch"],
                        "subject_id": lab["subject"],
                        "teacher_id": lab["teacher"],
                        "is_lab": True
                    })
                    global_teacher_busy.setdefault((day, slot), set()).add(lab["teacher"])

                parallel_subjects[key].add(lab["subject"])
                used_lab_days.add(day_key)

                placed = True
                break

            if placed:
                break

        if not placed:
            raise Exception(
                f"❌ Global lab placement failed:\n"
                f"Teacher {lab['teacher']}, Subject {lab['subject']}, Class {class_name}"
            )

    return timetable


# -----------------------------------------------------
# PHASE 2: CLASS-WISE LECTURES WITH SPREADING
# -----------------------------------------------------
def generate_class_lectures(
    class_id,
    class_name,
    data,
    global_teacher_busy,
    teacher_daily_lectures
):
    """
    Generate lectures for a single class.
    Spreads lectures across the week (max 1 per day per subject by default).
    """
    timetable = []

    weekly_load = build_weekly_load_map(data["weekly_loads"])
    lecture_slots = get_lecture_slots(class_name)

    # Collect lecture tasks for this class
    lecture_tasks = []

    for (t, s, c), load in weekly_load.items():
        if c == class_id and load["weekly_theory_load"] > 0:
            lecture_tasks.append({
                "teacher": t,
                "subject": s,
                "hours": int(load["weekly_theory_load"])
            })

    # 🔥 CRITICAL: schedule MOST CONSTRAINED teachers first
    lecture_tasks.sort(
        key=lambda x: len([
            k for k in global_teacher_busy
            if x["teacher"] in global_teacher_busy[k]
        ]),
        reverse=True
    )

    for task in lecture_tasks:
        t = task["teacher"]
        s = task["subject"]
        needed = task["hours"]
        placed = 0

        # Track per-subject-per-day count for spreading
        subject_day_count = defaultdict(int)

        # Multi-pass scheduling: Pass 1 spreads, Pass 2 fills
        for pass_num in [1, 2, 3]:
            for day in DAYS:
                for slot in lecture_slots:
                    if placed >= needed:
                        break

                    # Spreading rule: Pass 1 = max 1/day, Pass 2 = max 2/day
                    if pass_num == 1 and subject_day_count[day] >= 1:
                        continue
                    if pass_num == 2 and subject_day_count[day] >= 2:
                        continue

                    # Slot already used by this class?
                    if any(
                        e["day"] == day and e.get("slot_id") == slot
                        for e in timetable
                    ):
                        continue

                    # Check if teacher has lab in this slot's window
                    window = infer_lab_window(slot)
                    if window and any(
                        t in global_teacher_busy.get((day, s2), set())
                        for s2 in window
                    ):
                        continue

                    # Teacher busy in this exact slot?
                    if t in global_teacher_busy.get((day, slot), set()):
                        continue

                    # Daily lecture limit for teacher
                    teacher_limits = data.get("teacher_limits", {})
                    max_daily = teacher_limits.get(t)
                    if max_daily and teacher_daily_lectures[t][day] >= max_daily:
                        continue

                    # ✅ PLACE LECTURE
                    timetable.append({
                        "day": day,
                        "slot_id": slot,
                        "class_id": class_id,
                        "class_name": class_name,
                        "batch_id": None,
                        "subject_id": s,
                        "teacher_id": t,
                        "is_lab": False
                    })

                    global_teacher_busy.setdefault((day, slot), set()).add(t)
                    teacher_daily_lectures[t][day] += 1
                    subject_day_count[day] += 1
                    placed += 1

                if placed >= needed:
                    break
            if placed >= needed:
                break

        if placed < needed:
            raise Exception(
                f"❌ Lecture placement stuck for {class_name}, subject {s}\n"
                f"Placed {placed}/{needed} lectures"
            )

    return timetable


# -----------------------------------------------------
# MAIN GENERATION FUNCTION
# -----------------------------------------------------
def generate_timetable(data):
    """
    Main entry point for timetable generation.
    Returns list of timetable entries.
    """
    global_teacher_busy = {}
    teacher_daily_lectures = defaultdict(lambda: defaultdict(int))

    timetable = []

    # PHASE 1: Generate all labs first
    print("🔬 Generating labs...")
    lab_entries = generate_all_labs(data, global_teacher_busy)
    timetable.extend(lab_entries)
    print(f"✅ Generated {len(lab_entries)} lab entries")

    # PHASE 2: Generate lectures for each class
    print("📚 Generating lectures...")
    class_map = data["class_map"]

    for class_id, class_name in sorted(class_map.items(), key=lambda x: x[1]):
        print(f"  Processing {class_name}...")
        lecture_entries = generate_class_lectures(
            class_id,
            class_name,
            data,
            global_teacher_busy,
            teacher_daily_lectures
        )
        timetable.extend(lecture_entries)

    print(f"✅ Total entries generated: {len(timetable)}")

    return timetable