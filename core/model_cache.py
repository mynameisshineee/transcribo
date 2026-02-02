"""
Global model cache for VideoATexto.
Prevents redundant model loading across multiple transcriptions.
"""

from typing import Any, Dict, Optional
import threading

# Thread-safe singleton
_cache_instance: Optional["ModelCache"] = None
_cache_lock = threading.Lock()


class ModelCache:
    """
    Thread-safe global cache for Whisper models.
    Models are keyed by (model_name, device) to allow multiple configurations.
    """

    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load_counts: Dict[str, int] = {}

    def get_key(self, model_name: str, device: str, engine: str = "mlx") -> str:
        """Generate cache key for model."""
        return f"{engine}:{model_name}:{device}"

    def get(self, model_name: str, device: str, engine: str = "mlx") -> Optional[Any]:
        """
        Get cached model if available.

        Args:
            model_name: Model size (base, small, medium, large-v3)
            device: Compute device (mps, cuda, cpu)
            engine: Transcription engine (mlx, openai)

        Returns:
            Cached model or None
        """
        key = self.get_key(model_name, device, engine)
        with self._lock:
            return self._models.get(key)

    def set(self, model_name: str, device: str, model: Any, engine: str = "mlx") -> None:
        """
        Cache a loaded model.

        Args:
            model_name: Model size
            device: Compute device
            model: The loaded model object
            engine: Transcription engine
        """
        key = self.get_key(model_name, device, engine)
        with self._lock:
            self._models[key] = model
            self._load_counts[key] = self._load_counts.get(key, 0) + 1

    def has(self, model_name: str, device: str, engine: str = "mlx") -> bool:
        """Check if model is cached."""
        key = self.get_key(model_name, device, engine)
        with self._lock:
            return key in self._models

    def remove(self, model_name: str, device: str, engine: str = "mlx") -> bool:
        """
        Remove model from cache.

        Returns:
            True if model was removed, False if not found
        """
        key = self.get_key(model_name, device, engine)
        with self._lock:
            if key in self._models:
                del self._models[key]
                return True
            return False

    def clear(self) -> int:
        """
        Clear all cached models.

        Returns:
            Number of models cleared
        """
        with self._lock:
            count = len(self._models)
            self._models.clear()
            return count

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "cached_models": list(self._models.keys()),
                "count": len(self._models),
                "load_counts": dict(self._load_counts),
            }

    def load_mlx_model(self, model_name: str) -> Any:
        """
        Load MLX Whisper model with caching.

        Args:
            model_name: Model size (base, small, medium, large-v3)

        Returns:
            Loaded MLX model
        """
        device = "mlx"  # MLX manages its own device
        engine = "mlx"

        # Check cache first
        cached = self.get(model_name, device, engine)
        if cached is not None:
            return cached

        # Load model
        try:
            import mlx_whisper
        except ImportError:
            raise ImportError("mlx-whisper not installed. Run: pip install mlx-whisper")

        # MLX model names mapping
        mlx_models = {
            "tiny": "mlx-community/whisper-tiny-mlx",
            "base": "mlx-community/whisper-base-mlx",
            "small": "mlx-community/whisper-small-mlx",
            "medium": "mlx-community/whisper-medium-mlx",
            "large": "mlx-community/whisper-large-v3-mlx",
            "large-v3": "mlx-community/whisper-large-v3-mlx",
        }

        model_path = mlx_models.get(model_name, mlx_models["medium"])

        # MLX models are loaded on-demand during transcription
        # We just store the path for now
        self.set(model_name, device, model_path, engine)
        return model_path

    def load_openai_model(self, model_name: str, device: str) -> Any:
        """
        Load OpenAI Whisper model with caching.

        Args:
            model_name: Model size
            device: Compute device

        Returns:
            Loaded Whisper model
        """
        engine = "openai"

        # Check cache first
        cached = self.get(model_name, device, engine)
        if cached is not None:
            return cached

        # Load model
        try:
            import whisper
        except ImportError:
            raise ImportError("openai-whisper not installed. Run: pip install openai-whisper")

        model = whisper.load_model(model_name, device=device)
        self.set(model_name, device, model, engine)
        return model


def get_model_cache() -> ModelCache:
    """Get or create singleton ModelCache instance."""
    global _cache_instance

    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = ModelCache()

    return _cache_instance


def clear_model_cache() -> int:
    """Clear the global model cache."""
    cache = get_model_cache()
    return cache.clear()
