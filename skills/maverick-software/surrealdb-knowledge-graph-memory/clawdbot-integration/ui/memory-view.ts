import { html, nothing } from "lit";

export type MemoryHealthStatus = {
  surrealdb_binary: {
    installed: boolean;
    path: string | null;
    version: string | null;
  };
  surrealdb_server: {
    running: boolean;
    port: number;
    error?: string;
  };
  schema: {
    initialized: boolean;
    error?: string;
  };
  python_deps: {
    ok: boolean;
    dependencies: Record<string, boolean>;
  };
  data_dir: {
    path: string;
    exists: boolean;
  };
};

export type MemoryStats = {
  facts: number;
  entities: number;
  relationships: number;
  archived: number;
  avg_confidence: number;
  by_source: Array<{ source: string; count: number }>;
  error?: string;
};

export type MemoryProps = {
  loading: boolean;
  health: MemoryHealthStatus | null;
  stats: MemoryStats | null;
  error: string | null;
  maintenanceLog: string | null;
  installLog: string | null;
  busyAction: string | null;
  onRefresh: () => void;
  onAutoRepair: () => void;
  onInstallBinary: () => void;
  onInstallPython: () => void;
  onStartServer: () => void;
  onInitSchema: () => void;
  onRunMaintenance: (op: "decay" | "prune" | "full") => void;
};

export function renderMemory(props: MemoryProps) {
  return html`
    <section class="card">
      <div class="row" style="justify-content: space-between;">
        <div>
          <div class="card-title">🧠 Knowledge Graph Memory</div>
          <div class="card-sub">SurrealDB-powered memory with confidence scoring and graph relationships.</div>
        </div>
        <div class="row" style="gap: 8px;">
          <button class="btn" ?disabled=${props.loading || props.busyAction !== null} @click=${props.onRefresh}>
            ${props.loading ? "Loading…" : "↻ Refresh"}
          </button>
          <button class="btn primary" ?disabled=${props.busyAction !== null} @click=${props.onAutoRepair}>
            ${props.busyAction === "repair" ? "Repairing…" : "🔧 Auto-Repair"}
          </button>
        </div>
      </div>

      ${props.error
        ? html`<div class="callout danger" style="margin-top: 12px;">${props.error}</div>`
        : nothing}
    </section>

    <div class="row" style="margin-top: 16px; gap: 16px; align-items: flex-start;">
      <div class="col" style="flex: 1; min-width: 300px;">
        ${renderStats(props)}
      </div>
      <div class="col" style="flex: 1; min-width: 300px;">
        ${renderHealth(props)}
      </div>
    </div>

    <div class="row" style="margin-top: 16px; gap: 16px; align-items: flex-start;">
      <div class="col" style="flex: 1; min-width: 300px;">
        ${renderMaintenance(props)}
      </div>
      <div class="col" style="flex: 1; min-width: 300px;">
        ${renderInstallation(props)}
      </div>
    </div>
  `;
}

function renderStats(props: MemoryProps) {
  const stats = props.stats;
  const isActive = props.health?.surrealdb_server?.running ?? false;
  const hasData = stats && !stats.error;

  // Use real stats if available, otherwise show zeros
  const displayStats = hasData ? stats : { facts: 0, entities: 0, relationships: 0, archived: 0, avg_confidence: 0, by_source: [] };

  return html`
    <section class="card" style="${!isActive ? 'opacity: 0.6;' : ''}">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="card-title">📊 Statistics</div>
        ${isActive
          ? html`<a 
              href="http://localhost:8000" 
              target="_blank" 
              class="btn small"
              title="Open SurrealDB Studio"
            >🔗 Open DB Studio</a>`
          : html`<span class="chip chip-warn">Database Offline</span>`
        }
      </div>
      ${!isActive && !hasData
        ? html`<div class="muted" style="margin-top: 8px; font-size: 13px;">
            Start the database to view live statistics.
          </div>`
        : nothing}
      <div class="row" style="margin-top: 16px; gap: 12px; flex-wrap: wrap;">
        ${renderStatBox("Facts", displayStats.facts, isActive ? "var(--primary-color, #58a6ff)" : "var(--text-muted, #8b949e)")}
        ${renderStatBox("Entities", displayStats.entities, isActive ? "var(--success-color, #3fb950)" : "var(--text-muted, #8b949e)")}
        ${renderStatBox("Relations", displayStats.relationships, isActive ? "var(--warning-color, #d29922)" : "var(--text-muted, #8b949e)")}
        ${renderStatBox("Archived", displayStats.archived, "var(--text-muted, #8b949e)")}
      </div>
      <div style="margin-top: 16px; padding: 12px; background: var(--bg-tertiary, #0d1117); border-radius: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span class="muted">Average Confidence</span>
          <span style="font-size: 20px; font-weight: 600; ${!isActive ? 'color: var(--text-muted);' : ''}">${displayStats.avg_confidence.toFixed(2)}</span>
        </div>
        <div style="margin-top: 8px; height: 8px; background: var(--border-color, #30363d); border-radius: 4px; overflow: hidden;">
          <div style="height: 100%; width: ${displayStats.avg_confidence * 100}%; background: ${isActive ? 'var(--primary-color, #58a6ff)' : 'var(--text-muted, #8b949e)'}; border-radius: 4px;"></div>
        </div>
      </div>
      ${hasData && displayStats.by_source && displayStats.by_source.length > 0
        ? html`
            <div style="margin-top: 16px;">
              <div class="muted" style="margin-bottom: 8px;">By Source</div>
              ${displayStats.by_source.map(
                (s) => html`
                  <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                    <span>${s.source}</span>
                    <span class="chip">${s.count}</span>
                  </div>
                `
              )}
            </div>
          `
        : nothing}
    </section>
  `;
}

function renderStatBox(label: string, value: number, color: string) {
  return html`
    <div style="flex: 1; min-width: 80px; text-align: center; padding: 12px; background: var(--bg-tertiary, #0d1117); border-radius: 6px;">
      <div style="font-size: 28px; font-weight: 700; color: ${color};">${value}</div>
      <div class="muted" style="font-size: 12px;">${label}</div>
    </div>
  `;
}

function renderHealth(props: MemoryProps) {
  const health = props.health;

  return html`
    <section class="card">
      <div class="card-title">🏥 Health Status</div>
      <div style="margin-top: 12px;">
        ${renderHealthItem(
          "SurrealDB Binary",
          health?.surrealdb_binary?.installed ?? false,
          health?.surrealdb_binary?.installed
            ? health.surrealdb_binary.version || "Installed"
            : "Not installed"
        )}
        ${renderHealthItem(
          "Database Server",
          health?.surrealdb_server?.running ?? false,
          health?.surrealdb_server?.running
            ? `Running on :${health.surrealdb_server.port}`
            : health?.surrealdb_server?.error || "Not running"
        )}
        ${renderHealthItem(
          "Schema Initialized",
          health?.schema?.initialized ?? false,
          health?.schema?.initialized
            ? "Ready"
            : health?.schema?.error || "Not initialized"
        )}
        ${renderHealthItem(
          "Python Dependencies",
          health?.python_deps?.ok ?? false,
          health?.python_deps?.ok
            ? "All installed"
            : `Missing: ${Object.entries(health?.python_deps?.dependencies || {})
                .filter(([, v]) => !v)
                .map(([k]) => k)
                .join(", ")}`
        )}
        ${renderHealthItem(
          "Data Directory",
          health?.data_dir?.exists ?? false,
          health?.data_dir?.path || "~/.clawdbot/memory"
        )}
      </div>
    </section>
  `;
}

function renderHealthItem(label: string, ok: boolean, detail: string) {
  return html`
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-color, #30363d);">
      <span>${label}</span>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="muted" style="font-size: 12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${detail}
        </span>
        <span class="chip ${ok ? "chip-ok" : "chip-warn"}">${ok ? "✓" : "✗"}</span>
      </div>
    </div>
  `;
}

function renderMaintenance(props: MemoryProps) {
  const isServerRunning = props.health?.surrealdb_server?.running ?? false;

  return html`
    <section class="card">
      <div class="card-title">🔧 Maintenance</div>
      <div class="muted" style="margin-top: 8px;">
        Run maintenance operations to keep the knowledge graph healthy.
      </div>

      ${!isServerRunning
        ? html`<div class="callout warning" style="margin-top: 12px;">
            Database server must be running to perform maintenance.
          </div>`
        : nothing}

      <div style="display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap;">
        <button
          class="btn"
          ?disabled=${!isServerRunning || props.busyAction !== null}
          @click=${() => props.onRunMaintenance("decay")}
        >
          ${props.busyAction === "decay" ? "Running…" : "📉 Apply Decay"}
        </button>
        <button
          class="btn"
          ?disabled=${!isServerRunning || props.busyAction !== null}
          @click=${() => props.onRunMaintenance("prune")}
        >
          ${props.busyAction === "prune" ? "Running…" : "🗑️ Prune Stale"}
        </button>
        <button
          class="btn primary"
          ?disabled=${!isServerRunning || props.busyAction !== null}
          @click=${() => props.onRunMaintenance("full")}
        >
          ${props.busyAction === "full" ? "Running…" : "🔄 Full Maintenance"}
        </button>
      </div>

      ${props.maintenanceLog
        ? html`
            <div style="margin-top: 12px;">
              <div class="muted" style="margin-bottom: 4px;">Result</div>
              <pre style="background: var(--bg-tertiary, #0d1117); padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; max-height: 150px; overflow-y: auto; margin: 0;">
${props.maintenanceLog}</pre
              >
            </div>
          `
        : nothing}
    </section>
  `;
}

function renderInstallation(props: MemoryProps) {
  return html`
    <section class="card">
      <div class="card-title">📦 Installation</div>
      <div class="muted" style="margin-top: 8px;">
        Manual installation steps if auto-repair doesn't work.
      </div>

      <div style="display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap;">
        <button
          class="btn"
          ?disabled=${props.busyAction !== null}
          @click=${props.onInstallBinary}
        >
          ${props.busyAction === "binary" ? "Installing…" : "Install SurrealDB"}
        </button>
        <button
          class="btn"
          ?disabled=${props.busyAction !== null}
          @click=${props.onInstallPython}
        >
          ${props.busyAction === "python" ? "Installing…" : "Install Python Deps"}
        </button>
        <button
          class="btn"
          ?disabled=${props.busyAction !== null}
          @click=${props.onStartServer}
        >
          ${props.busyAction === "start" ? "Starting…" : "Start Server"}
        </button>
        <button
          class="btn"
          ?disabled=${props.busyAction !== null}
          @click=${props.onInitSchema}
        >
          ${props.busyAction === "schema" ? "Initializing…" : "Init Schema"}
        </button>
      </div>

      ${props.installLog
        ? html`
            <div style="margin-top: 12px;">
              <div class="muted" style="margin-bottom: 4px;">Output</div>
              <pre style="background: var(--bg-tertiary, #0d1117); padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; max-height: 150px; overflow-y: auto; margin: 0;">
${props.installLog}</pre
              >
            </div>
          `
        : nothing}
    </section>
  `;
}
