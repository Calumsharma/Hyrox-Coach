import SwiftUI

struct SignInView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @State private var email = ""
    @FocusState private var emailFocused: Bool

    var body: some View {
        ZStack {
            Theme.background.ignoresSafeArea()

            VStack(spacing: 28) {
                Spacer()

                HStack {
                    Text("HYROX TRAINING")
                        .font(Theme.labelMono(11))
                        .tracking(2)
                        .foregroundStyle(Theme.textSecondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .overlay(RoundedRectangle(cornerRadius: 3).stroke(Theme.hairline, lineWidth: 1.5))
                        .rotationEffect(.degrees(-2))
                    Spacer()
                }
                .padding(.horizontal, 32)

                VStack(spacing: 18) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .fill(Theme.surface)
                            .overlay(RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(Theme.hairline, lineWidth: 1))
                            .frame(width: 76, height: 76)
                        Image(systemName: "bolt.fill")
                            .font(.system(size: 32, weight: .bold))
                            .foregroundStyle(Theme.safetyOrange)
                    }

                    VStack(spacing: 8) {
                        Text("S9")
                            .font(Theme.stencilTitle(38))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(Theme.textPrimary)
                        Text("Recovery-driven training, built around your race.")
                            .font(.subheadline)
                            .foregroundStyle(Theme.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 40)
                    }
                }

                VStack(spacing: 14) {
                    TextField("", text: $email, prompt: Text("Email").foregroundStyle(Theme.textSecondary.opacity(0.6)))
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .focused($emailFocused)
                        .foregroundStyle(Theme.textPrimary)
                        .padding(16)
                        .background(
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .fill(Theme.surface)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                                        .strokeBorder(emailFocused ? Theme.safetyOrange : Theme.hairline, lineWidth: emailFocused ? 2 : 1)
                                )
                        )

                    Button {
                        Task { await auth.signIn(email: email) }
                    } label: {
                        Group {
                            if auth.isLoading {
                                ProgressView().tint(Theme.ink)
                            } else {
                                Text("Continue")
                                    .font(Theme.labelMono(14, weight: .bold))
                                    .tracking(1.5)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(Theme.ink)
                    .background(
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .fill(email.isEmpty ? Theme.stone.opacity(0.3) : Theme.safetyOrange)
                    )
                    .disabled(email.isEmpty || auth.isLoading)

                    if let error = auth.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }

                    #if DEBUG
                    VStack(spacing: 8) {
                        Button("Seed demo data (debug)") {
                            Task { await runDebugSeed() }
                        }
                        Button("Sign in only, skip onboarding (debug)") {
                            Task { await auth.signIn(email: "onboarding-test+\(Int(Date().timeIntervalSince1970))@s9.app") }
                        }
                    }
                    .font(.footnote)
                    .foregroundStyle(Theme.textSecondary)
                    .padding(.top, 8)
                    #endif
                }
                .padding(.horizontal, 32)

                Spacer()
                Spacer()
            }
        }
    }

    #if DEBUG
    private func runDebugSeed() async {
        await auth.signIn(email: "demo+\(Int(Date().timeIntervalSince1970))@s9.app")
        await auth.completeOnboarding(AthleteOnboarding(
            name: "Demo Athlete",
            age: 32,
            weightKg: 82,
            heightCm: 180,
            division: .openMen,
            experienceTier: .advanced,
            testedMaxHR: nil,
            predicted5kSeconds: 1080,
            current10kSeconds: 2400,
            selfReportedWeakStations: [.sledPush, .farmersCarry],
            goalTimeSeconds: 4500,
            goalEventDate: Date().addingTimeInterval(60 * 60 * 24 * 56)
        ))
        _ = try? await APIClient.shared.createTrainingBlock(TrainingBlockCreate(
            lengthWeeks: 8,
            startDate: Date(),
            goalEventDate: Date().addingTimeInterval(60 * 60 * 24 * 56),
            goalTimeSeconds: 4500
        ))
    }
    #endif
}
