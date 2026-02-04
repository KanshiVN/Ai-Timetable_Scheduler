import random
from generator import generate_timetable
from fitness import fitness
from fetch_data import fetch_slot_maps, fetch_subject_type_map

POPULATION_SIZE = 30
GENERATIONS = 50
MUTATION_RATE = 0.2


def optimize():
    # ✅ FETCH REQUIRED MAPS
    slot_day_map, slot_type_map, slot_order_map = fetch_slot_maps()
    subject_type_map = fetch_subject_type_map()

    # ✅ INITIAL POPULATION
    population = [
        generate_timetable()
        for _ in range(POPULATION_SIZE)
    ]

    for generation in range(GENERATIONS):
        scored_population = []

        for timetable in population:
            score = fitness(
                timetable,
                slot_day_map,
                slot_type_map,
                subject_type_map
            )
            scored_population.append((score, timetable))

        # Sort by fitness (descending)
        scored_population.sort(reverse=True, key=lambda x: x[0])

        print(f"Generation {generation} | Best fitness: {scored_population[0][0]}")

        # Selection (top 30%)
        survivors = [
            tt for _, tt in scored_population[:POPULATION_SIZE // 3]
        ]

        # Reproduction
        new_population = survivors.copy()

        while len(new_population) < POPULATION_SIZE:
            parent = random.choice(survivors)
            child = mutate(parent, slot_type_map)
            new_population.append(child)

        population = new_population

    # Return best timetable
    return scored_population[0][1]


def mutate(timetable, slot_type_map):
    new_tt = timetable.copy()

    if random.random() > MUTATION_RATE:
        return new_tt

    i, j = random.sample(range(len(new_tt)), 2)

    # ❗ DO NOT MIX LAB & LECTURE SLOTS
    if slot_type_map[new_tt[i]["slot_id"]] != slot_type_map[new_tt[j]["slot_id"]]:
        return new_tt

    new_tt[i]["slot_id"], new_tt[j]["slot_id"] = (
        new_tt[j]["slot_id"],
        new_tt[i]["slot_id"],
    )

    return new_tt
