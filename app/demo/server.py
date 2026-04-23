"""Demo server — standalone mock API for the starter kit UI.

Serves mock image metadata and AI-tag results based on sample data.
No Azure dependencies required.

Usage:
    cd app/demo
    pip install fastapi uvicorn
    uvicorn server:app --reload --port 8000
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Starter Kit Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory mock database
# ---------------------------------------------------------------------------
DEMO_AGENCY = "Sample Department"
DEMO_USER = "demo.user@example.org"

SAMPLE_IMAGES: list[dict] = [
    {
        "id": "a1b2c3d4",
        "original_filename": "Output_0084_png.rf.14864a26ae470a6ae688eac3fd1478c9.png",
        "blob_name": "a1b2c3d4_Output_0084.png",
        "agency": DEMO_AGENCY,
        "uploaded_by": DEMO_USER,
        "uploaded_at": "2026-04-08T14:22:00+00:00",
        "status": "completed",
        "content_type": "image/png",
        "size_bytes": 1_245_300,
        "output_blob_name": "a1b2c3d4_Output_0084-output.json",
        "tags": {
            "image_id": "Output_0084_png.rf.14864a26ae470a6ae688eac3fd1478c9",
            "scene_summary": "The image shows an urban road intersection with cars, trees, and buildings visible. Functional traffic lights are present.",
            "detections": {
                "potholes": False,
                "illegal_dumping": False,
                "mattresses": False,
                "garbage_bags": False,
                "tires": False,
                "cones": False,
                "clothing": False,
                "bikes": False,
                "toys": False,
                "discarded_furniture": False,
                "shopping_carts": False,
                "graffiti": False,
                "damaged_signs": False,
            },
            "confidence_scores": {
                "potholes": 0.02,
                "illegal_dumping": 0.01,
                "mattresses": 0.00,
                "garbage_bags": 0.03,
                "tires": 0.01,
                "cones": 0.00,
                "clothing": 0.01,
                "bikes": 0.00,
                "toys": 0.00,
                "discarded_furniture": 0.01,
                "shopping_carts": 0.00,
                "graffiti": 0.02,
                "damaged_signs": 0.01,
            },
        },
    },
    {
        "id": "e5f6g7h8",
        "original_filename": "Output_0086_png.rf.be5115874b049d54a0250eb40e79d495.png",
        "blob_name": "e5f6g7h8_Output_0086.png",
        "agency": DEMO_AGENCY,
        "uploaded_by": DEMO_USER,
        "uploaded_at": "2026-04-08T14:25:00+00:00",
        "status": "completed",
        "content_type": "image/png",
        "size_bytes": 1_102_400,
        "output_blob_name": "e5f6g7h8_Output_0086-output.json",
        "tags": {
            "image_id": "Output_0086_png.rf.be5115874b049d54a0250eb40e79d495",
            "scene_summary": "Urban road with vehicles, trees, and buildings visible. A functional traffic light is present.",
            "detections": {
                "potholes": False,
                "illegal_dumping": False,
                "mattresses": False,
                "garbage_bags": False,
                "tires": False,
                "cones": False,
                "clothing": False,
                "bikes": False,
                "toys": False,
                "discarded_furniture": False,
                "shopping_carts": False,
                "graffiti": False,
                "damaged_signs": False,
            },
            "confidence_scores": {
                "potholes": 0.01,
                "illegal_dumping": 0.02,
                "mattresses": 0.00,
                "garbage_bags": 0.01,
                "tires": 0.00,
                "cones": 0.00,
                "clothing": 0.00,
                "bikes": 0.01,
                "toys": 0.00,
                "discarded_furniture": 0.00,
                "shopping_carts": 0.00,
                "graffiti": 0.01,
                "damaged_signs": 0.02,
            },
        },
    },
    {
        "id": "i9j0k1l2",
        "original_filename": "Output_0112_pothole_detected.png",
        "blob_name": "i9j0k1l2_Output_0112_pothole_detected.png",
        "agency": DEMO_AGENCY,
        "uploaded_by": DEMO_USER,
        "uploaded_at": "2026-04-09T09:15:00+00:00",
        "status": "completed",
        "content_type": "image/png",
        "size_bytes": 987_650,
        "output_blob_name": "i9j0k1l2_Output_0112_pothole_detected-output.json",
        "tags": {
            "image_id": "Output_0112_pothole_detected",
            "scene_summary": "A residential street with visible road surface damage. Two potholes are detected near the center lane. No illegal dumping observed.",
            "detections": {
                "potholes": True,
                "illegal_dumping": False,
                "mattresses": False,
                "garbage_bags": False,
                "tires": False,
                "cones": True,
                "clothing": False,
                "bikes": False,
                "toys": False,
                "discarded_furniture": False,
                "shopping_carts": False,
                "graffiti": False,
                "damaged_signs": False,
            },
            "confidence_scores": {
                "potholes": 0.94,
                "illegal_dumping": 0.03,
                "mattresses": 0.00,
                "garbage_bags": 0.02,
                "tires": 0.01,
                "cones": 0.87,
                "clothing": 0.00,
                "bikes": 0.00,
                "toys": 0.00,
                "discarded_furniture": 0.01,
                "shopping_carts": 0.00,
                "graffiti": 0.00,
                "damaged_signs": 0.05,
            },
        },
    },
    {
        "id": "m3n4o5p6",
        "original_filename": "Output_0201_dumping_site.png",
        "blob_name": "m3n4o5p6_Output_0201_dumping_site.png",
        "agency": DEMO_AGENCY,
        "uploaded_by": DEMO_USER,
        "uploaded_at": "2026-04-09T11:42:00+00:00",
        "status": "completed",
        "content_type": "image/png",
        "size_bytes": 1_530_000,
        "output_blob_name": "m3n4o5p6_Output_0201_dumping_site-output.json",
        "tags": {
            "image_id": "Output_0201_dumping_site",
            "scene_summary": "Sidewalk area adjacent to a vacant lot with illegally dumped items including a mattress, several garbage bags, and discarded furniture. Graffiti visible on a nearby wall.",
            "detections": {
                "potholes": False,
                "illegal_dumping": True,
                "mattresses": True,
                "garbage_bags": True,
                "tires": False,
                "cones": False,
                "clothing": True,
                "bikes": False,
                "toys": False,
                "discarded_furniture": True,
                "shopping_carts": True,
                "graffiti": True,
                "damaged_signs": False,
            },
            "confidence_scores": {
                "potholes": 0.04,
                "illegal_dumping": 0.97,
                "mattresses": 0.92,
                "garbage_bags": 0.95,
                "tires": 0.06,
                "cones": 0.00,
                "clothing": 0.78,
                "bikes": 0.03,
                "toys": 0.02,
                "discarded_furniture": 0.89,
                "shopping_carts": 0.82,
                "graffiti": 0.91,
                "damaged_signs": 0.05,
            },
        },
    },
    {
        "id": "q7r8s9t0",
        "original_filename": "Output_0305_pending_upload.jpg",
        "blob_name": "q7r8s9t0_Output_0305_pending_upload.jpg",
        "agency": DEMO_AGENCY,
        "uploaded_by": DEMO_USER,
        "uploaded_at": "2026-04-10T08:02:00+00:00",
        "status": "pending",
        "content_type": "image/jpeg",
        "size_bytes": 780_200,
        "output_blob_name": "q7r8s9t0_Output_0305_pending_upload-output.json",
        "tags": None,
    },
]

# Mutable store keyed by upload_id
_db: dict[str, dict] = {img["id"]: img for img in SAMPLE_IMAGES}

# Placeholder image (1x1 transparent PNG as data-uri won't work for SAS demo,
# so we'll use picsum for realistic placeholders)
_PLACEHOLDER_URLS = [
    "https://picsum.photos/seed/road84/640/480",
    "https://picsum.photos/seed/road86/640/480",
    "https://picsum.photos/seed/road112/640/480",
    "https://picsum.photos/seed/road201/640/480",
    "https://picsum.photos/seed/road305/640/480",
]


def _preview_url(idx: int) -> str:
    return _PLACEHOLDER_URLS[idx % len(_PLACEHOLDER_URLS)]


# ---------------------------------------------------------------------------
# API endpoints mirroring the real Azure Function HTTP triggers
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_initiate(request: Request) -> JSONResponse:
    """Step 1 of SAS flow — return a mock SAS URL."""
    body = await request.json()
    filename = body.get("filename", "unnamed.png")
    content_type = body.get("content_type", "image/png")
    size_bytes = body.get("size_bytes", 0)

    upload_id = str(uuid.uuid4())[:8]
    safe_name = filename.replace(" ", "_")
    blob_name = f"{upload_id}_{safe_name}"

    record = {
        "id": upload_id,
        "original_filename": safe_name,
        "blob_name": blob_name,
        "agency": DEMO_AGENCY,
        "uploaded_by": DEMO_USER,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "content_type": content_type,
        "size_bytes": size_bytes,
        "output_blob_name": f"{upload_id}_{os.path.splitext(safe_name)[0]}-output.json",
        "tags": None,
    }
    _db[upload_id] = record

    return JSONResponse(
        {
            "message": "Upload authorized. Use the SAS URL to upload directly.",
            "upload_id": upload_id,
            "filename": safe_name,
            "status": "pending",
            "blob_name": blob_name,
            # Demo: SAS URL points to a local no-op PUT endpoint
            "sas_url": f"http://localhost:8000/api/demo-blob-upload/{blob_name}",
        },
        status_code=201,
    )


@app.put("/api/demo-blob-upload/{blob_name}")
async def demo_blob_upload(blob_name: str) -> JSONResponse:
    """Mock endpoint simulating Azure Blob PUT via SAS URL."""
    # After "upload", auto-complete processing after a short delay simulation
    for record in _db.values():
        if record["blob_name"] == blob_name and record["status"] == "pending":
            record["status"] = "completed"
            record["tags"] = {
                "image_id": blob_name,
                "scene_summary": "Demo: Image uploaded and processed. Urban scene analysis complete.",
                "detections": {
                    "potholes": False,
                    "illegal_dumping": False,
                    "mattresses": False,
                    "garbage_bags": False,
                    "tires": False,
                    "cones": False,
                    "clothing": False,
                    "bikes": False,
                    "toys": False,
                    "discarded_furniture": False,
                    "shopping_carts": False,
                    "graffiti": False,
                    "damaged_signs": False,
                },
                "confidence_scores": {
                    "potholes": 0.05,
                    "illegal_dumping": 0.02,
                    "mattresses": 0.00,
                    "garbage_bags": 0.01,
                    "tires": 0.00,
                    "cones": 0.00,
                    "clothing": 0.00,
                    "bikes": 0.00,
                    "toys": 0.00,
                    "discarded_furniture": 0.01,
                    "shopping_carts": 0.00,
                    "graffiti": 0.00,
                    "damaged_signs": 0.00,
                },
            }
            break
    return JSONResponse({"status": "ok"}, status_code=201)


@app.get("/api/images")
async def list_images() -> JSONResponse:
    """List all images for the demo agency."""
    images = sorted(_db.values(), key=lambda m: m.get("uploaded_at", ""), reverse=True)
    # Strip tags from list response (matches real API)
    stripped = [{k: v for k, v in img.items() if k != "tags"} for img in images]
    return JSONResponse({"agency": DEMO_AGENCY, "images": stripped, "count": len(stripped)})


@app.get("/api/images/{upload_id}")
async def get_image_detail(upload_id: str) -> JSONResponse:
    """Get detail + preview URL for one image."""
    record = _db.get(upload_id)
    if record is None:
        return JSONResponse({"detail": "Image not found."}, status_code=404)

    idx = list(_db.keys()).index(upload_id)
    result = {**record, "preview_url": _preview_url(idx)}

    if record["status"] == "completed" and record.get("tags"):
        result["tags"] = record["tags"]

    return JSONResponse(result)


@app.get("/api/images/{upload_id}/tags")
async def get_image_tags(upload_id: str) -> JSONResponse:
    """Get AI-generated tags for a processed image."""
    record = _db.get(upload_id)
    if record is None:
        return JSONResponse({"detail": "Image not found."}, status_code=404)

    if record["status"] != "completed":
        return JSONResponse({
            "upload_id": upload_id,
            "status": record["status"],
            "tags": None,
            "message": "Image processing is not yet complete.",
        })

    return JSONResponse({
        "upload_id": upload_id,
        "status": "completed",
        "tags": record.get("tags"),
    })


@app.delete("/api/images/{upload_id}")
async def delete_image(upload_id: str) -> JSONResponse:
    """Delete an image."""
    if upload_id not in _db:
        return JSONResponse({"detail": "Image not found."}, status_code=404)
    del _db[upload_id]
    return JSONResponse({"message": "Image and associated data deleted.", "upload_id": upload_id})
