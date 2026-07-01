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

async function assertNoHorizontalOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    content: document.documentElement.scrollWidth,
  }));
  if (dimensions.content > dimensions.viewport + 1) {
    throw new Error(`${label} overflows horizontally: ${dimensions.content}px content in ${dimensions.viewport}px viewport`);
  }
}

async function assertText(locator, expected, label) {
  const content = (await locator.textContent()) || "";
  if (!content.includes(expected)) throw new Error(`${label} did not show ${JSON.stringify(expected)}`);
}

let browser;
try {
  await waitForServer();
  browser = await chromium.launch({headless: true});

  const loadingPage = await browser.newPage({viewport: {width: 390, height: 844}, deviceScaleFactor: 1});
  await loadingPage.route("**/api/setup", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.continue();
  });
  await loadingPage.goto(base, {waitUntil: "domcontentloaded"});
  await assertText(loadingPage.locator("#company-name"), "Loading setup", "Loading state");
  await loadingPage.waitForLoadState("networkidle");
  await assertNoHorizontalOverflow(loadingPage, "Mobile setup");
  await loadingPage.close();

  const errorPage = await browser.newPage({viewport: {width: 390, height: 844}, deviceScaleFactor: 1});
  await errorPage.route("**/api/setup", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({error: "Synthetic setup failure"}),
  }));
  await errorPage.goto(base, {waitUntil: "networkidle"});
  await assertText(errorPage.locator("#error-banner"), "Synthetic setup failure", "Error state");
  await errorPage.close();

  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 1});
  await page.goto(base, {waitUntil: "networkidle"});
  await assertText(page.locator("#company-name"), "Set up your listening", "Incomplete setup state");
  await assertNoHorizontalOverflow(page, "Desktop setup");
  await page.screenshot({path: path.join(output, "onboarding.png")});

  const testCredential = `sc_${"x".repeat(24)}`;
  const credential = await page.request.post(`${base}/api/credential`, {
    data: {action: "save", api_key: testCredential},
    headers: {"X-SDSA-Request": "local", "Content-Type": "application/json"},
  });
  if (!credential.ok()) throw new Error(`Credential setup failed: ${credential.status()}`);
  await page.reload({waitUntil: "networkidle"});
  await page.route("**/api/provider/test", (route) => route.fulfill({
    status: 502,
    contentType: "application/json",
    body: JSON.stringify({error: "Synthetic provider failure"}),
  }));
  await page.getByRole("button", {name: "Test connection"}).click();
  await page.waitForFunction(
    (expected) => document.querySelector("#provider-message")?.textContent.includes(expected),
    "Synthetic provider failure",
  );
  await assertText(page.locator("#provider-message"), "Synthetic provider failure", "Provider error state");
  await page.unroute("**/api/provider/test");
  const credentialRemoval = await page.request.post(`${base}/api/credential`, {
    data: {action: "remove"},
    headers: {"X-SDSA-Request": "local", "Content-Type": "application/json"},
  });
  if (!credentialRemoval.ok()) throw new Error(`Credential cleanup failed: ${credentialRemoval.status()}`);

  const demo = await page.request.post(`${base}/api/reset/demo`, {
    data: {},
    headers: {"X-SDSA-Request": "local", "Content-Type": "application/json"},
  });
  if (!demo.ok()) throw new Error(`Fixture setup failed: ${demo.status()}`);
  await page.reload({waitUntil: "networkidle"});
  await page.getByRole("button", {name: "Review Queue"}).click();
  await assertText(page.getByRole("heading", {name: "Review Queue"}), "Review Queue", "Populated review state");
  await assertNoHorizontalOverflow(page, "Desktop review queue");
  await page.screenshot({path: path.join(output, "review-queue.png")});

  await page.getByRole("button", {name: "Experiments"}).focus();
  await page.keyboard.press("Enter");
  await assertText(page.getByRole("heading", {name: "Experiment Readout"}), "Experiment Readout", "Keyboard navigation");

  const mobilePage = await browser.newPage({viewport: {width: 390, height: 844}, deviceScaleFactor: 1});
  await mobilePage.goto(base, {waitUntil: "networkidle"});
  await mobilePage.getByRole("button", {name: "Review Queue"}).click();
  await assertNoHorizontalOverflow(mobilePage, "Mobile review queue");
  await mobilePage.getByRole("button", {name: "Experiments"}).click();
  await assertNoHorizontalOverflow(mobilePage, "Mobile experiment readout");
  await mobilePage.close();

  await page.setViewportSize({width: 1280, height: 640});
  await page.goto(pathToFileURL(path.join(root, "docs", "social-preview.html")).href);
  await page.screenshot({path: path.join(output, "social-preview.png")});
  console.log(`Browser states verified and release assets written to ${output}`);
} finally {
  if (browser) await browser.close();
  server.kill("SIGTERM");
  await rm(temporary, {recursive: true, force: true});
}
