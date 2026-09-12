import SwiftUI

/// "Ops Board" — the visual direction picked after Concrete & Chalk still read as too close
/// to stock iOS chrome (see /design/visual_direction_options.html for the three directions
/// compared). Same underlying palette, inverted: `ink` is now the primary app background
/// (not just an accent), `concrete` is now primary text, and data reads in a monospaced
/// face like a real console/ops-board readout — hairline rules instead of card shadows, a
/// horizontal week "tape" instead of a circular ring.
enum Theme {
    // Raw palette
    static let ink = Color(red: 0.110, green: 0.106, blue: 0.090)          // #1c1b17
    static let inkElevated = Color(red: 0.153, green: 0.145, blue: 0.122)  // #27251f — one step up from ink, for rows/cards
    static let concrete = Color(red: 0.847, green: 0.827, blue: 0.780)     // #d8d3c7
    static let stone = Color(red: 0.643, green: 0.616, blue: 0.573)        // #a49d8b
    static let mutedInk = Color(red: 0.396, green: 0.373, blue: 0.322)     // #655f52 — legacy light-on-light token, rarely used now
    static let safetyOrange = Color(red: 0.910, green: 0.341, blue: 0.059) // #e8570f

    // Semantic roles — reach for these in views; the raw palette above backs them.
    static let background = ink
    static let surface = inkElevated
    static let textPrimary = concrete
    static let textSecondary = stone
    static let hairline = stone.opacity(0.18)
    static let accent = safetyOrange

    /// Big display headlines ("WEEK 03/08", "S9"). Stands in for a bundled stencil display
    /// face until one's worth the extra build weight — heavy weight + tight tracking
    /// approximates the same industrial-signage feel with a system font.
    static func stencilTitle(_ size: CGFloat) -> Font {
        .system(size: size, weight: .black, design: .default)
    }

    /// Numeric/data readouts — intensity %, days-to-race, logged weights — set in the
    /// system monospaced face (SF Mono) for the console/ops-board feel.
    static func dataMono(_ size: CGFloat, weight: Font.Weight = .semibold) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }

    /// Small tracked-out all-caps labels ("TARGET WEAKNESS", "WEEKS").
    static func labelMono(_ size: CGFloat = 10, weight: Font.Weight = .semibold) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}
