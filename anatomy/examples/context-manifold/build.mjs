import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../kit/iso-kit.mjs";
import { kitScript } from "../../scripts/inline-kit.mjs";
import { PORTS, SHARE_PER_PORT, REACH, readoutOf } from "./model.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const theme = process.argv.includes("--light") ? "light" : "dark";

const WIDTH = 620;
const HEIGHT = 400;

const PLATE = { x: -152, y: -50, w: 332, d: 106, r: 8 };
const PLATE_H = 12;
const FOOT_H = 5;

const RAIL_Z = 15;
const RAIL_H = 3;
const CARRIAGE_Z = RAIL_Z + RAIL_H;
const CARRIAGE_H = 5;
const CARRIAGE_TOP = CARRIAGE_Z + CARRIAGE_H;

const STOP_X = [-142, 132];
const STOP_TOP = 26;

const PAD = { w: 22, d: 52 };
const PAD_TOP = 8;

const DIAL = [142, 0];
const DIAL_R = 22;
const DIAL_Z = 90;
const DIAL_H = 10;
const DIAL_TOP = DIAL_Z + DIAL_H;
const PER_TURN = PORTS.length;

const HEX = [-3 / 4, 3 / 4]; // needle sweep, in turns of the dial

const P = k.fitProjection(
  [
    ...k.boxCorners(PLATE, -PLATE_H - FOOT_H, 0),
    [PLATE.x, PLATE.y, STOP_TOP],
    [PLATE.x + PLATE.w, PLATE.y, STOP_TOP],
    [PLATE.x, PLATE.y + PLATE.d, PAD_TOP + 4],
    [PLATE.x + PLATE.w, PLATE.y + PLATE.d, DIAL_TOP],
    [DIAL[0] + DIAL_R, 0, DIAL_TOP],
    [DIAL[0] - DIAL_R, 0, DIAL_TOP],
  ],
  WIDTH,
  HEIGHT,
  { pad: 30, azimuth: 42 },
);

const at = (point) => k.iso(point, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));

function plate() {
  const out = [`<path class="iso-halo" d="${k.haloOf(PLATE, -PLATE_H - FOOT_H, PLATE_H, P)}"/>`];
  for (const [x, y] of byDepth(k.corners(PLATE, 24))) {
    out.push(S(k.cylinder(x, y, 7, -PLATE_H - FOOT_H, 1.6, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 5.4, -PLATE_H - FOOT_H + 1.6, FOOT_H - 1.6, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(PLATE, -PLATE_H, PLATE_H, P, 8, 1.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: "lo" }));
  const screws = k.corners(PLATE, 10);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));

  const strip = { x: PLATE.x + 14, y: PLATE.y + PLATE.d - 15, w: 258, d: 7, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y + 0.8, 0.6, [2, 3.6], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  out.push(D([at([strip.x + 2, strip.y + 3.5, 0.6]), at([strip.x + strip.w - 2, strip.y + 3.5, 0.6])], { size: 0.45 }));

  const label = { x: PLATE.x + 10, y: PLATE.y + 4, w: 46, d: 14, r: 1.5 };
  out.push(S(k.slabOf(label, 0, 0.8, P, 4), { tone: "lo", crease: "none" }));
  out.push(L(k.planOutline(k.insetPlan(label, 1.6), 0.8, P), { tone: "faint" }));
  out.push(L(k.lineOnTop([label.x + 5, label.y + 3.5], [label.x + label.w - 5, label.y + 3.5], 0.9, P), { tone: "lo", free: true }));
  out.push(L(k.lineOnTop([label.x + 5, label.y + 7], [label.x + label.w - 12, label.y + 7], 0.9, P), { tone: "lo", free: true }));
  out.push(L(k.lineOnTop([label.x + 5, label.y + 10.5], [label.x + label.w - 18, label.y + 10.5], 0.9, P), { tone: "lo", free: true }));
  out.push(D([at([label.x + label.w - 4, label.y + 3.5, 0.8]), at([label.x + 4, label.y + label.d - 3, 0.8])], { size: 0.4 }));
  return out.join("");
}

function feedBank() {
  const out = [];
  const block = { x: 8, y: -48, w: 112, d: 16, r: 3 };
  out.push(S(k.slabOf(block, 0, 16, P, 4, 0.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(block, 2.2), 16, P, 4), { tone: "faint" }));
  const screws = k.corners(block, 6);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 1.9, 16, P, 14)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 16])), { size: 0.42 }));
  for (let i = 0; i < 5; i++) {
    const x = block.x + 14 + i * 21;
    const y = block.y + block.d / 2;
    out.push(S(k.cylinder(x, y, 3.4, 16, 5.4, P, 22), { tone: "hi", crease: "lo" }));
    out.push(L(k.knurl(x, y, 3.4, 17, 20.4, 20, P, 0.2), { tone: "lo" }));
    out.push(L(k.ring(x, y, 3.6, 16, P, 20), { tone: "lo" }));
    out.push(L(k.sideArc(x, y, 3.4, 20, P, 14), { tone: "faint" }));
    out.push(D([at([x, y, 21.4])], { size: 0.45 }));
  }
  return out.join("");
}

function posts() {
  const out = [];
  const feet = [[-130, -26], [-130, 26], [124, -26], [124, 26]];
  for (const [x, y] of feet) {
    out.push(S(k.cylinder(x, y, 4.2, 0, 4, P, 24), { tone: "mid" }));
    out.push(S(k.cylinder(x, y, 3.2, 4, RAIL_Z - 4, P, 24), { tone: "mid", crease: "none" }));
    out.push(L(k.sideArc(x, y, 3.2, 6, P, 14), { tone: "faint" }));
  }
  for (const x of STOP_X) {
    out.push(S(k.slabOf({ x, y: -29, w: 5, d: 54, r: 1.2 }, RAIL_Z, STOP_TOP - RAIL_Z, P, 3, 0.5), { tone: "mid" }));
    out.push(D([at([x + 2.5, -22, STOP_TOP]), at([x + 2.5, 22, STOP_TOP])], { size: 0.45 }));
  }
  return out.join("");
}

function rail(y) {
  const out = [];
  out.push(S(k.slabOf({ x: -136, y, w: 266, d: 5, r: 1 }, RAIL_Z, RAIL_H, P, 3, 0.4), { tone: "mid" }));
  out.push(D([at([-130, y + 2.5, RAIL_Z + RAIL_H]), at([124, y + 2.5, RAIL_Z + RAIL_H])], { size: 0.4 }));
  return out.join("");
}

function port(entry) {
  const out = [];
  const plan = { x: entry.x - PAD.w / 2, y: -PAD.d / 2, w: PAD.w, d: PAD.d, r: 3 };
  out.push(S(k.slabOf(plan, 0, PAD_TOP, P, 4, 0.6), { tone: "hi", crease: "lo" }));
  out.push(L(k.planOutline(k.insetPlan(plan, 2.4), PAD_TOP, P, 4), { tone: "faint" }));
  out.push(L(k.ring(entry.x, 0, 6.4, PAD_TOP, P, 28), { tone: "mid" }));
  out.push(D([at([entry.x, 0, PAD_TOP])], { size: 0.45 }));
  const screws = [[plan.x + 4, plan.y + 4], [plan.x + plan.w - 4, plan.y + plan.d - 4]];
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 1.9, PAD_TOP, P, 14)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, PAD_TOP])), { size: 0.42 }));
  const marks = [1, 2, 3].map((index) => k.lineOnTop([entry.x - 5, 0 + index * 5 + 4], [entry.x + 5, 0 + index * 5 + 4], PAD_TOP, P));
  out.push(L(marks.join(""), { tone: "lo", free: true }));
  return out.join("");
}

function counter() {
  const out = [];
  const housing = { x: 78, y: 18, w: 74, d: 26, r: 4 };
  out.push(S(k.slabOf(housing, 0, 14, P, 4, 0.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(housing, 2.2), 14, P, 4), { tone: "faint" }));
  const screws = k.corners(housing, 5);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 1.9, 14, P, 14)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 14])), { size: 0.42 }));
  for (let i = 0; i < 3; i++) {
    const x = housing.x + 16 + i * 21;
    const y = housing.y + housing.d / 2;
    out.push(L(k.ring(x, y, 8.4, 14, P, 32), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 7.4, 14, 4.6, P, 32, 0.4), { tone: "hi", crease: "lo" }));
    out.push(L(k.knurl(x, y, 7.4, 15, 18.2, 44, P, 0.25), { tone: "lo" }));
    out.push(L(k.sideArc(x, y, 7.4, 17.2, P, 26), { tone: "faint" }));
    out.push(L(k.ring(x, y, 2.2, 18.6, P, 18), { tone: "mid" }));
  }
  return out.join("");
}

function gauge() {
  const out = [];
  const [x, y] = DIAL;
  const base = { x: x - 16, y: y - 16, w: 32, d: 32, r: 3 };
  const screws = k.corners(base, 6);
  out.push(S(k.slabOf(base, 0, 12, P, 4, 0.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(base, 2.4), 12, P, 4), { tone: "faint" }));
  out.push(L(screws.map(([sx, sy]) => k.ring(sx, sy, 1.9, 12, P, 14)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([sx, sy]) => at([sx, sy, 12])), { size: 0.42 }));
  out.push(S(k.cylinder(x, y, 7, 12, 4, P, 28), { tone: "mid" }));
  out.push(S(k.cylinder(x, y, 5.5, 16, 16, P, 28), { tone: "mid", crease: "none" }));
  out.push(L(k.sideArc(x, y, 5.5, 22, P, 16), { tone: "faint" }));
  out.push(S(k.cylinder(x, y, 5.5, 32, 54, P, 28), { tone: "mid", crease: "none" }));
  out.push(L([44, 60, 76].map((z) => k.sideArc(x, y, 5.5, z, P, 16)).join(""), { tone: "faint" }));
  out.push(S(k.cylinder(x, y, 7, 86, 4, P, 28), { tone: "mid" }));
  out.push(S(k.cylinder(x, y, DIAL_R, DIAL_Z, DIAL_H, P, 64, 0.8), { tone: "hi", crease: "lo" }));
  out.push(L(k.knurl(x, y, DIAL_R, DIAL_TOP - 3.4, DIAL_TOP, 84, P, 0.3), { tone: "lo" }));
  out.push(L(k.sideArc(x, y, DIAL_R, DIAL_TOP - 3.4, P, 40), { tone: "faint" }));
  out.push(L(k.ring(x, y, DIAL_R - 2.2, DIAL_TOP, P, 64), { tone: "lo" }));
  const ticks = k.radialTicks(x, y, DIAL_R - 3, 50, 5, DIAL_TOP, [1.3, 2.8], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  out.push(L(k.ring(x, y, 1.6, DIAL_TOP, P, 16), { tone: "mid" }));
  return out.join("");
}

function head() {
  const out = [];
  const body = { x: -26, y: -30, w: 52, d: 60, r: 3 };
  out.push(S(k.slabOf(body, CARRIAGE_Z, CARRIAGE_H, P, 5, 0.6), { tone: "mid" }));
  for (const [bx, by] of [[body.x + 7, body.y + 7], [body.x + body.w - 7, body.y + 7], [body.x + 7, body.y + body.d - 7], [body.x + body.w - 7, body.y + body.d - 7]]) {
    out.push(S(k.slabOf({ x: bx - 7, y: by - 7, w: 14, d: 14, r: 2 }, CARRIAGE_Z - 1, CARRIAGE_H + 2, P, 3, 0.4), { tone: "mid" }));
    out.push(D([at([bx, by, CARRIAGE_TOP + 2])], { size: 0.4, tone: "lo" }));
  }
  out.push(D([-16, -6, 4, 14].map((dx) => at([dx, body.y + body.d - 3, CARRIAGE_TOP])), { size: 0.4, tone: "lo" }));
  out.push(L(k.lineOnTop([body.x, body.y + 6], [body.x + body.w, body.y + 6], CARRIAGE_TOP, P), { tone: "faint" }));
  const handle = { x: body.x + body.w, y: -4, w: 4, d: 8, r: 1 };
  out.push(S(k.slabOf(handle, CARRIAGE_Z + 1, 3, P, 2, 0), { tone: "mid", crease: "none" }));
  out.push(S(k.cylinder(handle.x + 7, 0, 3.4, CARRIAGE_Z, 6, P, 20), { tone: "mid" }));
  out.push(L(k.knurl(handle.x + 7, 0, 3.4, CARRIAGE_Z, CARRIAGE_Z + 6, 18, P), { tone: "lo" }));
  out.push(L(k.lineOnTop([handle.x + 3.6, 0], [handle.x + 10.4, 0], CARRIAGE_Z + 6, P), { tone: "hi" }));
  out.push(S(k.cylinder(0, 0, 4.2, CARRIAGE_Z - 0.4, 2.4, P, 24), { tone: "hi", crease: "lo" }));
  out.push(S(k.cylinder(0, 0, 2.6, PAD_TOP, CARRIAGE_Z - 0.6 - PAD_TOP, P, 20), { tone: "hi", crease: "none", lit: true }));
  out.push(S(k.cylinder(0, 0, 1.5, CARRIAGE_Z - 0.6, 0.8, P, 16), { tone: "hi", lit: true }));
  return out.join("");
}

const idxOf = (x) => PORTS.reduce((best, entry, index) => (Math.abs(entry.x - x) < Math.abs(PORTS[best].x - x) ? index : best), 0);
const startX = PORTS[0].x;

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label:
    "A gantry manifold on a cast base. One head travels along two rails and stops over five ports. The first port carries the collaboration context, the other four carry the customer's business systems; a dial reads how much of the context is connected, one fifth per port, and a counter drum pair shows the same count.",
  body: [
    plate(),
    feedBank(),
    rail(-26),
    posts(),
    PORTS.map((entry) => port(entry)).join(""),
    counter(),
    rail(26),
    gauge(),
    `<g data-part="head" transform="${k.translateAlong(P, [startX, 0, 0])}">${head()}</g>`,
    `<path data-part="needle" class="iso-line" data-tone="hi" d="${k.lineOnTop([DIAL[0] + Math.sin(-0.75 * Math.PI * 0) * 3.4, DIAL[1] + Math.cos(-0.75 * Math.PI * 0) * 3.4], [DIAL[0], DIAL[1] - (DIAL_R - 4)], DIAL_TOP + 0.2, P)}" style="stroke-width:1.1"/>`,
  ],
});

const needlePath = (share) => {
  const angle = (HEX[0] + (HEX[1] - HEX[0]) * share) * Math.PI * 2;
  const [x, y] = DIAL;
  return k.lineOnTop(
    [x - Math.sin(angle) * 3.4, y + Math.cos(angle) * 3.4],
    [x + Math.sin(angle) * (DIAL_R - 4), y - Math.cos(angle) * (DIAL_R - 4)],
    DIAL_TOP + 0.2,
    P,
  );
};

const live = `
const P = ${JSON.stringify(P)};
const PORTS = ${JSON.stringify(PORTS.map((entry) => entry.x))};
const SHARE_PER_PORT = ${SHARE_PER_PORT};
const REACH = ${JSON.stringify(REACH)};
const DIAL = ${JSON.stringify(DIAL)};
const DIAL_R = ${DIAL_R}, DIAL_TOP = ${DIAL_TOP}, HEX = ${JSON.stringify(HEX)};
const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const head = svg.querySelector('[data-part="head"]');
const needle = svg.querySelector('[data-part="needle"]');
const readout = document.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
const nearest = (x) => PORTS.reduce((best, stop, index) => (Math.abs(stop - x) < Math.abs(PORTS[best] - x) ? index : best), 0);
const needleAt = (share) => {
  const angle = (HEX[0] + (HEX[1] - HEX[0]) * share) * Math.PI * 2;
  return lineOnTop(
    [DIAL[0] - Math.sin(angle) * 3.4, DIAL[1] + Math.cos(angle) * 3.4],
    [DIAL[0] + Math.sin(angle) * (DIAL_R - 4), DIAL[1] - Math.cos(angle) * (DIAL_R - 4)],
    DIAL_TOP + 0.2,
    P,
  );
};
const textOf = (index) => "接通 " + (index + 1) + "/" + PORTS.length + " 路 · 上下文 " + Math.round((index + 1) * SHARE_PER_PORT) + "%";
let x = PORTS[0], target = x, index = 0;
let frame = 0, last = 0, clock = 0, touring = true, visible = false, idleTimer = 0;
const tourAt = (t) => PORTS[Math.floor(t / 2.4) % PORTS.length];
function draw() {
  head.setAttribute("transform", translateAlong(P, [x, 0, 0]));
  const share = (index + 1) / PORTS.length;
  needle.setAttribute("d", needleAt(share));
  const text = textOf(index);
  if (readout.textContent !== text) readout.textContent = text;
  stage.setAttribute("aria-valuenow", String(index + 1));
  stage.setAttribute("aria-valuetext", text);
}
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  if (touring) { clock += dt; target = tourAt(clock); }
  x = still.matches ? target : x + (target - x) * (1 - Math.exp(-dt / 0.3));
  if (Math.abs(target - x) < 0.01) { x = target; index = nearest(x); }
  draw();
  frame = visible && !(x === target && !touring) ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
const steer = (next) => { touring = false; target = clamp(next, REACH[0], REACH[1]); index = nearest(target); clearTimeout(idleTimer); idleTimer = setTimeout(() => { touring = !still.matches; clock = 0; run(); }, 3600); run(); };
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
if (still.matches) touring = false;
stage.addEventListener("pointermove", (event) => {
  const box = svg.getBoundingClientRect();
  const share = clamp(((event.clientX - box.left) / box.width - 0.18) / 0.64, 0, 1);
  steer(REACH[0] + share * (REACH[1] - REACH[0]));
});
stage.addEventListener("pointerleave", () => steer(target));
stage.addEventListener("keydown", (event) => {
  let to = null;
  if (event.key === "ArrowRight" || event.key === "ArrowUp") to = Math.min(PORTS.length - 1, index + 1);
  if (event.key === "ArrowLeft" || event.key === "ArrowDown") to = Math.max(0, index - 1);
  if (event.key === "Home") to = 0;
  if (event.key === "End") to = PORTS.length - 1;
  if (to === null) return;
  event.preventDefault();
  steer(PORTS[to]);
});
draw();
`;

const body = k.plateHtml({
  fig: "Fig 1",
  title: "上下文汇流台 Context manifold",
  hint: "移动指针或方向键，让汇流头停在某一个料位上",
  readout: readoutOf(0),
  keys: [
    { mark: "lit", label: "汇流头与探针，唯一会动的部分" },
    { mark: "raised", label: "五个料位，第一个是协同上下文，另四个是客户的业务系统" },
    { mark: "edge", label: "表盘读上下文完整度，每接通一路加 20%" },
  ],
  caption:
    "豆包工作接通上下文就是一台龙门汇流台。汇流头沿两条导轨依次停在五个料位上，第一个料位是协同数据，单聊、群聊和企业知识都在这一路；另外四个料位是客户的业务系统，要靠连接器一路一路接进来。表盘和滚筒读的是同一个模型，探头停在第几路，就接通了几路。",
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="上下文汇流台：方向键让汇流头从一个料位走到下一个料位" aria-valuemin="1" aria-valuemax="5" aria-valuenow="1">${svg}</div>`,
});

writeFileSync(join(HERE, theme === "light" ? "context-manifold-light.html" : "context-manifold.html"), k.pageHtml({ title: "上下文汇流台", theme, body, script: kitScript() + live }));
console.log("wrote", theme === "light" ? "context-manifold-light.html" : "context-manifold.html");
