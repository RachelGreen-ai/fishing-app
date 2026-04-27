export async function createScan(evidence) {
  return requestJson("/api/scans", {
    method: "POST",
    body: JSON.stringify({ evidence })
  });
}

export async function getScan(scanId) {
  return requestJson(`/api/scans/${encodeURIComponent(scanId)}`);
}

export async function submitFeedback(scanId, feedback) {
  return requestJson(`/api/scans/${encodeURIComponent(scanId)}/feedback`, {
    method: "POST",
    body: JSON.stringify(feedback)
  });
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    ...options
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error || `Request failed with ${response.status}`);
  }

  return payload;
}
