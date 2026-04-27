import { speciesCatalog } from "./catalog.js";

const tierMap = [
  { min: 82, label: "Likely" },
  { min: 64, label: "Possible" },
  { min: 45, label: "Uncertain" },
  { min: 0, label: "Not Enough Evidence" }
];

export async function analyzeImageQuality(file) {
  if (!file) {
    return null;
  }

  const bitmap = await createImageBitmap(file);
  const maxSide = 240;
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  canvas.width = width;
  canvas.height = height;
  context.drawImage(bitmap, 0, 0, width, height);

  const pixels = context.getImageData(0, 0, width, height).data;
  const gray = new Float32Array(width * height);
  let total = 0;
  let totalSquared = 0;

  for (let i = 0, p = 0; i < pixels.length; i += 4, p += 1) {
    const value = 0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2];
    gray[p] = value;
    total += value;
    totalSquared += value * value;
  }

  const count = gray.length;
  const brightness = total / count;
  const variance = Math.max(0, totalSquared / count - brightness * brightness);
  const contrast = Math.sqrt(variance);
  let edges = 0;

  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const index = y * width + x;
      const dx = Math.abs(gray[index - 1] - gray[index + 1]);
      const dy = Math.abs(gray[index - width] - gray[index + width]);
      edges += dx + dy;
    }
  }

  const sharpness = edges / Math.max(1, (width - 2) * (height - 2));
  const sizeScore = scoreRange(Math.min(bitmap.width, bitmap.height), 480, 1100);
  const lightScore = scoreBell(brightness, 95, 180);
  const contrastScore = scoreRange(contrast, 24, 55);
  const sharpnessScore = scoreRange(sharpness, 14, 28);
  const overall = Math.round(sizeScore * 0.2 + lightScore * 0.25 + contrastScore * 0.2 + sharpnessScore * 0.35);

  return {
    width: bitmap.width,
    height: bitmap.height,
    overall,
    checks: [
      {
        id: "resolution",
        label: "Resolution",
        value: `${bitmap.width} x ${bitmap.height}`,
        status: sizeScore >= 70 ? "pass" : sizeScore >= 45 ? "warn" : "fail"
      },
      {
        id: "lighting",
        label: "Lighting",
        value: labelScore(lightScore),
        status: lightScore >= 70 ? "pass" : lightScore >= 45 ? "warn" : "fail"
      },
      {
        id: "contrast",
        label: "Contrast",
        value: labelScore(contrastScore),
        status: contrastScore >= 70 ? "pass" : contrastScore >= 45 ? "warn" : "fail"
      },
      {
        id: "sharpness",
        label: "Sharpness",
        value: labelScore(sharpnessScore),
        status: sharpnessScore >= 70 ? "pass" : sharpnessScore >= 45 ? "warn" : "fail"
      }
    ]
  };
}

export function identifyFish(evidence) {
  const month = evidence.caughtDate ? Number(evidence.caughtDate.slice(5, 7)) : null;
  const scored = speciesCatalog
    .map((species) => scoreSpecies(species, evidence, month))
    .sort((a, b) => b.score - a.score);

  const top = scored[0];
  const runnerUp = scored[1];
  const qualityPenalty = evidence.quality ? Math.max(0, 72 - evidence.quality.overall) * 0.35 : 18;
  const ambiguityPenalty = runnerUp ? Math.max(0, 22 - (top.score - runnerUp.score)) * 0.45 : 0;
  const rawConfidence = Math.round(Math.max(18, Math.min(96, top.score - qualityPenalty - ambiguityPenalty)));
  const confidence = evidence.photoReady ? rawConfidence : Math.min(rawConfidence, 42);
  const tier = getTier(confidence, evidence);
  const alternativeCap = evidence.photoReady ? 88 : 42;
  const alternatives = scored.slice(1, 4).map((candidate) => ({
    species: candidate.species,
    confidence: Math.round(Math.max(10, Math.min(alternativeCap, candidate.score - qualityPenalty))),
    reasons: candidate.reasons.slice(0, 3)
  }));

  return {
    tier,
    confidence,
    primary: top.species,
    alternatives,
    evidence: buildEvidence(top, evidence, month),
    guidance: buildGuidance(evidence, top, runnerUp),
    reviewRecommended: tier !== "Likely" || top.species.caution.includes("regulated")
  };
}

function scoreSpecies(species, evidence, month) {
  let score = 34;
  const reasons = [];

  for (const key of ["bodyShape", "mouth", "markings", "finTail", "color"]) {
    const value = evidence[key];
    if (!value) continue;

    if (species.traits[key]?.includes(value)) {
      score += key === "markings" || key === "mouth" ? 13 : 10;
      reasons.push(`${labelKey(key)} matches`);
    } else {
      score -= key === "markings" || key === "mouth" ? 7 : 5;
    }
  }

  if (evidence.waterType) {
    if (species.waterTypes.includes(evidence.waterType)) {
      score += 12;
      reasons.push("water type supports it");
    } else {
      score -= 20;
    }
  }

  if (evidence.region) {
    if (species.regions.includes(evidence.region)) {
      score += 9;
      reasons.push("regional range supports it");
    } else {
      score -= 10;
    }
  }

  if (evidence.habitat) {
    if (species.habitats.includes(evidence.habitat)) {
      score += 8;
      reasons.push("habitat supports it");
    } else {
      score -= 6;
    }
  }

  if (month) {
    if (species.peakMonths.includes(month)) {
      score += 5;
      reasons.push("season supports it");
    } else {
      score -= 2;
    }
  }

  if (evidence.quality?.overall >= 80) {
    score += 5;
  }

  return {
    species,
    score,
    reasons
  };
}

function buildEvidence(top, evidence, month) {
  const matchedTraits = [];
  const missing = [];

  for (const key of ["bodyShape", "mouth", "markings", "finTail", "color"]) {
    if (!evidence[key]) {
      missing.push(labelKey(key));
      continue;
    }

    if (top.species.traits[key]?.includes(evidence[key])) {
      matchedTraits.push(labelKey(key));
    }
  }

  return {
    visual: matchedTraits.length ? `Matches ${matchedTraits.join(", ")}` : "Few visual traits supplied",
    location: evidence.region && top.species.regions.includes(evidence.region)
      ? "Region supports this species"
      : evidence.region
        ? "Region is weak or outside normal range"
        : "No region supplied",
    season: month && top.species.peakMonths.includes(month)
      ? "Date is within common angling months"
      : month
        ? "Date is not a strong seasonal signal"
        : "No date supplied",
    missing: missing.length ? missing.join(", ") : "No major trait gaps",
    caution: top.species.caution
  };
}

function buildGuidance(evidence, top, runnerUp) {
  const guidance = [];

  if (!evidence.photoReady || (evidence.quality && evidence.quality.overall < 58)) {
    guidance.push("Retake with the full fish in frame and sharper side detail.");
  }

  if (!evidence.markings) {
    guidance.push("Add a clear side shot showing bars, stripes, spots, or mottling.");
  }

  if (!evidence.mouth) {
    guidance.push("Add a close view of the jaw and mouth position.");
  }

  if (runnerUp && runnerUp.species.lookalikeGroup === top.species.lookalikeGroup) {
    guidance.push(`Compare against ${runnerUp.species.commonName}; this is a known lookalike group.`);
  }

  if (!evidence.region || !evidence.waterType) {
    guidance.push("Add water type and region before using this for harvest decisions.");
  }

  return [...new Set(guidance)].slice(0, 4);
}

function getTier(confidence, evidence) {
  if (!evidence.photoReady || (evidence.quality && evidence.quality.overall < 40)) {
    return "Not Enough Evidence";
  }

  return tierMap.find((tier) => confidence >= tier.min).label;
}

function scoreRange(value, low, high) {
  if (value >= high) return 100;
  if (value <= low) return Math.max(0, (value / low) * 45);
  return 45 + ((value - low) / (high - low)) * 55;
}

function scoreBell(value, low, high) {
  if (value >= low && value <= high) return 100;
  const distance = value < low ? low - value : value - high;
  return Math.max(0, 100 - distance * 1.6);
}

function labelScore(score) {
  if (score >= 76) return "Strong";
  if (score >= 52) return "Usable";
  return "Weak";
}

function labelKey(key) {
  return {
    bodyShape: "body shape",
    mouth: "mouth",
    markings: "markings",
    finTail: "tail/fin",
    color: "color"
  }[key] || key;
}
