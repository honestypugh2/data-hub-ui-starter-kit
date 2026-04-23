import React, { useEffect, useState } from "react";
import { useMsal } from "@azure/msal-react";
import { getImageDetail } from "../../services/api";
import type { ImageDetail as ImageDetailType } from "../../types";
import StatusBadge from "../Status/StatusBadge";

interface Props {
  uploadId: string;
  onBack: () => void;
}

const ImageDetail: React.FC<Props> = ({ uploadId, onBack }) => {
  const { instance } = useMsal();
  const [detail, setDetail] = useState<ImageDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getImageDetail(instance, uploadId);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled)
          setError(
            err instanceof Error ? err.message : "Failed to load detail."
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchDetail();
    return () => {
      cancelled = true;
    };
  }, [instance, uploadId]);

  // Auto-poll while status is pending
  useEffect(() => {
    if (!detail || detail.status !== "pending") return;

    const interval = setInterval(async () => {
      try {
        const data = await getImageDetail(instance, uploadId);
        setDetail(data);
      } catch {
        // ignore transient errors during polling
      }
    }, 5_000);

    return () => clearInterval(interval);
  }, [detail, instance, uploadId]);

  if (loading) return <p>Loading…</p>;
  if (error) return <p className="msg msg-error">{error}</p>;
  if (!detail) return null;

  return (
    <section className="image-detail-section">
      <button className="btn btn-secondary" onClick={onBack}>
        ← Back to list
      </button>

      <h2>{detail.original_filename}</h2>

      <div className="detail-grid">
        <div className="detail-preview">
          <img
            src={detail.preview_url}
            alt={detail.original_filename}
            className="preview-image"
          />
        </div>

        <div className="detail-info">
          <dl>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={detail.status} />
            </dd>

            <dt>Uploaded By</dt>
            <dd>{detail.uploaded_by}</dd>

            <dt>Uploaded At</dt>
            <dd>{new Date(detail.uploaded_at).toLocaleString()}</dd>

            <dt>Agency</dt>
            <dd>{detail.agency}</dd>

            <dt>File Size</dt>
            <dd>{(detail.size_bytes / 1024).toFixed(1)} KB</dd>
          </dl>
        </div>
      </div>

      {detail.status === "completed" && detail.tags && (
        <div className="tags-section">
          <h3>AI-Generated Tags (JSON)</h3>
          <pre className="json-output">
            {JSON.stringify(detail.tags, null, 2)}
          </pre>
        </div>
      )}

      {detail.status === "pending" && (
        <p className="msg msg-info">
          Processing is in progress. Refresh in a moment to see results.
        </p>
      )}

      {detail.status === "failed" && (
        <p className="msg msg-error">
          Processing failed. Check the Function App logs for details.
        </p>
      )}
    </section>
  );
};

export default ImageDetail;
