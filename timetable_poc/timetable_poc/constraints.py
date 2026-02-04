# constraints.py
# =====================================================
# HARD CONSTRAINTS – FINAL, CONSISTENT VERSION
# =====================================================

from collections import defaultdict
from slot_maps import get_lecture_slots


# -----------------------------------------------------
# Helper: infer actual lab window from slot number
# -----------------------------------------------------
def infer_lab_window(slot):
    """Returns the 2-slot window tuple for a given slot"""
    if slot in (1, 2):
        return (1, 2)
    if slot in (3, 4):
        return (3, 4)
    if slot in (5, 6):
        return (5, 6)
    return None


# -----------------------------------------------------
# Helper: get slot from entry (handles both slot/slot_id)
# -----------------------------------------------------
def get_slot(entry):
    """Get slot number from entry (handles both 'slot' and 'slot_id' keys)"""
    return entry.get("slot_id") or entry.get("slot")


# -----------------------------------------------------
# HC1: Teacher clash (GLOBAL)
# -----------------------------------------------------
def check_teacher_clash(timetable):
    """
    Prevents same teacher from teaching different classes at overlapping times.
    Parallel batches of SAME class are allowed.
    """
    events = []
    
    for e in timetable:
        if e["teacher_id"] is None:
            continue

        day = e["day"]
        teacher = e["teacher_id"]
        class_id = e["class_id"]
        slot = get_slot(e)

        if e["is_lab"]:
            window = infer_lab_window(slot)
            time_set = set(window)
        else:
            time_set = {slot}

        events.append((day, teacher, class_id, time_set))

    # Check all pairs
    for i in range(len(events)):
        d1, t1, c1, ts1 = events[i]
        for j in range(i + 1, len(events)):
            d2, t2, c2, ts2 = events[j]
            
            # Different day or different teacher - no clash
            if d1 != d2 or t1 != t2:
                continue
            
            # Same class (parallel batches) - allowed
            if c1 == c2:
                continue
            
            # Different classes, same teacher, overlapping time - CLASH
            if ts1 & ts2:
                print(f"❌ Teacher clash: Teacher {t1} on {d1} at slots {ts1 & ts2}")
                return False

    return True


# -----------------------------------------------------
# HC2: Slot validity
# -----------------------------------------------------
def check_slot_validity(entry):
    """Validates that the slot is appropriate for the class"""
    slot = get_slot(entry)
    
    if entry["is_lab"]:
        return infer_lab_window(slot) is not None
    else:
        return slot in get_lecture_slots(entry["class_name"])


# -----------------------------------------------------
# HC3: Weekly load (HOURS BASED)
# -----------------------------------------------------
def check_weekly_load(timetable, weekly_load_map):
    """
    Validates weekly teaching load against defined limits.
    - Lectures: Each slot = 1 hour
    - Labs: Each window (2 slots) = 1 session unit
    """
    used = defaultdict(lambda: {"theory": 0, "practical": 0})
    seen_lab_events = set()

    for e in timetable:
        if e["teacher_id"] is None:
            continue

        key = (e["teacher_id"], e["subject_id"], e["class_id"])
        slot = get_slot(e)

        if e["is_lab"]:
            lab_window = infer_lab_window(slot)
            # Count each unique lab session once
            event = (
                e["day"],
                lab_window,
                e["teacher_id"],
                e["subject_id"],
                e["class_id"]
            )

            if event not in seen_lab_events:
                used[key]["practical"] += 1
                seen_lab_events.add(event)
        else:
            # Each lecture slot = 1 hour
            used[key]["theory"] += 1

    # Validate against limits
    for key, u in used.items():
        if key not in weekly_load_map:
            print(f"❌ Missing weekly load for: Teacher={key[0]}, Subject={key[1]}, Class={key[2]}")
            return False

        allowed = weekly_load_map[key]

        if u["practical"] > allowed["weekly_practical_load"]:
            print(f"❌ Practical overload: Teacher={key[0]}, Subject={key[1]}, Class={key[2]}")
            print(f"   Used: {u['practical']}, Allowed: {allowed['weekly_practical_load']}")
            return False

        if u["theory"] > allowed["weekly_theory_load"]:
            print(f"❌ Theory overload: Teacher={key[0]}, Subject={key[1]}, Class={key[2]}")
            print(f"   Used: {u['theory']}, Allowed: {allowed['weekly_theory_load']}")
            return False

    return True


# -----------------------------------------------------
# HC4: Daily teacher limits
# -----------------------------------------------------
def check_daily_limits(timetable, teacher_limits):
    """Validates daily lecture limits for each teacher"""
    daily = defaultdict(lambda: {"lecture": 0, "lab": 0})

    for e in timetable:
        if e["teacher_id"] is None:
            continue

        key = (e["teacher_id"], e["day"])

        if e["is_lab"]:
            daily[key]["lab"] += 1
        else:
            daily[key]["lecture"] += 1

    for (t, _), cnt in daily.items():
        limits = teacher_limits.get(t)
        if limits is None:
            continue

        # Check lecture limit
        if isinstance(limits, dict):
            max_lec = limits.get("max_lectures_per_day")
        else:
            max_lec = limits

        if max_lec and cnt["lecture"] > max_lec:
            print(f"❌ Daily lecture limit exceeded for teacher {t}")
            return False

    return True


# -----------------------------------------------------
# HC5: Allocation validity
# -----------------------------------------------------
def check_allocation_validity(entry, allocation_set, batch_allocation_set):
    """Validates that the assignment matches allocations in DB"""
    if entry["is_lab"]:
        key = (
            entry["teacher_id"],
            entry["subject_id"],
            entry["class_id"],
            entry["batch_id"]
        )
        return key in batch_allocation_set
    else:
        key = (
            entry["teacher_id"],
            entry["subject_id"],
            entry["class_id"]
        )
        return key in allocation_set


# -----------------------------------------------------
# HC6: Lab continuity (2 consecutive slots)
# -----------------------------------------------------
def check_lab_continuity(timetable):
    """
    Validates that all lab sessions use 2 consecutive slots
    in valid windows (1-2, 3-4, or 5-6)
    """
    labs = defaultdict(list)

    for e in timetable:
        if not e["is_lab"]:
            continue

        key = (
            e["day"],
            e["class_id"],
            e["batch_id"],
            e["subject_id"]
        )
        labs[key].append(get_slot(e))

    for key, slots in labs.items():
        slots = sorted(list(set(slots)))
        
        # Must be even number of slots
        if len(slots) % 2 != 0:
            print(f"❌ Lab continuity failed: Odd number of slots for {key}")
            return False
        
        # Check each pair is consecutive and in valid window
        for i in range(0, len(slots), 2):
            if slots[i+1] != slots[i] + 1:
                print(f"❌ Lab continuity failed: Non-consecutive slots {slots[i]}, {slots[i+1]}")
                return False
            
            expected_window = infer_lab_window(slots[i])
            if expected_window != (slots[i], slots[i+1]):
                print(f"❌ Lab continuity failed: Invalid window for slots {slots[i]}, {slots[i+1]}")
                return False

    return True


# -----------------------------------------------------
# HC7: Parallel batch subject-teacher uniqueness
# -----------------------------------------------------
def check_batch_subject_uniqueness(timetable):
    """
    SAME day + SAME class + SAME lab window:
    SAME subject + SAME teacher is NOT allowed ACROSS DIFFERENT BATCHES
    """
    lab_sessions = defaultdict(set)
    # key = (day, class_id, lab_window)
    # value = set of (batch_id, subject_id, teacher_id)

    for e in timetable:
        if not e["is_lab"]:
            continue

        slot = get_slot(e)
        lab_window = infer_lab_window(slot)
        key = (e["day"], e["class_id"], lab_window)

        lab_sessions[key].add(
            (e["batch_id"], e["subject_id"], e["teacher_id"])
        )

    for key, entries in lab_sessions.items():
        seen = {}
        for batch, subject, teacher in entries:
            pair = (subject, teacher)

            if pair in seen and seen[pair] != batch:
                print(f"❌ Parallel batch subject-teacher clash at {key}: {pair}")
                return False

            seen[pair] = batch

    return True


# -----------------------------------------------------
# MASTER VALIDATOR
# -----------------------------------------------------
def validate_timetable(
    timetable,
    weekly_load_map,
    teacher_limits,
    allocation_set,
    batch_allocation_set
):
    """
    Main validation function - checks all constraints.
    Returns True if all constraints pass, False otherwise.
    """
    print("\n🔍 Validating timetable...")
    
    if not check_teacher_clash(timetable):
        return False
    print("✅ No teacher clashes")
    
    if not check_lab_continuity(timetable):
        return False
    print("✅ Lab continuity valid")
    
    if not check_batch_subject_uniqueness(timetable):
        return False
    print("✅ No parallel batch conflicts")
    
    for e in timetable:
        if not check_slot_validity(e):
            print(f"❌ Invalid slot for {e}")
            return False
    print("✅ All slots valid")
    
    for e in timetable:
        if not check_allocation_validity(e, allocation_set, batch_allocation_set):
            print(f"❌ Invalid allocation for {e}")
            return False
    print("✅ All allocations valid")
    
    if not check_weekly_load(timetable, weekly_load_map):
        return False
    print("✅ Weekly loads within limits")
    
    if not check_daily_limits(timetable, teacher_limits):
        return False
    print("✅ Daily limits satisfied")

    print("✅ ALL CONSTRAINTS PASSED")
    return True