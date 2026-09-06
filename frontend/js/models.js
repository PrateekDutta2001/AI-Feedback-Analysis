const ModelsPage = {
  async render(root) {
    root.innerHTML = `
      <div class="page-header">
        <div><h1>ML Model Center</h1><p>Registry, evaluation metrics and retraining</p></div>
        <button class="btn primary" id="retrainBtn">Retrain Models</button>
      </div>
      <div id="modelHost">${UI.skeleton(4)}</div>
    `;
    document.getElementById("retrainBtn").onclick = async () => {
      const btn = document.getElementById("retrainBtn");
      btn.disabled = true;
      btn.textContent = "Training…";
      try {
        await API.post("/api/models/train", {});
        UI.toast("Model training completed.", "success");
        await this.load();
      } catch (error) {
        UI.toast(error.message, "error");
      } finally {
        btn.disabled = false;
        btn.textContent = "Retrain Models";
      }
    };
    await this.load();
  },
  async load() {
    const host = document.getElementById("modelHost");
    try {
      const result = await API.get("/api/models");
      if (!result.data.length) {
        host.innerHTML = UI.empty("No models registered yet", "Train models to populate the registry.");
        return;
      }
      host.innerHTML = result.data.map((row) => `
        <article class="card" style="margin-bottom:12px">
          <h3>${UI.escape(row.name)}</h3>
          <p>${UI.escape(row.algorithm)} · v${UI.escape(row.version)} · ${UI.escape(row.status)}</p>
          <p>Trained ${UI.escape((row.training_date || "").slice(0, 19))} · Dataset ${row.dataset_size}</p>
          <p>Accuracy ${(row.accuracy * 100).toFixed(1)}% · Precision ${(row.precision * 100).toFixed(1)}% · Recall ${(row.recall * 100).toFixed(1)}% · F1 ${(row.f1 * 100).toFixed(1)}%</p>
          ${row.metrics?.confusion_matrix ? `<div class="muted">Confusion matrix: ${JSON.stringify(row.metrics.confusion_matrix)}</div>` : ""}
        </article>
      `).join("");
    } catch (error) {
      host.innerHTML = UI.error(error.message);
    }
  },
};

const DatasetsPage = {
  async render(root) {
    root.innerHTML = `<div class="page-header"><div><h1>Data Management</h1><p>Uploaded datasets and quality statistics</p></div></div><div class="card" id="dsHost">${UI.skeleton(3)}</div>`;
    await this.load();
  },
  async load() {
    const host = document.getElementById("dsHost");
    try {
      const result = await API.get("/api/datasets");
      if (!result.data.length) {
        host.innerHTML = UI.empty("No datasets yet");
        return;
      }
      host.innerHTML = `<div class="table-wrap"><table class="data">
        <thead><tr><th>Name</th><th>Rows</th><th>Missing</th><th>Duplicates</th><th>Date coverage</th><th></th></tr></thead>
        <tbody>${result.data.map((row) => `<tr>
          <td>${UI.escape(row.name)}</td><td>${row.row_count}</td><td>${row.missing_values}</td>
          <td>${row.duplicate_count}</td><td>${UI.escape(row.date_min || "")} → ${UI.escape(row.date_max || "")}</td>
          <td><button class="btn danger" data-ds="${row.id}">Delete</button></td>
        </tr>`).join("")}</tbody></table></div>`;
      host.onclick = async (event) => {
        const btn = event.target.closest("[data-ds]");
        if (!btn || !confirm("Delete this dataset record?")) return;
        await API.delete(`/api/datasets/${btn.dataset.ds}`);
        UI.toast("Dataset deleted.", "success");
        this.load();
      };
    } catch (error) {
      host.innerHTML = UI.error(error.message);
    }
  },
};

const AuditPage = {
  async render(root) {
    root.innerHTML = `<div class="page-header"><div><h1>Audit Logs</h1><p>Immutable trail of important system actions</p></div></div><div class="card" id="auditHost">${UI.skeleton(3)}</div>`;
    try {
      const result = await API.get("/api/audit?page_size=50");
      const host = document.getElementById("auditHost");
      if (!result.data.length) {
        host.innerHTML = UI.empty("No audit events");
        return;
      }
      host.innerHTML = `<div class="table-wrap"><table class="data">
        <thead><tr><th>Time</th><th>Event</th><th>User</th><th>IP</th><th>Metadata</th></tr></thead>
        <tbody>${result.data.map((row) => `<tr>
          <td>${UI.escape((row.timestamp || "").slice(0, 19))}</td>
          <td>${UI.escape(row.event)}</td>
          <td>${UI.escape(row.user)}</td>
          <td>${UI.escape(row.ip || "")}</td>
          <td class="clip">${UI.escape(JSON.stringify(row.metadata))}</td>
        </tr>`).join("")}</tbody></table></div>`;
    } catch (error) {
      document.getElementById("auditHost").innerHTML = UI.error(error.message);
    }
  },
};

const SettingsPage = {
  async render(root) {
    root.innerHTML = UI.skeleton(2);
    try {
      const [settings, health] = await Promise.all([API.get("/api/settings"), API.get("/api/health")]);
      root.innerHTML = `
        <div class="page-header"><div><h1>Settings</h1><p>Runtime configuration and system health</p></div></div>
        <div class="grid grid-2">
          <article class="card">
            <h3>Application</h3>
            <p>Name: ${UI.escape(settings.data.app_name)}</p>
            <p>Environment: ${UI.escape(settings.data.app_env)}</p>
            <p>Similarity threshold: ${settings.data.similarity_threshold}</p>
            <p>Max upload: ${settings.data.max_upload_mb} MB</p>
          </article>
          <article class="card">
            <h3>Health</h3>
            <p>Status: ${UI.escape(health.status)}</p>
            <p>Database: ${UI.escape(health.database)}</p>
            <p>Models: ${UI.escape(health.models)}</p>
            <p class="muted">${UI.escape(health.timestamp)}</p>
          </article>
        </div>
      `;
    } catch (error) {
      root.innerHTML = UI.error(error.message);
    }
  },
};
