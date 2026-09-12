import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var recoveryScore: RecoveryScoreRead?
    @State private var isSyncing = false
    @State private var syncMessage: String?
    @State private var healthAuthorized = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if let recoveryScore {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text("Today's Recovery")
                                    .font(.subheadline.weight(.bold))
                                    .foregroundStyle(Theme.ink)
                                Spacer()
                                Text(trendLabel(recoveryScore.trend))
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(trendColor(recoveryScore.trend))
                            }
                            Text("\(Int(recoveryScore.compositeScore)) / 100")
                                .font(.title.weight(.black))
                                .foregroundStyle(Theme.ink)
                        }
                        .padding(.vertical, 4)
                    } else {
                        Text("No recovery data yet — connect Apple Health and sync to get started.")
                            .foregroundStyle(Theme.mutedInk)
                    }
                } header: {
                    Label("Recovery", systemImage: "heart.fill")
                }
                .listRowBackground(Theme.concreteDark)

                Section {
                    Button {
                        Task { await connectAndSync() }
                    } label: {
                        Group {
                            if isSyncing {
                                ProgressView().tint(Theme.safetyOrange)
                            } else {
                                Text(healthAuthorized ? "Sync Health Data" : "Connect Apple Health")
                                    .font(.subheadline.weight(.bold))
                                    .foregroundStyle(Theme.safetyOrange)
                            }
                        }
                    }
                    .disabled(isSyncing)
                    if let syncMessage {
                        Text(syncMessage).font(.caption).foregroundStyle(Theme.mutedInk)
                    }
                } header: {
                    Label("Wearable Data", systemImage: "applewatch")
                } footer: {
                    Text("Reads HRV, resting heart rate, and sleep from the Health app to adjust your training automatically. Works best with an Apple Watch on a real device — the Simulator has no health data of its own.")
                }
                .listRowBackground(Theme.concreteDark)

                Section {
                    Button {
                        auth.signOut()
                    } label: {
                        Text("Sign out")
                            .font(.subheadline.weight(.bold))
                            .foregroundStyle(Theme.safetyOrange)
                    }
                }
                .listRowBackground(Theme.concreteDark)
            }
            .tint(Theme.safetyOrange)
            .scrollContentBackground(.hidden)
            .background(Theme.concrete)
            .listRowSeparatorTint(Theme.stone.opacity(0.35))
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
            .task { await loadRecoveryStatus() }
        }
    }

    private func loadRecoveryStatus() async {
        recoveryScore = try? await APIClient.shared.getRecoveryStatus()
    }

    private func connectAndSync() async {
        isSyncing = true
        defer { isSyncing = false }
        do {
            try await HealthKitManager.shared.requestAuthorization()
            healthAuthorized = true
            let inputs = await HealthKitManager.shared.fetchLatestRecoveryInputs()
            guard inputs.hrvMs != nil || inputs.restingHrBpm != nil || inputs.sleepScore != nil else {
                syncMessage = "No Health data found — expected on the Simulator, try a real device with Health data."
                return
            }
            let payload = RecoveryReadingCreate(
                readingDate: Date(),
                hrvMs: inputs.hrvMs,
                restingHrBpm: inputs.restingHrBpm,
                sleepScore: inputs.sleepScore,
                vo2Max: inputs.vo2Max
            )
            let response = try await APIClient.shared.submitRecoveryReading(payload)
            recoveryScore = response.score
            syncMessage = "Synced just now."
        } catch {
            syncMessage = "Couldn't sync: \(error.localizedDescription)"
        }
    }

    private func trendLabel(_ trend: RecoveryTrend) -> String {
        switch trend {
        case .rising: return "RISING"
        case .stable: return "STABLE"
        case .falling: return "FALLING"
        }
    }

    private func trendColor(_ trend: RecoveryTrend) -> Color {
        switch trend {
        case .rising: return .green
        case .stable: return Theme.mutedInk
        case .falling: return Theme.safetyOrange
        }
    }
}
