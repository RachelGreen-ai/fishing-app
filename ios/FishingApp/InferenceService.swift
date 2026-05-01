import Foundation

enum InferenceService {
    static let engineInfo = IdentificationEngineInfo(
        name: "Hybrid Local Identifier",
        version: "0.4",
        family: "Core ML + geo-seasonal priors + optional traits",
        summary: "Ranks the local species catalog from the priority-6 on-device image classifier, then gently reranks with GPS/date/water context and optional visible traits.",
        limitations: [
            "Geo-seasonal priors are supporting signals only.",
            "Low-confidence image predictions should stay reviewable.",
            "A visually strong rare catch should remain possible.",
            "Harvest decisions still require current local regulations."
        ]
    )

    static func identify(_ evidence: FishEvidence) -> IdentificationResult {
        let month = Calendar.current.component(.month, from: evidence.date)
        let visualSignalCount = visualSignals(in: evidence) + (evidence.imagePredictions.isEmpty ? 0 : 2)
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

        if let imagePrediction = imagePrediction(for: species, in: evidence.imagePredictions) {
            let contribution = Int((Double(imagePrediction.confidencePercent) * 0.72).rounded())
            score += contribution
            reasons.append("image model \(imagePrediction.confidencePercent)%")
        } else if !evidence.imagePredictions.isEmpty {
            score -= 10
        }

        for (key, value) in traits where !value.isEmpty {
            if species.traits[key]?.contains(value) == true {
                score += visualWeight(for: key)
                reasons.append("\(label(key)) matches")
            } else {
                score -= max(4, visualWeight(for: key) / 2)
            }
        }

        let prior = GeoSeasonalPrior.signal(for: species, evidence: evidence, month: month)
        score += prior.score
        reasons.append(contentsOf: prior.reasons)

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
            EvidenceRow(label: "Visual", value: visualText(top: top, evidence: evidence, matchedTraits: matched)),
            EvidenceRow(label: "Local Prior", value: GeoSeasonalPrior.explanation(for: top, evidence: evidence, month: month)),
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

        if evidence.imagePredictions.isEmpty && visualSignals(in: evidence) == 0 {
            items.append("Add visible traits if the image model is unavailable or uncertain.")
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
            items.append("Add GPS/range and water type before using this for harvest decisions.")
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

    private static func imagePrediction(for species: Species, in predictions: [ImageModelPrediction]) -> ImageModelPrediction? {
        predictions.first { prediction in
            normalized(prediction.label) == species.id || normalized(prediction.label) == normalized(species.commonName)
        }
    }

    private static func visualText(top: Species, evidence: FishEvidence, matchedTraits: [String]) -> String {
        if let imagePrediction = imagePrediction(for: top, in: evidence.imagePredictions) {
            if matchedTraits.isEmpty {
                return "Image model supports this at \(imagePrediction.confidencePercent)%"
            }
            return "Image model \(imagePrediction.confidencePercent)% plus \(matchedTraits.joined(separator: ", "))"
        }

        return matchedTraits.isEmpty ? "No image model prediction yet; visible traits help" : "Matches \(matchedTraits.joined(separator: ", "))"
    }

    private static func normalized(_ value: String) -> String {
        value
            .lowercased()
            .replacingOccurrences(of: " ", with: "-")
            .replacingOccurrences(of: "_", with: "-")
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
