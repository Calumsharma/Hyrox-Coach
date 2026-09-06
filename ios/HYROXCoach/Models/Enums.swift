import Foundation

enum Division: String, Codable, CaseIterable, Identifiable {
    case openMen = "open_men"
    case openWomen = "open_women"
    case proMen = "pro_men"
    case proWomen = "pro_women"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .openMen: return "Open — Men"
        case .openWomen: return "Open — Women"
        case .proMen: return "Pro — Men"
        case .proWomen: return "Pro — Women"
        }
    }
}

enum StationSlug: String, Codable, CaseIterable, Identifiable {
    case skierg
    case sledPush = "sled_push"
    case sledPull = "sled_pull"
    case burpeeBroadJump = "burpee_broad_jump"
    case row
    case farmersCarry = "farmers_carry"
    case sandbagLunges = "sandbag_lunges"
    case wallBalls = "wall_balls"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .skierg: return "SkiErg"
        case .sledPush: return "Sled Push"
        case .sledPull: return "Sled Pull"
        case .burpeeBroadJump: return "Burpee Broad Jump"
        case .row: return "Rowing"
        case .farmersCarry: return "Farmers Carry"
        case .sandbagLunges: return "Sandbag Lunges"
        case .wallBalls: return "Wall Balls"
        }
    }
}

enum WorkoutType: String, Codable, Hashable {
    case run
    case stationSkill = "station_skill"
    case strength
    case aerobic
    case mobility
    case rest
    case raceDay = "race_day"

    var displayName: String {
        switch self {
        case .run: return "Run"
        case .stationSkill: return "Station Skill"
        case .strength: return "Strength"
        case .aerobic: return "Aerobic"
        case .mobility: return "Mobility"
        case .rest: return "Rest"
        case .raceDay: return "Race Day"
        }
    }
}

enum ExperienceTier: String, Codable, CaseIterable, Identifiable, Hashable {
    case beginner
    case intermediate
    case advanced

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .beginner: return "Beginner"
        case .intermediate: return "Intermediate"
        case .advanced: return "Advanced"
        }
    }
}
