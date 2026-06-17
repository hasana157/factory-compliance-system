import { useCallback, useState } from 'react';
import AlertNotification from './components/AlertNotification';
import AlertTimeline from './components/AlertTimeline';
import HistoricalLog from './components/HistoricalLog';
import LiveFeedMonitor from './components/LiveFeedMonitor';
import Navbar from './components/Navbar';
import { useFetchData } from './hooks/useFetchData';
import { useWebSocket } from './hooks/useWebSocket';
import type { Violation, ViolationFilters } from './types';
import { seedDemo } from './utils/api';

type Tab = 'live' | 'alerts' | 'history';

export default function App() {
  const { violations, setViolations, stats, loading, error, refresh } = useFetchData();
  const [activeTab, setActiveTab] = useState<Tab>('live');
  const [latestAlert, setLatestAlert] = useState<Violation | null>(null);

  const addReports = useCallback(
    (reports: Violation[]) => {
      setViolations((current) => [...reports, ...current]);
      const alert = reports.find((item) =>
        ['HIGH', 'CRITICAL'].includes(item.severity)
      );
      if (alert) setLatestAlert(alert);
      refresh();
    },
    [refresh, setViolations]
  );

  useWebSocket(
    useCallback(
      (alert: Violation) => {
        setLatestAlert(alert);
        setViolations((current) => [alert, ...current]);
      },
      [setViolations]
    )
  );

  async function handleSeedDemo() {
    const result = await seedDemo();
    addReports(result.reports);
  }

  function handleFilter(filters: ViolationFilters) {
    refresh(filters);
  }

  return (
    <main className="app-shell">
      <Navbar
        stats={stats}
        loading={loading}
        error={error}
        onSeedDemo={handleSeedDemo}
        onRefresh={() => refresh()}
      />
      <AlertNotification
        alert={latestAlert}
        onDismiss={() => setLatestAlert(null)}
      />

      <nav className="tabs" aria-label="Dashboard views">
        <button
          className={activeTab === 'live' ? 'active' : ''}
          onClick={() => setActiveTab('live')}
          type="button"
        >
          Live
        </button>
        <button
          className={activeTab === 'alerts' ? 'active' : ''}
          onClick={() => setActiveTab('alerts')}
          type="button"
        >
          Alerts
        </button>
        <button
          className={activeTab === 'history' ? 'active' : ''}
          onClick={() => setActiveTab('history')}
          type="button"
        >
          History
        </button>
      </nav>

      {activeTab === 'live' && (
        <LiveFeedMonitor violations={violations} onProcessed={addReports} />
      )}
      {activeTab === 'alerts' && <AlertTimeline violations={violations} />}
      {activeTab === 'history' && (
        <HistoricalLog violations={violations} onFilter={handleFilter} />
      )}
    </main>
  );
}
