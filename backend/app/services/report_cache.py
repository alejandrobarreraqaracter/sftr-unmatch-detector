from pathlib import Path


CACHE_ROOT = Path(__file__).resolve().parents[2] / "report_cache"


def ensure_cache_dir() -> Path:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return CACHE_ROOT


def snapshot_artifact_path(snapshot_id: int, fmt: str) -> Path:
    ensure_cache_dir()
    safe_format = fmt.lower()
    return CACHE_ROOT / f"regulatory_snapshot_{snapshot_id}.{safe_format}"


def artifact_exists(snapshot_id: int, fmt: str) -> bool:
    return snapshot_artifact_path(snapshot_id, fmt).exists()


def artifact_metadata(snapshot_id: int, fmt: str) -> dict:
    path = snapshot_artifact_path(snapshot_id, fmt)
    if not path.exists():
        return {
            "format": fmt,
            "cached": False,
            "size_bytes": 0,
            "path": str(path),
        }
    stat = path.stat()
    return {
        "format": fmt,
        "cached": True,
        "size_bytes": stat.st_size,
        "path": str(path),
        "mtime": stat.st_mtime,
    }


def write_artifact(snapshot_id: int, fmt: str, payload: bytes) -> Path:
    path = snapshot_artifact_path(snapshot_id, fmt)
    path.write_bytes(payload)
    return path


def read_artifact(snapshot_id: int, fmt: str) -> bytes | None:
    path = snapshot_artifact_path(snapshot_id, fmt)
    if not path.exists():
        return None
    return path.read_bytes()
