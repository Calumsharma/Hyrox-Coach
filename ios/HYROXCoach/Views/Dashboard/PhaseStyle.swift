import SwiftUI

enum PhaseStyle {
    static func color(for phase: String) -> Color {
        switch phase {
        case "base": return .blue
        case "build": return .orange
        case "peak": return .red
        case "deload": return .yellow
        case "taper": return .green
        default: return .gray
        }
    }

    static func icon(for phase: String) -> String {
        switch phase {
        case "base": return "leaf.fill"
        case "build": return "flame.fill"
        case "peak": return "bolt.fill"
        case "deload": return "arrow.down.circle.fill"
        case "taper": return "wind"
        default: return "circle.fill"
        }
    }
}

extension WorkoutType {
    var icon: String {
        switch self {
        case .run: return "figure.run"
        case .stationSkill: return "bolt.fill"
        case .strength: return "dumbbell.fill"
        case .aerobic: return "heart.fill"
        case .mobility: return "figure.cooldown"
        case .rest: return "moon.zzz.fill"
        case .raceDay: return "flag.checkered"
        }
    }

    var tint: Color {
        switch self {
        case .run: return .cyan
        case .stationSkill: return .purple
        case .strength: return .indigo
        case .aerobic: return .pink
        case .mobility: return .mint
        case .rest: return .gray
        case .raceDay: return .orange
        }
    }
}
