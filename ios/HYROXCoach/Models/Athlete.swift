import Foundation

struct PastHyroxResult: Codable, Identifiable {
    let id: String
    let eventDate: Date
    let division: Division
    let totalTimeSeconds: Int
    let stationSplitsSeconds: [String: Int]

    enum CodingKeys: String, CodingKey {
        case id
        case eventDate = "event_date"
        case division
        case totalTimeSeconds = "total_time_seconds"
        case stationSplitsSeconds = "station_splits_seconds"
    }
}

struct PastResultCreate: Codable {
    let eventDate: Date
    let division: Division
    let totalTimeSeconds: Int
    let stationSplitsSeconds: [String: Int]

    enum CodingKeys: String, CodingKey {
        case eventDate = "event_date"
        case division
        case totalTimeSeconds = "total_time_seconds"
        case stationSplitsSeconds = "station_splits_seconds"
    }
}

struct Athlete: Codable, Identifiable {
    let id: String
    let email: String
    let name: String?
    let age: Int?
    let weightKg: Double?
    let heightCm: Double?
    let division: Division?
    let experienceTier: ExperienceTier?
    let testedMaxHR: Int?
    let onboardingCompleted: Bool
    let predicted5kSeconds: Int?
    let current10kSeconds: Int?
    let selfReportedWeakStations: [StationSlug]
    let goalTimeSeconds: Int?
    let goalEventDate: Date?
    let pastResults: [PastHyroxResult]

    enum CodingKeys: String, CodingKey {
        case id, email, name, age, division
        case weightKg = "weight_kg"
        case heightCm = "height_cm"
        case experienceTier = "experience_tier"
        case testedMaxHR = "tested_max_hr"
        case onboardingCompleted = "onboarding_completed"
        case predicted5kSeconds = "predicted_5k_seconds"
        case current10kSeconds = "current_10k_seconds"
        case selfReportedWeakStations = "self_reported_weak_stations"
        case goalTimeSeconds = "goal_time_seconds"
        case goalEventDate = "goal_event_date"
        case pastResults = "past_results"
    }
}

struct AthleteOnboarding: Codable {
    let name: String
    let age: Int
    let weightKg: Double
    let heightCm: Double
    let division: Division
    let experienceTier: ExperienceTier
    let testedMaxHR: Int?
    let predicted5kSeconds: Int?
    let current10kSeconds: Int?
    let selfReportedWeakStations: [StationSlug]
    let goalTimeSeconds: Int?
    let goalEventDate: Date?

    enum CodingKeys: String, CodingKey {
        case name, age, division
        case weightKg = "weight_kg"
        case heightCm = "height_cm"
        case experienceTier = "experience_tier"
        case testedMaxHR = "tested_max_hr"
        case predicted5kSeconds = "predicted_5k_seconds"
        case current10kSeconds = "current_10k_seconds"
        case selfReportedWeakStations = "self_reported_weak_stations"
        case goalTimeSeconds = "goal_time_seconds"
        case goalEventDate = "goal_event_date"
    }
}
