import SwiftUI

private struct BlockLogEntry {
    var weightKg = ""
    var minutes = ""
    var seconds = ""
    var rpe: Double = 7
}

struct WorkoutDetailView: View {
    let workout: Workout
    @ObservedObject var viewModel: TrainingViewModel
    @StateObject private var library = ExerciseLibraryStore()
    @State private var notes = ""
    @State private var blockInputs: [Int: BlockLogEntry] = [:]
    @State private var conditioningRounds = ""
    @State private var conditioningExtraReps = ""
    @State private var conditioningRPE: Double = 7
    @State private var isSubmittingLog = false

    private var currentWorkout: Workout {
        viewModel.block?.weeks
            .flatMap(\.workouts)
            .first(where: { $0.id == workout.id }) ?? workout
    }

    private var loggableBlocks: [(index: Int, dict: [String: JSONValue], hasWeight: Bool, hasTime: Bool)] {
        guard let blockArray = currentWorkout.prescription["blocks"]?.arrayValue else { return [] }
        return blockArray.enumerated().compactMap { index, value in
            guard let dict = value.objectValue else { return nil }
            let hasWeight = dict["sets"] != nil && dict["reps"] != nil
            let hasTime = dict["duration_min"] != nil || dict["distance_m"] != nil
            guard hasWeight || hasTime else { return nil }
            return (index, dict, hasWeight, hasTime)
        }
    }

    private var conditioningFormat: String? {
        guard let format = currentWorkout.prescription["conditioning"]?.objectValue?["format"]?.stringValue,
              format == "amrap" || format == "rounds" else { return nil }
        return format
    }

    private func blockInputBinding(for index: Int) -> Binding<BlockLogEntry> {
        Binding(get: { blockInputs[index] ?? BlockLogEntry() }, set: { blockInputs[index] = $0 })
    }

    private func buildLogPayload() -> WorkoutLogUpdate {
        var blocks: [BlockLog] = []
        for entry in loggableBlocks {
            guard let input = blockInputs[entry.index] else { continue }
            let weight = entry.hasWeight ? Double(input.weightKg) : nil
            let minutes = Int(input.minutes) ?? 0
            let seconds = Int(input.seconds) ?? 0
            let actualTime = entry.hasTime && (minutes > 0 || seconds > 0) ? minutes * 60 + seconds : nil
            guard weight != nil || actualTime != nil else { continue }

            let sets: [SetLog] = weight != nil ? [SetLog(reps: nil, weightKg: weight)] : []
            blocks.append(BlockLog(index: entry.index, sets: sets, actualTimeSec: actualTime, rpe: input.rpe))
        }

        var conditioningLog: ConditioningLog?
        if conditioningFormat != nil {
            let rounds = Int(conditioningRounds)
            let extra = Int(conditioningExtraReps)
            if rounds != nil || extra != nil {
                conditioningLog = ConditioningLog(roundsCompleted: rounds, extraReps: extra, durationSec: nil, rpe: conditioningRPE)
            }
        }

        return WorkoutLogUpdate(notes: notes.isEmpty ? nil : notes, blocks: blocks, conditioning: conditioningLog)
    }

    private var loggedBlockSummaries: [String] {
        guard let loggedBlocks = currentWorkout.loggedResult?["blocks"]?.arrayValue,
              let prescriptionBlocks = currentWorkout.prescription["blocks"]?.arrayValue else { return [] }
        return loggedBlocks.compactMap { logged in
            guard let dict = logged.objectValue, let index = dict["index"]?.doubleValue.map(Int.init) else { return nil }
            let movement = (index < prescriptionBlocks.count ? prescriptionBlocks[index].objectValue?["movement"]?.stringValue : nil) ?? "Block \(index + 1)"
            let title = movement.replacingOccurrences(of: "_", with: " ").capitalized

            var parts: [String] = []
            if let firstWeight = dict["sets"]?.arrayValue?.first?.objectValue?["weight_kg"]?.doubleValue {
                parts.append(String(format: "%.1fkg", firstWeight))
            }
            if let timeSec = dict["actual_time_sec"]?.doubleValue {
                let total = Int(timeSec)
                parts.append(String(format: "%d:%02d", total / 60, total % 60))
            }
            if let rpe = dict["rpe"]?.doubleValue {
                parts.append(String(format: "RPE %.1f", rpe))
            }
            return parts.isEmpty ? nil : "\(title): \(parts.joined(separator: " · "))"
        }
    }

    private var conditioningSummary: String? {
        guard let dict = currentWorkout.loggedResult?["conditioning"]?.objectValue else { return nil }
        var parts: [String] = []
        if let rounds = dict["rounds_completed"]?.displayString, !rounds.isEmpty { parts.append("\(rounds) rounds") }
        if let extra = dict["extra_reps"]?.displayString, !extra.isEmpty { parts.append("+\(extra) reps") }
        if let rpe = dict["rpe"]?.doubleValue { parts.append(String(format: "RPE %.1f", rpe)) }
        return parts.isEmpty ? nil : "Conditioning: \(parts.joined(separator: " · "))"
    }

    var body: some View {
        List {
            if currentWorkout.prescription["by_feel"]?.boolValue == true {
                Section {
                    Text("No fixed prescription — do what your body needs.")
                        .foregroundStyle(Theme.mutedInk)
                }
                .listRowBackground(Theme.concreteDark)
            }

            if let warmUp = currentWorkout.prescription["warm_up"]?.arrayValue, !warmUp.isEmpty {
                Section("Warm-Up") {
                    ForEach(Array(warmUp.enumerated()), id: \.offset) { _, item in
                        Text(item.displayString).foregroundStyle(Theme.ink)
                    }
                }
                .listRowBackground(Theme.concreteDark)
            }

            if let blocks = currentWorkout.prescription["blocks"]?.arrayValue, !blocks.isEmpty {
                Section("Main Set") {
                    ForEach(Array(blocks.enumerated()), id: \.offset) { _, block in
                        if let dict = block.objectValue {
                            BlockRow(block: dict, library: library)
                        }
                    }
                }
                .listRowBackground(Theme.concreteDark)
            }

            if let conditioning = currentWorkout.prescription["conditioning"]?.objectValue {
                Section("Conditioning") {
                    ConditioningView(conditioning: conditioning, library: library)
                }
                .listRowBackground(Theme.concreteDark)
            }

            if let coolDown = currentWorkout.prescription["cool_down"]?.arrayValue, !coolDown.isEmpty {
                Section("Cool-Down") {
                    ForEach(Array(coolDown.enumerated()), id: \.offset) { _, item in
                        Text(item.displayString).foregroundStyle(Theme.ink)
                    }
                }
                .listRowBackground(Theme.concreteDark)
            }

            if let completedAt = currentWorkout.completedAt {
                Section("Logged") {
                    Text("Completed \(completedAt.formatted(date: .abbreviated, time: .shortened))")
                        .foregroundStyle(Theme.ink)
                    ForEach(loggedBlockSummaries, id: \.self) { summary in
                        Text(summary).font(.subheadline).foregroundStyle(Theme.mutedInk)
                    }
                    if let conditioningSummary {
                        Text(conditioningSummary).font(.subheadline).foregroundStyle(Theme.mutedInk)
                    }
                    if let notes = currentWorkout.loggedResult?["notes"]?.stringValue, !notes.isEmpty {
                        Text(notes).foregroundStyle(Theme.mutedInk)
                    }
                }
                .listRowBackground(Theme.concreteDark)
            } else {
                Section("Log this workout") {
                    ForEach(loggableBlocks, id: \.index) { entry in
                        BlockLogRow(
                            title: (entry.dict["movement"]?.stringValue ?? "movement").replacingOccurrences(of: "_", with: " ").capitalized,
                            showWeight: entry.hasWeight,
                            showTime: entry.hasTime,
                            entry: blockInputBinding(for: entry.index)
                        )
                    }
                    if conditioningFormat != nil {
                        ConditioningLogRow(rounds: $conditioningRounds, extraReps: $conditioningExtraReps, rpe: $conditioningRPE)
                    }
                    TextField("Notes (how did it feel?)", text: $notes, axis: .vertical)
                        .foregroundStyle(Theme.ink)
                    Button {
                        isSubmittingLog = true
                        Task {
                            await viewModel.logWorkout(currentWorkout, payload: buildLogPayload())
                            isSubmittingLog = false
                        }
                    } label: {
                        Group {
                            if isSubmittingLog {
                                ProgressView().tint(Theme.safetyOrange)
                            } else {
                                Text("Mark complete")
                                    .font(.subheadline.weight(.bold))
                                    .foregroundStyle(Theme.safetyOrange)
                            }
                        }
                    }
                    .disabled(isSubmittingLog)
                }
                .listRowBackground(Theme.concreteDark)
            }
        }
        .tint(Theme.safetyOrange)
        .scrollContentBackground(.hidden)
        .background(Theme.concrete)
        .listRowSeparatorTint(Theme.stone.opacity(0.35))
        .navigationTitle(currentWorkout.title)
        .navigationDestination(for: Exercise.self) { exercise in
            ExerciseDetailView(exercise: exercise)
        }
        .task { await library.loadIfNeeded() }
    }
}

private struct BlockLogRow: View {
    let title: String
    let showWeight: Bool
    let showTime: Bool
    @Binding var entry: BlockLogEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
            HStack(spacing: 10) {
                if showWeight {
                    TextField("kg", text: $entry.weightKg)
                        .keyboardType(.decimalPad)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 70)
                }
                if showTime {
                    TextField("min", text: $entry.minutes)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 50)
                    Text(":").foregroundStyle(Theme.mutedInk)
                    TextField("sec", text: $entry.seconds)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 50)
                }
                Spacer()
                Text(String(format: "RPE %.1f", entry.rpe))
                    .font(.caption)
                    .foregroundStyle(Theme.mutedInk)
            }
            Slider(value: $entry.rpe, in: 1...10, step: 0.5)
                .tint(Theme.safetyOrange)
        }
        .padding(.vertical, 4)
    }
}

private struct ConditioningLogRow: View {
    @Binding var rounds: String
    @Binding var extraReps: String
    @Binding var rpe: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Conditioning").font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
            HStack(spacing: 10) {
                TextField("Rounds", text: $rounds)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 70)
                Text("+").foregroundStyle(Theme.mutedInk)
                TextField("Reps", text: $extraReps)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 70)
                Spacer()
                Text(String(format: "RPE %.1f", rpe))
                    .font(.caption)
                    .foregroundStyle(Theme.mutedInk)
            }
            Slider(value: $rpe, in: 1...10, step: 0.5)
                .tint(Theme.safetyOrange)
        }
        .padding(.vertical, 4)
    }
}

private struct BlockRow: View {
    let block: [String: JSONValue]
    let library: ExerciseLibraryStore

    private var movementSlug: String? { block["movement"]?.stringValue }

    private var title: String {
        (movementSlug ?? "movement")
            .replacingOccurrences(of: "_", with: " ")
            .capitalized
    }

    private var linkedExercise: Exercise? {
        movementSlug.flatMap { library.exercise(forMovementSlug: $0) }
    }

    private var subtitleParts: [String] {
        var parts: [String] = []
        if let sets = block["sets"], let reps = block["reps"] {
            let unit = block["unit"]?.stringValue.map { " \($0)" } ?? ""
            parts.append("\(sets.displayString) x \(reps.displayString)\(unit)")
        }
        if let duration = block["duration_min"] { parts.append("\(duration.displayString) min") }
        if let distance = block["distance_m"] { parts.append("\(distance.displayString) m") }
        if let tempo = block["tempo"]?.stringValue { parts.append("tempo \(tempo)") }
        if let rest = block["rest_sec"] { parts.append("rest \(rest.displayString)s") }
        if let overloadLabel { parts.append(overloadLabel) }
        if let paceLabel { parts.append(paceLabel) }
        if let hrLabel = hrTargetLabel { parts.append(hrLabel) }
        if let suggestedLoadLabel { parts.append(suggestedLoadLabel) }
        return parts
    }

    private static let zoneDisplayNames: [String: String] = [
        "z1_recovery": "Zone 1",
        "z2_aerobic_base": "Zone 2",
        "z3_tempo": "Zone 3",
        "z4_threshold": "Zone 4",
        "z5_anaerobic": "Zone 5",
    ]

    private var hrTargetLabel: String? {
        guard let zoneValue = block["target_hr_zone"]?.stringValue else { return nil }
        let zoneName = Self.zoneDisplayNames[zoneValue] ?? zoneValue
        guard let bpmRange = block["target_hr_bpm"]?.arrayValue, bpmRange.count == 2 else {
            return zoneName
        }
        return "\(zoneName): \(bpmRange[0].displayString)-\(bpmRange[1].displayString) bpm"
    }

    private var detail: String? {
        block["detail"]?.stringValue ?? block["note"]?.stringValue
    }

    private var overloadLabel: String? {
        guard let kg = block["overload_kg"]?.doubleValue else { return nil }
        return String(format: "%.1fkg", kg)
    }

    private var paceLabel: String? {
        guard let sec = block["target_pace_per_km_sec"]?.doubleValue else { return nil }
        let totalSeconds = Int(sec.rounded())
        return String(format: "%d:%02d/km", totalSeconds / 60, totalSeconds % 60)
    }

    private var suggestedLoadLabel: String? {
        guard let kg = block["suggested_load_kg"]?.doubleValue else { return nil }
        return String(format: "Suggested %.1fkg", kg)
    }

    private var progressionNote: String? {
        block["progression_note"]?.stringValue
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let linkedExercise {
                NavigationLink(value: linkedExercise) {
                    HStack {
                        Text(title).font(.body).foregroundStyle(Theme.ink)
                        Image(systemName: "info.circle").font(.caption).foregroundStyle(Theme.safetyOrange)
                    }
                }
            } else {
                Text(title).font(.body).foregroundStyle(Theme.ink)
            }
            if !subtitleParts.isEmpty {
                Text(subtitleParts.joined(separator: " · "))
                    .font(.subheadline)
                    .foregroundStyle(Theme.mutedInk)
            }
            if let detail {
                Text(detail)
                    .font(.footnote)
                    .foregroundStyle(Theme.mutedInk)
            }
            if let progressionNote {
                Text(progressionNote)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(Theme.safetyOrange)
            }
        }
        .padding(.vertical, 2)
    }
}

private struct ConditioningView: View {
    let conditioning: [String: JSONValue]
    let library: ExerciseLibraryStore

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let format = conditioning["format"]?.stringValue {
                Text(headline(for: format))
                    .font(.headline)
                    .foregroundStyle(Theme.ink)
            }
            if let movements = conditioning["movements"]?.arrayValue {
                ForEach(Array(movements.enumerated()), id: \.offset) { _, movement in
                    Text("• \(movement.displayString)")
                        .foregroundStyle(Theme.ink)
                }
            }
            if let options = conditioning["options"]?.arrayValue {
                ForEach(Array(options.enumerated()), id: \.offset) { _, option in
                    if let dict = option.objectValue {
                        BlockRow(block: dict, library: library)
                    }
                }
            }
            if let previousComparison {
                Text(previousComparison)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(Theme.safetyOrange)
            }
        }
        .padding(.vertical, 2)
    }

    private var previousComparison: String? {
        guard let rounds = conditioning["previous_rounds_completed"]?.displayString, !rounds.isEmpty else { return nil }
        var text = "Last time: \(rounds) rounds"
        if let extra = conditioning["previous_extra_reps"]?.displayString, !extra.isEmpty {
            text += " + \(extra) reps"
        }
        if let rpe = conditioning["previous_rpe"]?.displayString, !rpe.isEmpty {
            text += " @ RPE \(rpe)"
        }
        return text
    }

    private func headline(for format: String) -> String {
        switch format {
        case "amrap":
            let duration = conditioning["duration_min"]?.displayString ?? ""
            return "\(duration)-min AMRAP"
        case "rounds":
            let rounds = conditioning["rounds"]?.displayString ?? ""
            let rest = conditioning["rest_sec"]?.displayString
            return rest.map { "\(rounds) rounds, rest \($0)s" } ?? "\(rounds) rounds"
        case "steady_aerobic":
            let duration = conditioning["duration_min"]?.displayString ?? ""
            return "\(duration) min steady aerobic"
        case "choice":
            return "Choose one"
        case "mixed_machine_amrap":
            return "Mixed machine AMRAP"
        default:
            return format.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}
