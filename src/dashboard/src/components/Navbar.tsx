import type { DashboardStats } from '../types';

interface NavbarProps {
  stats: DashboardStats;
  loading: boolean;
  error: string | null;
  onSeedDemo: () => void;
  onRefresh: () => void;
}

export default function Navbar({
  stats,
  loading,
  error,
  onSeedDemo,
  onRefresh
}: NavbarProps) {
  return (
    <header className="topbar">
      <div>
        <h1>Factory Compliance</h1>
        <p className="subtle">Operations dashboard</p>
      </div>
      <div className="topbar-metrics" aria-live="polite">
        <span className="metric">
          <strong>{stats.total}</strong>
          <small>Total</small>
        </span>
        <span className="metric high">
          <strong>{stats.by_severity.HIGH || 0}</strong>
          <small>High</small>
        </span>
        <span className="metric critical">
          <strong>{stats.by_severity.CRITICAL || 0}</strong>
          <small>Critical</small>
        </span>
      </div>
      <div className="topbar-actions">
        {error && <span className="status-text error">{error}</span>}
        {loading && <span className="status-text">Loading</span>}
        <button className="button secondary" onClick={onRefresh} type="button">
          Refresh
        </button>
        <button className="button primary" onClick={onSeedDemo} type="button">
          Seed Demo
        </button>
      </div>
    </header>
  );
}
