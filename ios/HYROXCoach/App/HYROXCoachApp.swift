import SwiftUI
import UIKit

@main
struct HYROXCoachApp: App {
    @StateObject private var authViewModel = AuthViewModel()

    init() {
        Self.applyConcreteAndChalkAppearance()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authViewModel)
        }
    }

    /// Applies the Concrete & Chalk identity to UIKit chrome (nav bars, table/list
    /// backgrounds, segmented controls) globally, so every screen matches without
    /// re-styling each one by hand.
    private static func applyConcreteAndChalkAppearance() {
        let concrete = UIColor(Theme.concrete)
        let ink = UIColor(Theme.ink)
        let stone = UIColor(Theme.stone.opacity(0.4))
        let orange = UIColor(Theme.safetyOrange)

        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = concrete
        navAppearance.shadowColor = stone
        navAppearance.titleTextAttributes = [.foregroundColor: ink, .font: UIFont.systemFont(ofSize: 17, weight: .black)]
        navAppearance.largeTitleTextAttributes = [.foregroundColor: ink, .font: UIFont.systemFont(ofSize: 32, weight: .black)]
        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance
        UINavigationBar.appearance().tintColor = orange

        UITableView.appearance().backgroundColor = concrete
        UITableView.appearance().separatorColor = stone

        let segmentAppearance = UISegmentedControl.appearance()
        segmentAppearance.backgroundColor = UIColor(Theme.stone.opacity(0.25))
        segmentAppearance.selectedSegmentTintColor = ink
        segmentAppearance.setTitleTextAttributes([.foregroundColor: orange, .font: UIFont.systemFont(ofSize: 13, weight: .bold)], for: .selected)
        segmentAppearance.setTitleTextAttributes([.foregroundColor: UIColor(Theme.mutedInk), .font: UIFont.systemFont(ofSize: 13, weight: .semibold)], for: .normal)

        UIStepper.appearance().tintColor = orange
        UISwitch.appearance().onTintColor = orange
    }
}
