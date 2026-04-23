import React, { useCallback, useEffect, useState } from "react";
import { listImages, deleteImage } from "../../services/demoApi";
import type { ImageMetadata } from "../../types";
import StatusBadge from "../Status/StatusBadge";
import DemoImageDetail from "../ImageDetail/DemoImageDetail";

const DemoImageGallery: React.FC = () => {
  const [images, setImages] = useState<ImageMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const fetchImages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listImages();
      setImages(data.images);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load images.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchImages();
  }, [fetchImages]);

  // Auto-poll when any images are still pending
  useEffect(() => {
    const hasPending = images.some((img) => img.status === "pending");
    if (!hasPending) return;

    const interval = setInterval(() => {
      fetchImages();
    }, 10_000);

    return () => clearInterval(interval);
  }, [images, fetchImages]);

  const handleDelete = async (uploadId: string) => {
    if (!window.confirm("Delete this image and all associated data?")) return;

    try {
      await deleteImage(uploadId);
      setImages((prev) => prev.filter((img) => img.id !== uploadId));
      if (selectedId === uploadId) setSelectedId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed.");
    }
  };

  if (selectedId) {
    return (
      <DemoImageDetail
        uploadId={selectedId}
        onBack={() => {
          setSelectedId(null);
          fetchImages();
        }}
      />
    );
  }

  return (
    <section className="image-list-section">
      <div className="section-header">
        <h2>Your Images</h2>
        <button className="btn btn-secondary" onClick={fetchImages}>
          Refresh
        </button>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p className="msg msg-error">{error}</p>}

      {!loading && images.length === 0 && (
        <p className="empty-state">No images uploaded yet.</p>
      )}

      {!loading && images.length > 0 && (
        <table className="image-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Uploaded</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {images.map((img) => (
              <tr key={img.id}>
                <td>
                  <button
                    className="link-btn"
                    onClick={() => setSelectedId(img.id)}
                  >
                    {img.original_filename}
                  </button>
                </td>
                <td>{new Date(img.uploaded_at).toLocaleString()}</td>
                <td>
                  <StatusBadge status={img.status} />
                </td>
                <td>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(img.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
};

export default DemoImageGallery;
