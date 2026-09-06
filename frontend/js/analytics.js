const AnalyticsPage = {
  async render(root, filters, mode) {
    root.innerHTML = `<div class="page-header"><div><h1>${this.title(mode)}</h1><p>Charts and rankings from live API aggregations</p></div></div>${UI.skeleton(4)}`;
    try {
      if (mode === "analytics") return this.sentiment(root, filters);
      if (mode === "topics") return this.topics(root, filters);
      if (mode === "products") return this.products(root, filters);
      return this.departments(root, filters);
    } catch (error) {
      root.innerHTML = UI.error(error.message);
    }
  },
  title(mode) {
    return { analytics: "Sentiment Analytics", topics: "Topic Discovery", products: "Product Analytics", departments: "Department Analytics" }[mode];
  },
  async sentiment(root, filters) {
    const [sentiment, trend] = await Promise.all([
      API.get(`/api/analytics/sentiment${API.qs(filters)}`),
      API.get(`/api/analytics/trends${API.qs(filters)}`),
    ]);
    root.innerHTML = `
      <div class="page-header"><div><h1>Sentiment Analytics</h1><p>Volume, rating, emotion, priority and resolution trends</p></div></div>
      <div class="grid grid-2">
        <div class="card chart-card"><h3>Sentiment distribution</h3><canvas id="aSent"></canvas></div>
        <div class="card chart-card"><h3>Sentiment trend</h3><canvas id="aTrend"></canvas></div>
        <div class="card chart-card"><h3>Rating trend</h3><canvas id="aRating"></canvas></div>
        <div class="card chart-card"><h3>Feedback volume</h3><canvas id="aVolume"></canvas></div>
        <div class="card chart-card"><h3>Priority trend</h3><canvas id="aPriority"></canvas></div>
        <div class="card chart-card"><h3>Resolution rate</h3><canvas id="aRes"></canvas></div>
      </div>
    `;
    const dist = sentiment.data.distribution;
    UI.chart("aSent", { type: "doughnut", data: { labels: Object.keys(dist), datasets: [{ data: Object.values(dist), backgroundColor: ["#059669", "#94a3b8", "#dc2626"] }] } });
    const t = trend.data;
    UI.chart("aTrend", { type: "line", data: { labels: t.sentiment.map((r) => r.date), datasets: [{ label: "Negative", data: t.sentiment.map((r) => r.negative || 0), borderColor: "#dc2626" }] } });
    UI.chart("aRating", { type: "line", data: { labels: t.rating.map((r) => r.date), datasets: [{ label: "Avg rating", data: t.rating.map((r) => r.avg_rating || 0), borderColor: "#2563eb" }] } });
    UI.chart("aVolume", { type: "bar", data: { labels: t.volume.map((r) => r.date), datasets: [{ data: t.volume.map((r) => r.count || 0), backgroundColor: "#1d4ed8" }] }, options: { plugins: { legend: { display: false } } } });
    UI.chart("aPriority", { type: "line", data: { labels: t.priority.map((r) => r.date), datasets: [{ label: "Critical", data: t.priority.map((r) => r.critical || 0), borderColor: "#dc2626" }] } });
    UI.chart("aRes", { type: "line", data: { labels: t.resolution.map((r) => r.date), datasets: [{ label: "Resolution %", data: t.resolution.map((r) => r.rate || 0), borderColor: "#059669" }] } });
  },
  async topics(root, filters) {
    const [topics, aspects] = await Promise.all([
      API.get(`/api/analytics/topics${API.qs(filters)}`),
      API.get(`/api/analytics/aspects${API.qs(filters)}`),
    ]);
    root.innerHTML = `
      <div class="page-header"><div><h1>Topics & Aspects</h1><p>KMeans topic clusters and lexicon-based aspect sentiment</p></div></div>
      <div class="grid grid-3">
        ${(topics.data || []).map((topic) => `
          <article class="card topic-card">
            <h3>${UI.escape(topic.name)}</h3>
            <div class="meta"><span>${topic.feedback_count} records</span><span>${topic.sentiment.negative_pct}% negative</span></div>
            <div class="keyword-list">${topic.top_keywords.map((k) => `<span class="keyword">${UI.escape(k)}</span>`).join("")}</div>
          </article>`).join("") || UI.empty("Not enough data for clustering")}
      </div>
      <div class="card" style="margin-top:16px">
        <h3>Aspect analysis</h3>
        <div class="table-wrap"><table class="data">
          <thead><tr><th>Aspect</th><th>Mentions</th><th>Positive</th><th>Neutral</th><th>Negative</th><th>Avg rating</th></tr></thead>
          <tbody>${(aspects.data || []).map((row) => `<tr><td>${UI.escape(row.aspect)}</td><td>${row.mentions}</td><td>${row.positive}%</td><td>${row.neutral}%</td><td>${row.negative}%</td><td>${row.average_rating}</td></tr>`).join("")}</tbody>
        </table></div>
      </div>
    `;
  },
  async products(root, filters) {
    const result = await API.get(`/api/analytics/products${API.qs(filters)}`);
    root.innerHTML = `
      <div class="page-header"><div><h1>Product Analytics</h1><p>Volume, sentiment, critical issues and themes</p></div></div>
      <div class="grid">
        ${(result.data || []).map((row) => `
          <article class="card">
            <h3>${UI.escape(row.product)}</h3>
            <p>${row.feedback_volume} records · Rating ${row.average_rating} · Critical ${row.critical_issues}</p>
            <p>Positive ${row.positive_pct}% · Negative ${row.negative_pct}%</p>
            <p class="muted">Top complaints: ${(row.top_complaints || []).map((k) => k.keyword).join(", ") || "n/a"}</p>
            <p class="muted">Positive themes: ${(row.top_positive_themes || []).map((k) => k.keyword).join(", ") || "n/a"}</p>
          </article>`).join("")}
      </div>
    `;
  },
  async departments(root, filters) {
    const result = await API.get(`/api/analytics/departments${API.qs(filters)}`);
    root.innerHTML = `
      <div class="page-header"><div><h1>Department Analytics</h1><p>Ranked by negative share and critical volume</p></div></div>
      <div class="card table-wrap"><table class="data">
        <thead><tr><th>Rank</th><th>Department</th><th>Feedback</th><th>Positive %</th><th>Negative %</th><th>Avg rating</th><th>Open</th><th>Critical</th></tr></thead>
        <tbody>${(result.data || []).map((row) => `<tr><td>${row.rank}</td><td>${UI.escape(row.department)}</td><td>${row.feedback_count}</td><td>${row.positive_pct}</td><td>${row.negative_pct}</td><td>${row.average_rating}</td><td>${row.open_issues}</td><td>${row.critical_issues}</td></tr>`).join("")}</tbody>
      </table></div>
    `;
  },
};
