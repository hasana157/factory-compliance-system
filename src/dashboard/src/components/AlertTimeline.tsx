import type { Violation } from '../types';
import { formatBehavior, formatDateTime } from '../utils/formatters';

interface AlertTimelineProps {
  violations: Violation[];
}

export default function AlertTimeline({ violations }: AlertTimelineProps) {
  const sorted = [...violations].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <section className="panel full-panel">
      <div className="panel-header">
        <div>
          <h2>Alert Timeline</h2>
          <p className="subtle">Chronological violation stream</p>
        </div>
      </div>
      <div className="timeline">
        {sorted.length === 0 ? (
          <p className="empty-state">No violations have been recorded.</p>
        ) : (
          sorted.map((violation) => (
            <article
              className={`timeline-item ${violation.severity.toLowerCase()}`}
              key={violation.event_id}
            >
              <div className="timeline-time">
                <strong>{violation.severity}</strong>
                <small>{formatDateTime(violation.timestamp)}</small>
              </div>
              <div>
                <h3>{formatBehavior(violation.behavior_class)}</h3>
                <p>{violation.event_description}</p>
                <small>
                  {violation.zone} / {violation.policy_rule_ref}
                </small>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
