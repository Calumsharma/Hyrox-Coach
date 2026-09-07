"""Exercise library seed data — written technique descriptions only.

No video links yet: we haven't filmed our own demos or licensed/white-labeled a video
library, and we don't fabricate links to content that doesn't exist. `video_source` stays
"none" until a real pipeline (self-filmed or licensed) is wired up.
"""

EXERCISES = [
    {
        "slug": "barbell_front_squat",
        "name": "Barbell Front Squat",
        "category": "strength",
        "description": "A squat with the bar racked across the front of the shoulders on the fingertips, elbows high. Builds the quad-dominant leg strength that underpins sled work and running.",
        "cues": ["Elbows up throughout", "Brace before descending", "Drive knees out over toes"],
    },
    {
        "slug": "hex_bar_deadlift",
        "name": "Hex Bar Deadlift",
        "category": "strength",
        "description": "A deadlift performed inside a hexagonal bar so the load sits at your sides rather than in front — more upright torso than a barbell deadlift, easier to load heavy safely.",
        "cues": ["Push the floor away", "Keep the bar path vertical", "Stand tall at lockout, don't hyperextend"],
    },
    {
        "slug": "incline_db_bench_press",
        "name": "Incline Dumbbell Bench Press",
        "category": "strength",
        "description": "Bench press on an incline bench using dumbbells, targeting the upper chest and shoulders.",
        "cues": ["30-45 degree incline", "Control the eccentric", "Don't flare elbows past 45 degrees"],
    },
    {
        "slug": "db_thruster",
        "name": "Dumbbell Thruster",
        "category": "strength",
        "description": "A front squat that flows directly into an overhead press, using dumbbells at the shoulders. A full-body, metabolically demanding movement.",
        "cues": ["Use leg drive to start the press", "Full lockout overhead", "Keep core braced throughout"],
    },
    {
        "slug": "goblet_squat",
        "name": "Goblet Squat",
        "category": "strength",
        "description": "A squat holding a single dumbbell or kettlebell at chest height. Used here as movement prep before loaded station work.",
        "cues": ["Elbows inside the knees at the bottom", "Keep the weight close to the chest", "Full depth, controlled tempo"],
    },
    {
        "slug": "bulgarian_split_squat",
        "name": "Bulgarian Split Squat",
        "category": "strength",
        "description": "A single-leg squat with the rear foot elevated behind you on a bench. Builds unilateral leg strength without the axial load of a bilateral barbell lift.",
        "cues": ["Most of the weight through the front foot", "Torso stays fairly upright", "Control the descent"],
    },
    {
        "slug": "sissy_squat",
        "name": "Sissy Squat",
        "category": "strength",
        "description": "A knee-dominant bodyweight squat variation where you lean back from the knees while staying upright through the hips — isolates the quads under a slow tempo.",
        "cues": ["Hips stay extended, only the knees bend", "Move slowly on the tempo prescribed", "Hold something light for balance if needed"],
    },
    {
        "slug": "db_or_barbell_rdl",
        "name": "Romanian Deadlift (DB or Barbell)",
        "category": "strength",
        "description": "A hip-hinge movement that loads the hamstrings and glutes through a stretch, performed with a dumbbell or barbell.",
        "cues": ["Soft knees, hinge at the hips", "Keep the weight close to your legs", "Feel the stretch in the hamstrings, don't round the back"],
    },
    {
        "slug": "bent_over_barbell_row",
        "name": "Bent-Over Barbell Row",
        "category": "strength",
        "description": "A hinged-over row pulling a barbell to the torso — builds the upper-back pulling strength used in farmer's carries and sled pulls.",
        "cues": ["Hinge to roughly 45 degrees", "Pull to the lower ribs, not the neck", "Avoid using momentum from the legs"],
    },
    {
        "slug": "kettlebell_swings",
        "name": "Kettlebell Swings",
        "category": "strength",
        "description": "A ballistic hip-hinge movement swinging a kettlebell to chest height using hip drive, not the arms.",
        "cues": ["Power comes from the hips, not the shoulders", "Arms stay relatively relaxed", "Brace hard at the top of the swing"],
    },
    {
        "slug": "db_bench_lat_pullover",
        "name": "DB Bench Lat Pullover",
        "category": "strength",
        "description": "Lying on a bench, a single or double dumbbell is lowered behind the head and pulled back over the chest — targets the lats and improves shoulder overhead range.",
        "cues": ["Keep a slight bend in the elbows throughout", "Lower only as far as shoulder mobility allows", "Brace the core to avoid arching the lower back"],
    },
    {
        "slug": "pull_ups",
        "name": "Pull-Ups",
        "category": "strength",
        "description": "A vertical pulling movement from a dead hang to chin over the bar. Band-assisted if needed to hit the prescribed reps.",
        "cues": ["Full hang at the bottom", "Chin clears the bar", "Control the descent rather than dropping"],
    },
    {
        "slug": "sled_push",
        "name": "Sled Push",
        "category": "station",
        "description": "Driving a weighted sled forward by pushing on an upright handle. One of the 8 official HYROX stations.",
        "cues": ["Low shin angle, drive through the legs", "Short, powerful steps", "Keep arms locked and braced, not pushing with the arms"],
    },
    {
        "slug": "sled_pull",
        "name": "Sled Pull",
        "category": "station",
        "description": "Pulling a weighted sled toward you hand-over-hand on a rope, or walking it backward. One of the 8 official HYROX stations.",
        "cues": ["Lean back and use bodyweight, not just arms", "Keep a consistent rhythm", "Short, controlled pulls rather than lunging for rope"],
    },
    {
        "slug": "farmers_carry",
        "name": "Farmer's Carry",
        "category": "station",
        "description": "Walking a set distance while carrying a heavy load in each hand. One of the 8 official HYROX stations.",
        "cues": ["Shoulders back, don't let the load pull you forward", "Grip hard, quick reset if you have to put it down", "Take quick, controlled steps"],
    },
    {
        "slug": "sandbag_walking_lunges",
        "name": "Sandbag Walking Lunges",
        "category": "station",
        "description": "Walking lunges performed carrying a sandbag (front rack, shoulder, or bear hug). One of the 8 official HYROX stations.",
        "cues": ["Full depth, back knee toward the floor", "Keep the torso tall", "Drive through the front heel to stand"],
    },
    {
        "slug": "wall_ball_touches",
        "name": "Wall Balls",
        "category": "station",
        "description": "A squat that flows into a throw of a weighted medicine ball at a target on the wall, catching it on the way down. One of the 8 official HYROX stations.",
        "cues": ["Full squat depth before the throw", "Use leg drive, not just arms, to throw", "Hit the target height every rep"],
    },
]
