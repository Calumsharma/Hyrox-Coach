import SwiftUI

struct ExerciseDetailView: View {
    let exercise: Exercise

    var body: some View {
        List {
            Section {
                Text(exercise.description)
                    .foregroundStyle(Theme.ink)
            }
            .listRowBackground(Theme.concreteDark)

            if !exercise.cues.isEmpty {
                Section("Coaching Cues") {
                    ForEach(exercise.cues, id: \.self) { cue in
                        Label(cue, systemImage: "checkmark.circle")
                            .foregroundStyle(Theme.ink)
                    }
                }
                .listRowBackground(Theme.concreteDark)
            }

            Section {
                if exercise.videoSource == "none" || exercise.videoURL == nil {
                    Label("Video coming soon", systemImage: "video.slash")
                        .foregroundStyle(Theme.mutedInk)
                } else if let url = exercise.videoURL, let link = URL(string: url) {
                    Link(destination: link) {
                        Label("Watch demo", systemImage: "play.circle.fill")
                    }
                    .tint(Theme.safetyOrange)
                }
            }
            .listRowBackground(Theme.concreteDark)
        }
        .scrollContentBackground(.hidden)
        .background(Theme.concrete)
        .listRowSeparatorTint(Theme.stone.opacity(0.35))
        .navigationTitle(exercise.name)
    }
}
