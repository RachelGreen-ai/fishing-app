import PhotosUI
import SwiftUI

struct IdentifyView: View {
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var hasPhoto = false
    @State private var photoQuality = 82
    @State private var region = "southeast"
    @State private var waterType = "freshwater"
    @State private var habitat = "lake"
    @State private var caughtDate = Date()
    @State private var waterbody = ""
    @State private var bodyShape = "stout"
    @State private var mouth = "large"
    @State private var markings = "horizontal-stripe"
    @State private var finTail = "rounded"
    @State private var color = "green"
    @State private var consent = PhotoConsent()
    @State private var result: IdentificationResult?
    @State private var catchLog: [CatchLogItem] = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    photoCard
                    contextCard
                    traitsCard
                    resultCard
                    catchLogCard
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Identify Fish")
        }
    }

    private var photoCard: some View {
        Card {
            SectionHeader(number: "1", title: "Photo Evidence", subtitle: "Side profile, good light, full fish visible.")

            PhotosPicker(selection: $selectedPhoto, matching: .images) {
                Label(hasPhoto ? "Photo selected" : "Add fish photo", systemImage: hasPhoto ? "checkmark.circle.fill" : "camera.viewfinder")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .onChange(of: selectedPhoto) {
                hasPhoto = selectedPhoto != nil
                result = nil
            }

            Stepper("Photo quality: \(photoQuality)", value: $photoQuality, in: 20...100, step: 5)

            VStack(alignment: .leading, spacing: 10) {
                SectionHeader(number: "P", title: "Photo Privacy", subtitle: "Consent travels with every scan session.")
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
    }

    private var contextCard: some View {
        Card {
            SectionHeader(number: "2", title: "Context", subtitle: "Range and season help handle lookalikes.")

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

            DatePicker("Date", selection: $caughtDate, displayedComponents: .date)
            TextField("Waterbody", text: $waterbody)
                .textFieldStyle(.roundedBorder)
        }
    }

    private var traitsCard: some View {
        Card {
            SectionHeader(number: "3", title: "Visual Traits", subtitle: "Use what is visible; unknown is fine.")

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
                Label("Run Identification", systemImage: "sparkles")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(hasPhoto && !consent.identification)
        }
    }

    @ViewBuilder
    private var resultCard: some View {
        Card {
            SectionHeader(number: "4", title: "Result", subtitle: "Confidence tier, evidence, and alternatives.")

            if let result {
                VStack(alignment: .leading, spacing: 14) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(result.tier.rawValue)
                                .font(.caption.bold())
                                .foregroundStyle(tierColor(result.tier))
                            Text(result.primary.commonName)
                                .font(.largeTitle.bold())
                            Text(result.primary.scientificName)
                                .italic()
                                .foregroundStyle(.secondary)
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
                }
            } else {
                ContentUnavailableView("Run a scan to see candidates.", systemImage: "fish")
            }
        }
    }

    private var catchLogCard: some View {
        Card {
            SectionHeader(number: "5", title: "Catch Log", subtitle: "Confirmed IDs stay on device in this target.")

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
