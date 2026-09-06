"""On-disk model persistence and in-memory model store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from backend.app.config import get_settings
from backend.app.utils.logger import get_logger

logger = get_logger("insightai.ml.registry")

MODEL_NAMES = ("sentiment", "emotion", "category", "intent")


class ModelStore:
    """Loads and saves scikit-learn pipelines plus metadata."""

    def __init__(self) -> None:
        self.models: dict[str, Any] = {}
        self.metadata: dict[str, dict[str, Any]] = {}

    @property
    def directory(self) -> Path:
        return get_settings().model_path

    def path_for(self, name: str) -> Path:
        return self.directory / f"{name}.joblib"

    def meta_path_for(self, name: str) -> Path:
        return self.directory / f"{name}.json"

    def exists(self, name: str) -> bool:
        return self.path_for(name).exists()

    def all_exist(self) -> bool:
        return all(self.exists(name) for name in MODEL_NAMES)

    def save(self, name: str, model: Any, metadata: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, self.path_for(name))
        self.meta_path_for(name).write_text(json.dumps(metadata, default=str, indent=2), encoding="utf-8")
        self.models[name] = model
        self.metadata[name] = metadata
        logger.info("Saved model %s version %s", name, metadata.get("version"))

    def load(self, name: str) -> Any:
        if name in self.models:
            return self.models[name]
        path = self.path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        model = joblib.load(path)
        self.models[name] = model
        meta_path = self.meta_path_for(name)
        if meta_path.exists():
            self.metadata[name] = json.loads(meta_path.read_text(encoding="utf-8"))
        return model

    def load_all(self) -> None:
        for name in MODEL_NAMES:
            if self.exists(name):
                self.load(name)
                logger.info("Loaded model %s", name)

    def get(self, name: str) -> Any:
        if name not in self.models:
            return self.load(name)
        return self.models[name]

    def healthy(self) -> bool:
        try:
            return all(name in self.models or self.exists(name) for name in MODEL_NAMES)
        except Exception:
            return False


store = ModelStore()
