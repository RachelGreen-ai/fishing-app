import Combine
import CoreML
import Foundation
import ImageIO
import UIKit
import Vision

enum FishImageClassifierError: LocalizedError {
    case missingModel
    case unreadableImage
    case noPredictions

    var errorDescription: String? {
        switch self {
        case .missingModel:
            return "FishSpeciesClassifier is not bundled yet."
        case .unreadableImage:
            return "The selected photo could not be read."
        case .noPredictions:
            return "The image model did not return species predictions."
        }
    }
}

final class FishImageClassifier: ObservableObject {
    static let bundledModelName = "FishSpeciesClassifier"

    var isModelBundled: Bool {
        modelURL != nil
    }

    var modelURL: URL? {
        Bundle.main.url(forResource: Self.bundledModelName, withExtension: "mlmodelc")
    }

    func classify(imageData: Data) async throws -> [ImageModelPrediction] {
        try await Task.detached(priority: .userInitiated) {
            guard let modelURL = Bundle.main.url(forResource: Self.bundledModelName, withExtension: "mlmodelc") else {
                throw FishImageClassifierError.missingModel
            }

            guard let image = UIImage(data: imageData), let cgImage = image.cgImage else {
                throw FishImageClassifierError.unreadableImage
            }

            let coreMLModel = try MLModel(contentsOf: modelURL)
            let visionModel = try VNCoreMLModel(for: coreMLModel)
            let request = VNCoreMLRequest(model: visionModel)
            request.imageCropAndScaleOption = .scaleFill

            let handler = VNImageRequestHandler(
                cgImage: cgImage,
                orientation: CGImagePropertyOrientation(image.imageOrientation),
                options: [:]
            )
            try handler.perform([request])

            let predictions = (request.results as? [VNClassificationObservation] ?? [])
                .prefix(5)
                .map {
                    ImageModelPrediction(
                        label: $0.identifier,
                        confidence: Double($0.confidence)
                    )
                }

            guard !predictions.isEmpty else {
                throw FishImageClassifierError.noPredictions
            }

            return predictions
        }.value
    }
}

extension CGImagePropertyOrientation {
    init(_ orientation: UIImage.Orientation) {
        switch orientation {
        case .up:
            self = .up
        case .upMirrored:
            self = .upMirrored
        case .down:
            self = .down
        case .downMirrored:
            self = .downMirrored
        case .left:
            self = .left
        case .leftMirrored:
            self = .leftMirrored
        case .right:
            self = .right
        case .rightMirrored:
            self = .rightMirrored
        @unknown default:
            self = .up
        }
    }
}
