import type { IPublicClientApplication } from "@azure/msal-browser";
import { loginRequest } from "./auth";
import type {
  ImageDetail,
  ImageListResponse,
  TagsResponse,
  UploadResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function getAccessToken(
  msalInstance: IPublicClientApplication
): Promise<string> {
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length === 0) {
    throw new Error("No authenticated account found.");
  }

  const response = await msalInstance.acquireTokenSilent({
    ...loginRequest,
    account: accounts[0],
  });

  return response.accessToken;
}

async function apiFetch<T>(
  msalInstance: IPublicClientApplication,
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAccessToken(msalInstance);

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export function listImages(
  msalInstance: IPublicClientApplication
): Promise<ImageListResponse> {
  return apiFetch<ImageListResponse>(msalInstance, "/api/images");
}

export function getImageDetail(
  msalInstance: IPublicClientApplication,
  uploadId: string
): Promise<ImageDetail> {
  return apiFetch<ImageDetail>(msalInstance, `/api/images/${uploadId}`);
}

export function getImageTags(
  msalInstance: IPublicClientApplication,
  uploadId: string
): Promise<TagsResponse> {
  return apiFetch<TagsResponse>(msalInstance, `/api/images/${uploadId}/tags`);
}

export async function uploadImage(
  msalInstance: IPublicClientApplication,
  file: File
): Promise<UploadResponse> {
  // Step 1: Request a write SAS URL from the backend
  const token = await getAccessToken(msalInstance);

  const initResponse = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
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

  // Step 2: Upload the file directly to Blob Storage via the SAS URL
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

export async function deleteImage(
  msalInstance: IPublicClientApplication,
  uploadId: string
): Promise<void> {
  await apiFetch<{ message: string }>(msalInstance, `/api/images/${uploadId}`, {
    method: "DELETE",
  });
}
