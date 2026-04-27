import Foundation

enum InferenceService {
    static func identify(_ evidence: FishEvidence) -> IdentificationResult {
        let month = Calendar.current.component(.month, from: evidence.date)
        let scored = SpeciesCatalog.all
            .map { score(species: $0, evidence: evidence, month: month) }
            .sorted { $0.score > $1.score }

        let top = scored[0]
        let runnerUp = scored.dropFirst().first
        let qualityPenalty = max(0, 72 - evidence.photoQuality) * 35 / 100
        let gap = runnerUp.map { top.score - $0.score } ?? 22
        let ambiguityPenalty = max(0, 22 - gap) * 45 / 100
        let rawConfidence = min(96, max(18, top.score - qualityPenalty - ambiguityPenalty))
        let confidence = evidence.hasPhoto ? rawConfidence : min(rawConfidence, 42)
        let tier = confidenceTier(confidence: confidence, evidence: evidence)
        let alternativeCap = evidence.hasPhoto ? 88 : 42
        let alternatives = scored.dropFirst().prefix(3).map { candidate in
            SpeciesCandidate(
                species: candidate.species,
                confidence: min(alternativeCap, max(10, candidate.score - qualityPenalty)),
                reasons: Array(candidate.reasons.prefix(3))
            )
        }

        return IdentificationResult(
            tier: tier,
            confidence: confidence,
            primary: top.species,
            alternatives: alternatives,
            evidenceRows: evidenceRows(top: top.species, evidence: evidence, month: month),
            guidance: guidance(evidence: evidence, top: top.species, runnerUp: runnerUp?.species),
            reviewRecommended: tier != .likely || top.species.caution.localizedCaseInsensitiveContains("regulated")
        )
    }

    private static func score(species: Species, evidence: FishEvidence, month: Int) -> (species: Species, score: Int, reasons: [String]) {
        var score = 34
        var reasons: [String] = []
        let traits = [
            "bodyShape": evidence.bodyShape,
            "mouth": evidence.mouth,
            "markings": evidence.markings,
            "finTail": evidence.finTail,
            "color": evidence.color
        ]

        for (key, value) in traits where !value.isEmpty {
            if species.traits[key]?.contains(value) == true {
                score += key == "mouth" || key == "markings" ? 13 : 10
                reasons.append("\(label(key)) matches")
            } else {
                score -= key == "mouth" || key == "markings" ? 7 : 5
            }
        }

        if !evidence.waterType.isEmpty {
            if species.waterTypes.contains(evidence.waterType) {
                score += 12
                reasons.append("water type supports it")
            } else {
                score -= 20
            }
        }

        if !evidence.region.isEmpty {
            if species.regions.contains(evidence.region) {
                score += 9
                reasons.append("regional range supports it")
            } else {
                score -= 10
            }
        }

        if !evidence.habitat.isEmpty {
            if species.habitats.contains(evidence.habitat) {
                score += 8
                reasons.append("habitat supports it")
            } else {
                score -= 6
            }
        }

        if species.peakMonths.contains(month) {
            score += 5
            reasons.append("season supports it")
        } else {
            score -= 2
        }

        if evidence.photoQuality >= 80 {
            score += 5
        }

        return (species, score, reasons)
    }

    private static func evidenceRows(top: Species, evidence: FishEvidence, month: Int) -> [EvidenceRow] {
        let traitValues = [
            "bodyShape": evidence.bodyShape,
            "mouth": evidence.mouth,
            "markings": evidence.markings,
            "finTail": evidence.finTail,
            "color": evidence.color
        ]
        let matched = traitValues.compactMap { key, value in
            !value.isEmpty && top.traits[key]?.contains(value) == true ? label(key) : nil
        }
        let missing = traitValues.compactMap { key, value in
            value.isEmpty ? label(key) : nil
        }

        return [
            EvidenceRow(label: "Visual", value: matched.isEmpty ? "Few visual traits supplied" : "Matches \(matched.joined(separator: ", "))"),
            EvidenceRow(label: "Location", value: locationText(top: top, evidence: evidence)),
            EvidenceRow(label: "Season", value: top.peakMonths.contains(month) ? "Date is within common angling months" : "Date is not a strong seasonal signal"),
            EvidenceRow(label: "Missing", value: missing.isEmpty ? "No major trait gaps" : missing.joined(separator: ", ")),
            EvidenceRow(label: "Caution", value: top.caution)
        ]
    }

    private static func guidance(evidence: FishEvidence, top: Species, runnerUp: Species?) -> [String] {
        var items: [String] = []

        if !evidence.hasPhoto || evidence.photoQuality < 58 {
            items.append("Retake with the full fish in frame and sharper side detail.")
        }

        if evidence.markings.isEmpty {
            items.append("Add a side shot showing bars, stripes, spots, or mottling.")
        }

        if evidence.mouth.isEmpty {
            items.append("Add a close view of the jaw and mouth position.")
        }

        if let runnerUp, runnerUp.lookalikeGroup == top.lookalikeGroup {
            items.append("Compare against \(runnerUp.commonName); this is a known lookalike group.")
        }

        if evidence.region.isEmpty || evidence.waterType.isEmpty {
            items.append("Add water type and region before using this for harvest decisions.")
        }

        return Array(Set(items)).prefix(4).map { $0 }
    }

    private static func confidenceTier(confidence: Int, evidence: FishEvidence) -> ConfidenceTier {
        if !evidence.hasPhoto || evidence.photoQuality < 40 {
            return .notEnoughEvidence
        }

        if confidence >= 82 { return .likely }
        if confidence >= 64 { return .possible }
        if confidence >= 45 { return .uncertain }
        return .notEnoughEvidence
    }

    private static func locationText(top: Species, evidence: FishEvidence) -> String {
        if evidence.region.isEmpty {
            return "No region supplied"
        }

        return top.regions.contains(evidence.region) ? "Region supports this species" : "Region is weak or outside normal range"
    }

    private static func label(_ key: String) -> String {
        [
            "bodyShape": "body shape",
            "mouth": "mouth",
            "markings": "markings",
            "finTail": "tail/fin",
            "color": "color"
        ][key] ?? key
    }
}
