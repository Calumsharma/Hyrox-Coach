import Foundation

struct Workout: Codable, Identifiable, Hashable {
    let id: String
    let dayOfWeek: Int
    let workoutType: WorkoutType
    let title: String
    let prescription: [String: JSONValue]
    let loggedResult: [String: JSONValue]?
    let completedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case dayOfWeek = "day_of_week"
        case workoutType = "workout_type"
        case title, prescription
        case loggedResult = "logged_result"
        case completedAt = "completed_at"
    }

    static let dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    var dayName: String { Workout.dayNames[dayOfWeek] }
}

struct TrainingWeek: Codable, Identifiable, Hashable {
    let id: String
    let weekNumber: Int
    let phase: String
    let plannedIntensity: Double
    let actualIntensity: Double
    var workouts: [Workout]

    enum CodingKeys: String, CodingKey {
        case id
        case weekNumber = "week_number"
        case phase
        case plannedIntensity = "planned_intensity"
        case actualIntensity = "actual_intensity"
        case workouts
    }
}

struct TrainingBlock: Codable, Identifiable {
    let id: String
    let discipline: Discipline
    let startDate: Date
    let lengthWeeks: Int
    let goalEventDate: Date?
    let goalTimeSeconds: Int?
    let targetWeaknesses: [String]
    let deloadWeekNumbers: [Int]
    let taperWeekNumbers: [Int]
    var weeks: [TrainingWeek]

    enum CodingKeys: String, CodingKey {
        case id, discipline
        case startDate = "start_date"
        case lengthWeeks = "length_weeks"
        case goalEventDate = "goal_event_date"
        case goalTimeSeconds = "goal_time_seconds"
        case targetWeaknesses = "target_weaknesses"
        case deloadWeekNumbers = "deload_week_numbers"
        case taperWeekNumbers = "taper_week_numbers"
        case weeks
    }
}

// MARK: - Structured logging

struct SetLog: Codable {
    var reps: Int?
    var weightKg: Double?
    enum CodingKeys: String, CodingKey { case reps; case weightKg = "weight_kg" }
}

struct BlockLog: Codable {
    let index: Int
    var sets: [SetLog] = []
    var actualTimeSec: Int?
    var actualDistanceM: Double?
    var rpe: Double?
    enum CodingKeys: String, CodingKey {
        case index, sets, rpe
        case actualTimeSec = "actual_time_sec"
        case actualDistanceM = "actual_distance_m"
    }
}

struct ConditioningLog: Codable {
    var roundsCompleted: Int?
    var extraReps: Int?
    var durationSec: Int?
    var rpe: Double?
    enum CodingKeys: String, CodingKey {
        case roundsCompleted = "rounds_completed"
        case extraReps = "extra_reps"
        case durationSec = "duration_sec"
        case rpe
    }
}

struct WorkoutLogUpdate: Codable {
    var notes: String?
    var blocks: [BlockLog] = []
    var conditioning: ConditioningLog?
}

struct TrainingBlockCreate: Codable {
    let lengthWeeks: Int
    let startDate: Date
    let goalEventDate: Date
    let goalTimeSeconds: Int
    var discipline: Discipline = .hyrox

    enum CodingKeys: String, CodingKey {
        case lengthWeeks = "length_weeks"
        case startDate = "start_date"
        case goalEventDate = "goal_event_date"
        case goalTimeSeconds = "goal_time_seconds"
        case discipline
    }
}
