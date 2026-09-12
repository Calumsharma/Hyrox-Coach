import SwiftUI

struct BlockHeaderView: View {
    let block: TrainingBlock

    private var daysToEvent: Int? {
        guard let goalDate = block.goalEventDate else { return nil }
        return Calendar.current.dateComponents([.day], from: Date(), to: goalDate).day
    }

    private var completedWeeks: Int {
        block.weeks.filter { week in
            week.workouts.allSatisfy { $0.completedAt != nil || $0.workoutType == .rest }
        }.count
    }

    private var progress: Double {
        guard block.lengthWeeks > 0 else { return 0 }
        return Double(completedWeeks) / Double(block.lengthWeeks)
    }

    var body: some View {
        VStack(spacing: 20) {
            HStack(alignment: .center, spacing: 20) {
                ZStack {
                    Circle()
                        .stroke(Color.secondary.opacity(0.15), lineWidth: 10)
                    Circle()
                        .trim(from: 0, to: progress)
                        .stroke(Theme.safetyOrange, style: StrokeStyle(lineWidth: 10, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                    VStack(spacing: 0) {
                        Text("\(completedWeeks)/\(block.lengthWeeks)")
                            .font(.headline.monospacedDigit())
                        Text("weeks")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(width: 84, height: 84)

                VStack(alignment: .leading, spacing: 6) {
                    if let days = daysToEvent {
                        Text(days >= 0 ? "\(days) days to race day" : "Race day has passed")
                            .font(.title3.bold())
                    } else {
                        Text("Training block")
                            .font(.title3.bold())
                    }
                    if let goalTime = block.goalTimeSeconds {
                        Label(Self.formatTime(goalTime), systemImage: "flag.checkered")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
            }

            if !block.targetWeaknesses.isEmpty {
                HStack(spacing: 8) {
                    ForEach(block.targetWeaknesses, id: \.self) { slug in
                        WeaknessChip(stationSlug: slug)
                    }
                    Spacer()
                }
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .fill(Theme.concreteDark)
                .overlay(RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(Theme.stone.opacity(0.4), lineWidth: 1))
        )
        .listRowInsets(EdgeInsets())
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
        .padding(.vertical, 4)
    }

    static func formatTime(_ seconds: Int) -> String {
        String(format: "%d:%02d:%02d goal", seconds / 3600, (seconds % 3600) / 60, seconds % 60)
    }
}

private struct WeaknessChip: View {
    let stationSlug: String

    private var station: StationSlug? { StationSlug(rawValue: stationSlug) }

    var body: some View {
        Label(station?.displayName ?? stationSlug, systemImage: "target")
            .font(.caption.weight(.bold))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Theme.ink, in: RoundedRectangle(cornerRadius: 3))
            .foregroundStyle(Theme.safetyOrange)
    }
}
