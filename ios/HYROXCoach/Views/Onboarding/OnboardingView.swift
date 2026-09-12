import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject private var auth: AuthViewModel

    @State private var name = ""
    @State private var age: Int? = 30
    @State private var weightKg = 80.0
    @State private var heightCm = 175.0
    @State private var division: Division = .openMen
    @State private var predicted5k: Int?
    @State private var current10k: Int?
    @State private var weakStations: [StationSlug] = []
    @State private var testedMaxHR: Int?
    @State private var goalTime: Int?
    @State private var goalEventDate = Date().addingTimeInterval(60 * 60 * 24 * 56)
    @State private var lengthWeeks: Int? = 8

    @State private var pastRaces: [PastResultCreate] = []
    @State private var showingAddRace = false
    @State private var experienceTier: ExperienceTier = .beginner
    @State private var tierManuallySet = false
    @State private var isApplyingSuggestion = false
    @State private var isSubmittingRaces = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Name", text: $name)
                    WheelIntPicker(label: "Age", value: $age, range: 14...90, unit: "yrs", defaultValue: 30)
                    WeightPicker(label: "Weight", weightKg: $weightKg)
                    HeightPicker(label: "Height", heightCm: $heightCm)
                    Picker("Division", selection: $division) {
                        ForEach(Division.allCases.filter(\.isSolo)) { division in
                            Text(division.displayName).tag(division)
                        }
                    }
                } header: {
                    Label("About You", systemImage: "person.fill")
                }
                .listRowBackground(Theme.surface)

                Section {
                    WheelTimePicker(label: "Current 5K PB", seconds: $predicted5k, defaultSeconds: 1500, maxMinutes: 60)
                    WheelTimePicker(label: "Current 10K PB", seconds: $current10k, defaultSeconds: 3000, maxMinutes: 120)
                    WheelIntPicker(label: "Tested Max HR", value: $testedMaxHR, range: 120...220, unit: "bpm", defaultValue: 185)
                } header: {
                    Label("Current Fitness", systemImage: "heart.fill")
                } footer: {
                    Text("Leave max HR at the default and we'll estimate your zones from age instead.")
                }
                .listRowBackground(Theme.surface)

                Section {
                    ForEach(Array(pastRaces.enumerated()), id: \.offset) { index, race in
                        VStack(alignment: .leading, spacing: 2) {
                            Text("\(race.division.displayName) — \(TimeInputField.format(race.totalTimeSeconds))")
                                .foregroundStyle(Theme.textPrimary)
                            Text(race.eventDate.formatted(date: .abbreviated, time: .omitted))
                                .font(.caption)
                                .foregroundStyle(Theme.textSecondary)
                        }
                    }
                    .onDelete { indexSet in
                        pastRaces.remove(atOffsets: indexSet)
                        Task { await refreshSuggestedTier() }
                    }
                    Button("+ Add a Past Race") { showingAddRace = true }
                        .foregroundStyle(Theme.safetyOrange)
                        .fontWeight(.bold)
                } header: {
                    Label("Past HYROX Races", systemImage: "flag.checkered")
                } footer: {
                    Text("Include doubles races too — they count toward your experience level even though you train solo.")
                }
                .listRowBackground(Theme.surface)

                Section {
                    Picker("Experience level", selection: $experienceTier) {
                        ForEach(ExperienceTier.allCases) { tier in
                            Text(tier.displayName).tag(tier)
                        }
                    }
                } header: {
                    Label("Experience Level", systemImage: "chart.line.uptrend.xyaxis")
                } footer: {
                    Text("We'll suggest a level from your race history, but you can pick a different one.")
                }
                .listRowBackground(Theme.surface)
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
                                    .foregroundStyle(Theme.textPrimary)
                                Spacer()
                                if let rank = weakStations.firstIndex(of: station) {
                                    Text("\(rank + 1)")
                                        .font(.caption.bold())
                                        .foregroundStyle(Theme.ink)
                                        .frame(width: 22, height: 22)
                                        .background(Circle().fill(Theme.safetyOrange))
                                }
                            }
                        }
                    }
                } header: {
                    Label("Weakest Stations", systemImage: "exclamationmark.triangle.fill")
                } footer: {
                    Text("Tap in order, worst first. Your program will lean into these.")
                }
                .listRowBackground(Theme.surface)

                Section {
                    WheelTimePicker(label: "Goal Race Time", seconds: $goalTime, defaultSeconds: 4500, maxMinutes: 180)
                    DatePicker("Goal event date", selection: $goalEventDate, displayedComponents: .date)
                    WheelIntPicker(label: "Program Length", value: $lengthWeeks, range: 4...20, unit: "wks", defaultValue: 8)
                } header: {
                    Label("Goal", systemImage: "target")
                }
                .listRowBackground(Theme.surface)

                if let error = auth.errorMessage {
                    Text(error).foregroundStyle(.red)
                        .listRowBackground(Theme.surface)
                }

                Section {
                    Button {
                        Task { await submit() }
                    } label: {
                        Group {
                            if auth.isLoading || isSubmittingRaces {
                                ProgressView().tint(Theme.ink)
                            } else {
                                Text("Build My Program")
                                    .font(Theme.labelMono(14, weight: .black))
                                    .tracking(1)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 6)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(Theme.ink)
                    .listRowBackground(
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .fill((name.isEmpty || auth.isLoading || isSubmittingRaces) ? Theme.stone.opacity(0.3) : Theme.safetyOrange)
                    )
                    .disabled(name.isEmpty || auth.isLoading || isSubmittingRaces)
                }
            }
            .tint(Theme.safetyOrange)
            .scrollContentBackground(.hidden)
            .background(Theme.background)
            .listRowSeparatorTint(Theme.hairline)
            .navigationTitle("Athlete Profile")
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
            age: age ?? 30,
            weightKg: weightKg,
            heightCm: heightCm,
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

        auth.isBuildingProgram = true
        defer { auth.isBuildingProgram = false }

        isSubmittingRaces = true
        for race in pastRaces {
            _ = try? await APIClient.shared.addPastResult(race)
        }
        do {
            _ = try await APIClient.shared.createTrainingBlock(TrainingBlockCreate(
                lengthWeeks: lengthWeeks ?? 8,
                startDate: Date(),
                goalEventDate: goalEventDate,
                goalTimeSeconds: goalTime ?? 4500
            ))
        } catch {
            auth.errorMessage = "Profile saved, but the program couldn't be built: \(error.localizedDescription)"
        }
        isSubmittingRaces = false
    }
}
