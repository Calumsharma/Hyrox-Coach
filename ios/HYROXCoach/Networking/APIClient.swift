import Foundation

enum APIError: Error, LocalizedError {
    case unauthorized
    case server(String)
    case decoding(Error)

    var errorDescription: String? {
        switch self {
        case .unauthorized: return "Session expired. Please sign in again."
        case .server(let message): return message
        case .decoding: return "Couldn't read the server's response."
        }
    }
}

final class APIClient {
    static let shared = APIClient()

    /// The Simulator shares the host Mac's network stack, so localhost reaches the
    /// backend directly. Point this at a real host once the backend is deployed.
    var baseURL = URL(string: "http://127.0.0.1:8000")!

    private let session = URLSession.shared

    private lazy var decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .formatted(Self.dateOnlyFormatter)
        return decoder
    }()

    private lazy var encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .formatted(Self.dateOnlyFormatter)
        return encoder
    }()

    private static let dateOnlyFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter
    }()

    private init() {}

    func devLogin(email: String) async throws -> (token: String, athleteId: String) {
        struct Request: Codable { let email: String }
        struct Response: Codable {
            let accessToken: String
            let athleteId: String
            enum CodingKeys: String, CodingKey {
                case accessToken = "access_token"
                case athleteId = "athlete_id"
            }
        }
        let response: Response = try await request("/auth/dev-login", method: "POST", body: Request(email: email), authorized: false)
        return (response.accessToken, response.athleteId)
    }

    func getMe() async throws -> Athlete {
        try await request("/athletes/me", method: "GET")
    }

    func completeOnboarding(_ payload: AthleteOnboarding) async throws -> Athlete {
        try await request("/athletes/me/onboarding", method: "PUT", body: payload)
    }

    func suggestExperienceTier(bestSoloTimeSeconds: Int?, raceCount: Int) async throws -> ExperienceTier {
        struct Request: Codable {
            let bestSoloTimeSeconds: Int?
            let raceCount: Int
            enum CodingKeys: String, CodingKey {
                case bestSoloTimeSeconds = "best_solo_time_seconds"
                case raceCount = "race_count"
            }
        }
        struct Response: Codable {
            let suggestedTier: ExperienceTier
            enum CodingKeys: String, CodingKey { case suggestedTier = "suggested_tier" }
        }
        let response: Response = try await request(
            "/athletes/tier-suggestion", method: "POST",
            body: Request(bestSoloTimeSeconds: bestSoloTimeSeconds, raceCount: raceCount),
            authorized: false
        )
        return response.suggestedTier
    }

    func addPastResult(_ payload: PastResultCreate) async throws -> PastHyroxResult {
        try await request("/athletes/me/past-results", method: "POST", body: payload)
    }

    func listStations() async throws -> [StationReference] {
        try await request("/stations", method: "GET")
    }

    func listExercises() async throws -> [Exercise] {
        try await request("/exercises", method: "GET", authorized: false)
    }

    func createTrainingBlock(_ payload: TrainingBlockCreate) async throws -> TrainingBlock {
        try await request("/training-blocks", method: "POST", body: payload)
    }

    func getCurrentBlock() async throws -> TrainingBlock? {
        try await request("/training-blocks/current", method: "GET")
    }

    func logWorkout(id: String, loggedResult: [String: JSONValue]) async throws -> Workout {
        struct Request: Codable { let loggedResult: [String: JSONValue]
            enum CodingKeys: String, CodingKey { case loggedResult = "logged_result" }
        }
        return try await request("/workouts/\(id)/log", method: "PATCH", body: Request(loggedResult: loggedResult))
    }

    // MARK: - Core request plumbing

    private func request<Response: Decodable>(
        _ path: String,
        method: String,
        authorized: Bool = true
    ) async throws -> Response {
        try await request(path, method: method, body: Optional<Empty>.none, authorized: authorized)
    }

    private func request<Body: Encodable, Response: Decodable>(
        _ path: String,
        method: String,
        body: Body?,
        authorized: Bool = true
    ) async throws -> Response {
        var urlRequest = URLRequest(url: baseURL.appendingPathComponent(path))
        urlRequest.httpMethod = method

        if authorized {
            guard let token = KeychainStore.load() else { throw APIError.unauthorized }
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body {
            urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
            urlRequest.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: urlRequest)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.server("No response from server")
        }
        if httpResponse.statusCode == 401 {
            throw APIError.unauthorized
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = (try? decoder.decode(ErrorDetail.self, from: data))?.detail ?? "Server error (\(httpResponse.statusCode))"
            throw APIError.server(message)
        }

        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private struct Empty: Encodable {}
    private struct ErrorDetail: Decodable { let detail: String }
}
