"""Fixed HYROX race skeleton: 8x(1km run + station), always in this order.

Loads are the official 2025/26 season standards. Source: HYROX rulebook + division
weight charts (checked against multiple independent sources during planning).
Women's Pro loads equal Men's Open loads on every weighted station.
"""

from app.models.enums import StationSlug

STATIONS = [
    {
        "slug": StationSlug.SKIERG,
        "order": 1,
        "name": "SkiErg",
        "distance_or_reps": "1000 m",
        "primary_demand": "upper body / aerobic power",
        "division_loads": {},  # no load variation, distance is fixed for all
    },
    {
        "slug": StationSlug.SLED_PUSH,
        "order": 2,
        "name": "Sled Push",
        "distance_or_reps": "50 m",
        "primary_demand": "leg strength / posterior chain",
        "division_loads": {
            "open_men": {"load_kg": 152},
            "pro_men": {"load_kg": 202},
            "open_women": {"load_kg": 102},
            "pro_women": {"load_kg": 152},
        },
    },
    {
        "slug": StationSlug.SLED_PULL,
        "order": 3,
        "name": "Sled Pull",
        "distance_or_reps": "50 m",
        "primary_demand": "posterior chain / grip",
        "division_loads": {
            "open_men": {"load_kg": 103},
            "pro_men": {"load_kg": 153},
            "open_women": {"load_kg": 78},
            "pro_women": {"load_kg": 103},
        },
    },
    {
        "slug": StationSlug.BURPEE_BROAD_JUMP,
        "order": 4,
        "name": "Burpee Broad Jump",
        "distance_or_reps": "80 m",
        "primary_demand": "full body / anaerobic capacity",
        "division_loads": {},
    },
    {
        "slug": StationSlug.ROW,
        "order": 5,
        "name": "Rowing",
        "distance_or_reps": "1000 m",
        "primary_demand": "posterior chain / aerobic power",
        "division_loads": {},
    },
    {
        "slug": StationSlug.FARMERS_CARRY,
        "order": 6,
        "name": "Farmers Carry",
        "distance_or_reps": "200 m",
        "primary_demand": "grip / carry endurance",
        "division_loads": {
            "open_men": {"load_kg_per_hand": 24},
            "pro_men": {"load_kg_per_hand": 32},
            "open_women": {"load_kg_per_hand": 16},
            "pro_women": {"load_kg_per_hand": 24},
        },
    },
    {
        "slug": StationSlug.SANDBAG_LUNGES,
        "order": 7,
        "name": "Sandbag Lunges",
        "distance_or_reps": "100 m",
        "primary_demand": "leg strength / stability under load",
        "division_loads": {
            "open_men": {"load_kg": 20},
            "pro_men": {"load_kg": 30},
            "open_women": {"load_kg": 10},
            "pro_women": {"load_kg": 20},
        },
    },
    {
        "slug": StationSlug.WALL_BALLS,
        "order": 8,
        "name": "Wall Balls",
        "distance_or_reps": "100 reps",
        "primary_demand": "muscular endurance / compromised shoulders-legs",
        "division_loads": {
            "open_men": {"load_kg": 6, "target_height_m": 3.00},
            "pro_men": {"load_kg": 9, "target_height_m": 3.00},
            "open_women": {"load_kg": 4, "target_height_m": 2.70},
            "pro_women": {"load_kg": 6, "target_height_m": 2.70},
        },
    },
]
