// Empty state: travel-poster welcome with an animated flight path
// and a departures marquee of the cities already loaded.

export default function ({ data, parentElement }) {
  const d = data || {};
  const root = mount(parentElement, "tp-welcome");

  const art = svg(`
    <svg class="tp-welcome-art" viewBox="0 0 520 300" aria-hidden="true">
      <circle class="tp-w-sun" cx="380" cy="120" r="86"/>
      <g class="tp-w-waves" fill="none" stroke-width="3" stroke-linecap="round">
        <path d="M20 250 q 25 -12 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0"/>
        <path d="M0 270 q 25 -12 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0 t 50 0"/>
      </g>
      <path id="tp-w-arc" class="tp-w-arc" d="M60 220 C 160 40, 330 20, 440 180" fill="none" stroke-width="2.5" stroke-dasharray="3 10" stroke-linecap="round"/>
      <circle class="tp-w-from" cx="60" cy="220" r="7"/>
      <g class="tp-w-to"><circle cx="440" cy="180" r="16" class="tp-w-pulse"/><circle cx="440" cy="180" r="7"/></g>
      <text class="tp-w-plane" font-size="34" text-anchor="middle" dominant-baseline="central">flight
        <animateMotion dur="7s" repeatCount="indefinite" rotate="auto" keyPoints="0;1" keyTimes="0;1" calcMode="spline" keySplines=".45 0 .55 1">
          <mpath href="#tp-w-arc"/>
        </animateMotion>
      </text>
    </svg>`);
  // SVG text rotates with x-axis = path direction; the glyph points up, so turn it 90°.
  art.querySelector(".tp-w-plane").setAttribute("transform", "rotate(90)");
  if (REDUCED) art.querySelector("animateMotion").remove();

  const steps = [
    ["calendar_month", "Pick your days", "Dates, pace, budget and what you love — on the left."],
    ["fact_check", "We check the details", "Real places, opening hours, walking times and the forecast."],
    ["swap_horiz", "Make it yours", "Swap any stop, follow the map, print a pocket guide."],
  ];

  root.append(
    h("div", { class: "tp-welcome-grid" },
      h("div", { class: "tp-welcome-copy" },
        h("div", { class: "tp-kicker" }, icon("explore"), " Next departure"),
        h("h1", {}, d.city || "Your city", ",", h("br"), h("em", {}, "day by day.")),
        h("p", {}, "A walkable plan built from real places in the city, checked against opening hours, " +
                   "travel times and the weather. Set up your trip on the left — it takes about half a minute.")),
      art),
    h("ol", { class: "tp-steps" }, steps.map(([ic, t, s], i) =>
      h("li", { class: "tp-step", style: `--i:${i}` },
        h("span", { class: "tp-step-no" }, String(i + 1).padStart(2, "0")),
        icon(ic, "tp-step-ico"),
        h("b", {}, t), h("span", {}, s)))),
  );

  const cities = d.cities || [];
  if (cities.length) {
    const row = () => h("div", { class: "tp-marquee-row", "aria-hidden": "true" },
      cities.concat(cities, cities, cities).map((c) => h("span", { class: "tp-marquee-item" },
        h("b", {}, c.code), c.name, icon("flight_takeoff"))));
    root.appendChild(h("div", { class: "tp-marquee", role: "note",
      "aria-label": "Destinations ready to plan: " + cities.map((c) => c.name).join(", ") },
      h("div", { class: "tp-marquee-lbl" }, "Departures"), h("div", { class: "tp-marquee-track" }, row(), row())));
  }
}
