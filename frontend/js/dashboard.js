const DashboardPage = {
  async render(root, filters) {
    root.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Enterprise feedback intelligence overview</p>
        </div>
        <div class="health-row" id="healthRow">${UI.skeleton(1)}</div>
      </div>
      ${UI.skeleton(8)}
    `;
    try {
      const [dash, health] = await Promise.all([
        API.get(`/api/dashboard${API.qs(filters)}`),
        API.get("/api/health"),
      ]);
      const kpi = dash.data.kpis;
      const charts = dash.data.charts;
      root.innerHTML = `
        <div class="page-header">
          <div>
            <h1>Dashboard</h1>
            <p>Live KPIs calculated from analyzed feedback</p>
          </div>
          <div class="health-row">
            <span class="health-pill ${health.status === "healthy" ? "" : "bad"}">App ${health.status}</span>
            <span class="health-pill ${health.database === "healthy" ? "" : "bad"}">Database ${health.database}</span>
            <span class="health-pill ${health.models === "healthy" ? "" : "bad"}">Models ${health.models}</span>
          </div>
        </div>
        <div class="grid grid-4">
          ${this.kpi("Total Feedback", kpi.total_feedback, kpi.total_delta)}
          ${this.kpi("Positive", kpi.positive_pct + "%", kpi.positive_delta)}
          ${this.kpi("Negative", kpi.negative_pct + "%", kpi.negative_delta)}
          ${this.kpi("Neutral", kpi.neutral_pct + "%", kpi.neutral_delta)}
          ${this.kpi("Critical Feedback", kpi.critical, kpi.critical_delta)}
          ${this.kpi("Avg Sentiment Score", kpi.avg_sentiment, kpi.rating_delta, "")}
          ${this.kpi("Resolved Feedback", kpi.resolved, 0, "")}
          ${this.kpi("Open Issues", kpi.open_issues, 0, "")}
        </div>
        <div class="grid grid-2" style="margin-top:16px">
          <div class="card chart-card"><h3>Sentiment distribution</h3><canvas id="chartSentiment"></canvas></div>
          <div class="card chart-card"><h3>Sentiment trend</h3><canvas id="chartTrend"></canvas></div>
          <div class="card chart-card"><h3>Feedback by category</h3><canvas id="chartCategory"></canvas></div>
          <div class="card chart-card"><h3>Feedback by channel</h3><canvas id="chartChannel"></canvas></div>
          <div class="card chart-card"><h3>Emotion distribution</h3><canvas id="chartEmotion"></canvas></div>
          <div class="card chart-card"><h3>Priority distribution</h3><canvas id="chartPriority"></canvas></div>
          <div class="card"><h3>Top keywords</h3>${this.keywords(charts.keywords)}</div>
          <div class="card"><h3>AI Insights</h3>${(dash.data.insights || []).map((item) => `<div class="insight ${item.type}"><strong>${UI.escape(item.title)}</strong><p>${UI.escape(item.message)}</p></div>`).join("") || UI.empty("No insights yet")}</div>
        </div>
        <div class="grid grid-2" style="margin-top:16px">
          <div class="card"><h3>Department performance</h3>${this.table(charts.departments, ["department", "feedback_count", "negative_pct", "average_rating"], ["Department", "Volume", "Negative %", "Rating"])}</div>
          <div class="card"><h3>Product / service performance</h3>${this.table(charts.products, ["product", "feedback_volume", "negative_pct", "average_rating"], ["Product", "Volume", "Negative %", "Rating"])}</div>
        </div>
      `;
      this.draw(charts);
    } catch (error) {
      root.innerHTML = UI.error(error.message);
    }
  },
  kpi(label, value, delta, suffix = "%") {
    return `<article class="card kpi"><div class="label">${label}</div><div class="value">${value}</div>${delta === 0 || delta === "" ? "" : UI.delta(delta, suffix)}</article>`;
  },
  keywords(items) {
    if (!items?.length) return UI.empty("No keywords");
    return `<div class="keyword-list">${items.map((item) => `<span class="keyword">${UI.escape(item.keyword)}</span>`).join("")}</div>`;
  },
  table(rows, keys, headers) {
    if (!rows?.length) return UI.empty("No data");
    return `<div class="table-wrap"><table class="data metric-table"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.slice(0, 7).map((row) => `<tr>${keys.map((key) => `<td>${UI.escape(row[key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  },
  draw(charts) {
    const palette = ["#2563eb", "#059669", "#dc2626", "#d97706", "#7c3aed", "#0ea5e9", "#14b8a6", "#f43f5e"];
    UI.chart("chartSentiment", {
      type: "doughnut",
      data: {
        labels: Object.keys(charts.sentiment_distribution),
        datasets: [{ data: Object.values(charts.sentiment_distribution), backgroundColor: ["#059669", "#94a3b8", "#dc2626"] }],
      },
      options: { plugins: { legend: { position: "bottom" } } },
    });
    const trend = charts.sentiment_trend || [];
    UI.chart("chartTrend", {
      type: "line",
      data: {
        labels: trend.map((row) => row.date),
        datasets: [
          { label: "Negative", data: trend.map((row) => row.negative || 0), borderColor: "#dc2626", tension: 0.3 },
          { label: "Positive", data: trend.map((row) => row.positive || 0), borderColor: "#059669", tension: 0.3 },
          { label: "Neutral", data: trend.map((row) => row.neutral || 0), borderColor: "#64748b", tension: 0.3 },
        ],
      },
      options: { responsive: true, maintainAspectRatio: true },
    });
    const bar = (id, rows) => UI.chart(id, {
      type: "bar",
      data: { labels: rows.map((r) => r.label), datasets: [{ data: rows.map((r) => r.value), backgroundColor: palette }] },
      options: { plugins: { legend: { display: false } } },
    });
    bar("chartCategory", charts.category || []);
    bar("chartChannel", charts.channel || []);
    bar("chartEmotion", charts.emotion || []);
    bar("chartPriority", charts.priority || []);
  },
};
