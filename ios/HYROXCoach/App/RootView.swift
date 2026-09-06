import SwiftUI

struct RootView: View {
    @EnvironmentObject private var auth: AuthViewModel

    var body: some View {
        Group {
            if let athlete = auth.athlete {
                if athlete.onboardingCompleted {
                    DashboardView()
                } else {
                    OnboardingView()
                }
            } else {
                SignInView()
            }
        }
        .animation(.default, value: auth.athlete?.onboardingCompleted)
    }
}
