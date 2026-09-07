import SwiftUI

struct ExerciseDetailView: View {
    let exercise: Exercise

    var body: some View {
        List {
            Section {
                Text(exercise.description)
            }

            if !exercise.cues.isEmpty {
                Section("Coaching Cues") {
                    ForEach(exercise.cues, id: \.self) { cue in
                        Label(cue, systemImage: "checkmark.circle")
                    }
                }
            }

            Section {
                if exercise.videoSource == "none" || exercise.videoURL == nil {
                    Label("Video coming soon", systemImage: "video.slash")
                        .foregroundStyle(.secondary)
                } else if let url = exercise.videoURL, let link = URL(string: url) {
                    Link(destination: link) {
                        Label("Watch demo", systemImage: "play.circle.fill")
                    }
                }
            }
        }
        .navigationTitle(exercise.name)
    }
}
