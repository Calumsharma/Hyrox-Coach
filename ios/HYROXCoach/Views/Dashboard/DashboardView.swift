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
                    ProgressView()
                } else if let block = viewModel.block {
                    blockView(block)
                } else {
                    emptyState
                }
            }
            .tint(Theme.safetyOrange)
            .background(Theme.concrete)
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
                    .fill(Theme.ink)
                    .frame(width: 88, height: 88)
                Image(systemName: "figure.strengthtraining.functional")
                    .font(.system(size: 40))
                    .foregroundStyle(Theme.safetyOrange)
            }
            VStack(spacing: 6) {
                Text("No active training block")
                    .font(.title3.bold())
                    .foregroundStyle(Theme.ink)
                Text("Set a goal event and we'll build a periodized program around your weaknesses.")
                    .font(.subheadline)
                    .foregroundStyle(Theme.mutedInk)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            Button {
                showingNewBlock = true
            } label: {
                Label("Start a training block", systemImage: "sparkles")
                    .font(.system(size: 15, weight: .black))
                    .tracking(0.5)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .strokeBorder(Theme.ink, lineWidth: 2)
                    )
            }
            .buttonStyle(.plain)
            .foregroundStyle(Theme.ink)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.concrete)
    }

    private func blockView(_ block: TrainingBlock) -> some View {
        List {
            BlockHeaderView(block: block)

            Section {
                ForEach(block.weeks) { week in
                    NavigationLink(value: week) {
                        WeekCard(week: week)
                    }
                    .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
                }
            } header: {
                Text("Weeks")
                    .foregroundStyle(Theme.mutedInk)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Theme.concrete)
        .navigationDestination(for: TrainingWeek.self) { week in
            WeekDetailView(week: week, viewModel: viewModel)
        }
    }
}

private struct WeekCard: View {
    let week: TrainingWeek

    private var completedCount: Int {
        week.workouts.filter { $0.completedAt != nil }.count
    }

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(PhaseStyle.color(for: week.phase).opacity(0.15))
                Image(systemName: PhaseStyle.icon(for: week.phase))
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(PhaseStyle.color(for: week.phase))
            }
            .frame(width: 48, height: 48)

            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("Week \(week.weekNumber)")
                        .font(.headline)
                        .foregroundStyle(Theme.ink)
                    Text(week.phase.capitalized)
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(PhaseStyle.color(for: week.phase).opacity(0.15), in: Capsule())
                        .foregroundStyle(PhaseStyle.color(for: week.phase))
                }

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(Theme.stone.opacity(0.3))
                        Capsule()
                            .fill(PhaseStyle.color(for: week.phase))
                            .frame(width: geo.size.width * week.actualIntensity)
                    }
                }
                .frame(height: 6)

                Text("\(completedCount)/\(week.workouts.count) logged  ·  \(Int(week.actualIntensity * 100))% intensity")
                    .font(.caption)
                    .foregroundStyle(Theme.mutedInk)
            }

            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Theme.mutedInk)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .fill(Theme.concreteDark)
                .overlay(RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(Theme.stone.opacity(0.35), lineWidth: 1))
        )
    }
}
