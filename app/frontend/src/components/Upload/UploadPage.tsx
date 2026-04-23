import React, { useState, useRef } from "react";
import { useMsal } from "@azure/msal-react";
import { uploadImage } from "../../services/api";

const ALLOWED_TYPES = ["image/jpeg", "image/png"];
const MAX_SIZE_MB = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

const UploadPage: React.FC = () => {
  const { instance } = useMsal();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMessage(null);
    setError(null);

    const file = e.target.files?.[0] ?? null;
    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Only JPG and PNG images are allowed.");
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setError(`File exceeds the maximum size of ${MAX_SIZE_MB} MB.`);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setMessage(null);

    try {
      const result = await uploadImage(instance, selectedFile);
      setMessage(
        `Uploaded "${result.filename}" successfully. Processing will begin shortly.`
      );
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <section className="upload-section">
      <h2>Upload Image</h2>
      <p className="upload-hint">
        Select a JPG or PNG image (max {MAX_SIZE_MB} MB). The image will be
        processed automatically by the AI tagging pipeline.
      </p>
      <div className="upload-controls">
        <input
          ref={fileInputRef}
          type="file"
          accept=".jpg,.jpeg,.png"
          onChange={handleFileChange}
          disabled={uploading}
        />
        <button
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
        >
          {uploading ? "Uploading…" : "Upload"}
        </button>
      </div>
      {message && <p className="msg msg-success">{message}</p>}
      {error && <p className="msg msg-error">{error}</p>}
    </section>
  );
};

export default UploadPage;
