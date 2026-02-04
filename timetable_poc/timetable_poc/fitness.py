from collections import defaultdict

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

def fitness(timetable, slot_day_map, slot_type_map, subject_type_map):
    score = 1000

    # ---------------------------------------
    # 1. Teacher clash (HARD)
    # ---------------------------------------
    teacher_day_slot = set()

    for entry in timetable:
        key = (
            entry["teacher_id"],
            slot_day_map[entry["slot"]],
            entry["slot"]
        )

        if key in teacher_day_slot:
            score -= 300
        else:
            teacher_day_slot.add(key)

    # ---------------------------------------
    # 2. Practical over-concentration (SOFT)
    # ---------------------------------------
    practical_count = defaultdict(int)

    for entry in timetable:
        if entry["is_lab"]:
            practical_count[(entry["class_id"], entry["day"])] += 1

    for (_, _), count in practical_count.items():
        if count > 2:
            score -= 50 * (count - 2)

    # ---------------------------------------
    # 3. Subject spread (SOFT)
    # ---------------------------------------
    subject_days = defaultdict(set)

    for entry in timetable:
        subject_days[entry["subject_id"]].add(entry["day"])

    for days in subject_days.values():
        if len(days) < 2:
            score -= 20

    return max(score, 0)
