import Foundation

enum WearableProvider: String, Codable {
    case whoop, garmin, oura
    case appleHealth = "apple_health"
}

enum RecoveryTrend: String, Codable {
    case rising, stable, falling
}

struct RecoveryReadingCreate: Codable {
    let readingDate: Date
    var source: WearableProvider = .appleHealth
    var hrvMs: Double?
    var restingHrBpm: Double?
    var sleepScore: Double?
    var vo2Max: Double?

    enum CodingKeys: String, CodingKey {
        case readingDate = "reading_date"
        case source
        case hrvMs = "hrv_ms"
        case restingHrBpm = "resting_hr_bpm"
        case sleepScore = "sleep_score"
        case vo2Max = "vo2_max"
    }
}

struct RecoveryScoreRead: Codable {
    let scoreDate: Date
    let compositeScore: Double
    let trend: RecoveryTrend
    let hrvZ: Double?
    let restingHrZ: Double?
    let sleepZ: Double?

    enum CodingKeys: String, CodingKey {
        case scoreDate = "score_date"
        case compositeScore = "composite_score"
        case trend
        case hrvZ = "hrv_z"
        case restingHrZ = "resting_hr_z"
        case sleepZ = "sleep_z"
    }
}

struct RecoveryUpdateResponse: Codable {
    let score: RecoveryScoreRead
    let adjustedWeek: TrainingWeek?

    enum CodingKeys: String, CodingKey {
        case score
        case adjustedWeek = "adjusted_week"
    }
}
