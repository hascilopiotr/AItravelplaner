// Trip hero: destination poster with split-flap code, rotating postmark,
// ticket-stub stats with count-up numbers and a budget meter.

const FLAP_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function flapBoard(code, animate) {
  const board = h("div", { class: "tp-flap", "aria-label": "Destination code " + code, role: "img" });
  [...code].forEach((ch, i) => {
    const cell = h("span", { class: "tp-flap-cell", "aria-hidden": "true" }, animate ? " " : ch);
    board.appendChild(cell);
    if (!animate) return;
    const end = performance.now() + 500 + i * 260;
    const tick = () => {
      if (performance.now() >= end) { cell.textContent = ch; cell.classList.add("settled"); return; }
      cell.textContent = FLAP_CHARS[Math.floor(Math.random() * FLAP_CHARS.length)];
      cell.classList.remove("flip"); void cell.offsetWidth; cell.classList.add("flip");
      setTimeout(tick, 70);
    };
    setTimeout(tick, 120 * i);
  });
  return board;
}

function postmark(text) {
  const id = "tp-pm-" + Math.random().toString(36).slice(2, 8);
  const el = svg(`
    <svg class="tp-postmark" viewBox="0 0 200 200" aria-hidden="true">
      <defs><path id="${id}" d="M100,100 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0"/></defs>
      <circle cx="100" cy="100" r="92" fill="none" stroke="currentColor" stroke-width="2.5"/>
      <circle cx="100" cy="100" r="56" fill="none" stroke="currentColor" stroke-width="1.5"/>
      <g class="tp-postmark-ring"><text font-size="15" letter-spacing="3.2"><textPath href="#${id}"></textPath></text></g>
      <text class="tp-postmark-plane" x="100" y="100" text-anchor="middle" dominant-baseline="central" font-size="56">flight</text>
    </svg>`);
  el.querySelector("textPath").textContent = text;
  return el;
}

function countUp(el, to, animate) {
  if (!animate) { el.textContent = String(to); return; }
  const t0 = performance.now(), dur = 900;
  const step = (t) => {
    const p = Math.min(1, (t - t0) / dur);
    el.textContent = String(Math.round(to * (1 - Math.pow(1 - p, 3))));
    if (p < 1) requestAnimationFrame(step);
  };
  el.textContent = "0";
  setTimeout(() => requestAnimationFrame(step), 500);
}

export default function ({ data, parentElement }) {
  const d = data || {};
  const animate = firstTime("hero:" + d.sig);
  const root = mount(parentElement, "tp-hero-wrap" + (animate ? " tp-animate" : ""));

  // ── Poster ──
  const photo = safeUrl(d.photo);
  const media = h("div", { class: "tp-hero-media" + (photo ? "" : " tp-hero-nophoto") });
  if (photo) {
    const img = h("img", { alt: "", loading: "eager", decoding: "async" });
    img.src = photo;
    img.addEventListener("load", () => media.classList.add("loaded"));
    img.addEventListener("error", () => { img.remove(); media.classList.add("tp-hero-nophoto"); });
    media.appendChild(img);
  }
  media.appendChild(svg(`
    <svg class="tp-hero-sun" viewBox="0 0 200 200" aria-hidden="true">
      <circle cx="100" cy="100" r="70"/>
      <g stroke-width="5"><line x1="20" y1="130" x2="180" y2="130"/><line x1="30" y1="146" x2="170" y2="146"/><line x1="44" y1="162" x2="156" y2="162"/></g>
    </svg>`));

  const body = h("div", { class: "tp-hero-body" },
    h("div", { class: "tp-kicker tp-kicker-light" }, "Itinerary · ", d.ref || ""),
    flapBoard(d.code || "---", animate),
    h("h1", { class: "tp-hero-city" }, d.city || ""),
    h("div", { class: "tp-hero-sub" },
      d.region ? h("span", {}, d.region) : null,
      h("span", { class: "tp-hero-dates" }, d.dates || "")),
  );
  root.appendChild(h("section", { class: "tp-hero", "aria-label": "Trip to " + (d.city || "") },
    media, body, postmark(d.postmark || "")));

  // ── Ticket stubs ──
  const stubs = h("div", { class: "tp-stubs" });
  (d.stats || []).forEach((s, i) => {
    const val = h("div", { class: "tp-stub-val" });
    if (typeof s.value === "number") countUp(val, s.value, animate);
    else val.textContent = s.text || "";
    stubs.appendChild(h("div", { class: "tp-stub", style: `--i:${i}` },
      h("div", { class: "tp-stub-lbl" }, icon(s.icon || "confirmation_number"), s.label), val,
      s.note ? h("div", { class: "tp-stub-note" }, s.note) : null));
  });

  const b = d.budget || {};
  const pct = Math.max(0, Math.min(100, b.pct || 0));
  const fill = h("div", { class: "tp-meter-fill", style: `--to:${pct}%` });
  if (!animate) fill.style.width = pct + "%";
  stubs.appendChild(h("div", { class: "tp-stub tp-stub-budget" + (b.over ? " over" : ""), style: `--i:${(d.stats || []).length}` },
    h("div", { class: "tp-stub-lbl" }, icon("savings"), "Spend per person"),
    h("div", { class: "tp-stub-val" }, b.used || ""),
    h("div", { class: "tp-meter", role: "meter", "aria-valuemin": "0", "aria-valuemax": "100",
               "aria-valuenow": String(Math.round(pct)), "aria-label": "Budget used" }, fill),
    h("div", { class: "tp-stub-note" }, b.note || "")));
  root.appendChild(stubs);

  if (d.lede) root.appendChild(h("p", { class: "tp-lede" }, d.lede));

  if ((d.notices || []).length) {
    root.appendChild(h("ul", { class: "tp-notices" },
      d.notices.map((n) => h("li", { class: "tp-notice " + (n.kind === "error" ? "err" : "warn") },
        icon(n.kind === "error" ? "error" : "warning"), h("span", {}, n.text)))));
  }
}
