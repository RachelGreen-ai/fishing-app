import CoreLocation
import PhotosUI
import SwiftUI

struct IdentifyView: View {
    @StateObject private var locationProvider = LocationProvider()
    @StateObject private var imageClassifier = FishImageClassifier()
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImageData: Data?
    @State private var imageModelPredictions: [ImageModelPrediction] = []
    @State private var imageModelStatus = "No Core ML species model bundled yet."
    @State private var isClassifyingPhoto = false
    @State private var hasPhoto = false
    @State private var photoQuality = 82
    @State private var region = ""
    @State private var waterType = ""
    @State private var habitat = ""
    @State private var caughtDate = Date()
    @State private var waterbody = ""
    @State private var bodyShape = ""
    @State private var mouth = ""
    @State private var markings = ""
    @State private var finTail = ""
    @State private var color = ""
    @State private var consent = PhotoConsent()
    @State private var result: IdentificationResult?
    @State private var catchLog: [CatchLogItem] = []
    @State private var showImproveResult = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    photoCard
                    resultCard
                    modelCard
                    improveResultCard
                    catchLogCard
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Identify Fish")
            .onAppear {
                caughtDate = Date()
            }
            .onChange(of: locationProvider.region) {
                guard let region = locationProvider.region else { return }
                self.region = region
                if hasPhoto, consent.identification {
                    result = InferenceService.identify(evidence)
                }
            }
        }
    }

    private var photoCard: some View {
        Card {
            SectionHeader(number: "1", title: "Take Or Choose A Photo", subtitle: "Start with the fish. Details can come later if they matter.")

            PhotosPicker(selection: $selectedPhoto, matching: .images) {
                Label(hasPhoto ? "Photo selected" : "Take Photo Or Choose From Gallery", systemImage: hasPhoto ? "checkmark.circle.fill" : "camera.viewfinder")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .onChange(of: selectedPhoto) {
                Task {
                    await handleSelectedPhotoChange()
                }
            }

            HStack {
                ContextPill(label: "Date", value: caughtDate.formatted(date: .abbreviated, time: .omitted))
                ContextPill(label: "Time", value: caughtDate.formatted(date: .omitted, time: .shortened))
            }

            HStack {
                ContextPill(label: "Season", value: seasonName(for: caughtDate))
                ContextPill(label: "Range", value: region.isEmpty ? "Not set" : readable(region))
            }

            HStack {
                ContextPill(label: "Water", value: waterType.isEmpty ? "Ask if needed" : readable(waterType))
                Button {
                    locationProvider.requestRegion()
                } label: {
                    Label(locationProvider.isLocating ? "Locating" : "Use GPS", systemImage: "location")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(locationProvider.isLocating)
            }

            if let locationStatus = locationProvider.statusMessage {
                Label(locationStatus, systemImage: locationProvider.region == nil ? "info.circle" : "checkmark.circle")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Stepper("Photo quality: \(photoQuality)", value: $photoQuality, in: 20...100, step: 5)
                .onChange(of: photoQuality) {
                    if hasPhoto {
                        result = InferenceService.identify(evidence)
                    }
                }

            Button {
                result = InferenceService.identify(evidence)
            } label: {
                Label(hasPhoto ? "Identify Now" : "Add Photo First", systemImage: "sparkles")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!hasPhoto || !consent.identification)

            DisclosureGroup("Photo privacy") {
                VStack(alignment: .leading, spacing: 10) {
                Toggle("Use this photo for identification", isOn: $consent.identification)
                Toggle("Allow de-identified training review", isOn: $consent.trainingReview)
                Picker("Retention", selection: $consent.retentionPolicy) {
                    Text("Delete after scan").tag("delete-after-scan")
                    Text("Keep 24 hours").tag("24-hours")
                    Text("Keep 30 days").tag("30-days")
                }
                }
                .padding(.top, 8)
            }
            .padding(.top, 8)
        }
    }

    private var modelCard: some View {
        Card {
            SectionHeader(number: "M", title: "Model", subtitle: "Current native identification engine.")

            let info = InferenceService.engineInfo

            LabeledContent("Engine", value: "\(info.name) \(info.version)")
            LabeledContent("Type", value: info.family)
            LabeledContent("Core ML", value: imageClassifier.isModelBundled ? "FishSpeciesClassifier loaded" : "Awaiting FishSpeciesClassifier")
            Text(info.summary)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if isClassifyingPhoto {
                ProgressView("Classifying photo")
            } else {
                Text(imageModelStatus)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if !imageModelPredictions.isEmpty {
                Text("Image Model Predictions")
                    .font(.headline)
                ForEach(imageModelPredictions) { prediction in
                    LabeledContent(prediction.label, value: "\(prediction.confidencePercent)%")
                }
            }

            ForEach(info.limitations, id: \.self) { item in
                Label(item, systemImage: "exclamationmark.triangle")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var improveResultCard: some View {
        Card {
            DisclosureGroup("Improve result", isExpanded: $showImproveResult) {
                VStack(alignment: .leading, spacing: 14) {
                    SectionHeader(number: "A", title: "Auto Context", subtitle: "Date is automatic. Add range or water only when it helps.")

            Picker("Region", selection: $region) {
                option("Unknown", "")
                option("Southeast", "southeast")
                option("Northeast", "northeast")
                option("Great Lakes", "great-lakes")
                option("Midwest", "midwest")
                option("West / Inland", "west")
                option("Pacific Coast", "pacific")
                option("Gulf Coast", "gulf")
                option("Atlantic Coast", "atlantic")
            }

            Picker("Water", selection: $waterType) {
                option("Unknown", "")
                option("Freshwater", "freshwater")
                option("Saltwater", "saltwater")
                option("Brackish", "brackish")
            }

            Picker("Habitat", selection: $habitat) {
                option("Unknown", "")
                option("Lake", "lake")
                option("Pond", "pond")
                option("River", "river")
                option("Stream", "stream")
                option("Inshore", "inshore")
                option("Reef", "reef")
                option("Offshore", "offshore")
            }

            DatePicker("Date & time", selection: $caughtDate, displayedComponents: [.date, .hourAndMinute])
                .onChange(of: caughtDate) {
                    if hasPhoto {
                        result = InferenceService.identify(evidence)
                    }
                }

                    SectionHeader(number: "B", title: "Visible Traits", subtitle: "Answer only what is obvious from the photo.")

            Picker("Body", selection: $bodyShape) {
                option("Unknown", "")
                option("Deep / panfish", "deep")
                option("Elongated", "elongated")
                option("Torpedo", "torpedo")
                option("Flat", "flat")
                option("Stout", "stout")
            }

            Picker("Mouth", selection: $mouth) {
                option("Unknown", "")
                option("Large jaw", "large")
                option("Small mouth", "small")
                option("Whiskers / barbels", "barbels")
                option("Toothy", "toothy")
                option("Downturned", "downturned")
            }

            Picker("Markings", selection: $markings) {
                option("Unknown", "")
                option("Horizontal stripe", "horizontal-stripe")
                option("Vertical bars", "vertical-bars")
                option("Spots", "spots")
                option("Mottled", "mottled")
                option("Blue / orange face", "blue-orange")
                option("Mostly plain", "plain")
            }

            Picker("Tail / Fin", selection: $finTail) {
                option("Unknown", "")
                option("Forked tail", "forked")
                option("Rounded tail", "rounded")
                option("Spiny dorsal", "spiny")
                option("Adipose fin", "adipose")
                option("Long dorsal", "continuous-dorsal")
            }

            Picker("Color", selection: $color) {
                option("Unknown", "")
                option("Green", "green")
                option("Brown / bronze", "brown")
                option("Silver", "silver")
                option("Blue / slate", "blue")
                option("Red / copper", "red")
                option("Yellow / gold", "yellow")
            }

            Button {
                result = InferenceService.identify(evidence)
            } label: {
                        Label("Update Result", systemImage: "arrow.clockwise")
                    .frame(maxWidth: .infinity)
            }
                    .buttonStyle(.bordered)
                }
                .padding(.top, 8)
            }
        }
    }

    @ViewBuilder
    private var resultCard: some View {
        Card {
            SectionHeader(number: "2", title: "Result", subtitle: "Confidence tier, evidence, and alternatives.")

            if let result {
                VStack(alignment: .leading, spacing: 14) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(result.tier.rawValue)
                                .font(.caption.bold())
                                .foregroundStyle(tierColor(result.tier))
                            Text(result.isAbstained ? "Need More Evidence" : result.primary.commonName)
                                .font(.largeTitle.bold())
                            if result.isAbstained {
                                Text("Best current candidate: \(result.primary.commonName)")
                                    .foregroundStyle(.secondary)
                            } else {
                                Text(result.primary.scientificName)
                                    .italic()
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        Text("\(result.confidence)%")
                            .font(.title2.bold())
                    }

                    ForEach(result.evidenceRows) { row in
                        LabeledContent(row.label, value: row.value)
                    }

                    if !result.alternatives.isEmpty {
                        Text("Alternatives")
                            .font(.headline)
                        ForEach(result.alternatives) { candidate in
                            Button {
                                self.result?.primary = candidate.species
                            } label: {
                                HStack {
                                    Text(candidate.species.commonName)
                                    Spacer()
                                    Text("\(candidate.confidence)%")
                                }
                            }
                            .buttonStyle(.bordered)
                        }
                    }

                    if !result.guidance.isEmpty {
                        Text("Next Evidence")
                            .font(.headline)
                        ForEach(result.guidance, id: \.self) { item in
                            Label(item, systemImage: "info.circle")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Button {
                        showImproveResult = true
                    } label: {
                        Label("Improve Result", systemImage: "slider.horizontal.3")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)

                    Button {
                        catchLog.insert(
                            CatchLogItem(
                                speciesName: result.primary.commonName,
                                status: "confirmed",
                                date: caughtDate,
                                waterbody: waterbody,
                                confidence: result.confidence
                            ),
                            at: 0
                        )
                    } label: {
                        Label("Confirm & Save", systemImage: "tray.and.arrow.down")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(result.isAbstained)
                }
            } else {
                ContentUnavailableView("Add a fish photo to start.", systemImage: "fish")
            }
        }
    }

    private var catchLogCard: some View {
        Card {
            SectionHeader(number: "3", title: "Catch Log", subtitle: "Confirmed IDs stay on device in this target.")

            TextField("Waterbody for saved catch", text: $waterbody)
                .textFieldStyle(.roundedBorder)

            if catchLog.isEmpty {
                ContentUnavailableView("No confirmed catches yet.", systemImage: "list.bullet.clipboard")
            } else {
                ForEach(catchLog) { item in
                    LabeledContent {
                        Text("\(item.confidence)%")
                    } label: {
                        VStack(alignment: .leading) {
                            Text(item.speciesName).bold()
                            Text(item.waterbody.isEmpty ? item.status : "\(item.status) · \(item.waterbody)")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    private var evidence: FishEvidence {
        FishEvidence(
            hasPhoto: hasPhoto,
            photoQuality: hasPhoto ? photoQuality : 0,
            imagePredictions: imageModelPredictions,
            region: region,
            waterType: waterType,
            habitat: habitat,
            date: caughtDate,
            waterbody: waterbody,
            bodyShape: bodyShape,
            mouth: mouth,
            markings: markings,
            finTail: finTail,
            color: color,
            consent: consent
        )
    }

    private func handleSelectedPhotoChange() async {
        hasPhoto = selectedPhoto != nil
        caughtDate = Date()
        selectedImageData = nil
        imageModelPredictions = []

        guard let selectedPhoto else {
            imageModelStatus = "No Core ML species model bundled yet."
            result = nil
            return
        }

        do {
            selectedImageData = try await selectedPhoto.loadTransferable(type: Data.self)
        } catch {
            imageModelStatus = "Could not load the selected photo."
        }

        await classifySelectedPhotoIfPossible()

        if hasPhoto && consent.identification {
            result = InferenceService.identify(evidence)
        } else {
            result = nil
        }
    }

    private func classifySelectedPhotoIfPossible() async {
        guard let selectedImageData else {
            return
        }

        guard imageClassifier.isModelBundled else {
            imageModelStatus = "Ready for FishSpeciesClassifier. Using hybrid evidence until the model is bundled."
            return
        }

        isClassifyingPhoto = true
        imageModelStatus = "Classifying selected photo..."
        defer { isClassifyingPhoto = false }

        do {
            let predictions = try await imageClassifier.classify(imageData: selectedImageData)
            imageModelPredictions = predictions
            imageModelStatus = "Core ML returned \(predictions.count) species candidates."
            if hasPhoto && consent.identification {
                result = InferenceService.identify(evidence)
            }
        } catch {
            imageModelPredictions = []
            imageModelStatus = error.localizedDescription
        }
    }

    private func option(_ label: String, _ value: String) -> some View {
        Text(label).tag(value)
    }

    private func tierColor(_ tier: ConfidenceTier) -> Color {
        switch tier {
        case .likely:
            return .green
        case .possible, .uncertain, .userCorrected:
            return .orange
        case .notEnoughEvidence:
            return .red
        }
    }

    private func seasonName(for date: Date) -> String {
        let month = Calendar.current.component(.month, from: date)
        if [12, 1, 2].contains(month) { return "winter" }
        if [3, 4, 5].contains(month) { return "spring" }
        if [6, 7, 8].contains(month) { return "summer" }
        return "fall"
    }

    private func readable(_ value: String) -> String {
        value.replacingOccurrences(of: "-", with: " ")
    }
}

private struct ContextPill: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(.caption2.bold())
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline.weight(.semibold))
                .lineLimit(1)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

@MainActor
private final class LocationProvider: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var region: String?
    @Published var statusMessage: String?
    @Published var isLocating = false

    private let manager = CLLocationManager()

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
    }

    func requestRegion() {
        guard CLLocationManager.locationServicesEnabled() else {
            statusMessage = "Location services are off. Set range manually."
            return
        }

        isLocating = true
        statusMessage = "Getting broad range from GPS..."

        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .denied, .restricted:
            isLocating = false
            statusMessage = "Location permission is off. Set range manually."
        @unknown default:
            isLocating = false
            statusMessage = "Location is unavailable. Set range manually."
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        Task { @MainActor in
            switch manager.authorizationStatus {
            case .authorizedAlways, .authorizedWhenInUse:
                manager.requestLocation()
            case .denied, .restricted:
                isLocating = false
                statusMessage = "Location permission is off. Set range manually."
            case .notDetermined:
                break
            @unknown default:
                isLocating = false
                statusMessage = "Location is unavailable. Set range manually."
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let coordinate = locations.last?.coordinate else { return }

        Task { @MainActor in
            if let detectedRegion = Self.region(for: coordinate) {
                region = detectedRegion
                statusMessage = "Range set to \(Self.readable(detectedRegion)) from GPS."
            } else {
                region = nil
                statusMessage = "GPS is outside supported U.S. ranges. Set range manually."
            }
            isLocating = false
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in
            isLocating = false
            statusMessage = "Could not read GPS. Set range manually."
        }
    }

    private static func region(for coordinate: CLLocationCoordinate2D) -> String? {
        let latitude = coordinate.latitude
        let longitude = coordinate.longitude

        if latitude < 25 || latitude > 50 || longitude < -125 || longitude > -66 {
            return nil
        }

        if longitude <= -118 {
            return "pacific"
        }

        if latitude <= 31 && longitude >= -98 {
            return "gulf"
        }

        if longitude >= -82 && latitude <= 39 {
            return "atlantic"
        }

        if latitude >= 41 && longitude >= -93 && longitude <= -75 {
            return "great-lakes"
        }

        if longitude >= -90 {
            return latitude >= 38 ? "northeast" : "southeast"
        }

        if longitude <= -104 {
            return "west"
        }

        return "midwest"
    }

    private static func readable(_ value: String) -> String {
        value.replacingOccurrences(of: "-", with: " ")
    }
}

private struct Card<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            content
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

private struct SectionHeader: View {
    let number: String
    let title: String
    let subtitle: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text(number)
                .font(.caption.bold())
                .foregroundStyle(.white)
                .frame(width: 28, height: 28)
                .background(.primary)
                .clipShape(Circle())
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
