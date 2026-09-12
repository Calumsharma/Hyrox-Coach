import SwiftUI

/// "Concrete & Chalk" — the visual identity picked from the comparison gallery: chalky
/// warehouse-gym grey, stamped safety-orange, industrial stencil type. See
/// /design/identity_options.html for the full rationale and the other directions considered.
enum Theme {
    static let concrete = Color(red: 0.847, green: 0.827, blue: 0.780)     // #d8d3c7
    static let concreteDark = Color(red: 0.780, green: 0.757, blue: 0.698) // #c7c1b2
    static let stone = Color(red: 0.643, green: 0.616, blue: 0.573)       // #a49d8b
    static let ink = Color(red: 0.110, green: 0.106, blue: 0.090)         // #1c1b17
    static let mutedInk = Color(red: 0.396, green: 0.373, blue: 0.322)    // #655f52
    static let safetyOrange = Color(red: 0.910, green: 0.341, blue: 0.059) // #e8570f

    /// Stands in for the Archivo Black display face from the identity comparison until a
    /// bundled custom font is worth the extra build weight — heavy weight + tight tracking
    /// approximates the same stenciled-warehouse-signage feel with a system font.
    static func stencilTitle(_ size: CGFloat) -> Font {
        .system(size: size, weight: .black, design: .default)
    }
}
