import Foundation

@MainActor
final class ExerciseLibraryStore: ObservableObject {
    @Published private(set) var exercisesBySlug: [String: Exercise] = [:]
    private var hasLoaded = false

    func loadIfNeeded() async {
        guard !hasLoaded else { return }
        hasLoaded = true
        guard let exercises = try? await APIClient.shared.listExercises() else { return }
        exercisesBySlug = Dictionary(uniqueKeysWithValues: exercises.map { ($0.slug, $0) })
    }

    func exercise(forMovementSlug slug: String) -> Exercise? {
        exercisesBySlug[slug]
    }
}
