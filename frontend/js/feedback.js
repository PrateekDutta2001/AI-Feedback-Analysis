const FeedbackPage = {
  state: { page: 1, selected: new Set(), lookups: {} },
  async render(root, filters) {
    this.root = root;
    this.filters = filters;
    root.innerHTML = `
      <div class="page-header">
        <div><h1>All Feedback</h1><p>Search, filter, and inspect analyzed records</p></div>
        <div class="actions">
          <button class="btn" data-bulk="analyze">Analyze</button>
          <button class="btn" data-bulk="status">Change status</button>
          <button class="btn" data-export="csv">Export CSV</button>
          <button class="btn" data-export="json">Export JSON</button>
          <button class="btn danger" data-bulk="delete">Delete</button>
        </div>
      </div>
      <div id="filterBar">${UI.skeleton(1)}</div>
      <div class="card" id="tableHost">${UI.skeleton(3)}</div>
    `;
    await this.loadLookups();
    this.drawFilters();
    await this.loadTable();
    root.onclick = (event) => this.onClick(event);
  },
  async loadLookups() {
    const dash = await API.get("/api/dashboard");
    this.state.lookups = dash.data.lookups || {};
  },
  drawFilters() {
    const l = this.state.lookups;
    document.getElementById("filterBar").innerHTML = `
      <div class="filters">
        <input id="q" placeholder="Search text or ID" value="${UI.escape(this.filters.q || "")}" />
        <select id="f-sentiment">${UI.optionList(["positive", "neutral", "negative"], this.filters.sentiment)}</select>
        <select id="f-category">${UI.optionList(["Product", "Service", "Delivery", "Payment", "Pricing", "Customer Support", "Technical Issue", "Account", "UX/UI", "Performance", "Security", "Documentation", "Other"], this.filters.category)}</select>
        <select id="f-priority">${UI.optionList(["low", "medium", "high", "critical"], this.filters.priority)}</select>
        <select id="f-channel">${UI.optionList(l.channels, this.filters.channel)}</select>
        <select id="f-department">${UI.optionList(l.departments, this.filters.department)}</select>
        <select id="f-product">${UI.optionList(l.products, this.filters.product)}</select>
        <select id="f-status">${UI.optionList(l.statuses, this.filters.status)}</select>
        <select id="sort">
          <option value="date">Sort: Date</option>
          <option value="rating">Sort: Rating</option>
          <option value="product">Sort: Product</option>
        </select>
        <button class="btn primary" id="applyFilters">Apply filters</button>
      </div>
    `;
    document.getElementById("applyFilters").onclick = () => {
      this.state.page = 1;
      this.loadTable();
    };
  },
  currentFilters() {
    return {
      ...this.filters,
      q: document.getElementById("q")?.value,
      sentiment: document.getElementById("f-sentiment")?.value,
      category: document.getElementById("f-category")?.value,
      priority: document.getElementById("f-priority")?.value,
      channel: document.getElementById("f-channel")?.value,
      department: document.getElementById("f-department")?.value,
      product: document.getElementById("f-product")?.value,
      status: document.getElementById("f-status")?.value,
      sort: document.getElementById("sort")?.value,
      page: this.state.page,
      page_size: 20,
    };
  },
  async loadTable() {
    const host = document.getElementById("tableHost");
    host.innerHTML = UI.skeleton(3);
    try {
      const result = await API.get(`/api/feedback${API.qs(this.currentFilters())}`);
      const rows = result.data || [];
      if (!rows.length) {
        host.innerHTML = UI.empty("No feedback found");
        return;
      }
      host.innerHTML = `
        <div class="table-wrap">
          <table class="data">
            <thead>
              <tr>
                <th><input type="checkbox" id="selectAll" /></th>
                <th>ID</th><th>Date</th><th>Feedback</th><th>Sentiment</th><th>Emotion</th>
                <th>Category</th><th>Intent</th><th>Priority</th><th>Rating</th>
                <th>Product</th><th>Department</th><th>Channel</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map((row) => `
                <tr data-id="${row.id}">
                  <td><input type="checkbox" class="row-check" value="${row.id}" /></td>
                  <td>${UI.escape(row.feedback_id)}</td>
                  <td>${UI.escape((row.date || "").slice(0, 10))}</td>
                  <td class="clip">${UI.escape(row.text)}</td>
                  <td>${UI.badge(row.analysis?.sentiment?.label)}</td>
                  <td>${UI.badge(row.analysis?.emotion?.label)}</td>
                  <td>${UI.escape(row.analysis?.category)}</td>
                  <td>${UI.escape(row.analysis?.intent)}</td>
                  <td>${UI.badge(row.analysis?.priority)}</td>
                  <td>${row.rating}</td>
                  <td>${UI.escape(row.product)}</td>
                  <td>${UI.escape(row.department)}</td>
                  <td>${UI.escape(row.channel)}</td>
                  <td>${UI.badge(row.status)}</td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
        <div class="pager">
          <span>${result.meta.total} records</span>
          <div class="actions">
            <button class="btn" data-page="-1">Previous</button>
            <button class="btn" data-page="1">Next</button>
          </div>
        </div>
      `;
      document.getElementById("selectAll").onchange = (event) => {
        document.querySelectorAll(".row-check").forEach((box) => {
          box.checked = event.target.checked;
        });
      };
    } catch (error) {
      host.innerHTML = UI.error(error.message);
    }
  },
  selectedIds() {
    return Array.from(document.querySelectorAll(".row-check:checked")).map((node) => Number(node.value));
  },
  async onClick(event) {
    const pageBtn = event.target.closest("[data-page]");
    if (pageBtn) {
      this.state.page = Math.max(1, this.state.page + Number(pageBtn.dataset.page));
      await this.loadTable();
      return;
    }
    const exportBtn = event.target.closest("[data-export]");
    if (exportBtn) {
      API.download(`/api/export/${exportBtn.dataset.export}${API.qs(this.currentFilters())}`);
      UI.toast("Export started.", "information");
      return;
    }
    const bulk = event.target.closest("[data-bulk]");
    if (bulk) {
      const ids = this.selectedIds();
      if (!ids.length) {
        UI.toast("Select at least one row.", "warning");
        return;
      }
      try {
        if (bulk.dataset.bulk === "analyze") {
          await API.post("/api/feedback/bulk-analyze", { ids });
          UI.toast("Feedback analyzed successfully.", "success");
        } else if (bulk.dataset.bulk === "status") {
          const status = prompt("New status: open, in_progress, resolved, closed", "resolved");
          if (!status) return;
          await API.post("/api/feedback/bulk-status", { ids, status });
          UI.toast("Status updated.", "success");
        } else if (bulk.dataset.bulk === "delete") {
          if (!confirm("Delete selected feedback?")) return;
          await API.post("/api/feedback/bulk-delete", { ids });
          UI.toast("Records deleted.", "success");
        }
        await this.loadTable();
      } catch (error) {
        UI.toast(error.message, "error");
      }
      return;
    }
    const row = event.target.closest("tr[data-id]");
    if (row && !event.target.closest("input")) {
      this.openDetail(Number(row.dataset.id));
    }
  },
  async openDetail(id) {
    try {
      const result = await API.get(`/api/feedback/${id}`);
      const item = result.data;
      const analysis = item.analysis || {};
      UI.drawer(`
        <h2>${UI.escape(item.feedback_id)}</h2>
        <p class="muted">${UI.escape(item.date || "")} · ${UI.escape(item.product)} · ${UI.escape(item.channel)}</p>
        <div class="detail-block"><h3>Original feedback</h3><p>${UI.escape(item.text)}</p></div>
        <div class="detail-block">
          <h3>AI analysis</h3>
          <p>Sentiment ${UI.badge(analysis.sentiment?.label)} (${Math.round((analysis.sentiment?.confidence || 0) * 100)}%)</p>
          <p>Emotion ${UI.badge(analysis.emotion?.label)}</p>
          <p>Category ${UI.escape(analysis.category)} · Intent ${UI.escape(analysis.intent)}</p>
          <p>Priority ${UI.badge(analysis.priority)} · Severity ${analysis.severity}/5</p>
          <p>Keywords: ${(analysis.keywords || []).map((k) => k.keyword || k).join(", ")}</p>
        </div>
        <div class="detail-block">
          <h3>Explanation</h3>
          <p>${UI.escape(analysis.explanation?.sentiment || "")}</p>
          <p>${UI.escape((analysis.explanation?.priority || []).join(" · "))}</p>
          <p>${UI.escape((analysis.explanation?.severity || []).join(" · "))}</p>
        </div>
        <div class="detail-block">
          <h3>Recommended action</h3>
          <p>${UI.escape(analysis.recommendation || "")}</p>
        </div>
        <div class="detail-block">
          <h3>Similar feedback</h3>
          ${(item.similar || []).map((row) => `<p>${UI.escape(row.feedback_id)} · ${Math.round(row.similarity * 100)}% · ${UI.escape(row.text)}</p>`).join("") || "<p class='muted'>No near-duplicates found.</p>"}
        </div>
      `);
    } catch (error) {
      UI.toast(error.message, "error");
    }
  },
  async renderAdd(root) {
    root.innerHTML = `
      <div class="page-header"><div><h1>Add Feedback</h1><p>Manual ingestion with automatic ML analysis</p></div></div>
      <form class="card form-grid" id="createForm">
        <div class="field"><label>Feedback ID</label><input name="feedback_id" placeholder="Auto-generated if empty" /></div>
        <div class="field"><label>Customer / User ID</label><input name="customer_id" required /></div>
        <div class="field full"><label>Feedback text</label><textarea name="text" rows="5" required></textarea></div>
        <div class="field"><label>Date</label><input type="datetime-local" name="date" /></div>
        <div class="field"><label>Product</label><input name="product" required value="InsightPortal" /></div>
        <div class="field"><label>Department</label>
          <select name="department">
            ${["Customer Support", "Operations", "Product", "Engineering", "Sales", "Finance", "HR"].map((v) => `<option>${v}</option>`).join("")}
          </select>
        </div>
        <div class="field"><label>Channel</label>
          <select name="channel">${["Website", "Mobile App", "Email", "Call Center", "Social Media", "Survey", "Chat", "Internal"].map((v) => `<option>${v}</option>`).join("")}</select>
        </div>
        <div class="field"><label>Location</label><input name="location" required value="Mumbai" /></div>
        <div class="field"><label>Customer segment</label>
          <select name="segment">${["Enterprise", "SMB", "Startup", "Consumer", "Partner", "Internal"].map((v) => `<option>${v}</option>`).join("")}</select>
        </div>
        <div class="field"><label>Rating</label><input name="rating" type="number" min="1" max="5" value="3" required /></div>
        <div class="field"><label>Status</label>
          <select name="status"><option>open</option><option>in_progress</option><option>resolved</option><option>closed</option></select>
        </div>
        <div class="field full"><button class="btn primary" type="submit">Submit and analyze</button></div>
      </form>
      <div id="createResult"></div>
    `;
    document.getElementById("createForm").onsubmit = async (event) => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.target).entries());
      if (!data.feedback_id) delete data.feedback_id;
      if (data.date) data.date = new Date(data.date).toISOString();
      else delete data.date;
      data.rating = Number(data.rating);
      try {
        const result = await API.post("/api/feedback", data);
        UI.toast("Feedback analyzed successfully.", "success");
        document.getElementById("createResult").innerHTML = `<div class="card"><pre>${UI.escape(JSON.stringify(result.data.analysis, null, 2))}</pre></div>`;
      } catch (error) {
        UI.toast(error.message, "error");
      }
    };
  },
  async renderImport(root) {
    root.innerHTML = `
      <div class="page-header"><div><h1>Import Data</h1><p>Validate a CSV, preview rows, then run the ML pipeline</p></div></div>
      <div class="card">
        <input type="file" id="csvFile" accept=".csv" />
        <div class="actions" style="margin-top:12px">
          <button class="btn" id="previewBtn">Validate & preview</button>
          <button class="btn primary" id="importBtn">Import and analyze</button>
        </div>
        <div id="importStatus" class="muted" style="margin-top:12px"></div>
        <div id="importPreview"></div>
      </div>
    `;
    const fileInput = document.getElementById("csvFile");
    document.getElementById("previewBtn").onclick = async () => {
      if (!fileInput.files[0]) return UI.toast("Choose a CSV file first.", "warning");
      const body = new FormData();
      body.append("file", fileInput.files[0]);
      try {
        const result = await API.post("/api/upload", body);
        const data = result.data;
        document.getElementById("importPreview").innerHTML = `
          <p>${data.row_count} rows · ${data.missing_values} missing values · ${data.duplicate_count} duplicates</p>
          <p>${(data.issues || []).join(" · ") || "No blocking issues"}</p>
          <div class="table-wrap"><table class="data"><thead><tr>${data.columns.map((c) => `<th>${UI.escape(c)}</th>`).join("")}</tr></thead>
          <tbody>${data.preview.map((row) => `<tr>${data.columns.map((c) => `<td>${UI.escape(row[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
        `;
      } catch (error) {
        UI.toast(error.message, "error");
      }
    };
    document.getElementById("importBtn").onclick = async () => {
      if (!fileInput.files[0]) return UI.toast("Choose a CSV file first.", "warning");
      const body = new FormData();
      body.append("file", fileInput.files[0]);
      document.getElementById("importStatus").innerHTML = `<span class="spinner"></span> Importing and analyzing…`;
      try {
        const result = await API.post("/api/import", body);
        document.getElementById("importStatus").textContent = `Imported ${result.data.imported} rows, skipped ${result.data.skipped}.`;
        UI.toast("Dataset imported successfully.", "success");
      } catch (error) {
        document.getElementById("importStatus").textContent = "";
        UI.toast(error.message, "error");
      }
    };
  },
};
