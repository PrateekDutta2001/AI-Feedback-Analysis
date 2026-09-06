const AlertsPage = {
  async render(root) {
    root.innerHTML = `
      <div class="page-header">
        <div><h1>Alert Center</h1><p>Rule-generated operational alerts</p></div>
        <div class="actions">
          <select id="alertStatus"><option value="">All statuses</option><option>unread</option><option>read</option><option>resolved</option></select>
          <button class="btn" id="refreshAlerts">Recalculate</button>
        </div>
      </div>
      <div class="card" id="alertTable">${UI.skeleton(3)}</div>
    `;
    document.getElementById("refreshAlerts").onclick = async () => {
      await API.post("/api/alerts/refresh", {});
      UI.toast("Alerts recalculated.", "success");
      this.load();
    };
    document.getElementById("alertStatus").onchange = () => this.load();
    this.load();
  },
  async load() {
    const host = document.getElementById("alertTable");
    try {
      const status = document.getElementById("alertStatus").value;
      const result = await API.get(`/api/alerts${API.qs({ status })}`);
      App.setUnread(result.meta.unread || result.data.filter((row) => row.status === "unread").length);
      if (!result.data.length) {
        host.innerHTML = UI.empty("No alerts");
        return;
      }
      host.innerHTML = `<div class="table-wrap"><table class="data">
        <thead><tr><th>ID</th><th>Type</th><th>Severity</th><th>Message</th><th>Created</th><th>Status</th><th></th></tr></thead>
        <tbody>${result.data.map((row) => `<tr>
          <td>${UI.escape(row.alert_id)}</td>
          <td>${UI.escape(row.type)}</td>
          <td>${UI.badge(row.severity)}</td>
          <td class="clip">${UI.escape(row.message)}</td>
          <td>${UI.escape((row.created_at || "").slice(0, 16))}</td>
          <td>${UI.badge(row.status)}</td>
          <td>
            <button class="btn" data-alert="${row.id}" data-status="read">Read</button>
            <button class="btn" data-alert="${row.id}" data-status="resolved">Resolve</button>
            <button class="btn danger" data-del-alert="${row.id}">Delete</button>
          </td>
        </tr>`).join("")}</tbody></table></div>`;
      host.onclick = async (event) => {
        const update = event.target.closest("[data-alert]");
        const remove = event.target.closest("[data-del-alert]");
        try {
          if (update) {
            await API.patch(`/api/alerts/${update.dataset.alert}`, { status: update.dataset.status });
            UI.toast(update.dataset.status === "resolved" ? "Alert resolved." : "Alert marked as read.", "success");
          }
          if (remove) {
            await API.delete(`/api/alerts/${remove.dataset.delAlert}`);
            UI.toast("Alert deleted.", "success");
          }
          if (update || remove) this.load();
        } catch (error) {
          UI.toast(error.message, "error");
        }
      };
    } catch (error) {
      host.innerHTML = UI.error(error.message);
    }
  },
};
