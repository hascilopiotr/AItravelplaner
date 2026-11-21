// One day: header, itinerary on a route rail, and a sticky Leaflet map.
// Hovering a stop lights its pin (and vice versa), clicking zooms the map,
// "Swap" asks Python for alternatives.

const LEAFLET = {
  css: "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  cssSri: "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=",
  js: "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
  jsSri: "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=",
};

function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (window.__tpLeaflet) return window.__tpLeaflet;
  window.__tpLeaflet = new Promise((resolve, reject) => {
    const css = document.createElement("link");
    Object.assign(css, { rel: "stylesheet", href: LEAFLET.css, integrity: LEAFLET.cssSri, crossOrigin: "" });
    document.head.appendChild(css);
    const s = document.createElement("script");
    Object.assign(s, { src: LEAFLET.js, integrity: LEAFLET.jsSri, crossOrigin: "" });
    s.onload = () => resolve(window.L);
    s.onerror = () => { window.__tpLeaflet = null; reject(new Error("Leaflet failed to load")); };
    document.head.appendChild(s);
  });
  return window.__tpLeaflet;
}

function header(d) {
  const w = d.weather;
  const head = h("header", { class: "tp-day-head" },
    h("div", { class: "tp-day-no", "aria-hidden": "true" }, String(d.n).padStart(2, "0")),
    h("div", { class: "tp-day-titles" },
      h("div", { class: "tp-kicker" }, `Day ${d.n} of ${d.of}`),
      h("h2", { class: "tp-day-title" }, d.weekday, h("em", {}, ", " + d.date_long))),
    h("div", { class: "tp-day-chips" },
      w ? h("span", { class: "tp-chip tp-chip-wx" }, icon(w.icon), h("b", {}, w.range), " ", w.label,
              w.rain != null ? h("span", { class: "tp-chip-sub" }, icon("water_drop"), w.rain + "%") : null)
        : h("span", { class: "tp-chip" }, icon("thermostat"), "No forecast yet"),
      h("span", { class: "tp-chip" }, icon("pin_drop"), `${d.n_stops} stops`),
      h("span", { class: "tp-chip" }, icon("payments"), d.cost)),
  );
  const out = [head];
  if (d.summary) out.push(h("p", { class: "tp-day-summary" }, d.summary));
  if ((d.issues || []).length) {
    out.push(h("details", { class: "tp-issues" },
      h("summary", {}, icon("report"), `${d.issues.length} thing${d.issues.length > 1 ? "s" : ""} to check on this day`),
      h("ul", {}, d.issues.map((x) => h("li", {}, x)))));
  }
  return out;
}

function stopCard(s, i, onSwap) {
  const photo = safeUrl(s.photo);
  const fig = h("figure", { class: "tp-stop-fig" + (photo ? "" : " noimg") }, icon(s.icon, "tp-stop-fig-icon"));
  if (photo) {
    const img = h("img", { alt: "", loading: "lazy", decoding: "async" });
    img.src = photo;
    img.addEventListener("error", () => { img.remove(); fig.classList.add("noimg"); });
    fig.appendChild(img);
  }
  const swap = h("button", { type: "button", class: "tp-swap", "aria-label": `Swap ${s.name} for a similar place` },
    icon("swap_horiz"), "Swap");
  swap.addEventListener("click", (e) => { e.stopPropagation(); onSwap(i); });

  return h("li", { class: "tp-stop", "data-i": String(i), style: `--i:${i}` },
    h("div", { class: "tp-stop-time" },
      h("b", {}, s.arrival), h("span", {}, s.departure), s.mins ? h("em", {}, s.mins) : null),
    h("div", { class: "tp-stop-pin", "aria-hidden": "true" }, String(i + 1).padStart(2, "0")),
    h("article", { class: "tp-stop-card", tabindex: "0", "aria-label": `Stop ${i + 1}: ${s.name}, ${s.arrival} to ${s.departure}` },
      fig,
      h("div", { class: "tp-stop-body" },
        s.kind ? h("div", { class: "tp-stop-kind" }, icon(s.icon), s.kind) : null,
        h("h3", { class: "tp-stop-name" }, s.name),
        s.address ? h("div", { class: "tp-stop-addr" }, s.address) : null,
        s.reason ? h("p", { class: "tp-stop-reason" }, s.reason) : null,
        s.hours ? h("div", { class: "tp-stop-hours" }, icon("schedule"), h("span", {}, s.hours)) : null,
        h("div", { class: "tp-stop-foot" },
          h("div", { class: "tp-price" + (s.free ? " free" : "") }, h("b", {}, s.price), s.free ? null : h("span", {}, "pp")),
          swap))),
  );
}

function leg(l) {
  return h("li", { class: "tp-leg " + (l.walk ? "walk" : "ride"), "aria-label": l.text },
    h("span", { class: "tp-leg-ico" }, icon(l.walk ? "directions_walk" : "tram")),
    h("span", { class: "tp-leg-txt" }, l.text));
}

export default function ({ data, parentElement, setTriggerValue }) {
  const d = data || {};
  const animate = firstTime("day:" + d.sig);
  const root = mount(parentElement, "tp-day" + (animate ? " tp-animate" : ""));
  header(d.day || {}).forEach((n) => root.appendChild(n));

  const stops = d.stops || [];
  if (!stops.length) {
    root.appendChild(h("div", { class: "tp-empty" }, icon("beach_access"), "A free day — nothing planned."));
    return;
  }

  const list = h("ol", { class: "tp-route", "aria-label": "Stops in order" });
  const cards = [];
  stops.forEach((s, i) => {
    if (i > 0 && s.leg) list.appendChild(leg(s.leg));
    const li = stopCard(s, i, (idx) => setTriggerValue("swap", idx));
    cards.push(li);
    list.appendChild(li);
  });

  const mapEl = h("div", { class: "tp-map", role: "region", "aria-label": "Map of the day's stops" });
  const fitBtn = h("button", { type: "button", class: "tp-map-btn", title: "Show the whole day" }, icon("fit_screen"), "Whole day");
  const aside = h("aside", { class: "tp-map-wrap" },
    h("div", { class: "tp-map-frame" }, mapEl, fitBtn),
    safeUrl(d.route_url) ? h("a", { class: "tp-gmaps", href: d.route_url, target: "_blank", rel: "noopener noreferrer" },
      icon("near_me"), "Walk it in Google Maps", icon("arrow_outward")) : null);

  root.appendChild(h("div", { class: "tp-board" }, list, aside));

  // Staggered reveal as cards scroll in.
  let io = null;
  if (animate && "IntersectionObserver" in window) {
    io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { rootMargin: "0px 0px -8% 0px" });
    list.querySelectorAll(".tp-stop, .tp-leg").forEach((el) => io.observe(el));
  } else {
    list.querySelectorAll(".tp-stop, .tp-leg").forEach((el) => el.classList.add("in"));
  }

  // ── Map ──
  let map = null, markers = [], active = -1, cancelled = false;
  const pts = stops.map((s) => (s.lat != null && s.lon != null ? [s.lat, s.lon] : null));
  const have = pts.filter(Boolean);

  function setActive(i, from) {
    if (i === active) return;
    if (active >= 0) {
      cards[active].classList.remove("active");
      markers[active]?.getElement()?.classList.remove("active");
    }
    active = i;
    if (i < 0) return;
    cards[i].classList.add("active");
    const m = markers[i];
    if (m) {
      m.getElement()?.classList.add("active");
      m.setZIndexOffset(1000);
      if (from === "card" && !map.getBounds().pad(-0.1).contains(m.getLatLng())) map.panTo(m.getLatLng(), { animate: !REDUCED });
    }
  }

  cards.forEach((li, i) => {
    const card = li.querySelector(".tp-stop-card");
    card.addEventListener("mouseenter", () => map && setActive(i, "card"));
    card.addEventListener("focus", () => map && setActive(i, "card"));
    card.addEventListener("click", () => {
      if (!map || !pts[i]) return;
      setActive(i, "card");
      map.flyTo(pts[i], Math.max(map.getZoom(), 16), { duration: REDUCED ? 0 : 0.8 });
    });
    card.addEventListener("keydown", (e) => { if (e.key === "Enter") card.click(); });
  });

  if (!have.length) {
    mapEl.classList.add("tp-map-none");
    mapEl.appendChild(h("div", {}, icon("wrong_location"), "No coordinates for these stops."));
    fitBtn.remove();
  } else {
    loadLeaflet().then((L) => {
      if (cancelled) return;
      map = L.map(mapEl, { scrollWheelZoom: false, zoomControl: true, attributionControl: true, zoomSnap: 0.25 });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
      const fit = (anim) => have.length > 1
        ? map.fitBounds(have, { padding: [48, 48], maxZoom: 16, animate: anim })
        : map.setView(have[0], 16, { animate: anim });
      fit(false);

      if (have.length > 1) {
        L.polyline(have, { className: "tp-line-under", weight: 7, interactive: false }).addTo(map);
        const draw = L.polyline(have, { className: "tp-line-draw", weight: 3, interactive: false }).addTo(map);
        L.polyline(have, { className: "tp-line-dots", weight: 3, interactive: false }).addTo(map);
        const path = draw.getElement();
        if (path && animate) {
          const len = path.getTotalLength();
          path.style.strokeDasharray = `${len}`;
          path.style.strokeDashoffset = `${len}`;
          requestAnimationFrame(() => { path.style.transition = "stroke-dashoffset 1.6s cubic-bezier(.6,.05,.3,1) .3s"; path.style.strokeDashoffset = "0"; });
          setTimeout(() => { path.style.strokeDasharray = ""; path.style.strokeDashoffset = ""; path.style.transition = ""; }, 2200);
        }
      }

      markers = stops.map((s, i) => {
        if (!pts[i]) return null;
        const m = L.marker(pts[i], {
          icon: L.divIcon({
            className: "tp-pin", iconSize: [34, 42], iconAnchor: [17, 40],
            html: `<span class="tp-pin-in" style="--i:${i}">${String(i + 1).padStart(2, "0")}</span>`,
          }),
          riseOnHover: true, keyboard: false, alt: "",
        }).addTo(map);
        const tip = h("div", {}, h("b", {}, s.name), h("br"), `${s.arrival}–${s.departure}`);
        m.bindTooltip(tip, { direction: "top", offset: [0, -38], className: "tp-tip" });
        m.on("mouseover", () => setActive(i, "pin"));
        m.on("click", () => {
          setActive(i, "pin");
          cards[i].scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "center" });
          cards[i].classList.remove("ping"); void cards[i].offsetWidth; cards[i].classList.add("ping");
        });
        return m;
      });
      if (animate) mapEl.classList.add("tp-pins-drop");

      fitBtn.addEventListener("click", () => { setActive(-1); fit(!REDUCED); });
      // The map may mount before layout settles (fonts, images); re-measure once.
      setTimeout(() => { if (map) { map.invalidateSize(); fit(false); } }, 250);
    }).catch(() => {
      mapEl.classList.add("tp-map-none");
      mapEl.replaceChildren(h("div", {}, icon("cloud_off"), "Map couldn't load — check your connection."));
    });
  }

  return () => {
    cancelled = true;
    if (io) io.disconnect();
    if (map) map.remove();
  };
}
