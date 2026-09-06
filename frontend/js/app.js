const App = {
  route: "dashboard",
  filters: {},
  setUnread(count) {
    document.getElementById("notifyDot").hidden = !count;
  },
  globalFilters() {
    return {
      date_from: document.getElementById("dateFrom").value,
      date_to: document.getElementById("dateTo").value,
      q: this.filters.q || "",
    };
  },
  async refreshAlertsBadge() {
    try {
      const result = await API.get("/api/alerts?status=unread&page_size=5");
      this.setUnread(result.meta.total || result.data.length);
    } catch (_error) {
      this.setUnread(0);
    }
  },
  show(route) {
    this.route = route;
    document.querySelectorAll(".view").forEach((view) => {
      view.hidden = view.id !== `view-${route}`;
    });
    document.querySelectorAll(".side-nav a").forEach((link) => {
      link.classList.toggle("active", link.dataset.route === route);
    });
  },
  async render() {
    const hash = (location.hash || "#/dashboard").replace("#/", "");
    const route = hash.split("?")[0] || "dashboard";
    this.show(route);
    const root = document.getElementById(`view-${route}`);
    if (!root) return;
    const filters = this.globalFilters();
    if (route === "dashboard") return DashboardPage.render(root, filters);
    if (route === "feedback") return FeedbackPage.render(root, filters);
    if (route === "feedback-add") return FeedbackPage.renderAdd(root);
    if (route === "feedback-import") return FeedbackPage.renderImport(root);
    if (["analytics", "topics", "products", "departments"].includes(route)) return AnalyticsPage.render(root, filters, route);
    if (route === "insights") return InsightsPage.render(root, filters);
    if (route === "alerts") return AlertsPage.render(root);
    if (route === "models") return ModelsPage.render(root);
    if (route === "datasets") return DatasetsPage.render(root);
    if (route === "audit") return AuditPage.render(root);
    if (route === "settings") return SettingsPage.render(root);
  },
};

document.getElementById("themeToggle").onclick = () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("insightai-theme", next);
};

document.getElementById("menuToggle").onclick = () => {
  document.getElementById("sidebar").classList.toggle("collapsed");
};

document.getElementById("globalSearchForm").onsubmit = (event) => {
  event.preventDefault();
  App.filters.q = document.getElementById("globalSearch").value;
  location.hash = "#/feedback";
  App.render();
};

document.getElementById("notifyBtn").onclick = () => {
  location.hash = "#/alerts";
};

["dateFrom", "dateTo"].forEach((id) => {
  document.getElementById(id).addEventListener("change", () => App.render());
});

window.addEventListener("hashchange", () => App.render());
document.documentElement.dataset.theme = localStorage.getItem("insightai-theme") || "light";
if (!location.hash) location.hash = "#/dashboard";
App.refreshAlertsBadge();
App.render();
