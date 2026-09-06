const UI = {
  toast(message, type = "information") {
    const host = document.getElementById("toasts");
    const node = document.createElement("div");
    node.className = `toast ${type === "information" ? "info" : type}`;
    node.textContent = message;
    host.appendChild(node);
    setTimeout(() => node.remove(), 4200);
  },
  escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  },
  badge(value) {
    const label = this.escape(value || "n/a");
    return `<span class="badge ${label.toLowerCase().replaceAll(" ", "_")}">${label}</span>`;
  },
  skeleton(count = 4) {
    return `<div class="grid">${Array.from({ length: count }, () => `<div class="card skeleton" style="height:88px"></div>`).join("")}</div>`;
  },
  empty(title, detail) {
    return `<div class="empty"><h3>${this.escape(title)}</h3><p>${this.escape(detail || "No records match the current filters.")}</p></div>`;
  },
  error(message) {
    return `<div class="error-state"><h3>Unable to load this view</h3><p>${this.escape(message)}</p></div>`;
  },
  delta(value, suffix = "%") {
    const number = Number(value || 0);
    const cls = number >= 0 ? "up" : "down";
    const arrow = number >= 0 ? "↑" : "↓";
    return `<span class="delta ${cls}">${arrow} ${Math.abs(number)}${suffix}</span>`;
  },
  charts: {},
  chart(id, config) {
    if (this.charts[id]) this.charts[id].destroy();
    const canvas = document.getElementById(id);
    if (!canvas || typeof Chart === "undefined") return;
    this.charts[id] = new Chart(canvas, config);
  },
  closeOverlays() {
    document.getElementById("drawer").hidden = true;
    document.getElementById("modal").hidden = true;
  },
  drawer(html) {
    const host = document.getElementById("drawer");
    host.hidden = false;
    host.innerHTML = `<div class="drawer-panel">${html}<div class="detail-block"><button class="btn" data-close-overlay>Close</button></div></div>`;
  },
  modal(html) {
    const host = document.getElementById("modal");
    host.hidden = false;
    host.innerHTML = `<div class="modal-panel">${html}</div>`;
  },
  optionList(values, selected = "") {
    return [`<option value="">All</option>`]
      .concat((values || []).map((value) => `<option value="${this.escape(value)}" ${value === selected ? "selected" : ""}>${this.escape(value)}</option>`))
      .join("");
  },
};

document.addEventListener("click", (event) => {
  if (event.target.closest("[data-close-overlay]") || event.target.id === "drawer" || event.target.id === "modal") {
    UI.closeOverlays();
  }
});
