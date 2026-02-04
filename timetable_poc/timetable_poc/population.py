import random
from generator import generate_timetable

def generate_population(size=20):
    population = []
    for _ in range(size):
        timetable = generate_timetable(randomize=True)
        population.append(timetable)
    return population
