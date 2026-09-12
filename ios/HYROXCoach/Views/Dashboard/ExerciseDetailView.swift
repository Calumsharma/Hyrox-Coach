import SwiftUI

struct ExerciseDetailView: View {
    let exercise: Exercise

    var body: some View {
        List {
            Section {
                Text(exercise.description)
                    .foregroundStyle(Theme.textPrimary)
            }
            .listRowBackground(Theme.surface)

            if !exercise.cues.isEmpty {
                Section("Coaching Cues") {
                    ForEach(exercise.cues, id: \.self) { cue in
                        Label(cue, systemImage: "checkmark.circle")
                            .foregroundStyle(Theme.textPrimary)
                    }
                }
                .listRowBackground(Theme.surface)
            }

            Section {
                if exercise.videoSource == "none" || exercise.videoURL == nil {
                    Label("Video coming soon", systemImage: "video.slash")
                        .foregroundStyle(Theme.textSecondary)
                } else if let url = exercise.videoURL, let link = URL(string: url) {
                    Link(destination: link) {
                        Label("Watch demo", systemImage: "play.circle.fill")
                    }
                    .tint(Theme.safetyOrange)
                }
            }
            .listRowBackground(Theme.surface)
        }
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .listRowSeparatorTint(Theme.hairline)
        .navigationTitle(exercise.name)
    }
}
