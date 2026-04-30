import Combine
import CoreGraphics
import CoreML
import Foundation
import ImageIO
import UIKit
import Vision

enum FishDetectorError: LocalizedError {
    case missingModel
    case unreadableImage
    case noOutput

    var errorDescription: String? {
        switch self {
        case .missingModel:
            return "FishDetector is not bundled yet."
        case .unreadableImage:
            return "The selected photo could not be read."
        case .noOutput:
            return "The fish detector did not return usable output."
        }
    }
}

struct FishDetection: Identifiable {
    let id = UUID()
    let confidence: Double
    let boundingBox: CGRect

    var confidencePercent: Int {
        Int((confidence * 100).rounded())
    }
}

struct FishDetectionResult {
    let detections: [FishDetection]

    var bestConfidence: Double {
        detections.map(\.confidence).max() ?? 0
    }

    var bestConfidencePercent: Int {
        Int((bestConfidence * 100).rounded())
    }

    var foundFish: Bool {
        bestConfidence >= 0.25
    }

    var statusText: String {
        guard foundFish else {
            return "No fish confidently detected."
        }
        if detections.count == 1 {
            return "Fish detected at \(bestConfidencePercent)%."
        }
        return "\(detections.count) fish candidates detected; best \(bestConfidencePercent)%."
    }
}

final class FishDetector: ObservableObject {
    static let bundledModelName = "FishDetector"

    var isModelBundled: Bool {
        modelURL != nil
    }

    var modelURL: URL? {
        Bundle.main.url(forResource: Self.bundledModelName, withExtension: "mlmodelc")
    }

    func detect(imageData: Data) async throws -> FishDetectionResult {
        try await Task.detached(priority: .userInitiated) {
            guard let modelURL = Bundle.main.url(forResource: Self.bundledModelName, withExtension: "mlmodelc") else {
                throw FishDetectorError.missingModel
            }

            guard let image = UIImage(data: imageData), let cgImage = image.cgImage else {
                throw FishDetectorError.unreadableImage
            }

            let coreMLModel = try MLModel(contentsOf: modelURL)
            let visionModel = try VNCoreMLModel(for: coreMLModel)
            let request = VNCoreMLRequest(model: visionModel)
            request.imageCropAndScaleOption = .scaleFit

            let handler = VNImageRequestHandler(
                cgImage: cgImage,
                orientation: CGImagePropertyOrientation(image.imageOrientation),
                options: [:]
            )
            try handler.perform([request])

            if let objectDetections = request.results as? [VNRecognizedObjectObservation] {
                return FishDetectionResult(
                    detections: objectDetections.map {
                        FishDetection(
                            confidence: Double($0.labels.first?.confidence ?? 0),
                            boundingBox: $0.boundingBox
                        )
                    }
                )
            }

            let featureOutputs = request.results as? [VNCoreMLFeatureValueObservation] ?? []
            let confidence = featureOutputs.first { $0.featureName == "confidence" }?.featureValue.multiArrayValue
            let coordinates = featureOutputs.first { $0.featureName == "coordinates" }?.featureValue.multiArrayValue
            guard let confidence, let coordinates else {
                throw FishDetectorError.noOutput
            }

            return FishDetectionResult(detections: FishDetector.parseDetections(confidence: confidence, coordinates: coordinates))
        }.value
    }

    private static func parseDetections(confidence: MLMultiArray, coordinates: MLMultiArray) -> [FishDetection] {
        let confidenceShape = confidence.shape.map(\.intValue)
        let coordinateShape = coordinates.shape.map(\.intValue)
        let rows = detectionRowCount(confidenceShape: confidenceShape, coordinateShape: coordinateShape)
        guard rows > 0 else { return [] }

        return (0..<rows).compactMap { row in
            let score = maxConfidence(in: confidence, row: row, rows: rows)
            guard score >= 0.25 else { return nil }
            let box = normalizedBox(from: coordinates, row: row, rows: rows)
            return FishDetection(confidence: score, boundingBox: box)
        }
        .sorted { $0.confidence > $1.confidence }
    }

    private static func detectionRowCount(confidenceShape: [Int], coordinateShape: [Int]) -> Int {
        if coordinateShape.count == 2, coordinateShape[1] == 4 {
            return coordinateShape[0]
        }
        if coordinateShape.count == 3, coordinateShape[0] == 1, coordinateShape[2] == 4 {
            return coordinateShape[1]
        }
        if confidenceShape.count == 2 {
            return confidenceShape[0]
        }
        if confidenceShape.count == 3, confidenceShape[0] == 1 {
            return confidenceShape[1]
        }
        return 0
    }

    private static func maxConfidence(in array: MLMultiArray, row: Int, rows: Int) -> Double {
        let shape = array.shape.map(\.intValue)
        if shape.count == 2 {
            let columns = shape[0] == rows ? shape[1] : shape[0]
            return (0..<columns).map { column in
                shape[0] == rows ? value(in: array, at: [row, column]) : value(in: array, at: [column, row])
            }.max() ?? 0
        }
        if shape.count == 3, shape[0] == 1 {
            let columns = shape[1] == rows ? shape[2] : shape[1]
            return (0..<columns).map { column in
                shape[1] == rows ? value(in: array, at: [0, row, column]) : value(in: array, at: [0, column, row])
            }.max() ?? 0
        }
        return 0
    }

    private static func normalizedBox(from array: MLMultiArray, row: Int, rows: Int) -> CGRect {
        let shape = array.shape.map(\.intValue)
        let values: [Double]
        if shape.count == 2, shape[0] == rows {
            values = (0..<4).map { value(in: array, at: [row, $0]) }
        } else if shape.count == 2 {
            values = (0..<4).map { value(in: array, at: [$0, row]) }
        } else if shape.count == 3, shape[1] == rows {
            values = (0..<4).map { value(in: array, at: [0, row, $0]) }
        } else if shape.count == 3 {
            values = (0..<4).map { value(in: array, at: [0, $0, row]) }
        } else {
            values = [0, 0, 0, 0]
        }

        let x = values.indices.contains(0) ? values[0] : 0
        let y = values.indices.contains(1) ? values[1] : 0
        let width = values.indices.contains(2) ? values[2] : 0
        let height = values.indices.contains(3) ? values[3] : 0
        return CGRect(
            x: max(0, x - width / 2),
            y: max(0, y - height / 2),
            width: min(1, width),
            height: min(1, height)
        )
    }

    private static func value(in array: MLMultiArray, at indexes: [Int]) -> Double {
        array[indexes.map { NSNumber(value: $0) }].doubleValue
    }
}
