import Foundation

struct Exercise: Codable, Identifiable, Hashable {
    let slug: String
    let name: String
    let category: String
    let description: String
    let cues: [String]
    let videoURL: String?
    let videoSource: String

    var id: String { slug }

    enum CodingKeys: String, CodingKey {
        case slug, name, category, description, cues
        case videoURL = "video_url"
        case videoSource = "video_source"
    }
}
