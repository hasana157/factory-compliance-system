import { useMemo, useState } from 'react';
import type { Violation } from '../types';
import { processVideoPath, uploadVideo } from '../utils/api';
import { formatBehavior, percent } from '../utils/formatters';

interface LiveFeedMonitorProps {
  violations: Violation[];
  onProcessed: (reports: Violation[]) => void;
}

export default function LiveFeedMonitor({
  violations,
  onProcessed
}: LiveFeedMonitorProps) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [videoPath, setVideoPath] = useState(
    'data/test/Carrying_Overload_with_Forklift/demo_overload.mp4'
  );
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const visibleDetections = useMemo(() => violations.slice(0, 4), [violations]);

  async function handleFileChange(nextFile: File | null) {
    setFile(nextFile);
    setMessage(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(nextFile ? URL.createObjectURL(nextFile) : null);
  }

  async function processSelected() {
    setProcessing(true);
    setMessage(null);
    try {
      const result = file
        ? await uploadVideo(file)
        : await processVideoPath(videoPath.trim());
      onProcessed(result.reports);
      setMessage(`${result.count} compliance record(s) generated`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setProcessing(false);
    }
  }

  return (
    <section className="view-grid live-view">
      <div className="panel video-panel">
        <div className="panel-header">
          <div>
            <h2>Live Feed Monitor</h2>
            <p className="subtle">Clip inspection and detection overlay</p>
          </div>
          <span className="status-pill online">Ready</span>
        </div>

        <div className="video-stage">
          {previewUrl ? (
            <video src={previewUrl} controls muted />
          ) : (
            <div className="factory-frame" aria-label="Factory floor preview">
              <div className="walkway" />
              <div className="machine machine-a" />
              <div className="machine machine-b" />
              <div className="forklift-shape" />
            </div>
          )}

          {visibleDetections.map((item, index) => (
            <div
              className={`detection-box ${item.severity.toLowerCase()}`}
              key={`${item.event_id}-${index}`}
              style={{
                left: `${8 + index * 13}%`,
                top: `${16 + index * 9}%`,
                width: '22%',
                height: '28%'
              }}
            >
              <span>{item.severity}</span>
            </div>
          ))}
        </div>
      </div>

      <aside className="panel control-panel">
        <div className="panel-header">
          <h2>Process Clip</h2>
        </div>
        <label className="field">
          <span>Dataset path</span>
          <input
            value={videoPath}
            onChange={(event) => setVideoPath(event.target.value)}
            disabled={Boolean(file)}
          />
        </label>
        <label className="file-drop">
          <span>{file ? file.name : 'Choose video file'}</span>
          <input
            type="file"
            accept="video/*"
            onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
          />
        </label>
        <div className="button-row">
          <button
            className="button primary"
            type="button"
            onClick={processSelected}
            disabled={processing}
          >
            {processing ? 'Processing' : 'Process'}
          </button>
          {file && (
            <button
              className="button secondary"
              type="button"
              onClick={() => handleFileChange(null)}
            >
              Clear File
            </button>
          )}
        </div>
        {message && <p className="inline-message">{message}</p>}

        <div className="detection-summary">
          <h3>Recent Detections</h3>
          {visibleDetections.length === 0 ? (
            <p className="subtle">No records yet</p>
          ) : (
            visibleDetections.map((item) => (
              <div className="summary-row" key={item.event_id}>
                <span>{formatBehavior(item.behavior_class)}</span>
                <strong>{percent(item.confidence)}</strong>
              </div>
            ))
          )}
        </div>
      </aside>
    </section>
  );
}
