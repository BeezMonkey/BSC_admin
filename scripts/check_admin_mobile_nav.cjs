// Run with Node.js and Playwright installed. Uses only local assets and an isolated browser.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium, devices } = require("playwright");

const root = path.resolve(__dirname, "..");
const origin = "http://admin-navigation.test";
const markup = fs.readFileSync(path.join(root, "templates/admin_base.html"), "utf8")
  .match(/<div class="app-shell"[\s\S]*?<script/)[0].replace(/<script$/, "")
  .replace(/{% include "core\/partials\/admin_navigation_links.html" %}/g,
    '<a class="sidebar-link" href="/destination">Dashboard</a><a class="sidebar-link" href="/destination">Service Logs</a>')
  .replace(/{% block content %}{% endblock %}/,
    '<div class="page-header"><h1>Service Logs</h1><p>Review support records.</p></div>' +
    '<div style="height:100px">Content area</div><label>Notes<input id="test-input" value="Test note"></label>' +
    '<div class="table-wrap" style="overflow:auto;margin-top:20px"><table style="width:900px"><tr><td>Service date</td><td>Participant</td><td>Hours</td></tr></table></div>' +
    '<div id="scroll-region" style="overflow:auto;margin-top:20px"><div style="width:900px;height:50px">Horizontal planner</div></div>' +
    '<div style="height:1600px">Page content</div>')
  .replace(/{%[\s\S]*?%}|{{[\s\S]*?}}/g, "");
const html = '<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">' +
  '<link rel="stylesheet" href="/static/css/app.css"><link rel="stylesheet" href="/static/css/admin.css">' +
  '<main class="page">' + markup + '</main><script src="/static/js/admin_nav.js"></script>';

(async function () {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}),
  });
  try {
    const context = await browser.newContext({ ...devices["iPhone 13"] });
    const errors = [];
    await context.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      if (!url.pathname.startsWith("/static/")) return route.fulfill({ contentType: "text/html", body: html });
      const file = path.resolve(root, "." + url.pathname);
      if (!file.startsWith(path.join(root, "static") + path.sep) || !fs.existsSync(file)) return route.abort();
      const types = { ".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2" };
      return route.fulfill({ contentType: types[path.extname(file)], body: fs.readFileSync(file) });
    });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(origin + "/previous");
    await page.goto(origin + "/current");
    const cdp = await context.newCDPSession(page);
    async function swipe(x, y, dx, dy, steps = 12, delay = 20) {
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y, id: 1 }] });
      for (let n = 1; n <= steps; n++) {
        await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: x + dx * n / steps, y: y + dy * n / steps, id: 1 }] });
        await page.waitForTimeout(delay);
      }
      await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      await page.waitForTimeout(500);
    }
    const expanded = () => page.locator(".admin-mobile-menu-button").getAttribute("aria-expanded");
    const clickClose = async () => {
      await page.locator(".admin-mobile-close-button").tap();
      await page.waitForTimeout(300);
    };
    await swipe(65, 110, 210, 0);
    assert.equal(page.url(), origin + "/current", "swipe must not navigate backward");
    assert.equal(await expanded(), "true", "touch swipe opens the drawer");
    assert.equal(await page.locator(".admin-mobile-surface").evaluate(el => getComputedStyle(el).transform), "none", "content remains stationary with the original overlay style");
    console.log("PASS native touch opens overlay without history navigation");
    await swipe(200, 25, -180, 0);
    assert.equal(await expanded(), "false", "left swipe closes drawer");
    console.log("PASS native touch closes overlay");
    await swipe(180, 110, 170, 0);
    assert.equal(await expanded(), "true", "content swipe is not limited to a narrow lane");
    await clickClose();
    await swipe(65, 200, 200, 0);
    assert.equal(await expanded(), "true", "plain content with native touch-action also supports swipe");
    await clickClose();
    console.log("PASS inset and central content gestures");
    await swipe(65, 110, 25, 0, 12, 50);
    assert.equal(await expanded(), "false", "short slow drag snaps closed");
    console.log("PASS incomplete drag snaps back");
    await swipe(80, 600, 0, -250);
    assert.ok(await page.evaluate(() => scrollY) > 50, "vertical page scroll must work");
    assert.equal(await expanded(), "false");
    await page.evaluate(() => scrollTo(0, 0));
    console.log("PASS vertical page scrolling");
    const input = await page.locator("#test-input").boundingBox();
    await swipe(input.x + 40, input.y + 20, 150, 0);
    assert.equal(await expanded(), "false", "input gestures must not open the drawer");
    for (const selector of [".table-wrap", "#scroll-region"]) {
      const box = await page.locator(selector).boundingBox();
      await swipe(290, box.y + 20, -180, 0);
      assert.ok(await page.locator(selector).evaluate(el => el.scrollLeft) > 50, "horizontal scrolling must work: " + selector);
      await swipe(65, box.y + 20, 180, 0);
      assert.equal(await expanded(), "false", "horizontal scroll region must not open drawer");
    }
    console.log("PASS input and horizontal scroll guards");
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: 65, y: 110, id: 1 }] });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: 145, y: 110, id: 1 }] });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchCancel", touchPoints: [] });
    await page.waitForTimeout(300);
    assert.equal(await expanded(), "false");
    assert.equal(await page.locator(".admin-mobile-drawer").evaluate(el => el.hidden), true);
    console.log("PASS cancelled touch resets");
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: 65, y: 110, id: 1 }] });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: 130, y: 110, id: 1 }] });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: 130, y: 110, id: 1 }, { x: 220, y: 180, id: 2 }] });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await page.waitForTimeout(300);
    assert.equal(await expanded(), "false", "second finger cancels the drawer gesture");
    assert.equal(await page.locator(".admin-mobile-surface").evaluate(el => el.inert), false);
    console.log("PASS multi-touch cancellation");
    await page.locator(".admin-mobile-menu-button").tap();
    await page.waitForTimeout(300);
    assert.equal(await expanded(), "true");
    assert.equal(await page.locator(".admin-mobile-surface").evaluate(el => el.inert), true);
    await page.keyboard.press("Shift+Tab");
    assert.equal(await page.locator(".admin-mobile-logout button").evaluate(el => el === document.activeElement), true);
    await page.keyboard.press("Tab");
    assert.equal(await page.locator(".admin-mobile-close-button").evaluate(el => el === document.activeElement), true);
    console.log("PASS keyboard focus stays in drawer");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    assert.equal(await expanded(), "false");
    await page.locator(".admin-mobile-menu-button").tap();
    await page.waitForTimeout(300);
    await page.locator(".admin-mobile-drawer-backdrop").tap({ position: { x: 365, y: 200 } });
    await page.waitForTimeout(300);
    assert.equal(await expanded(), "false");
    console.log("PASS hamburger, Escape and backdrop");
    await page.locator(".admin-mobile-menu-button").tap();
    await page.waitForTimeout(300);
    await page.locator(".admin-mobile-drawer a").first().tap();
    await page.waitForURL(origin + "/destination");
    console.log("PASS navigation links still work");
    await swipe(8, 110, 170, 0);
    assert.equal(await expanded(), "false", "browser-edge swipe never opens the drawer");
    console.log("PASS browser-edge exclusion");
    for (const width of [320, 390, 760]) {
      await page.setViewportSize({ width, height: 844 });
      await page.locator(".admin-mobile-menu-button").tap();
      await page.waitForTimeout(300);
      const bounds = await page.locator(".admin-mobile-drawer").boundingBox();
      assert.ok(bounds.x >= -1 && bounds.x + bounds.width <= width, "drawer fits mobile viewport");
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "no page horizontal overflow");
      if (process.env.ADMIN_NAV_CAPTURE_DIR) {
        fs.mkdirSync(process.env.ADMIN_NAV_CAPTURE_DIR, { recursive: true });
        await page.screenshot({ path: path.join(process.env.ADMIN_NAV_CAPTURE_DIR, "drawer-" + width + ".png") });
      }
      await clickClose();
    }
    console.log("PASS 320px, 390px and 760px layouts");
    await page.locator(".admin-mobile-menu-button").tap();
    await page.waitForTimeout(300);
    await page.setViewportSize({ width: 1280, height: 800 });
    assert.equal(await page.locator(".admin-mobile-menu-button").isVisible(), false);
    assert.equal(await page.locator(".sidebar").isVisible(), true);
    assert.equal(await page.locator(".admin-mobile-surface").evaluate(el => el.inert), false);
    console.log("PASS desktop navigation");
    if (process.env.ADMIN_NAV_CAPTURE_DIR) await page.screenshot({ path: path.join(process.env.ADMIN_NAV_CAPTURE_DIR, "desktop.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.locator(".admin-mobile-menu-button").tap();
    await page.waitForTimeout(300);
    assert.equal(await expanded(), "true");
    assert.ok(parseFloat(await page.locator(".admin-mobile-drawer").evaluate(el => getComputedStyle(el).transitionDuration)) < .001);
    await clickClose();
    console.log("PASS reduced-motion preference");
    assert.deepEqual(errors, []);
    console.log("PASS no JavaScript errors");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
