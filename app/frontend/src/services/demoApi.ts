/**
 * Demo API service — same interface as api.ts but without MSAL.
 * Talks directly to the demo FastAPI server.
 */
import type {
  ImageDetail,
  ImageListResponse,
  TagsResponse,
  UploadResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export function listImages(): Promise<ImageListResponse> {
  return apiFetch<ImageListResponse>("/api/images");
}

export function getImageDetail(uploadId: string): Promise<ImageDetail> {
  return apiFetch<ImageDetail>(`/api/images/${uploadId}`);
}

export function getImageTags(uploadId: string): Promise<TagsResponse> {
  return apiFetch<TagsResponse>(`/api/images/${uploadId}/tags`);
}

export async function uploadImage(file: File): Promise<UploadResponse> {
  // Step 1: Request a write SAS URL from the backend
  const initResponse = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type,
      size_bytes: file.size,
    }),
  });

  if (!initResponse.ok) {
    const body = await initResponse.text();
    throw new Error(`Upload init failed (${initResponse.status}): ${body}`);
  }

  const result = (await initResponse.json()) as UploadResponse;

  // Step 2: Upload file directly via SAS URL (demo mock endpoint)
  const uploadResponse = await fetch(result.sas_url, {
    method: "PUT",
    headers: {
      "x-ms-blob-type": "BlockBlob",
      "Content-Type": file.type,
    },
    body: file,
  });

  if (!uploadResponse.ok) {
    throw new Error(
      `Direct blob upload failed (${uploadResponse.status}): ${uploadResponse.statusText}`
    );
  }

  return result;
}

export async function deleteImage(uploadId: string): Promise<void> {
  await apiFetch<{ message: string }>(`/api/images/${uploadId}`, {
    method: "DELETE",
  });
}
