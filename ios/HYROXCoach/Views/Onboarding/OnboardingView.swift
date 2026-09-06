import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject private var auth: AuthViewModel

    @State private var name = ""
    @State private var age = 30
    @State private var weightKg = 80.0
    @State private var division: Division = .openMen
    @State private var predicted5k: Int?
    @State private var current10k: Int?
    @State private var weakStations: [StationSlug] = []
    @State private var goalTime: Int?
    @State private var goalEventDate = Date().addingTimeInterval(60 * 60 * 24 * 56)

    @State private var bestSoloTime: Int?
    @State private var raceCount = 0
    @State private var experienceTier: ExperienceTier = .beginner
    @State private var tierManuallySet = false
    @State private var isApplyingSuggestion = false

    var body: some View {
        NavigationStack {
            Form {
                Section("About you") {
                    TextField("Name", text: $name)
                    Stepper("Age: \(age)", value: $age, in: 14...90)
                    HStack {
                        Text("Weight")
                        Spacer()
                        TextField("kg", value: $weightKg, format: .number)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 60)
                        Text("kg")
                    }
                    Picker("Division", selection: $division) {
                        ForEach(Division.allCases) { division in
                            Text(division.displayName).tag(division)
                        }
                    }
                }

                Section("Current fitness") {
                    TimeInputField(label: "Predicted 5k", seconds: $predicted5k)
                    TimeInputField(label: "Current 10k", seconds: $current10k)
                }

                Section {
                    TimeInputField(label: "Best solo HYROX time", seconds: $bestSoloTime)
                    Stepper("HYROX races (incl. doubles): \(raceCount)", value: $raceCount, in: 0...50)
                    Picker("Experience level", selection: $experienceTier) {
                        ForEach(ExperienceTier.allCases) { tier in
                            Text(tier.displayName).tag(tier)
                        }
                    }
                } header: {
                    Text("Experience level")
                } footer: {
                    Text("We'll suggest a level from your time and race count, but you can pick a different one.")
                }
                .onChange(of: bestSoloTime) { _, _ in Task { await refreshSuggestedTier() } }
                .onChange(of: raceCount) { _, _ in Task { await refreshSuggestedTier() } }
                .onChange(of: experienceTier) { _, _ in
                    if isApplyingSuggestion {
                        isApplyingSuggestion = false
                    } else {
                        tierManuallySet = true
                    }
                }

                Section {
                    ForEach(StationSlug.allCases) { station in
                        Button {
                            toggle(station)
                        } label: {
                            HStack {
                                Text(station.displayName)
                                    .foregroundStyle(.primary)
                                Spacer()
                                if let rank = weakStations.firstIndex(of: station) {
                                    Text("#\(rank + 1)")
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                } header: {
                    Text("Weakest stations")
                } footer: {
                    Text("Tap in order, worst first. Your program will lean into these.")
                }

                Section("Goal") {
                    TimeInputField(label: "Goal race time", seconds: $goalTime)
                    DatePicker("Goal event date", selection: $goalEventDate, displayedComponents: .date)
                }

                if let error = auth.errorMessage {
                    Text(error).foregroundStyle(.red)
                }

                Section {
                    Button {
                        Task { await submit() }
                    } label: {
                        if auth.isLoading {
                            ProgressView().frame(maxWidth: .infinity)
                        } else {
                            Text("Build my program").frame(maxWidth: .infinity)
                        }
                    }
                    .disabled(name.isEmpty || auth.isLoading)
                }
            }
            .navigationTitle("Tell us about you")
        }
    }

    private func toggle(_ station: StationSlug) {
        if let index = weakStations.firstIndex(of: station) {
            weakStations.remove(at: index)
        } else if weakStations.count < 3 {
            weakStations.append(station)
        }
    }

    private func refreshSuggestedTier() async {
        guard !tierManuallySet else { return }
        guard let suggested = try? await APIClient.shared.suggestExperienceTier(bestSoloTimeSeconds: bestSoloTime, raceCount: raceCount) else { return }
        isApplyingSuggestion = true
        experienceTier = suggested
    }

    private func submit() async {
        let payload = AthleteOnboarding(
            name: name,
            age: age,
            weightKg: weightKg,
            division: division,
            experienceTier: experienceTier,
            predicted5kSeconds: predicted5k,
            current10kSeconds: current10k,
            selfReportedWeakStations: weakStations,
            goalTimeSeconds: goalTime,
            goalEventDate: goalEventDate
        )
        await auth.completeOnboarding(payload)
    }
}
