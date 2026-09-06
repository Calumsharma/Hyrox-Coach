import Foundation

@MainActor
final class AuthViewModel: ObservableObject {
    @Published var athlete: Athlete?
    @Published var isLoading = false
    @Published var errorMessage: String?

    var isSignedIn: Bool { athlete != nil }

    init() {
        if KeychainStore.load() != nil {
            Task { await refreshAthlete() }
        }
    }

    func signIn(email: String) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let (token, _) = try await APIClient.shared.devLogin(email: email)
            KeychainStore.save(token)
            athlete = try await APIClient.shared.getMe()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refreshAthlete() async {
        do {
            athlete = try await APIClient.shared.getMe()
        } catch {
            KeychainStore.clear()
            athlete = nil
        }
    }

    func completeOnboarding(_ payload: AthleteOnboarding) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            athlete = try await APIClient.shared.completeOnboarding(payload)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func signOut() {
        KeychainStore.clear()
        athlete = nil
    }
}
