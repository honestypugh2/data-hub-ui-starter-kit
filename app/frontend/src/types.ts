export interface ImageMetadata {
  id: string;
  original_filename: string;
  blob_name: string;
  agency: string;
  uploaded_by: string;
  uploaded_at: string;
  status: "pending" | "completed" | "failed";
  content_type: string;
  size_bytes: number;
  output_blob_name: string;
}

export interface ImageDetail extends ImageMetadata {
  preview_url: string;
  tags?: Record<string, unknown>;
}

export interface ImageListResponse {
  agency: string;
  images: ImageMetadata[];
  count: number;
}

export interface UploadResponse {
  message: string;
  upload_id: string;
  filename: string;
  status: string;
  blob_name: string;
  sas_url: string;
}

export interface TagsResponse {
  upload_id: string;
  status: string;
  tags: Record<string, unknown> | null;
  message?: string;
}
