// Drive the running Next.js dev server in a real browser and screenshot it.
//
// Uses Playwright against the SYSTEM Google Chrome (channel: "chrome") — no
// chromium download needed. Headless Chrome's own `--screenshot` flag does NOT
// apply Next.js App Router CSS (data-precedence <link>s), so screenshots come
// out unstyled; Playwright with waitUntil:"networkidle" renders correctly.
//
// Prereq: `npm i -D playwright --no-save` in frontend/ (module only, no browser).
// Run FROM frontend/ (ESM resolves ./node_modules there):  node .claude/skills/run-frontend/driver.mjs [url]
//
// Default URL drives the workflow builder (the three-pane React Flow editor);
// pass any route to just nav + screenshot + console-error check that page.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const TARGET = process.argv[2] || "http://localhost:3000/trading-room/workflow";
const OUT = new URL("./screenshots/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const errors = [];

const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

await page.goto(TARGET, { waitUntil: "networkidle" });

const hasCanvas = await page.locator(".react-flow").count();
if (hasCanvas) {
  // workflow builder: prove the canvas renders nodes and the panes are interactive
  await page.waitForSelector(".react-flow__node", { timeout: 15000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/desktop.png` });
  console.log(`canvas: ${await page.locator(".react-flow__node").count()} nodes, ${await page.locator(".react-flow__edge").count()} edges`);

  await page.locator(".react-flow__node").first().click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/node-selected.png` });
  console.log("inspector:", JSON.stringify((await page.locator("aside").last().innerText().catch(() => "")).slice(0, 100)));

  console.log("validation before:", await page.locator("text=/有效|缺少|循環/").first().innerText().catch(() => "?"));
  const edge = page.locator(".react-flow__edge").first();
  if (await edge.count()) { await edge.click({ force: true }); await page.keyboard.press("Backspace"); await page.waitForTimeout(300); }
  console.log("validation after edge delete:", await page.locator("text=/有效|缺少|循環/").first().innerText().catch(() => "?"));
  const undo = page.locator('button[title="復原"]');
  if (await undo.count()) { await undo.click(); await page.waitForTimeout(300); }
  console.log("validation after undo:", await page.locator("text=/有效|缺少|循環/").first().innerText().catch(() => "?"));

  // full-stack: Run the workflow (frontend -> backend -> DB session -> broker -> result panel)
  const runBtn = page.locator('button:has-text("執行")');
  if (await runBtn.count()) {
    await runBtn.click();
    await page.waitForTimeout(8000); // Run fetches live OHLCV; give it time
    await page.screenshot({ path: `${OUT}/after-run.png` });
    console.log("run result:", JSON.stringify((await page.locator("text=/Status/").first().innerText().catch(() => "no result panel")).slice(0, 120)));
  }

  await page.setViewportSize({ width: 1024, height: 800 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/tablet.png` });
} else {
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/page.png` });
}

console.log("console errors:", errors.length ? JSON.stringify(errors.slice(0, 8)) : "none");
console.log("screenshots in:", OUT);
await browser.close();
