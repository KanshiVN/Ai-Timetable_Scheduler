# slot_maps.py
# =====================================================
# DAILY SLOT STRUCTURE WITH FULL LAB FALLBACK SUPPORT
# =====================================================

# -------------------------------
# GLOBAL SLOT DEFINITIONS
# -------------------------------

SLOTS = {
    1: "08:30-09:30",
    2: "09:30-10:30",
    3: "10:45-11:45",
    4: "11:45-12:45",
    5: "13:30-14:30",
    6: "14:30-15:30"
}

# -------------------------------
# LAB SLOT GROUPS (2-hour windows)
# -------------------------------

LAB_SLOT_GROUPS = {
    "MORNING": (1, 2),
    "MIDDAY": (3, 4),
    "AFTERNOON": (5, 6)
}

ALL_LAB_WINDOWS = [
    LAB_SLOT_GROUPS["MORNING"],
    LAB_SLOT_GROUPS["MIDDAY"],
    LAB_SLOT_GROUPS["AFTERNOON"]
]

# -------------------------------
# CLASS-WISE SLOT RULES
# Preferred window comes first, others act as fallback
# -------------------------------

CLASS_SLOT_RULES = {
    # -------- SE --------
    "SE-A": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["MORNING"],
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["AFTERNOON"]
        ],
        "LECTURE": [3, 4, 5, 6]
    },
    "SE-B": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["MORNING"],
            LAB_SLOT_GROUPS["AFTERNOON"]
        ],
        "LECTURE": [1, 2, 5, 6]
    },
    "SE-C": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["AFTERNOON"],
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["MORNING"]
        ],
        "LECTURE": [1, 2, 3, 4]
    },

    # -------- TE --------
    "TE-A": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["MORNING"],
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["AFTERNOON"]
        ],
        "LECTURE": [3, 4, 5, 6]
    },
    "TE-B": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["AFTERNOON"],
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["MORNING"]
        ],
        "LECTURE": [1, 2, 3, 4]
    },

    # -------- BE --------
    "BE-A": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["MORNING"],
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["AFTERNOON"]
        ],
        "LECTURE": [3, 4, 5, 6]
    },
    "BE-B": {
        "LAB_PRIORITY": [
            LAB_SLOT_GROUPS["AFTERNOON"],
            LAB_SLOT_GROUPS["MIDDAY"],
            LAB_SLOT_GROUPS["MORNING"]
        ],
        "LECTURE": [1, 2, 3, 4]
    }
}


# -------------------------------
# HELPER FUNCTIONS
# -------------------------------

def get_lab_slot_groups(class_name):
    """
    Returns ordered list of lab windows: preferred → fallback
    This allows the generator to try preferred slots first
    """
    return CLASS_SLOT_RULES[class_name]["LAB_PRIORITY"]


def get_lab_slots(class_name):
    """
    Returns primary lab window (used for validation)
    """
    return CLASS_SLOT_RULES[class_name]["LAB_PRIORITY"][0]


def get_lecture_slots(class_name):
    """
    Returns list of valid lecture slots for a class
    """
    return CLASS_SLOT_RULES[class_name]["LECTURE"]


def get_slot_time(slot_id):
    """
    Returns time string for a slot ID
    """
    return SLOTS.get(slot_id, "Unknown")


def get_all_slots():
    """
    Returns all slot IDs
    """
    return list(SLOTS.keys())