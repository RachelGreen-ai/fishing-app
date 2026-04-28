#!/usr/bin/env swift
import CreateML
import Foundation

struct Arguments {
    let datasetRoot: URL
    let outputModel: URL
    let maxIterations: Int
}

func usage() -> Never {
    fputs("""
    Usage:
      xcrun swift ml/scripts/train_createml_image_classifier.swift <dataset_root> <output_model.mlmodel> [max_iterations]

    dataset_root must contain train/, validation/, and test/ labeled-directory splits.

    """, stderr)
    exit(2)
}

func parseArguments() -> Arguments {
    let values = CommandLine.arguments.dropFirst()
    guard values.count == 2 || values.count == 3 else {
        usage()
    }

    let datasetRoot = URL(fileURLWithPath: String(values[values.startIndex])).standardizedFileURL
    let outputModel = URL(fileURLWithPath: String(values[values.index(after: values.startIndex)])).standardizedFileURL
    let maxIterations = values.count == 3 ? Int(values.last!) ?? 25 : 25

    return Arguments(datasetRoot: datasetRoot, outputModel: outputModel, maxIterations: maxIterations)
}

let arguments = parseArguments()
let trainURL = arguments.datasetRoot.appendingPathComponent("train", isDirectory: true)
let validationURL = arguments.datasetRoot.appendingPathComponent("validation", isDirectory: true)
let testURL = arguments.datasetRoot.appendingPathComponent("test", isDirectory: true)

let trainingData = MLImageClassifier.DataSource.labeledDirectories(at: trainURL)
let validationData = MLImageClassifier.DataSource.labeledDirectories(at: validationURL)
let testData = MLImageClassifier.DataSource.labeledDirectories(at: testURL)

let parameters = MLImageClassifier.ModelParameters(
    validationData: validationData,
    maxIterations: arguments.maxIterations,
    augmentationOptions: [.crop, .exposure, .blur, .noise, .flip]
)

print("Training Create ML image classifier")
print("dataset_root=\(arguments.datasetRoot.path)")
print("output_model=\(arguments.outputModel.path)")
print("max_iterations=\(arguments.maxIterations)")

let classifier = try MLImageClassifier(trainingData: trainingData, parameters: parameters)
let evaluation = classifier.evaluation(on: testData)

try FileManager.default.createDirectory(
    at: arguments.outputModel.deletingLastPathComponent(),
    withIntermediateDirectories: true
)

let metadata = MLModelMetadata(
    author: "Fishing App",
    shortDescription: "Europe archive seed fish classifier",
    version: "0.1.0"
)
try classifier.write(to: arguments.outputModel, metadata: metadata)

print("evaluation=\(evaluation)")
print("wrote_model=\(arguments.outputModel.path)")
