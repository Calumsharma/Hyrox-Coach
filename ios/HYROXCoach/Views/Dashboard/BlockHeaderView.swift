import SwiftUI

struct BlockHeaderView: View {
    let block: TrainingBlock

    private var daysToEvent: Int? {
        guard let goalDate = block.goalEventDate else { return nil }
        return Calendar.current.dateComponents([.day], from: Date(), to: goalDate).day
    }

    private var currentWeekNumber: Int {
        let daysElapsed = Calendar.current.dateComponents([.day], from: block.startDate, to: Date()).day ?? 0
        return max(1, min(block.lengthWeeks, daysElapsed / 7 + 1))
    }

    private var currentWeek: TrainingWeek? {
        block.weeks.first(where: { $0.weekNumber == currentWeekNumber })
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("HYROX TRAINING BLOCK")
                    .font(Theme.labelMono(10))
                    .tracking(1.6)
                    .foregroundStyle(Theme.textSecondary)
                Spacer()
            }

            Text(String(format: "WEEK %02d / %02d", currentWeekNumber, block.lengthWeeks))
                .font(Theme.stencilTitle(24))
                .foregroundStyle(Theme.textPrimary)

            Rectangle().fill(Theme.hairline).frame(height: 1)

            HStack(spacing: 3) {
                ForEach(block.weeks) { week in
                    Rectangle()
                        .fill(tickColor(for: week))
                        .frame(height: 24)
                        .overlay(
                            week.weekNumber == currentWeekNumber
                                ? RoundedRectangle(cornerRadius: 1).stroke(Theme.safetyOrange, lineWidth: 1)
                                : nil
                        )
                }
            }

            HStack(spacing: 1) {
                statTile(
                    value: daysToEvent.map { $0 >= 0 ? "\($0)" : "—" } ?? "—",
                    label: "DAYS TO RACE"
                )
                statTile(
                    value: currentWeek.map { "\(Int($0.actualIntensity * 100))%" } ?? "—",
                    label: "ACTUAL INTENSITY"
                )
            }
            .background(Theme.hairline)
            .overlay(RoundedRectangle(cornerRadius: 2).stroke(Theme.hairline, lineWidth: 1))

            if let goalTime = block.goalTimeSeconds {
                Text(Self.formatTime(goalTime))
                    .font(Theme.dataMono(12))
                    .foregroundStyle(Theme.textSecondary)
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
        .padding(18)
        .background(Theme.surface)
        .listRowInsets(EdgeInsets())
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
    }

    private func tickColor(for week: TrainingWeek) -> Color {
        if week.weekNumber < currentWeekNumber { return Theme.safetyOrange }
        if week.weekNumber == currentWeekNumber { return Theme.safetyOrange.opacity(0.35) }
        return Theme.hairline
    }

    private func statTile(value: String, label: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(Theme.dataMono(22, weight: .bold))
                .foregroundStyle(Theme.textPrimary)
            Text(label)
                .font(Theme.labelMono(8.5))
                .tracking(1.1)
                .foregroundStyle(Theme.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Theme.surface)
    }

    static func formatTime(_ seconds: Int) -> String {
        String(format: "GOAL %d:%02d:%02d", seconds / 3600, (seconds % 3600) / 60, seconds % 60)
    }
}

private struct WeaknessChip: View {
    let stationSlug: String

    private var station: StationSlug? { StationSlug(rawValue: stationSlug) }

    var body: some View {
        Text((station?.displayName ?? stationSlug).uppercased())
            .font(Theme.labelMono(9.5, weight: .bold))
            .tracking(0.6)
            .padding(.horizontal, 9)
            .padding(.vertical, 6)
            .background(Theme.ink, in: RoundedRectangle(cornerRadius: 3))
            .foregroundStyle(Theme.safetyOrange)
    }
}
