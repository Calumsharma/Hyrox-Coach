import SwiftUI

struct WeekDetailView: View {
    let week: TrainingWeek
    @ObservedObject var viewModel: TrainingViewModel

    private var currentWeek: TrainingWeek {
        viewModel.block?.weeks.first(where: { $0.id == week.id }) ?? week
    }

    var body: some View {
        List {
            Section {
                HStack {
                    Label(currentWeek.phase.capitalized, systemImage: PhaseStyle.icon(for: currentWeek.phase))
                        .foregroundStyle(PhaseStyle.color(for: currentWeek.phase))
                        .font(.headline)
                    Spacer()
                    Text("Intensity \(Int(currentWeek.actualIntensity * 100))%")
                        .foregroundStyle(Theme.textSecondary)
                }
            }
            .listRowBackground(PhaseStyle.color(for: currentWeek.phase).opacity(0.12))

            Section {
                ForEach(currentWeek.workouts.sorted(by: { $0.dayOfWeek < $1.dayOfWeek })) { workout in
                    NavigationLink(value: workout) {
                        WorkoutRow(workout: workout)
                    }
                }
            }
            .listRowBackground(Theme.surface)
        }
        .tint(Theme.safetyOrange)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .listRowSeparatorTint(Theme.hairline)
        .navigationTitle("Week \(currentWeek.weekNumber)")
        .navigationDestination(for: Workout.self) { workout in
            WorkoutDetailView(workout: workout, viewModel: viewModel)
        }
    }
}

private struct WorkoutRow: View {
    let workout: Workout

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle().fill(workout.workoutType.tint.opacity(0.15))
                Image(systemName: workout.workoutType.icon)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(workout.workoutType.tint)
            }
            .frame(width: 38, height: 38)

            VStack(alignment: .leading, spacing: 2) {
                Text(workout.dayName).font(.caption).foregroundStyle(Theme.textSecondary)
                Text(workout.title).font(.body).foregroundStyle(Theme.textPrimary)
            }
            Spacer()
            if workout.completedAt != nil {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            }
        }
        .padding(.vertical, 2)
    }
}
