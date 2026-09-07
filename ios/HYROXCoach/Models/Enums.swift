import Foundation

enum Division: String, Codable, CaseIterable, Identifiable {
    case openMen = "open_men"
    case openWomen = "open_women"
    case proMen = "pro_men"
    case proWomen = "pro_women"
    case doublesMen = "doubles_men"
    case doublesWomen = "doubles_women"
    case doublesMixed = "doubles_mixed"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .openMen: return "Open — Men"
        case .openWomen: return "Open — Women"
        case .proMen: return "Pro — Men"
        case .proWomen: return "Pro — Women"
        case .doublesMen: return "Doubles — Men"
        case .doublesWomen: return "Doubles — Women"
        case .doublesMixed: return "Doubles — Mixed"
        }
    }

    var isSolo: Bool {
        switch self {
        case .openMen, .openWomen, .proMen, .proWomen: return true
        case .doublesMen, .doublesWomen, .doublesMixed: return false
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

enum Discipline: String, Codable, CaseIterable, Identifiable, Hashable {
    case hyrox
    case fiveK = "5k"
    case tenK = "10k"
    case halfMarathon = "half_marathon"
    case marathon
    case halfIronman = "half_ironman"
    case crossfitCompetition = "crossfit_competition"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .hyrox: return "HYROX"
        case .fiveK: return "5K"
        case .tenK: return "10K"
        case .halfMarathon: return "Half Marathon"
        case .marathon: return "Marathon"
        case .halfIronman: return "Half Ironman"
        case .crossfitCompetition: return "CrossFit Competition"
        }
    }

    /// Only HYROX has a real program builder on the backend right now — see
    /// UnsupportedDisciplineError in app/services/program_engine.py. Others are shown in
    /// the picker as a stated roadmap, not working features.
    var isSupported: Bool { self == .hyrox }
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
