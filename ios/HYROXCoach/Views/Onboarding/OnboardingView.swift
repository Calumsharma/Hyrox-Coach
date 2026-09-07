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
    @State private var testedMaxHR: Int?
    @State private var goalTime: Int?
    @State private var goalEventDate = Date().addingTimeInterval(60 * 60 * 24 * 56)

    @State private var pastRaces: [PastResultCreate] = []
    @State private var showingAddRace = false
    @State private var experienceTier: ExperienceTier = .beginner
    @State private var tierManuallySet = false
    @State private var isApplyingSuggestion = false
    @State private var isSubmittingRaces = false

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
                        ForEach(Division.allCases.filter(\.isSolo)) { division in
                            Text(division.displayName).tag(division)
                        }
                    }
                }

                Section {
                    TimeInputField(label: "Predicted 5k", seconds: $predicted5k)
                    TimeInputField(label: "Current 10k", seconds: $current10k)
                    HStack {
                        Text("Tested max HR")
                        Spacer()
                        TextField("optional", value: $testedMaxHR, format: .number)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 70)
                        Text("bpm")
                    }
                } header: {
                    Text("Current fitness")
                } footer: {
                    Text("Leave blank and we'll estimate your zones from age instead.")
                }

                Section {
                    ForEach(Array(pastRaces.enumerated()), id: \.offset) { index, race in
                        VStack(alignment: .leading, spacing: 2) {
                            Text("\(race.division.displayName) — \(TimeInputField.format(race.totalTimeSeconds))")
                            Text(race.eventDate.formatted(date: .abbreviated, time: .omitted))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .onDelete { indexSet in
                        pastRaces.remove(atOffsets: indexSet)
                        Task { await refreshSuggestedTier() }
                    }
                    Button("Add a past race") { showingAddRace = true }
                } header: {
                    Text("Past HYROX races")
                } footer: {
                    Text("Include doubles races too — they count toward your experience level even though you train solo.")
                }

                Section {
                    Picker("Experience level", selection: $experienceTier) {
                        ForEach(ExperienceTier.allCases) { tier in
                            Text(tier.displayName).tag(tier)
                        }
                    }
                } header: {
                    Text("Experience level")
                } footer: {
                    Text("We'll suggest a level from your race history, but you can pick a different one.")
                }
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
                        if auth.isLoading || isSubmittingRaces {
                            ProgressView().frame(maxWidth: .infinity)
                        } else {
                            Text("Build my program").frame(maxWidth: .infinity)
                        }
                    }
                    .disabled(name.isEmpty || auth.isLoading || isSubmittingRaces)
                }
            }
            .navigationTitle("Tell us about you")
            .sheet(isPresented: $showingAddRace) {
                AddPastRaceView { race in
                    pastRaces.append(race)
                    Task { await refreshSuggestedTier() }
                }
            }
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
        let bestSoloTime = pastRaces.filter(\.division.isSolo).map(\.totalTimeSeconds).min()
        guard let suggested = try? await APIClient.shared.suggestExperienceTier(bestSoloTimeSeconds: bestSoloTime, raceCount: pastRaces.count) else { return }
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
            testedMaxHR: testedMaxHR,
            predicted5kSeconds: predicted5k,
            current10kSeconds: current10k,
            selfReportedWeakStations: weakStations,
            goalTimeSeconds: goalTime,
            goalEventDate: goalEventDate
        )
        await auth.completeOnboarding(payload)
        guard auth.errorMessage == nil else { return }

        isSubmittingRaces = true
        for race in pastRaces {
            _ = try? await APIClient.shared.addPastResult(race)
        }
        isSubmittingRaces = false
    }
}
