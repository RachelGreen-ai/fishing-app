import Foundation

enum InferenceService {
    static let engineInfo = IdentificationEngineInfo(
        name: "Local Evidence Scorer",
        version: "0.2",
        family: "Heuristic, not Core ML",
        summary: "Ranks the local species catalog from user-visible traits plus GPS/date/water context. A Core ML/Vision adapter is ready for FishSpeciesClassifier.mlmodel, but no trained model is bundled yet.",
        limitations: [
            "No bundled fish species Core ML model is currently in the iOS app.",
            "Photo pixels are not converted into species labels yet.",
            "Range, season, water, and habitat are supporting signals only."
        ]
    )

    static func identify(_ evidence: FishEvidence) -> IdentificationResult {
        let month = Calendar.current.component(.month, from: evidence.date)
        let visualSignalCount = visualSignals(in: evidence)
        let scored = SpeciesCatalog.all
            .map { score(species: $0, evidence: evidence, month: month) }
            .sorted { $0.score > $1.score }

        let top = scored[0]
        let runnerUp = scored.dropFirst().first
        let qualityPenalty = max(0, 72 - evidence.photoQuality) * 35 / 100
        let gap = runnerUp.map { top.score - $0.score } ?? 22
        let ambiguityPenalty = max(0, 20 - gap) * 45 / 100
        var confidence = min(96, max(12, top.score - qualityPenalty - ambiguityPenalty))

        if !evidence.hasPhoto {
            confidence = min(confidence, 32)
        } else if visualSignalCount == 0 {
            confidence = min(confidence, 38)
        } else if visualSignalCount == 1 {
            confidence = min(confidence, 58)
        } else if gap < 8 {
            confidence = min(confidence, 68)
        }

        let isAbstained = shouldAbstain(confidence: confidence, evidence: evidence, visualSignalCount: visualSignalCount)
        let tier = isAbstained ? .notEnoughEvidence : confidenceTier(confidence: confidence, evidence: evidence)
        let alternativeCap = isAbstained ? 48 : 88
        let alternatives = scored.dropFirst().prefix(3).map { candidate in
            SpeciesCandidate(
                species: candidate.species,
                confidence: min(alternativeCap, max(10, candidate.score - qualityPenalty)),
                reasons: Array(candidate.reasons.prefix(3))
            )
        }

        return IdentificationResult(
            modelInfo: engineInfo,
            tier: tier,
            confidence: confidence,
            visualSignalCount: visualSignalCount,
            isAbstained: isAbstained,
            primary: top.species,
            alternatives: alternatives,
            evidenceRows: evidenceRows(top: top.species, evidence: evidence, month: month),
            guidance: guidance(evidence: evidence, top: top.species, runnerUp: runnerUp?.species),
            reviewRecommended: tier != .likely || top.species.caution.localizedCaseInsensitiveContains("regulated")
        )
    }

    private static func score(species: Species, evidence: FishEvidence, month: Int) -> (species: Species, score: Int, reasons: [String]) {
        var score = 25
        var reasons: [String] = []
        let traits = traitValues(in: evidence)

        for (key, value) in traits where !value.isEmpty {
            if species.traits[key]?.contains(value) == true {
                score += visualWeight(for: key)
                reasons.append("\(label(key)) matches")
            } else {
                score -= max(4, visualWeight(for: key) / 2)
            }
        }

        if !evidence.waterType.isEmpty {
            if species.waterTypes.contains(evidence.waterType) {
                score += 10
                reasons.append("water type supports it")
            } else {
                score -= 18
            }
        }

        if !evidence.region.isEmpty {
            if species.regions.contains(evidence.region) {
                score += 8
                reasons.append("regional range supports it")
            } else {
                score -= 12
            }
        }

        if !evidence.habitat.isEmpty {
            if species.habitats.contains(evidence.habitat) {
                score += 6
                reasons.append("habitat supports it")
            } else {
                score -= 5
            }
        }

        if species.peakMonths.contains(month) {
            score += 4
            reasons.append("season supports it")
        } else {
            score -= 1
        }

        if evidence.photoQuality >= 80 {
            score += 4
        }

        return (species, score, reasons)
    }

    private static func evidenceRows(top: Species, evidence: FishEvidence, month: Int) -> [EvidenceRow] {
        let traitValues = traitValues(in: evidence)
        let matched = traitValues.compactMap { key, value in
            !value.isEmpty && top.traits[key]?.contains(value) == true ? label(key) : nil
        }
        let missing = traitValues.compactMap { key, value in
            value.isEmpty ? label(key) : nil
        }

        return [
            EvidenceRow(label: "Model", value: "\(engineInfo.name) \(engineInfo.version)"),
            EvidenceRow(label: "Visual", value: matched.isEmpty ? "No species image ML yet; visible traits are needed" : "Matches \(matched.joined(separator: ", "))"),
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

        if visualSignals(in: evidence) == 0 {
            items.append("This build needs visible traits because no Core ML species classifier is bundled yet.")
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

    private static func shouldAbstain(confidence: Int, evidence: FishEvidence, visualSignalCount: Int) -> Bool {
        if !evidence.hasPhoto || evidence.photoQuality < 40 {
            return true
        }

        if visualSignalCount == 0 {
            return true
        }

        return confidence < 45
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

    private static func traitValues(in evidence: FishEvidence) -> [(String, String)] {
        [
            ("bodyShape", evidence.bodyShape),
            ("mouth", evidence.mouth),
            ("markings", evidence.markings),
            ("finTail", evidence.finTail),
            ("color", evidence.color)
        ]
    }

    private static func visualSignals(in evidence: FishEvidence) -> Int {
        traitValues(in: evidence).filter { !$0.1.isEmpty }.count
    }

    private static func visualWeight(for key: String) -> Int {
        [
            "bodyShape": 10,
            "mouth": 16,
            "markings": 16,
            "finTail": 10,
            "color": 7
        ][key] ?? 8
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
