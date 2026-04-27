import Foundation

enum SpeciesCatalog {
    static let all: [Species] = [
        Species(
            id: "largemouth-bass",
            commonName: "Largemouth Bass",
            scientificName: "Micropterus salmoides",
            family: "Black bass",
            waterTypes: ["freshwater"],
            regions: ["southeast", "midwest", "great-lakes", "northeast", "west"],
            habitats: ["lake", "pond", "river"],
            peakMonths: [3, 4, 5, 6, 7, 8, 9, 10],
            traits: [
                "bodyShape": ["stout", "elongated"],
                "mouth": ["large"],
                "markings": ["horizontal-stripe", "mottled"],
                "finTail": ["rounded", "spiny"],
                "color": ["green", "brown"]
            ],
            lookalikeGroup: "black-bass",
            caution: "Check local harvest rules before keeping black bass."
        ),
        Species(
            id: "smallmouth-bass",
            commonName: "Smallmouth Bass",
            scientificName: "Micropterus dolomieu",
            family: "Black bass",
            waterTypes: ["freshwater"],
            regions: ["northeast", "great-lakes", "midwest", "west"],
            habitats: ["river", "lake", "stream"],
            peakMonths: [4, 5, 6, 7, 8, 9, 10],
            traits: [
                "bodyShape": ["stout", "elongated"],
                "mouth": ["large", "small"],
                "markings": ["vertical-bars", "mottled"],
                "finTail": ["rounded", "spiny"],
                "color": ["brown", "green"]
            ],
            lookalikeGroup: "black-bass",
            caution: "Look closely at jaw position and side pattern versus largemouth bass."
        ),
        Species(
            id: "spotted-bass",
            commonName: "Spotted Bass",
            scientificName: "Micropterus punctulatus",
            family: "Black bass",
            waterTypes: ["freshwater"],
            regions: ["southeast", "midwest"],
            habitats: ["river", "lake"],
            peakMonths: [3, 4, 5, 6, 7, 8, 9],
            traits: [
                "bodyShape": ["stout", "elongated"],
                "mouth": ["large"],
                "markings": ["horizontal-stripe", "spots"],
                "finTail": ["rounded", "spiny"],
                "color": ["green", "brown"]
            ],
            lookalikeGroup: "black-bass",
            caution: "Often confused with largemouth bass; verify jaw and cheek scale details."
        ),
        Species(
            id: "bluegill",
            commonName: "Bluegill",
            scientificName: "Lepomis macrochirus",
            family: "Sunfish",
            waterTypes: ["freshwater"],
            regions: ["southeast", "midwest", "great-lakes", "northeast", "west"],
            habitats: ["lake", "pond", "river"],
            peakMonths: [4, 5, 6, 7, 8, 9],
            traits: [
                "bodyShape": ["deep"],
                "mouth": ["small"],
                "markings": ["vertical-bars", "blue-orange"],
                "finTail": ["spiny", "rounded"],
                "color": ["green", "yellow", "blue"]
            ],
            lookalikeGroup: "sunfish",
            caution: "Panfish limits are often aggregate by species group."
        ),
        Species(
            id: "rainbow-trout",
            commonName: "Rainbow Trout",
            scientificName: "Oncorhynchus mykiss",
            family: "Trout",
            waterTypes: ["freshwater"],
            regions: ["west", "great-lakes", "northeast", "midwest"],
            habitats: ["stream", "river", "lake"],
            peakMonths: [3, 4, 5, 6, 9, 10, 11],
            traits: [
                "bodyShape": ["torpedo", "elongated"],
                "mouth": ["small"],
                "markings": ["spots", "horizontal-stripe"],
                "finTail": ["adipose", "forked"],
                "color": ["silver", "red", "green"]
            ],
            lookalikeGroup: "trout",
            caution: "Wild, stocked, and migratory trout rules can differ by waterbody."
        ),
        Species(
            id: "channel-catfish",
            commonName: "Channel Catfish",
            scientificName: "Ictalurus punctatus",
            family: "Catfish",
            waterTypes: ["freshwater", "brackish"],
            regions: ["southeast", "midwest", "great-lakes", "northeast", "west"],
            habitats: ["river", "lake", "pond"],
            peakMonths: [4, 5, 6, 7, 8, 9],
            traits: [
                "bodyShape": ["elongated"],
                "mouth": ["barbels"],
                "markings": ["spots", "plain"],
                "finTail": ["forked"],
                "color": ["blue", "silver", "brown"]
            ],
            lookalikeGroup: "catfish",
            caution: "Different catfish species can have separate size and creel rules."
        ),
        Species(
            id: "red-drum",
            commonName: "Red Drum",
            scientificName: "Sciaenops ocellatus",
            family: "Drum",
            waterTypes: ["saltwater", "brackish"],
            regions: ["gulf", "atlantic", "southeast"],
            habitats: ["inshore"],
            peakMonths: [4, 5, 6, 7, 8, 9, 10, 11],
            traits: [
                "bodyShape": ["stout", "elongated"],
                "mouth": ["downturned", "small"],
                "markings": ["spots", "plain"],
                "finTail": ["rounded"],
                "color": ["red", "silver", "brown"]
            ],
            lookalikeGroup: "drum",
            caution: "Slot limits are common; location and date matter before harvest."
        ),
        Species(
            id: "red-snapper",
            commonName: "Red Snapper",
            scientificName: "Lutjanus campechanus",
            family: "Snapper",
            waterTypes: ["saltwater"],
            regions: ["gulf", "atlantic", "southeast"],
            habitats: ["reef", "offshore"],
            peakMonths: [5, 6, 7, 8, 9],
            traits: [
                "bodyShape": ["stout"],
                "mouth": ["large"],
                "markings": ["plain"],
                "finTail": ["spiny", "forked"],
                "color": ["red"]
            ],
            lookalikeGroup: "snapper",
            caution: "Highly regulated; require strong evidence and current local rules."
        )
    ]

    static func species(id: String) -> Species? {
        all.first { $0.id == id }
    }
}
