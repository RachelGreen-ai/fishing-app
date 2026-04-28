#!/usr/bin/env swift
import CoreML
import Foundation
import Vision

struct Prediction: Encodable {
    let label: String
    let score: Double
}

struct PredictionRow: Encodable {
    let image_id: String
    let predictions: [Prediction]
    let latency_ms: Double
}

func usage() -> Never {
    fputs("""
    Usage:
      xcrun swift ml/scripts/predict_coreml_image_classifier.swift <model.mlmodel|model.mlmodelc> <manifest.jsonl> <image_root> <output_predictions.jsonl>

    """, stderr)
    exit(2)
}

func loadJSONLines(_ path: URL) throws -> [[String: Any]] {
    let contents = try String(contentsOf: path, encoding: .utf8)
    return try contents
        .split(separator: "\n")
        .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        .map { line in
            let data = Data(line.utf8)
            guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw NSError(domain: "PredictCoreML", code: 1, userInfo: [NSLocalizedDescriptionKey: "Invalid JSONL row"])
            }
            return object
        }
}

func modelURL(from url: URL) throws -> URL {
    if url.pathExtension == "mlmodel" {
        return try MLModel.compileModel(at: url)
    }
    return url
}

let args = Array(CommandLine.arguments.dropFirst())
guard args.count == 4 else {
    usage()
}

let rawModelURL = URL(fileURLWithPath: args[0]).standardizedFileURL
let manifestURL = URL(fileURLWithPath: args[1]).standardizedFileURL
let imageRoot = URL(fileURLWithPath: args[2], isDirectory: true).standardizedFileURL
let outputURL = URL(fileURLWithPath: args[3]).standardizedFileURL

let compiledModelURL = try modelURL(from: rawModelURL)
let model = try MLModel(contentsOf: compiledModelURL)
let visionModel = try VNCoreMLModel(for: model)
let request = VNCoreMLRequest(model: visionModel)
request.imageCropAndScaleOption = .centerCrop

let manifestRows = try loadJSONLines(manifestURL)
try FileManager.default.createDirectory(
    at: outputURL.deletingLastPathComponent(),
    withIntermediateDirectories: true
)
FileManager.default.createFile(atPath: outputURL.path, contents: nil)
let outputHandle = try FileHandle(forWritingTo: outputURL)
defer {
    try? outputHandle.close()
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]

for row in manifestRows {
    guard let imageID = row["image_id"] as? String,
          let imagePath = row["image"] as? String else {
        continue
    }

    let imageURL = imageRoot.appendingPathComponent(imagePath)
    let start = Date()
    let handler = VNImageRequestHandler(url: imageURL, options: [:])
    try handler.perform([request])
    let elapsed = Date().timeIntervalSince(start) * 1000.0

    let observations = (request.results as? [VNClassificationObservation] ?? [])
        .prefix(5)
        .map { Prediction(label: $0.identifier, score: Double($0.confidence)) }

    let predictionRow = PredictionRow(
        image_id: imageID,
        predictions: observations,
        latency_ms: elapsed
    )
    let encoded = try encoder.encode(predictionRow)
    outputHandle.write(encoded)
    outputHandle.write(Data("\n".utf8))
}

print("wrote_predictions=\(outputURL.path)")
