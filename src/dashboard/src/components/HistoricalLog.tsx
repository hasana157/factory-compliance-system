import { useMemo, useState } from 'react';
import type { Violation, ViolationFilters } from '../types';
import { exportUrl } from '../utils/api';
import { formatBehavior, formatDateTime, percent } from '../utils/formatters';
import ExportButton from './ExportButton';
import FilterBar from './FilterBar';

interface HistoricalLogProps {
  violations: Violation[];
  onFilter: (filters: ViolationFilters) => void;
}

export default function HistoricalLog({ violations, onFilter }: HistoricalLogProps) {
  const [filters, setFilters] = useState<ViolationFilters>({});
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const pageCount = Math.max(1, Math.ceil(violations.length / pageSize));
  const pageRows = useMemo(
    () => violations.slice((page - 1) * pageSize, page * pageSize),
    [violations, page]
  );

  function applyFilters() {
    setPage(1);
    onFilter(filters);
  }

  function resetFilters() {
    setPage(1);
    setFilters({});
    onFilter({});
  }

  return (
    <section className="panel full-panel">
      <div className="panel-header">
        <div>
          <h2>Historical Log</h2>
          <p className="subtle">Searchable compliance records</p>
        </div>
        <div className="button-row">
          <ExportButton href={exportUrl('csv', filters)} label="CSV" />
          <ExportButton href={exportUrl('json', filters)} label="JSON" />
        </div>
      </div>

      <FilterBar
        filters={filters}
        onChange={setFilters}
        onApply={applyFilters}
        onReset={resetFilters}
      />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Behavior</th>
              <th>Severity</th>
              <th>Zone</th>
              <th>Confidence</th>
              <th>Policy</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-cell">
                  No matching records
                </td>
              </tr>
            ) : (
              pageRows.map((record) => (
                <tr key={record.event_id}>
                  <td>{formatDateTime(record.timestamp)}</td>
                  <td>{formatBehavior(record.behavior_class)}</td>
                  <td>
                    <span className={`severity-chip ${record.severity.toLowerCase()}`}>
                      {record.severity}
                    </span>
                  </td>
                  <td>{record.zone}</td>
                  <td>{percent(record.confidence)}</td>
                  <td>{record.policy_rule_ref}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <button
          className="button secondary"
          type="button"
          disabled={page === 1}
          onClick={() => setPage((value) => Math.max(1, value - 1))}
        >
          Previous
        </button>
        <span>
          Page {page} of {pageCount}
        </span>
        <button
          className="button secondary"
          type="button"
          disabled={page === pageCount}
          onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
        >
          Next
        </button>
      </div>
    </section>
  );
}
