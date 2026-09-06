import SwiftUI

struct NewBlockView: View {
    @ObservedObject var viewModel: TrainingViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var lengthWeeks = 8
    @State private var startDate = Date()
    @State private var goalEventDate = Date().addingTimeInterval(60 * 60 * 24 * 56)
    @State private var goalTime: Int?

    var body: some View {
        NavigationStack {
            Form {
                Stepper("Block length: \(lengthWeeks) weeks", value: $lengthWeeks, in: 4...20)
                DatePicker("Start date", selection: $startDate, displayedComponents: .date)
                DatePicker("Goal event date", selection: $goalEventDate, displayedComponents: .date)
                TimeInputField(label: "Goal race time", seconds: $goalTime)

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
            .navigationTitle("New Training Block")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Create") {
                        Task {
                            await viewModel.createBlock(
                                lengthWeeks: lengthWeeks,
                                startDate: startDate,
                                goalEventDate: goalEventDate,
                                goalTimeSeconds: goalTime ?? 4500
                            )
                            if viewModel.errorMessage == nil { dismiss() }
                        }
                    }
                    .disabled(viewModel.isLoading)
                }
            }
        }
    }
}
