import SwiftUI

struct AddPastRaceView: View {
    let onAdd: (PastResultCreate) -> Void
    @Environment(\.dismiss) private var dismiss

    @State private var eventDate = Date().addingTimeInterval(-60 * 60 * 24 * 90)
    @State private var division: Division = .openMen
    @State private var totalTime: Int?
    @State private var includeSplits = false
    @State private var splits: [StationSlug: Int] = [:]

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    DatePicker("Event date", selection: $eventDate, displayedComponents: .date)
                    Picker("Division", selection: $division) {
                        ForEach(Division.allCases) { division in
                            Text(division.displayName).tag(division)
                        }
                    }
                    TimeInputField(label: "Total time", seconds: $totalTime)
                }

                Section {
                    Toggle("Add station splits", isOn: $includeSplits.animation())
                    if includeSplits {
                        ForEach(StationSlug.allCases) { station in
                            TimeInputField(
                                label: station.displayName,
                                seconds: Binding(
                                    get: { splits[station] },
                                    set: { splits[station] = $0 }
                                )
                            )
                        }
                    }
                } footer: {
                    Text("Splits help us pinpoint exactly which stations are costing you time, instead of relying on your own guess.")
                }
            }
            .navigationTitle("Add a Past Race")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Add") {
                        guard let totalTime else { return }
                        let splitsPayload = includeSplits
                            ? Dictionary(uniqueKeysWithValues: splits.map { ($0.key.rawValue, $0.value) })
                            : [:]
                        onAdd(PastResultCreate(
                            eventDate: eventDate,
                            division: division,
                            totalTimeSeconds: totalTime,
                            stationSplitsSeconds: splitsPayload
                        ))
                        dismiss()
                    }
                    .disabled(totalTime == nil)
                }
            }
        }
    }
}
