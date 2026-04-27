import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { identifyFish } from "./src/inference.js";

const root = process.cwd();
const port = Number(process.env.PORT || 4173);
const host = process.env.HOST || "127.0.0.1";
const scans = new Map();
const uploads = new Map();
const feedbackEvents = [];

const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml"
};

function resolvePath(url) {
  const pathname = new URL(url, `http://localhost:${port}`).pathname;
  const requested = pathname === "/" ? "/index.html" : pathname;
  const clean = normalize(requested).replace(/^(\.\.[/\\])+/, "");
  return join(root, clean);
}

async function readJson(req) {
  const chunks = [];

  for await (const chunk of req) {
    chunks.push(chunk);
  }

  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

function sendJson(res, status, payload) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  res.end(JSON.stringify(payload));
}

async function handleApi(req, res, url) {
  if (req.method === "POST" && url.pathname === "/api/uploads") {
    const body = await readJson(req);
    const consent = body.consent || {};

    if (!consent.identification) {
      sendJson(res, 400, { error: "Photo identification consent is required before creating an upload session." });
      return true;
    }

    const id = crypto.randomUUID();
    const now = new Date();
    const upload = {
      id,
      status: "upload-url-issued",
      storageKey: `mock-uploads/${id}`,
      uploadUrl: `/api/uploads/${id}/binary`,
      expiresAt: new Date(now.getTime() + 10 * 60 * 1000).toISOString(),
      metadata: {
        contentType: body.contentType || "application/octet-stream",
        sizeBytes: Number(body.sizeBytes || 0),
        width: body.width || null,
        height: body.height || null
      },
      consent: {
        identification: Boolean(consent.identification),
        training: Boolean(consent.training),
        retentionPolicy: consent.retentionPolicy || "delete-after-scan"
      },
      createdAt: now.toISOString()
    };

    uploads.set(id, upload);
    sendJson(res, 201, upload);
    return true;
  }

  const uploadCompleteMatch = url.pathname.match(/^\/api\/uploads\/([^/]+)\/complete$/);
  if (req.method === "POST" && uploadCompleteMatch) {
    const upload = uploads.get(uploadCompleteMatch[1]);
    if (!upload) {
      sendJson(res, 404, { error: "Upload session not found" });
      return true;
    }

    upload.status = "metadata-captured";
    upload.completedAt = new Date().toISOString();
    sendJson(res, 200, upload);
    return true;
  }

  if (req.method === "POST" && url.pathname === "/api/scans") {
    const body = await readJson(req);
    const id = crypto.randomUUID();
    const evidence = body.evidence || {};
    const upload = body.uploadId ? uploads.get(body.uploadId) : null;

    if (evidence.photoReady && !upload) {
      sendJson(res, 400, { error: "A photo scan requires a valid upload session." });
      return true;
    }

    const result = identifyFish(evidence);
    const now = new Date().toISOString();
    const scan = {
      id,
      status: "complete",
      evidence,
      uploadId: upload?.id || null,
      image: upload ? {
        uploadId: upload.id,
        status: upload.status,
        metadata: upload.metadata,
        consent: upload.consent,
        storageKey: upload.storageKey
      } : null,
      result,
      createdAt: now,
      completedAt: now,
      provider: {
        name: "local-orchestrator",
        mode: "mock",
        version: "0.1.0"
      }
    };

    scans.set(id, scan);
    sendJson(res, 201, scan);
    return true;
  }

  const scanMatch = url.pathname.match(/^\/api\/scans\/([^/]+)$/);
  if (req.method === "GET" && scanMatch) {
    const scan = scans.get(scanMatch[1]);
    sendJson(res, scan ? 200 : 404, scan || { error: "Scan not found" });
    return true;
  }

  const feedbackMatch = url.pathname.match(/^\/api\/scans\/([^/]+)\/feedback$/);
  if (req.method === "POST" && feedbackMatch) {
    const scan = scans.get(feedbackMatch[1]);
    if (!scan) {
      sendJson(res, 404, { error: "Scan not found" });
      return true;
    }

    const body = await readJson(req);
    const event = {
      id: crypto.randomUUID(),
      scanId: scan.id,
      predictedSpeciesId: scan.result.primary.id,
      selectedSpeciesId: body.speciesId || scan.result.primary.id,
      type: body.type || "confirmation",
      note: body.note || "",
      createdAt: new Date().toISOString()
    };

    feedbackEvents.unshift(event);
    scan.feedback = [event, ...(scan.feedback || [])];
    sendJson(res, 201, { event, reviewQueueSize: feedbackEvents.length });
    return true;
  }

  return false;
}

createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${host}:${port}`);
    if (url.pathname.startsWith("/api/") && await handleApi(req, res, url)) {
      return;
    }

    const filePath = resolvePath(req.url || "/");
    const body = await readFile(filePath);
    res.writeHead(200, {
      "Content-Type": types[extname(filePath)] || "application/octet-stream",
      "Cache-Control": "no-store"
    });
    res.end(body);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Not found");
  }
}).listen(port, host, () => {
  console.log(`Fishing app running at http://${host}:${port}`);
});
