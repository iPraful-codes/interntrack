const STATUSES = ["Wishlist", "Applied", "Interview", "Offer", "Rejected"];
const $ = (selector) => document.querySelector(selector);
const filters = { status: "", q: "" };

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (res.status === 204) return null;
  const body = await res.json();
  if (!res.ok) throw new Error((body.errors || ["Request failed"]).join(", "));
  return body;
}

// Builds DOM nodes with textContent only, so user input is never parsed as HTML.
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function row(a) {
  const status = el("select", { className: `pill ${a.status}` });
  status.setAttribute("aria-label", `Status for ${a.company}`);
  STATUSES.forEach((s) => status.append(el("option", { value: s, textContent: s, selected: s === a.status })));
  status.onchange = async () => {
    await api(`/api/applications/${a.id}`, { method: "PUT", body: JSON.stringify({ status: status.value }) });
    refresh();
  };

  const remove = el("button", {
    className: "ghost",
    textContent: "Delete",
    onclick: async () => {
      if (!confirm(`Delete ${a.company}?`)) return;
      await api(`/api/applications/${a.id}`, { method: "DELETE" });
      refresh();
    },
  });

  const company = a.link
    ? el("a", { href: a.link, target: "_blank", rel: "noopener noreferrer", textContent: a.company })
    : el("span", { textContent: a.company });
  const role = el("td", {}, el("span", { textContent: a.role }));
  if (a.notes) role.append(el("small", { className: "note", textContent: a.notes }));

  return el("tr", {}, el("td", {}, company), role, el("td", { textContent: a.location || "" }),
    el("td", { textContent: a.applied_on }), el("td", {}, status), el("td", {}, remove));
}

async function renderList() {
  const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
  const items = await api(`/api/applications?${params}`);
  $("#rows").replaceChildren(...items.map(row));
  $("#none").hidden = items.length > 0;
}

async function renderStats() {
  const s = await api("/api/stats");
  $("#total").textContent = s.total;
  $("#rate").textContent = `${s.interview_rate}%`;

  const pipeline = $("#pipeline");
  const legend = $("#legend");
  pipeline.replaceChildren();
  legend.replaceChildren();
  if (!s.total) pipeline.append(el("p", { className: "empty", textContent: "Add your first application to see your pipeline." }));
  STATUSES.forEach((name) => {
    const n = s.by_status[name];
    if (n) pipeline.append(el("div", { className: `seg ${name}`, style: `flex: ${n}`, textContent: n, title: `${name}: ${n}` }));
    legend.append(el("li", { className: name, textContent: `${name} ${n}` }));
  });

  const weekly = $("#weekly");
  weekly.replaceChildren();
  const recent = s.weekly.slice(-12);
  if (!recent.length) weekly.append(el("p", { className: "empty", textContent: "Nothing sent yet." }));
  const max = Math.max(1, ...recent.map((w) => w.n));
  recent.forEach((w) => weekly.append(
    el("div", { className: "wk", title: `Week of ${w.week_start}: ${w.n}` },
      el("span", { textContent: w.n }),
      el("i", { style: `height: ${(w.n / max) * 100}%` }),
      el("small", { textContent: w.week_start.slice(5) }))));
}

const refresh = () => Promise.all([renderList(), renderStats()]);
const setToday = () => { $("#add-form").applied_on.value = new Date().toLocaleDateString("en-CA"); };

$("#add-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries([...new FormData(form)].filter(([, value]) => value.trim()));
  try {
    await api("/api/applications", { method: "POST", body: JSON.stringify(data) });
    form.reset();
    setToday();
    $("#error").textContent = "";
    refresh();
  } catch (err) {
    $("#error").textContent = err.message;
  }
});

$("#search").addEventListener("input", (e) => { filters.q = e.target.value; renderList(); });
$("#filter").addEventListener("change", (e) => { filters.status = e.target.value; renderList(); });

setToday();
refresh();
