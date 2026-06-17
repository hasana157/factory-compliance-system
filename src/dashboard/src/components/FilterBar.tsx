import type { ViolationFilters } from '../types';
import { BEHAVIOR_CLASSES, SEVERITY_ORDER } from '../utils/constants';
import { formatBehavior } from '../utils/formatters';

interface FilterBarProps {
  filters: ViolationFilters;
  onChange: (filters: ViolationFilters) => void;
  onApply: () => void;
  onReset: () => void;
}

export default function FilterBar({
  filters,
  onChange,
  onApply,
  onReset
}: FilterBarProps) {
  return (
    <div className="filter-bar">
      <label className="field compact">
        <span>Severity</span>
        <select
          value={filters.severity || ''}
          onChange={(event) => onChange({ ...filters, severity: event.target.value })}
        >
          <option value="">All</option>
          {SEVERITY_ORDER.map((severity) => (
            <option key={severity} value={severity}>
              {severity}
            </option>
          ))}
        </select>
      </label>
      <label className="field compact">
        <span>Behavior</span>
        <select
          value={filters.behavior_class || ''}
          onChange={(event) =>
            onChange({ ...filters, behavior_class: event.target.value })
          }
        >
          <option value="">All</option>
          {BEHAVIOR_CLASSES.map((behavior) => (
            <option key={behavior} value={behavior}>
              {formatBehavior(behavior)}
            </option>
          ))}
        </select>
      </label>
      <label className="field compact">
        <span>Start</span>
        <input
          type="date"
          value={filters.start_date || ''}
          onChange={(event) => onChange({ ...filters, start_date: event.target.value })}
        />
      </label>
      <label className="field compact">
        <span>End</span>
        <input
          type="date"
          value={filters.end_date || ''}
          onChange={(event) => onChange({ ...filters, end_date: event.target.value })}
        />
      </label>
      <button className="button primary" type="button" onClick={onApply}>
        Apply
      </button>
      <button className="button secondary" type="button" onClick={onReset}>
        Reset
      </button>
    </div>
  );
}
