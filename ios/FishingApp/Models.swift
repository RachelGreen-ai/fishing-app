import Foundation

enum ConfidenceTier: String {
    case likely = "Likely"
    case possible = "Possible"
    case uncertain = "Uncertain"
    case notEnoughEvidence = "Not Enough Evidence"
    case userCorrected = "User Corrected"
}

struct Species: Identifiable, Hashable {
    let id: String
    let commonName: String
    let scientificName: String
    let family: String
    let waterTypes: Set<String>
    let regions: Set<String>
    let habitats: Set<String>
    let peakMonths: Set<Int>
    let traits: [String: Set<String>]
    let lookalikeGroup: String
    let caution: String
}

struct FishEvidence {
    var hasPhoto: Bool
    var photoQuality: Int
    var region: String
    var waterType: String
    var habitat: String
    var date: Date
    var waterbody: String
    var bodyShape: String
    var mouth: String
    var markings: String
    var finTail: String
    var color: String
    var consent: PhotoConsent
}

struct IdentificationEngineInfo {
    let name: String
    let version: String
    let family: String
    let summary: String
    let limitations: [String]
}

struct PhotoConsent {
    var identification: Bool = true
    var trainingReview: Bool = false
    var retentionPolicy: String = "24-hours"
}

struct ImageModelPrediction: Identifiable, Hashable {
    let id = UUID()
    let label: String
    let confidence: Double

    var confidencePercent: Int {
        Int((confidence * 100).rounded())
    }
}

struct SpeciesCandidate: Identifiable {
    let id = UUID()
    let species: Species
    let confidence: Int
    let reasons: [String]
}

struct IdentificationResult {
    let modelInfo: IdentificationEngineInfo
    let tier: ConfidenceTier
    let confidence: Int
    let visualSignalCount: Int
    let isAbstained: Bool
    var primary: Species
    let alternatives: [SpeciesCandidate]
    let evidenceRows: [EvidenceRow]
    let guidance: [String]
    let reviewRecommended: Bool
}

struct EvidenceRow: Identifiable {
    let id = UUID()
    let label: String
    let value: String
}

struct CatchLogItem: Identifiable {
    let id = UUID()
    let speciesName: String
    let status: String
    let date: Date
    let waterbody: String
    let confidence: Int
}
