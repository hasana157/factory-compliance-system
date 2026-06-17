import type { Violation } from '../types';
import { formatBehavior, formatDateTime } from '../utils/formatters';

interface AlertNotificationProps {
  alert: Violation | null;
  onDismiss: () => void;
}

export default function AlertNotification({
  alert,
  onDismiss
}: AlertNotificationProps) {
  if (!alert || !['HIGH', 'CRITICAL'].includes(alert.severity)) return null;

  return (
    <div className={`alert-notification ${alert.severity.toLowerCase()}`}>
      <div>
        <strong>{alert.severity} safety alert</strong>
        <span>{formatBehavior(alert.behavior_class)}</span>
        <small>{formatDateTime(alert.timestamp)}</small>
      </div>
      <button className="icon-button" onClick={onDismiss} type="button" aria-label="Dismiss">
        x
      </button>
    </div>
  );
}
