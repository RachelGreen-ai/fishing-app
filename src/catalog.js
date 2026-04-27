export const speciesCatalog = [
  {
    id: "largemouth-bass",
    commonName: "Largemouth Bass",
    scientificName: "Micropterus salmoides",
    family: "Black bass",
    waterTypes: ["freshwater"],
    regions: ["southeast", "midwest", "great-lakes", "northeast", "west"],
    habitats: ["lake", "pond", "river"],
    peakMonths: [3, 4, 5, 6, 7, 8, 9, 10],
    traits: {
      bodyShape: ["stout", "elongated"],
      mouth: ["large"],
      markings: ["horizontal-stripe", "mottled"],
      finTail: ["rounded", "spiny"],
      color: ["green", "brown"]
    },
    lookalikeGroup: "black-bass",
    caution: "Check local harvest rules before keeping black bass."
  },
  {
    id: "smallmouth-bass",
    commonName: "Smallmouth Bass",
    scientificName: "Micropterus dolomieu",
    family: "Black bass",
    waterTypes: ["freshwater"],
    regions: ["northeast", "great-lakes", "midwest", "west"],
    habitats: ["river", "lake", "stream"],
    peakMonths: [4, 5, 6, 7, 8, 9, 10],
    traits: {
      bodyShape: ["stout", "elongated"],
      mouth: ["large", "small"],
      markings: ["vertical-bars", "mottled"],
      finTail: ["rounded", "spiny"],
      color: ["brown", "green"]
    },
    lookalikeGroup: "black-bass",
    caution: "Look closely at jaw position and side pattern versus largemouth bass."
  },
  {
    id: "spotted-bass",
    commonName: "Spotted Bass",
    scientificName: "Micropterus punctulatus",
    family: "Black bass",
    waterTypes: ["freshwater"],
    regions: ["southeast", "midwest"],
    habitats: ["river", "lake"],
    peakMonths: [3, 4, 5, 6, 7, 8, 9],
    traits: {
      bodyShape: ["stout", "elongated"],
      mouth: ["large"],
      markings: ["horizontal-stripe", "spots"],
      finTail: ["rounded", "spiny"],
      color: ["green", "brown"]
    },
    lookalikeGroup: "black-bass",
    caution: "Often confused with largemouth bass; verify jaw and cheek scale details."
  },
  {
    id: "bluegill",
    commonName: "Bluegill",
    scientificName: "Lepomis macrochirus",
    family: "Sunfish",
    waterTypes: ["freshwater"],
    regions: ["southeast", "midwest", "great-lakes", "northeast", "west"],
    habitats: ["lake", "pond", "river"],
    peakMonths: [4, 5, 6, 7, 8, 9],
    traits: {
      bodyShape: ["deep"],
      mouth: ["small"],
      markings: ["vertical-bars", "blue-orange"],
      finTail: ["spiny", "rounded"],
      color: ["green", "yellow", "blue"]
    },
    lookalikeGroup: "sunfish",
    caution: "Panfish limits are often aggregate by species group."
  },
  {
    id: "pumpkinseed",
    commonName: "Pumpkinseed",
    scientificName: "Lepomis gibbosus",
    family: "Sunfish",
    waterTypes: ["freshwater"],
    regions: ["northeast", "great-lakes", "midwest"],
    habitats: ["lake", "pond", "stream"],
    peakMonths: [5, 6, 7, 8, 9],
    traits: {
      bodyShape: ["deep"],
      mouth: ["small"],
      markings: ["blue-orange", "mottled", "vertical-bars"],
      finTail: ["spiny", "rounded"],
      color: ["yellow", "green", "blue"]
    },
    lookalikeGroup: "sunfish",
    caution: "Look for the orange-red ear flap edge before calling it pumpkinseed."
  },
  {
    id: "black-crappie",
    commonName: "Black Crappie",
    scientificName: "Pomoxis nigromaculatus",
    family: "Sunfish",
    waterTypes: ["freshwater"],
    regions: ["southeast", "midwest", "great-lakes", "northeast"],
    habitats: ["lake", "pond", "river"],
    peakMonths: [3, 4, 5, 6, 9, 10],
    traits: {
      bodyShape: ["deep"],
      mouth: ["large"],
      markings: ["spots", "mottled"],
      finTail: ["spiny"],
      color: ["silver", "green"]
    },
    lookalikeGroup: "crappie",
    caution: "Black and white crappie can require dorsal spine counts."
  },
  {
    id: "rainbow-trout",
    commonName: "Rainbow Trout",
    scientificName: "Oncorhynchus mykiss",
    family: "Trout",
    waterTypes: ["freshwater"],
    regions: ["west", "great-lakes", "northeast", "midwest"],
    habitats: ["stream", "river", "lake"],
    peakMonths: [3, 4, 5, 6, 9, 10, 11],
    traits: {
      bodyShape: ["torpedo", "elongated"],
      mouth: ["small"],
      markings: ["spots", "horizontal-stripe"],
      finTail: ["adipose", "forked"],
      color: ["silver", "red", "green"]
    },
    lookalikeGroup: "trout",
    caution: "Wild, stocked, and migratory trout rules can differ by waterbody."
  },
  {
    id: "brook-trout",
    commonName: "Brook Trout",
    scientificName: "Salvelinus fontinalis",
    family: "Char",
    waterTypes: ["freshwater"],
    regions: ["northeast", "great-lakes", "midwest"],
    habitats: ["stream", "river", "lake"],
    peakMonths: [4, 5, 6, 9, 10],
    traits: {
      bodyShape: ["torpedo", "elongated"],
      mouth: ["small"],
      markings: ["spots", "mottled"],
      finTail: ["adipose", "forked"],
      color: ["brown", "green", "red"]
    },
    lookalikeGroup: "trout",
    caution: "Check for native brook trout protections and special waters."
  },
  {
    id: "channel-catfish",
    commonName: "Channel Catfish",
    scientificName: "Ictalurus punctatus",
    family: "Catfish",
    waterTypes: ["freshwater", "brackish"],
    regions: ["southeast", "midwest", "great-lakes", "northeast", "west"],
    habitats: ["river", "lake", "pond"],
    peakMonths: [4, 5, 6, 7, 8, 9],
    traits: {
      bodyShape: ["elongated"],
      mouth: ["barbels"],
      markings: ["spots", "plain"],
      finTail: ["forked"],
      color: ["blue", "silver", "brown"]
    },
    lookalikeGroup: "catfish",
    caution: "Different catfish species can have separate size and creel rules."
  },
  {
    id: "walleye",
    commonName: "Walleye",
    scientificName: "Sander vitreus",
    family: "Perch",
    waterTypes: ["freshwater"],
    regions: ["great-lakes", "midwest", "northeast", "west"],
    habitats: ["lake", "river"],
    peakMonths: [3, 4, 5, 6, 9, 10],
    traits: {
      bodyShape: ["elongated"],
      mouth: ["toothy", "large"],
      markings: ["mottled", "vertical-bars"],
      finTail: ["spiny", "forked"],
      color: ["yellow", "brown", "green"]
    },
    lookalikeGroup: "perch-walleye",
    caution: "Walleye seasons can be tightly managed around spawning."
  },
  {
    id: "northern-pike",
    commonName: "Northern Pike",
    scientificName: "Esox lucius",
    family: "Pike",
    waterTypes: ["freshwater", "brackish"],
    regions: ["great-lakes", "midwest", "northeast", "west"],
    habitats: ["lake", "river"],
    peakMonths: [3, 4, 5, 6, 9, 10],
    traits: {
      bodyShape: ["torpedo", "elongated"],
      mouth: ["toothy", "large"],
      markings: ["spots", "mottled"],
      finTail: ["forked"],
      color: ["green", "yellow"]
    },
    lookalikeGroup: "pike",
    caution: "Verify against muskie where ranges overlap."
  },
  {
    id: "striped-bass",
    commonName: "Striped Bass",
    scientificName: "Morone saxatilis",
    family: "Temperate bass",
    waterTypes: ["saltwater", "brackish", "freshwater"],
    regions: ["atlantic", "northeast", "southeast", "west"],
    habitats: ["inshore", "river", "lake"],
    peakMonths: [3, 4, 5, 6, 9, 10, 11],
    traits: {
      bodyShape: ["torpedo", "elongated"],
      mouth: ["large"],
      markings: ["horizontal-stripe"],
      finTail: ["forked", "spiny"],
      color: ["silver", "blue"]
    },
    lookalikeGroup: "striped-bass",
    caution: "Striped bass rules vary sharply by state, slot, and coast."
  },
  {
    id: "red-drum",
    commonName: "Red Drum",
    scientificName: "Sciaenops ocellatus",
    family: "Drum",
    waterTypes: ["saltwater", "brackish"],
    regions: ["gulf", "atlantic", "southeast"],
    habitats: ["inshore"],
    peakMonths: [4, 5, 6, 7, 8, 9, 10, 11],
    traits: {
      bodyShape: ["stout", "elongated"],
      mouth: ["downturned", "small"],
      markings: ["spots", "plain"],
      finTail: ["rounded"],
      color: ["red", "silver", "brown"]
    },
    lookalikeGroup: "drum",
    caution: "Slot limits are common; location and date matter before harvest."
  },
  {
    id: "summer-flounder",
    commonName: "Summer Flounder",
    scientificName: "Paralichthys dentatus",
    family: "Flounder",
    waterTypes: ["saltwater", "brackish"],
    regions: ["atlantic", "northeast", "southeast"],
    habitats: ["inshore"],
    peakMonths: [5, 6, 7, 8, 9, 10],
    traits: {
      bodyShape: ["flat"],
      mouth: ["large"],
      markings: ["spots", "mottled"],
      finTail: ["continuous-dorsal"],
      color: ["brown"]
    },
    lookalikeGroup: "flatfish",
    caution: "Flounder species and minimum sizes vary by state."
  },
  {
    id: "red-snapper",
    commonName: "Red Snapper",
    scientificName: "Lutjanus campechanus",
    family: "Snapper",
    waterTypes: ["saltwater"],
    regions: ["gulf", "atlantic", "southeast"],
    habitats: ["reef", "offshore"],
    peakMonths: [5, 6, 7, 8, 9],
    traits: {
      bodyShape: ["stout"],
      mouth: ["large"],
      markings: ["plain"],
      finTail: ["spiny", "forked"],
      color: ["red"]
    },
    lookalikeGroup: "snapper",
    caution: "Highly regulated; require strong evidence and current local rules."
  },
  {
    id: "yellowfin-tuna",
    commonName: "Yellowfin Tuna",
    scientificName: "Thunnus albacares",
    family: "Tuna",
    waterTypes: ["saltwater"],
    regions: ["gulf", "atlantic", "pacific"],
    habitats: ["offshore"],
    peakMonths: [4, 5, 6, 7, 8, 9, 10],
    traits: {
      bodyShape: ["torpedo"],
      mouth: ["small"],
      markings: ["plain", "horizontal-stripe"],
      finTail: ["forked"],
      color: ["blue", "yellow", "silver"]
    },
    lookalikeGroup: "tuna",
    caution: "Tuna identification can affect reporting and possession rules."
  }
];

export function getSpeciesById(id) {
  return speciesCatalog.find((species) => species.id === id);
}
