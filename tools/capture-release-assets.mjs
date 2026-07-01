import {spawn} from "node:child_process";
import {mkdtemp, mkdir, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import path from "node:path";
import {pathToFileURL} from "node:url";
import {chromium} from "playwright";


const root = path.resolve(import.meta.dirname, "..");
const output = path.join(root, "docs", "images");
const temporary = await mkdtemp(path.join(tmpdir(), "sdsa-capture-"));
const profile = path.join(temporary, "profile.json");
const database = path.join(temporary, "state.sqlite3");
const envFile = path.join(temporary, ".env");
const port = 8768;
const base = `http://127.0.0.1:${port}`;

await mkdir(output, {recursive: true});

const server = spawn("python3", [
  "scripts/signal_agent.py",
  "--profile", profile,
  "--database", database,
  "--env-file", envFile,
  "serve", "--host", "127.0.0.1", "--port", String(port), "--no-browser",
], {cwd: root, stdio: "ignore"});

async function waitForServer() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(`${base}/api/setup`);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Local capture server did not start")
}

let browser;
try {
  await waitForServer();
  browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 1});
  await page.goto(base, {waitUntil: "networkidle"});
  await page.screenshot({path: path.join(output, "onboarding.png")});

  const demo = await page.request.post(`${base}/api/reset/demo`, {
    data: {},
    headers: {"X-SDSA-Request": "local", "Content-Type": "application/json"},
  });
  if (!demo.ok()) throw new Error(`Fixture setup failed: ${demo.status()}`);
  await page.reload({waitUntil: "networkidle"});
  await page.getByRole("button", {name: "Review Queue"}).click();
  await page.screenshot({path: path.join(output, "review-queue.png")});

  await page.setViewportSize({width: 1280, height: 640});
  await page.goto(pathToFileURL(path.join(root, "docs", "social-preview.html")).href);
  await page.screenshot({path: path.join(output, "social-preview.png")});
  console.log(`Release assets written to ${output}`);
} finally {
  if (browser) await browser.close();
  server.kill("SIGTERM");
  await rm(temporary, {recursive: true, force: true});
}
