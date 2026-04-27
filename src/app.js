import { speciesCatalog, getSpeciesById } from "./catalog.js";
import { completeUpload, createScan, createUploadSession, submitFeedback } from "./api.js";
import { analyzeImageQuality } from "./inference.js";

const state = {
  photoFile: null,
  photoDataUrl: "",
  quality: null,
  upload: null,
  lastResult: null,
  currentScan: null
};

const elements = {
  scanStatus: document.querySelector("#scanStatus"),
  photoInput: document.querySelector("#fishPhoto"),
  previewFrame: document.querySelector("#previewFrame"),
  photoPreview: document.querySelector("#photoPreview"),
  qualityGrid: document.querySelector("#qualityGrid"),
  uploadStatus: document.querySelector("#uploadStatus"),
  identifyConsent: document.querySelector("#identifyConsent"),
  trainingConsent: document.querySelector("#trainingConsent"),
  retentionPolicy: document.querySelector("#retentionPolicy"),
  resultView: document.querySelector("#resultView"),
  catchLog: document.querySelector("#catchLog"),
  identifyButton: document.querySelector("#identifyButton")
};

const fields = [
  "region",
  "waterType",
  "habitat",
  "caughtDate",
  "waterbody",
  "bodyShape",
  "mouth",
  "markings",
  "finTail",
  "color"
];

document.querySelector("#caughtDate").valueAsDate = new Date();
elements.photoInput.addEventListener("change", handlePhotoChange);
elements.identifyButton.addEventListener("click", runIdentification);
elements.resultView.addEventListener("click", handleResultAction);
elements.catchLog.addEventListener("click", handleLogAction);
fields.forEach((id) => document.querySelector(`#${id}`).addEventListener("change", refreshStatus));
[
  elements.identifyConsent,
  elements.trainingConsent,
  elements.retentionPolicy
].forEach((control) => control.addEventListener("change", handlePrivacyChange));

renderQuality();
renderUploadStatus();
renderCatchLog();
refreshStatus();

async function handlePhotoChange(event) {
  const [file] = event.target.files || [];
  if (!file) return;

  state.photoFile = file;
  state.upload = null;
  state.photoDataUrl = await readFileAsDataUrl(file);
  elements.photoPreview.src = state.photoDataUrl;
  elements.previewFrame.classList.remove("is-empty");
  elements.scanStatus.textContent = "Checking photo";
  elements.qualityGrid.innerHTML = `<div class="quality-card pending">Analyzing image...</div>`;
  renderUploadStatus();

  try {
    state.quality = await analyzeImageQuality(file);
    renderQuality();
    refreshStatus();
  } catch (error) {
    state.quality = null;
    elements.qualityGrid.innerHTML = `<div class="quality-card fail">Image check failed</div>`;
    elements.scanStatus.textContent = "Photo issue";
  }
}

async function runIdentification() {
  const evidence = getEvidence();
  renderPendingResult();
  elements.identifyButton.disabled = true;
  elements.scanStatus.textContent = "Scanning";

  try {
    const upload = await prepareUpload(evidence);
    const scan = await createScan(evidence, { uploadId: upload?.id });
    state.currentScan = scan;
    state.lastResult = scan.result;
    renderResult(scan.result, scan);
    elements.scanStatus.textContent = scan.result.tier;
  } catch (error) {
    renderError(error);
    elements.scanStatus.textContent = "Scan failed";
  } finally {
    elements.identifyButton.disabled = false;
  }
}

function getEvidence() {
  return {
    ...Object.fromEntries(fields.map((id) => [id, document.querySelector(`#${id}`).value])),
    photoReady: Boolean(state.photoFile),
    quality: state.quality,
    consent: getConsent()
  };
}

async function prepareUpload(evidence) {
  if (!state.photoFile) {
    return null;
  }

  if (!evidence.consent.identification) {
    throw new Error("Photo identification consent is required for scans with images.");
  }

  if (state.upload) {
    return state.upload;
  }

  elements.uploadStatus.textContent = "Preparing upload session";
  const upload = await createUploadSession({
    contentType: state.photoFile.type,
    sizeBytes: state.photoFile.size,
    width: state.quality?.width,
    height: state.quality?.height,
    consent: evidence.consent
  });

  state.upload = await completeUpload(upload.id);
  renderUploadStatus();
  return state.upload;
}

function getConsent() {
  return {
    identification: elements.identifyConsent.checked,
    training: elements.trainingConsent.checked,
    retentionPolicy: elements.retentionPolicy.value
  };
}

function renderQuality() {
  if (!state.quality) {
    elements.qualityGrid.innerHTML = `
      <div class="quality-card pending">
        <strong>Waiting</strong>
        <span>Add a photo to run checks.</span>
      </div>
    `;
    return;
  }

  elements.qualityGrid.innerHTML = `
    <div class="quality-card score ${qualityClass(state.quality.overall)}">
      <strong>${state.quality.overall}</strong>
      <span>Photo score</span>
    </div>
    ${state.quality.checks.map((check) => `
      <div class="quality-card ${check.status}">
        <strong>${check.label}</strong>
        <span>${check.value}</span>
      </div>
    `).join("")}
  `;
}

function renderUploadStatus() {
  if (!state.photoFile) {
    elements.uploadStatus.textContent = "No upload session";
    return;
  }

  if (!elements.identifyConsent.checked) {
    elements.uploadStatus.textContent = "Photo consent off";
    return;
  }

  if (!state.upload) {
    elements.uploadStatus.textContent = "Upload session ready on scan";
    return;
  }

  elements.uploadStatus.textContent = `Upload ${state.upload.id.slice(0, 8)} · ${readable(state.upload.consent.retentionPolicy)}`;
}

function renderPendingResult() {
  elements.resultView.className = "result-view";
  elements.resultView.innerHTML = `
    <div class="result-empty compact-empty">
      <strong>Running scan</strong>
      <span>Creating scan session and applying priors.</span>
    </div>
  `;
}

function renderError(error) {
  elements.resultView.className = "result-view";
  elements.resultView.innerHTML = `
    <div class="result-empty error-empty">
      <strong>Scan failed</strong>
      <span>${error.message || "Try again."}</span>
    </div>
  `;
}

function renderResult(result, scan = state.currentScan) {
  const primary = result.primary;
  elements.resultView.className = "result-view";
  elements.resultView.innerHTML = `
    <div class="result-head">
      <div>
        <span class="tier ${tierClass(result.tier)}">${result.tier}</span>
        <h3>${primary.commonName}</h3>
        <p><em>${primary.scientificName}</em></p>
        <p class="scan-meta">${scan?.provider?.name || "local"} · scan ${scan?.id?.slice(0, 8) || "draft"}</p>
        ${scan?.image ? `<p class="scan-meta">photo ${scan.image.status} · ${readable(scan.image.consent.retentionPolicy)}</p>` : ""}
      </div>
      <div class="confidence-meter" aria-label="Confidence ${result.confidence} percent">
        <span style="--confidence:${result.confidence}%"></span>
        <strong>${result.confidence}%</strong>
      </div>
    </div>

    <div class="evidence-list">
      ${renderEvidenceRow("Visual", result.evidence.visual)}
      ${renderEvidenceRow("Location", result.evidence.location)}
      ${renderEvidenceRow("Season", result.evidence.season)}
      ${renderEvidenceRow("Missing", result.evidence.missing)}
      ${renderEvidenceRow("Caution", result.evidence.caution)}
    </div>

    <div class="alternatives">
      <h4>Alternatives</h4>
      ${result.alternatives.map((candidate) => `
        <button type="button" class="alternative" data-action="choose-alternative" data-species-id="${candidate.species.id}">
          <span>${candidate.species.commonName}</span>
          <strong>${candidate.confidence}%</strong>
        </button>
      `).join("")}
    </div>

    <div class="guidance">
      <h4>Next Evidence</h4>
      <ul>${result.guidance.map((item) => `<li>${item}</li>`).join("") || "<li>No extra evidence needed for casual logging.</li>"}</ul>
    </div>

    <div class="feedback-row">
      <button type="button" class="secondary-action" data-action="correct">Correct ID</button>
      <button type="button" class="primary-action" data-action="save">Confirm & Save</button>
    </div>
  `;
}

function renderEvidenceRow(label, value) {
  return `
    <div class="evidence-row">
      <span>${label}</span>
      <strong>${value}</strong>
    </div>
  `;
}

async function handleResultAction(event) {
  const button = event.target.closest("button");
  if (!button || !state.lastResult) return;

  const action = button.dataset.action;
  if (action === "save") {
    await sendFeedback({
      speciesId: state.lastResult.primary.id,
      type: "confirmed"
    });
    saveCatch(state.lastResult.primary.id, "confirmed");
  }

  if (action === "choose-alternative") {
    const speciesId = button.dataset.speciesId;
    const species = getSpeciesById(speciesId);
    if (!species) return;
    state.lastResult = {
      ...state.lastResult,
      primary: species,
      tier: "User Corrected",
      confidence: Math.min(state.lastResult.confidence, 80)
    };
    renderResult(state.lastResult);
    await sendFeedback({
      speciesId,
      type: "alternative-selected"
    });
  }

  if (action === "correct") {
    renderCorrectionForm();
  }
}

function renderCorrectionForm() {
  const options = speciesCatalog
    .map((species) => `<option value="${species.id}">${species.commonName}</option>`)
    .join("");

  elements.resultView.insertAdjacentHTML("beforeend", `
    <form class="correction-form" id="correctionForm">
      <label>
        <span>Correct species</span>
        <select id="correctSpecies">${options}</select>
      </label>
      <label>
        <span>Note</span>
        <input id="correctionNote" type="text" placeholder="Optional" />
      </label>
      <button type="submit" class="primary-action">Save Correction</button>
    </form>
  `);

  document.querySelector("#correctionForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const speciesId = document.querySelector("#correctSpecies").value;
    const note = document.querySelector("#correctionNote").value;
    await sendFeedback({
      speciesId,
      type: "manual-correction",
      note
    });
    saveCatch(speciesId, "corrected");
  }, { once: true });
}

function saveCatch(speciesId, status) {
  const species = getSpeciesById(speciesId);
  const evidence = getEvidence();
  const catches = getStored("catchLog");
  catches.unshift({
    id: crypto.randomUUID(),
    speciesId,
    commonName: species.commonName,
    status,
    date: evidence.caughtDate || new Date().toISOString().slice(0, 10),
    waterbody: evidence.waterbody,
    waterType: evidence.waterType,
    region: evidence.region,
    tier: state.lastResult?.tier || "Saved",
    confidence: state.lastResult?.confidence || 0
  });
  localStorage.setItem("catchLog", JSON.stringify(catches.slice(0, 20)));
  renderCatchLog();
  elements.scanStatus.textContent = "Saved";
}

async function sendFeedback(feedback) {
  if (state.currentScan?.id) {
    try {
      await submitFeedback(state.currentScan.id, feedback);
    } catch (error) {
      saveReviewEvent(feedback.speciesId, `${feedback.type}-api-failed`, error.message);
    }
    return;
  }

  saveReviewEvent(feedback.speciesId, feedback.type, feedback.note);
}

function saveReviewEvent(speciesId, reason, note = "") {
  const reviews = getStored("reviewQueue");
  reviews.unshift({
    id: crypto.randomUUID(),
    speciesId,
    predictedSpeciesId: state.lastResult?.primary?.id,
    reason,
    note,
    evidence: getEvidence(),
    createdAt: new Date().toISOString()
  });
  localStorage.setItem("reviewQueue", JSON.stringify(reviews.slice(0, 50)));
}

function renderCatchLog() {
  const catches = getStored("catchLog");
  if (!catches.length) {
    elements.catchLog.innerHTML = `<div class="empty-log">No confirmed catches yet.</div>`;
    return;
  }

  elements.catchLog.innerHTML = catches.map((item) => `
    <article class="log-item">
      <div>
        <strong>${item.commonName}</strong>
        <span>${[item.date, item.waterbody, readable(item.waterType)].filter(Boolean).join(" · ")}</span>
      </div>
      <button type="button" aria-label="Remove ${item.commonName}" data-action="remove-log" data-id="${item.id}">x</button>
    </article>
  `).join("");
}

function handleLogAction(event) {
  const button = event.target.closest("button[data-action='remove-log']");
  if (!button) return;

  const catches = getStored("catchLog").filter((item) => item.id !== button.dataset.id);
  localStorage.setItem("catchLog", JSON.stringify(catches));
  renderCatchLog();
}

function refreshStatus() {
  if (!state.photoFile) {
    elements.scanStatus.textContent = "No scan";
    return;
  }

  elements.scanStatus.textContent = state.quality ? `Photo ${state.quality.overall}` : "Photo added";
}

function handlePrivacyChange() {
  state.upload = null;
  renderUploadStatus();
  refreshStatus();
}

function getStored(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(reader.result));
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsDataURL(file);
  });
}

function qualityClass(score) {
  if (score >= 72) return "pass";
  if (score >= 48) return "warn";
  return "fail";
}

function tierClass(tier) {
  return tier.toLowerCase().replaceAll(" ", "-");
}

function readable(value) {
  return value ? value.replaceAll("-", " ") : "";
}
