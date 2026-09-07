import SwiftUI

struct WorkoutDetailView: View {
    let workout: Workout
    @ObservedObject var viewModel: TrainingViewModel
    @StateObject private var library = ExerciseLibraryStore()
    @State private var notes = ""

    private var currentWorkout: Workout {
        viewModel.block?.weeks
            .flatMap(\.workouts)
            .first(where: { $0.id == workout.id }) ?? workout
    }

    var body: some View {
        List {
            if currentWorkout.prescription["by_feel"]?.boolValue == true {
                Section {
                    Text("No fixed prescription — do what your body needs.")
                        .foregroundStyle(.secondary)
                }
            }

            if let warmUp = currentWorkout.prescription["warm_up"]?.arrayValue, !warmUp.isEmpty {
                Section("Warm-Up") {
                    ForEach(Array(warmUp.enumerated()), id: \.offset) { _, item in
                        Text(item.displayString)
                    }
                }
            }

            if let blocks = currentWorkout.prescription["blocks"]?.arrayValue, !blocks.isEmpty {
                Section("Main Set") {
                    ForEach(Array(blocks.enumerated()), id: \.offset) { _, block in
                        if let dict = block.objectValue {
                            BlockRow(block: dict, library: library)
                        }
                    }
                }
            }

            if let conditioning = currentWorkout.prescription["conditioning"]?.objectValue {
                Section("Conditioning") {
                    ConditioningView(conditioning: conditioning, library: library)
                }
            }

            if let coolDown = currentWorkout.prescription["cool_down"]?.arrayValue, !coolDown.isEmpty {
                Section("Cool-Down") {
                    ForEach(Array(coolDown.enumerated()), id: \.offset) { _, item in
                        Text(item.displayString)
                    }
                }
            }

            if let completedAt = currentWorkout.completedAt {
                Section("Logged") {
                    Text("Completed \(completedAt.formatted(date: .abbreviated, time: .shortened))")
                    if let notes = currentWorkout.loggedResult?["notes"]?.stringValue, !notes.isEmpty {
                        Text(notes).foregroundStyle(.secondary)
                    }
                }
            } else {
                Section("Log this workout") {
                    TextField("Notes (how did it feel?)", text: $notes, axis: .vertical)
                    Button("Mark complete") {
                        Task { await viewModel.logWorkout(currentWorkout, notes: notes) }
                    }
                }
            }
        }
        .navigationTitle(currentWorkout.title)
        .navigationDestination(for: Exercise.self) { exercise in
            ExerciseDetailView(exercise: exercise)
        }
        .task { await library.loadIfNeeded() }
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
        if let hrLabel = hrTargetLabel { parts.append(hrLabel) }
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

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let linkedExercise {
                NavigationLink(value: linkedExercise) {
                    HStack {
                        Text(title).font(.body)
                        Image(systemName: "info.circle").font(.caption).foregroundStyle(.blue)
                    }
                }
            } else {
                Text(title).font(.body)
            }
            if !subtitleParts.isEmpty {
                Text(subtitleParts.joined(separator: " · "))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            if let detail {
                Text(detail)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
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
            }
            if let movements = conditioning["movements"]?.arrayValue {
                ForEach(Array(movements.enumerated()), id: \.offset) { _, movement in
                    Text("• \(movement.displayString)")
                }
            }
            if let options = conditioning["options"]?.arrayValue {
                ForEach(Array(options.enumerated()), id: \.offset) { _, option in
                    if let dict = option.objectValue {
                        BlockRow(block: dict, library: library)
                    }
                }
            }
        }
        .padding(.vertical, 2)
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
