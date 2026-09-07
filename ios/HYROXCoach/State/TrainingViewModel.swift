import Foundation

@MainActor
final class TrainingViewModel: ObservableObject {
    @Published var block: TrainingBlock?
    @Published var isLoading = false
    @Published var errorMessage: String?

    func loadCurrentBlock() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            block = try await APIClient.shared.getCurrentBlock()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createBlock(lengthWeeks: Int, startDate: Date, goalEventDate: Date, goalTimeSeconds: Int, discipline: Discipline = .hyrox) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            block = try await APIClient.shared.createTrainingBlock(
                TrainingBlockCreate(
                    lengthWeeks: lengthWeeks,
                    startDate: startDate,
                    goalEventDate: goalEventDate,
                    goalTimeSeconds: goalTimeSeconds,
                    discipline: discipline
                )
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func logWorkout(_ workout: Workout, notes: String) async {
        do {
            let updated = try await APIClient.shared.logWorkout(
                id: workout.id,
                loggedResult: ["notes": .string(notes)]
            )
            applyUpdatedWorkout(updated)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func applyUpdatedWorkout(_ updated: Workout) {
        guard var block else { return }
        block.weeks = block.weeks.map { week in
            var week = week
            week.workouts = week.workouts.map { $0.id == updated.id ? updated : $0 }
            return week
        }
        self.block = block
    }
}
