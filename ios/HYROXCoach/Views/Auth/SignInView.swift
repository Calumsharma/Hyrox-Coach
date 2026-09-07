import SwiftUI

struct SignInView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @State private var email = ""

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            VStack(spacing: 8) {
                Text("HYROX Coach")
                    .font(.largeTitle.bold())
                Text("Recovery-driven training, built around your race.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            VStack(spacing: 12) {
                TextField("Email", text: $email)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))

                Button {
                    Task { await auth.signIn(email: email) }
                } label: {
                    if auth.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("Continue")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(email.isEmpty || auth.isLoading)

                if let error = auth.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                #if DEBUG
                Button("Seed demo data (debug)") {
                    Task { await runDebugSeed() }
                }
                .font(.footnote)

                Button("Sign in only, skip onboarding (debug)") {
                    Task { await auth.signIn(email: "onboarding-test+\(Int(Date().timeIntervalSince1970))@hyroxcoach.app") }
                }
                .font(.footnote)
                #endif
            }
            .padding(.horizontal, 32)

            Spacer()
            Spacer()
        }
    }

    #if DEBUG
    private func runDebugSeed() async {
        await auth.signIn(email: "demo+\(Int(Date().timeIntervalSince1970))@hyroxcoach.app")
        await auth.completeOnboarding(AthleteOnboarding(
            name: "Demo Athlete",
            age: 32,
            weightKg: 82,
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
