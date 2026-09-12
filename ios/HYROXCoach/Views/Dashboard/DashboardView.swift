import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @StateObject private var viewModel = TrainingViewModel()
    @State private var showingNewBlock = false
    @State private var showingSettings = false

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading && viewModel.block == nil {
                    ProgressView().tint(Theme.safetyOrange)
                } else if let block = viewModel.block {
                    blockView(block)
                } else {
                    emptyState
                }
            }
            .tint(Theme.safetyOrange)
            .background(Theme.background)
            .navigationTitle("Your Block")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showingSettings = true
                    } label: {
                        Image(systemName: "gearshape.fill")
                    }
                }
            }
            .sheet(isPresented: $showingNewBlock) {
                NewBlockView(viewModel: viewModel)
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView()
            }
            .task {
                await viewModel.loadCurrentBlock()
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 20) {
            ZStack {
                RoundedRectangle(cornerRadius: 4, style: .continuous)
                    .fill(Theme.surface)
                    .overlay(RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(Theme.hairline, lineWidth: 1))
                    .frame(width: 88, height: 88)
                Image(systemName: "figure.strengthtraining.functional")
                    .font(.system(size: 40))
                    .foregroundStyle(Theme.safetyOrange)
            }
            VStack(spacing: 6) {
                Text("No active training block")
                    .font(.title3.bold())
                    .foregroundStyle(Theme.textPrimary)
                Text("Set a goal event and we'll build a periodized program around your weaknesses.")
                    .font(.subheadline)
                    .foregroundStyle(Theme.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            Button {
                showingNewBlock = true
            } label: {
                Label("Start a training block", systemImage: "sparkles")
                    .font(Theme.labelMono(14, weight: .black))
                    .tracking(0.5)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .strokeBorder(Theme.hairline, lineWidth: 1.5)
                    )
            }
            .buttonStyle(.plain)
            .foregroundStyle(Theme.textPrimary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.background)
    }

    private func blockView(_ block: TrainingBlock) -> some View {
        List {
            BlockHeaderView(block: block)

            Section {
                ForEach(block.weeks) { week in
                    NavigationLink(value: week) {
                        WeekRow(week: week)
                    }
                    .listRowInsets(EdgeInsets(top: 0, leading: 18, bottom: 0, trailing: 18))
                    .listRowSeparatorTint(Theme.hairline)
                    .listRowBackground(week.weekNumber == currentWeekNumber(block) ? Theme.surface : Color.clear)
                }
            } header: {
                Text("WEEKS")
                    .font(Theme.labelMono(10))
                    .tracking(1.4)
                    .foregroundStyle(Theme.textSecondary)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .navigationDestination(for: TrainingWeek.self) { week in
            WeekDetailView(week: week, viewModel: viewModel)
        }
    }

    private func currentWeekNumber(_ block: TrainingBlock) -> Int {
        let daysElapsed = Calendar.current.dateComponents([.day], from: block.startDate, to: Date()).day ?? 0
        return max(1, min(block.lengthWeeks, daysElapsed / 7 + 1))
    }
}

private struct WeekRow: View {
    let week: TrainingWeek

    private var completedCount: Int {
        week.workouts.filter { $0.completedAt != nil }.count
    }

    var body: some View {
        HStack(spacing: 12) {
            Text(String(format: "W%02d", week.weekNumber))
                .font(Theme.dataMono(14, weight: .bold))
                .foregroundStyle(Theme.textPrimary)
                .frame(width: 46, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                Text(week.phase.uppercased())
                    .font(Theme.labelMono(10))
                    .tracking(1)
                    .foregroundStyle(PhaseStyle.color(for: week.phase))

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(Theme.hairline)
                        Capsule()
                            .fill(PhaseStyle.color(for: week.phase))
                            .frame(width: max(2, geo.size.width * week.actualIntensity))
                    }
                }
                .frame(height: 3)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text("\(Int(week.actualIntensity * 100))%")
                    .font(Theme.dataMono(13, weight: .semibold))
                    .foregroundStyle(Theme.textPrimary)
                Text("\(completedCount)/\(week.workouts.count)")
                    .font(Theme.dataMono(10))
                    .foregroundStyle(Theme.textSecondary)
            }

            Image(systemName: "chevron.right")
                .font(.caption2.weight(.bold))
                .foregroundStyle(Theme.textSecondary)
        }
        .padding(.vertical, 12)
    }
}
