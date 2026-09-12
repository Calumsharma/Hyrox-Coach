import SwiftUI
import UIKit

@main
struct HYROXCoachApp: App {
    @StateObject private var authViewModel = AuthViewModel()

    init() {
        Self.applyOpsBoardAppearance()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authViewModel)
        }
        .environment(\.colorScheme, .dark)
    }

    /// Applies the "Ops Board" identity to UIKit chrome (nav bars, table/list backgrounds,
    /// segmented controls) globally, so every screen matches without re-styling each one by
    /// hand. Dark-first: ink background, concrete text, safety-orange the sole accent.
    private static func applyOpsBoardAppearance() {
        let ink = UIColor(Theme.ink)
        let concrete = UIColor(Theme.concrete)
        let hairline = UIColor(Theme.hairline)
        let orange = UIColor(Theme.safetyOrange)
        let monoFont = UIFont.monospacedSystemFont(ofSize: 17, weight: .heavy)
        let monoLargeFont = UIFont.monospacedSystemFont(ofSize: 30, weight: .heavy)

        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = ink
        navAppearance.shadowColor = hairline
        navAppearance.titleTextAttributes = [.foregroundColor: concrete, .font: monoFont]
        navAppearance.largeTitleTextAttributes = [.foregroundColor: concrete, .font: monoLargeFont]
        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance
        UINavigationBar.appearance().tintColor = orange

        UITableView.appearance().backgroundColor = ink
        UITableView.appearance().separatorColor = hairline

        let segmentAppearance = UISegmentedControl.appearance()
        segmentAppearance.backgroundColor = UIColor(Theme.stone.opacity(0.15))
        segmentAppearance.selectedSegmentTintColor = orange
        segmentAppearance.setTitleTextAttributes([.foregroundColor: ink, .font: UIFont.monospacedSystemFont(ofSize: 13, weight: .bold)], for: .selected)
        segmentAppearance.setTitleTextAttributes([.foregroundColor: UIColor(Theme.stone), .font: UIFont.monospacedSystemFont(ofSize: 13, weight: .semibold)], for: .normal)

        UIStepper.appearance().tintColor = orange
        UISwitch.appearance().onTintColor = orange
    }
}
