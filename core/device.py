"""
Unified device detection for Transcribo.
Handles MPS (Apple Silicon), CUDA (NVIDIA), and CPU fallback.
"""

import platform
from typing import Dict, Optional, Tuple

# Singleton for device info
_device_info: Optional[Dict] = None


def get_device() -> str:
    """
    Detect and return the best available compute device.

    Returns:
        str: "mps" for Apple Silicon, "cuda" for NVIDIA, or "cpu" as fallback.
    """
    try:
        import torch

        # Apple Silicon (M1/M2/M3/M4)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"

        # NVIDIA GPU
        if torch.cuda.is_available():
            return "cuda"

    except ImportError:
        pass

    return "cpu"


def get_device_info() -> Dict:
    """
    Get detailed information about the compute environment.

    Returns:
        dict: System and device information.
    """
    global _device_info

    if _device_info is not None:
        return _device_info

    info = {
        "device": get_device(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "torch_version": None,
        "mps_available": False,
        "mps_built": False,
        "cuda_available": False,
        "cuda_version": None,
        "cpu_count": None,
        "ram_gb": None,
    }

    # CPU info
    try:
        import os
        info["cpu_count"] = os.cpu_count()
    except Exception:
        pass

    # RAM info
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        pass

    # PyTorch info
    try:
        import torch

        info["torch_version"] = torch.__version__

        # MPS (Apple Silicon)
        if hasattr(torch.backends, "mps"):
            info["mps_available"] = torch.backends.mps.is_available()
            info["mps_built"] = torch.backends.mps.is_built()

        # CUDA (NVIDIA)
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["cuda_version"] = torch.version.cuda

    except ImportError:
        pass

    _device_info = info
    return info


def get_device_summary() -> str:
    """Get a one-line summary of the device configuration."""
    info = get_device_info()
    device = info["device"]

    if device == "mps":
        return f"Apple Silicon (MPS) - {info.get('ram_gb', '?')}GB RAM"
    elif device == "cuda":
        return f"NVIDIA GPU (CUDA {info.get('cuda_version', '?')})"
    else:
        return f"CPU ({info.get('cpu_count', '?')} cores)"


def supports_fp16() -> bool:
    """Check if the device supports fp16 precision."""
    device = get_device()
    return device in ("mps", "cuda")


def get_optimal_batch_size(model_size: str = "medium") -> int:
    """
    Get optimal batch size based on device and model.

    Args:
        model_size: Whisper model size (base, small, medium, large-v3)

    Returns:
        int: Recommended batch size
    """
    device = get_device()
    info = get_device_info()
    ram_gb = info.get("ram_gb", 8)

    # Base recommendations
    batch_sizes = {
        "base": 16,
        "small": 8,
        "medium": 4,
        "large-v3": 2,
        "large": 2,
    }

    base_batch = batch_sizes.get(model_size, 4)

    # Adjust for device and RAM
    if device == "mps" and ram_gb >= 32:
        return base_batch * 2
    elif device == "cuda":
        return base_batch * 2
    elif device == "cpu":
        return max(1, base_batch // 2)

    return base_batch


def print_device_info() -> None:
    """Print formatted device information."""
    info = get_device_info()

    print("\n" + "=" * 50)
    print("DEVICE INFORMATION")
    print("=" * 50)
    print(f"Platform:      {info['platform']} ({info['architecture']})")
    print(f"Python:        {info['python_version']}")
    print(f"PyTorch:       {info['torch_version'] or 'Not installed'}")
    print(f"Active Device: {info['device'].upper()}")
    print("-" * 50)

    if info["mps_built"]:
        status = "Available" if info["mps_available"] else "Not available"
        print(f"MPS (Apple):   {status}")

    if info["cuda_available"]:
        print(f"CUDA (NVIDIA): Available (v{info['cuda_version']})")

    print(f"CPU Cores:     {info['cpu_count']}")
    print(f"RAM:           {info['ram_gb']} GB")
    print("=" * 50 + "\n")
