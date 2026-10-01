"""Authenticated fixed-family product assets; optional engineering reference, never device state."""
import hashlib
import json
from pathlib import Path
from .common import DomainError

FAMILIES={"PLUG","SWITCH","PRESENCE"}


def product_files(root,family):
    root=Path(root).resolve()
    try:
        catalog=json.loads((root/"catalog.json").read_text(encoding="utf-8"))
        if catalog.get("format")!="carbentra-product-catalog" or catalog.get("schema_version")!=1:raise ValueError("catalog")
        entry=catalog["products"][family]
        if family not in FAMILIES or not isinstance(entry,dict):raise ValueError("family")
        paths={}
        for kind in ("manifest","model","hero"):
            relative=entry[kind]
            if not isinstance(relative,str) or Path(relative).is_absolute():raise ValueError("path")
            path=(root/relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():raise ValueError("path")
            paths[kind]=path
        manifest=json.loads(paths["manifest"].read_text(encoding="utf-8"))
        if manifest.get("family")!=family or manifest.get("source_mode")!="REFERENCE":raise ValueError("manifest")
        manifest={**manifest,"model_url":f"/api/v1/assets/product/model?family={family}","hero_url":f"/api/v1/assets/product/hero?family={family}"}
        return manifest,paths
    except (OSError,ValueError,KeyError,TypeError):
        raise DomainError("product_asset_unavailable","The requested pinned product reference is unavailable or invalid",503)


def verify_asset(path,manifest,kind):
    hash_key,bytes_key=("display_sha256","bytes") if kind=="model" else ("hero_sha256","hero_bytes")
    try:
        expected=manifest[hash_key]
        if not isinstance(expected,str) or len(expected)!=64 or path.stat().st_size!=manifest[bytes_key]:raise ValueError("size")
        with path.open("rb") as stream:
            header=stream.read(12);stream.seek(0)
            actual=hashlib.file_digest(stream,"sha256").hexdigest()
        if actual!=expected or (kind=="model" and header[:4]!=b"glTF") or (kind=="hero" and header[:8]!=b"\x89PNG\r\n\x1a\n"):
            raise ValueError("signature")
    except (OSError,ValueError,KeyError,TypeError):
        raise DomainError("product_asset_invalid","Product asset integrity check failed",503)
    return expected
