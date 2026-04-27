import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { identifyFish } from "./src/inference.js";

const root = process.cwd();
const port = Number(process.env.PORT || 4173);
const host = process.env.HOST || "127.0.0.1";
const scans = new Map();
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
  if (req.method === "POST" && url.pathname === "/api/scans") {
    const body = await readJson(req);
    const id = crypto.randomUUID();
    const evidence = body.evidence || {};
    const result = identifyFish(evidence);
    const now = new Date().toISOString();
    const scan = {
      id,
      status: "complete",
      evidence,
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
