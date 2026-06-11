"""Image viewing tool for vision-capable models."""

from __future__ import annotations

from pathlib import Path

IMAGE_EXTS: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}

MAX_IMAGE_BYTES = 4 * 1024 * 1024


async def do_view_image(sandbox, filename: str, use_vision: bool = True) -> tuple[bytes, str] | str:
    basename = Path(filename).name
    ext = Path(basename).suffix.lower()
    mime_type = IMAGE_EXTS.get(ext)
    if not mime_type:
        return f"Not a supported image type: {filename}"
    if not use_vision:
        return "Vision not available for this model. Use bash tools instead."
    search_paths = [f"/challenge/distfiles/{basename}", f"/challenge/workspace/{basename}"]
    if filename.startswith("/"):
        search_paths.insert(0, filename)
    for path in search_paths:
        try:
            data = await sandbox.read_file_bytes(path)
            if len(data) > MAX_IMAGE_BYTES:
                return f"Image too large ({len(data) / 1024 / 1024:.1f} MB > 4 MB limit)."
            return (data, mime_type)
        except Exception:
            continue
    return f"File not found: {filename}"
