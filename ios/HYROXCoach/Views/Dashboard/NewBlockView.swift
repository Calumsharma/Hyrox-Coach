import SwiftUI

struct NewBlockView: View {
    @ObservedObject var viewModel: TrainingViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var lengthWeeks: Int? = 8
    @State private var startDate = Date()
    @State private var goalEventDate = Date().addingTimeInterval(60 * 60 * 24 * 56)
    @State private var goalTime: Int?
    @State private var discipline: Discipline = .hyrox

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Event", selection: $discipline) {
                        ForEach(Discipline.allCases) { discipline in
                            Text(discipline.isSupported ? discipline.displayName : "\(discipline.displayName) (coming soon)")
                                .tag(discipline)
                        }
                    }
                } footer: {
                    if !discipline.isSupported {
                        Text("We only have a real, coach-built program for HYROX right now — other events are on the roadmap.")
                    }
                }
                .listRowBackground(Theme.concreteDark)

                Section {
                    WheelIntPicker(label: "Block Length", value: $lengthWeeks, range: 4...20, unit: "wks", defaultValue: 8)
                    DatePicker("Start date", selection: $startDate, displayedComponents: .date)
                    DatePicker("Goal event date", selection: $goalEventDate, displayedComponents: .date)
                    WheelTimePicker(label: "Goal Race Time", seconds: $goalTime, defaultSeconds: 4500, maxMinutes: 180)
                }
                .listRowBackground(Theme.concreteDark)

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                        .listRowBackground(Theme.concreteDark)
                }
            }
            .tint(Theme.safetyOrange)
            .scrollContentBackground(.hidden)
            .background(Theme.concrete)
            .listRowSeparatorTint(Theme.stone.opacity(0.35))
            .navigationTitle("New Training Block")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task {
                            await viewModel.createBlock(
                                lengthWeeks: lengthWeeks ?? 8,
                                startDate: startDate,
                                goalEventDate: goalEventDate,
                                goalTimeSeconds: goalTime ?? 4500,
                                discipline: discipline
                            )
                            if viewModel.errorMessage == nil { dismiss() }
                        }
                    } label: {
                        if viewModel.isLoading {
                            ProgressView().tint(Theme.safetyOrange)
                        } else {
                            Text("Create").fontWeight(.black)
                        }
                    }
                    .disabled(viewModel.isLoading)
                }
            }
        }
    }
}
