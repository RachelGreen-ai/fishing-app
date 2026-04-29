import Foundation

struct GeoSeasonalSignal {
    let score: Int
    let reasons: [String]
}

enum GeoSeasonalPrior {
    static func signal(for species: Species, evidence: FishEvidence, month: Int) -> GeoSeasonalSignal {
        var score = 0
        var reasons: [String] = []

        if !evidence.region.isEmpty {
            if species.regions.contains(evidence.region) {
                score += 8
                reasons.append("local range supports it")
            } else {
                score -= 7
                reasons.append("less common for this range")
            }
        }

        if !evidence.waterType.isEmpty {
            if species.waterTypes.contains(evidence.waterType) {
                score += 7
                reasons.append("water type fits")
            } else {
                score -= 12
            }
        }

        if !evidence.habitat.isEmpty {
            if species.habitats.contains(evidence.habitat) {
                score += 4
                reasons.append("habitat fits")
            } else {
                score -= 4
            }
        }

        if species.peakMonths.contains(month) {
            score += 3
            reasons.append("season supports it")
        }

        return GeoSeasonalSignal(score: score, reasons: reasons)
    }

    static func explanation(for species: Species, evidence: FishEvidence, month: Int) -> String {
        let signal = signal(for: species, evidence: evidence, month: month)

        if signal.reasons.isEmpty {
            return "No local prior applied"
        }

        if signal.score >= 12 {
            return "Strong local support: \(signal.reasons.joined(separator: ", "))"
        }

        if signal.score > 0 {
            return "Some local support: \(signal.reasons.joined(separator: ", "))"
        }

        return "Local signal is weak; visual evidence should dominate"
    }
}
