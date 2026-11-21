// Day selector as a row of tickets. Sends the picked ISO date back to Python.

export default function ({ data, parentElement, setTriggerValue }) {
  const d = data || {};
  const animate = firstTime("strip:" + d.sig);
  const root = mount(parentElement, "tp-strip" + (animate ? " tp-animate" : ""));
  root.setAttribute("role", "tablist");
  root.setAttribute("aria-label", "Days of the trip");

  const buttons = [];
  (d.days || []).forEach((day, i) => {
    const on = day.iso === d.selected;
    const btn = h("button", {
      type: "button", role: "tab", class: "tp-ticket" + (on ? " on" : ""),
      "aria-selected": on ? "true" : "false", tabindex: on ? "0" : "-1", style: `--i:${i}`,
      "aria-label": `Day ${i + 1}, ${day.long}${day.weather ? ", " + day.weather : ""}, ${day.stops} stops` +
                    (day.issues ? `, ${day.issues} to check` : ""),
    },
      h("span", { class: "tp-ticket-no" }, "Day ", String(i + 1).padStart(2, "0")),
      h("span", { class: "tp-ticket-date" },
        h("b", {}, day.d), h("span", {}, day.dow, h("br"), day.mon)),
      h("span", { class: "tp-ticket-wx" },
        day.wx_icon ? icon(day.wx_icon) : null, day.temp || "—"),
      h("span", { class: "tp-ticket-foot" },
        h("span", {}, `${day.stops} stops`),
        day.issues ? h("span", { class: "tp-ticket-flag" }, icon("priority_high"), String(day.issues))
                   : h("span", { class: "tp-ticket-ok" }, icon("check"))),
    );
    btn.addEventListener("click", () => {
      if (btn.classList.contains("on")) return;
      buttons.forEach((b) => { b.classList.remove("on"); b.setAttribute("aria-selected", "false"); b.tabIndex = -1; });
      btn.classList.add("on"); btn.setAttribute("aria-selected", "true"); btn.tabIndex = 0;
      setTriggerValue("pick", day.iso);
    });
    btn.addEventListener("keydown", (e) => {
      const k = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!k) return;
      e.preventDefault();
      const next = buttons[(i + k + buttons.length) % buttons.length];
      next.focus(); next.click();
    });
    buttons.push(btn);
    root.appendChild(btn);
  });
}
