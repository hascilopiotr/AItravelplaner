// Shared helpers, prepended to every component module by ui/widgets.py.
// Untrusted text (place names, AI text) is only ever set through text nodes.

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.setAttribute("style", v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

function icon(name, cls) {
  // Icon names come from our own Python tables, never from data.
  return h("span", { class: "material-symbols-rounded " + (cls || ""), "aria-hidden": "true" }, name);
}

function svg(markup) {
  // Only for static SVG written in this file.
  const t = document.createElement("template");
  t.innerHTML = markup.trim();
  return t.content.firstChild;
}

// Play an entrance animation only the first time a given thing is shown,
// not on every Streamlit rerun.
function firstTime(id) {
  const seen = (window.__tpSeen = window.__tpSeen || new Set());
  if (REDUCED || seen.has(id)) return false;
  seen.add(id);
  return true;
}

function safeUrl(u) {
  return typeof u === "string" && /^https:\/\//.test(u) ? u : null;
}

function mount(parentElement, cls) {
  parentElement.replaceChildren();
  const root = h("div", { class: cls });
  parentElement.appendChild(root);
  return root;
}
