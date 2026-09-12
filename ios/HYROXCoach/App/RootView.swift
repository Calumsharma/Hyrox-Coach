import SwiftUI

struct RootView: View {
    @EnvironmentObject private var auth: AuthViewModel

    var body: some View {
        Group {
            if let athlete = auth.athlete {
                if athlete.onboardingCompleted {
                    if auth.isBuildingProgram {
                        BuildingProgramView()
                    } else {
                        DashboardView()
                    }
                } else {
                    OnboardingView()
                }
            } else {
                SignInView()
            }
        }
        .animation(.default, value: auth.athlete?.onboardingCompleted)
        .animation(.default, value: auth.isBuildingProgram)
    }
}

private struct BuildingProgramView: View {
    var body: some View {
        ZStack {
            Theme.concrete.ignoresSafeArea()
            VStack(spacing: 18) {
                ProgressView()
                    .tint(Theme.safetyOrange)
                    .scaleEffect(1.4)
                Text("BUILDING YOUR PROGRAM")
                    .font(.system(size: 13, weight: .black))
                    .tracking(1.5)
                    .foregroundStyle(Theme.ink)
                Text("Periodizing your block around your weaknesses and goal race.")
                    .font(.subheadline)
                    .foregroundStyle(Theme.mutedInk)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 48)
            }
        }
    }
}
