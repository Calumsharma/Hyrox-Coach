import Foundation

struct StationReference: Codable, Identifiable {
    let slug: StationSlug
    let order: Int
    let name: String
    let distanceOrReps: String
    let primaryDemand: String
    let divisionLoads: [String: [String: Double]]

    var id: String { slug.rawValue }

    enum CodingKeys: String, CodingKey {
        case slug, order, name
        case distanceOrReps = "distance_or_reps"
        case primaryDemand = "primary_demand"
        case divisionLoads = "division_loads"
    }
}
