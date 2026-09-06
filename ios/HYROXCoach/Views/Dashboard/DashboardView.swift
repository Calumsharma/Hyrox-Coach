import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @StateObject private var viewModel = TrainingViewModel()
    @State private var showingNewBlock = false

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
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Your Block")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Sign out") { auth.signOut() }
                }
            }
            .sheet(isPresented: $showingNewBlock) {
                NewBlockView(viewModel: viewModel)
            }
            .task {
                await viewModel.loadCurrentBlock()
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 20) {
            ZStack {
                Circle()
                    .fill(LinearGradient(colors: [.orange, .red], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .frame(width: 96, height: 96)
                    .opacity(0.15)
                Image(systemName: "figure.strengthtraining.functional")
                    .font(.system(size: 44))
                    .foregroundStyle(
                        LinearGradient(colors: [.orange, .red], startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
            }
            VStack(spacing: 6) {
                Text("No active training block")
                    .font(.title3.bold())
                Text("Set a goal event and we'll build a periodized program around your weaknesses.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            Button {
                showingNewBlock = true
            } label: {
                Label("Start a training block", systemImage: "sparkles")
                    .font(.headline)
                    .padding(.horizontal, 8)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .tint(.orange)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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
            }
        }
        .listStyle(.plain)
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
                    Text(week.phase.capitalized)
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(PhaseStyle.color(for: week.phase).opacity(0.15), in: Capsule())
                        .foregroundStyle(PhaseStyle.color(for: week.phase))
                }

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(Color.secondary.opacity(0.15))
                        Capsule()
                            .fill(PhaseStyle.color(for: week.phase))
                            .frame(width: geo.size.width * week.actualIntensity)
                    }
                }
                .frame(height: 6)

                Text("\(completedCount)/\(week.workouts.count) logged  ·  \(Int(week.actualIntensity * 100))% intensity")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.tertiary)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(.secondarySystemGroupedBackground))
        )
    }
}
