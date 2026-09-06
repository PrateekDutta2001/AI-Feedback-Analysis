const InsightsPage = {
  async render(root, filters) {
    root.innerHTML = `<div class="page-header"><div><h1>AI Insights</h1><p>Generated from current database statistics</p></div></div>${UI.skeleton(4)}`;
    try {
      const result = await API.get(`/api/insights${API.qs(filters)}`);
      const items = result.data.insights || [];
      root.innerHTML = `
        <div class="page-header"><div><h1>AI Insights</h1><p>Positive trends, negative trends, emerging issues and recommendations</p></div></div>
        <div class="grid">${items.map((item) => `<article class="card insight ${item.type}"><div class="muted">${UI.escape(item.type.replaceAll("_", " "))}</div><h3>${UI.escape(item.title)}</h3><p>${UI.escape(item.message)}</p></article>`).join("") || UI.empty("Insights will appear once enough feedback is analyzed")}</div>
      `;
    } catch (error) {
      root.innerHTML = UI.error(error.message);
    }
  },
};
