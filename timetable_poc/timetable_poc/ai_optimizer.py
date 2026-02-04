from population import generate_population
from fitness import fitness
from slot_maps import get_slot_maps

def get_best_timetable():
    slot_day_map, slot_order_map, lecture_slots_by_day = get_slot_maps()
    population = generate_population(size=40)

    scored = []
    for timetable in population:
        score = fitness(
            timetable,
            slot_day_map,
            slot_order_map,
            lecture_slots_by_day
        )
        scored.append((score, timetable))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_timetable = scored[0]

    print("Best fitness score:", best_score)
    return best_timetable
