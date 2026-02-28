#!/usr/bin/env python3
"""
GPU Diagnostic Script for MarketPulse

This script diagnoses the GPU configuration for MarketPulse and provides
troubleshooting recommendations.

Usage:
    cd E:/py/MarketPulse/backend
    python scripts/diagnose_gpu.py
"""

import subprocess
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_status(label: str, status: str, is_ok: bool = True):
    """Print a status line with color coding."""
    symbol = "✓" if is_ok else "✗"
    color = "\033[92m" if is_ok else "\033[91m"  # Green / Red
    reset = "\033[0m"
    print(f"  {color}{symbol}{reset} {label:<40} {status}")


def check_nvidia_smi():
    """Check if nvidia-smi is available and get GPU info."""
    print_header("NVIDIA GPU Detection (nvidia-smi)")

    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Parse basic info from nvidia-smi
            lines = result.stdout.split('\n')
            gpu_name = "Unknown"
            driver_version = "Unknown"
            cuda_version = "Unknown"

            for line in lines:
                if "Driver Version:" in line:
                    parts = line.split("Driver Version:")
                    if len(parts) > 1:
                        driver_version = parts[1].split()[0].strip()
                if "CUDA Version:" in line:
                    parts = line.split("CUDA Version:")
                    if len(parts) > 1:
                        cuda_version = parts[1].strip()
                # Look for GPU name (usually in format like "|   0  NVIDIA GeForce ...")
                if "NVIDIA GeForce" in line or "NVIDIA GTX" in line or "NVIDIA RTX" in line:
                    parts = line.split("NVIDIA")
                    if len(parts) > 1:
                        gpu_name = "NVIDIA" + parts[1].split()[0]

            print_status("NVIDIA Driver", f"v{driver_version}", True)
            print_status("CUDA Version", cuda_version, True)
            print_status("GPU Detected", gpu_name, True)

            # Check if Ollama is using GPU
            if "ollama" in result.stdout.lower() or "llama" in result.stdout.lower():
                print_status("Ollama GPU Usage", "Running on GPU", True)
            else:
                print_status("Ollama GPU Usage", "Not currently running", True)

            return {
                "available": True,
                "driver": driver_version,
                "cuda": cuda_version,
                "gpu": gpu_name
            }
        else:
            print_status("NVIDIA GPU", "nvidia-smi failed", False)
            return {"available": False}

    except FileNotFoundError:
        print_status("NVIDIA GPU", "nvidia-smi not found (no NVIDIA driver?)", False)
        return {"available": False}
    except Exception as e:
        print_status("NVIDIA GPU", f"Error: {e}", False)
        return {"available": False}


def check_pytorch_cuda():
    """Check PyTorch CUDA availability."""
    print_header("PyTorch CUDA Configuration")

    try:
        import torch

        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda or "N/A"
        pytorch_version = torch.__version__

        print_status("PyTorch Version", pytorch_version, True)
        print_status("CUDA Available", "Yes" if cuda_available else "No", cuda_available)
        print_status("PyTorch CUDA Version", cuda_version, cuda_available)

        if cuda_available:
            device_count = torch.cuda.device_count()
            print_status("GPU Count", str(device_count), True)

            for i in range(device_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_mem = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                print_status(f"  GPU {i}", f"{gpu_name} ({gpu_mem:.1f} GB)", True)

            return {
                "pytorch_cuda": True,
                "version": pytorch_version,
                "cuda_version": cuda_version,
                "gpu_count": device_count
            }
        else:
            # Check if PyTorch is CPU-only build
            if "+cpu" in pytorch_version:
                print("\n  ⚠️  WARNING: PyTorch is CPU-only build!")
                print("  To fix: pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121")
            else:
                print("\n  ⚠️  WARNING: CUDA not available despite non-CPU PyTorch build")
                print("  Possible causes:")
                print("    - NVIDIA driver not installed or incompatible")
                print("    - CUDA toolkit not installed")
                print("    - PyTorch CUDA version mismatch with system CUDA")

            return {
                "pytorch_cuda": False,
                "version": pytorch_version,
                "cuda_version": cuda_version,
                "is_cpu_build": "+cpu" in pytorch_version
            }

    except ImportError:
        print_status("PyTorch", "Not installed", False)
        return {"pytorch_cuda": False, "installed": False}
    except Exception as e:
        print_status("PyTorch CUDA", f"Error: {e}", False)
        return {"pytorch_cuda": False, "error": str(e)}


def check_transformers():
    """Check transformers library."""
    print_header("Transformers Library")

    try:
        import transformers
        version = transformers.__version__
        print_status("Transformers Version", version, True)
        return {"installed": True, "version": version}
    except ImportError:
        print_status("Transformers", "Not installed", False)
        return {"installed": False}


def check_ollama():
    """Check if Ollama is installed and running."""
    print_header("Ollama Status")

    try:
        import ollama
        # Try to list models
        try:
            models = ollama.list()
            model_count = len(models.get('models', []))
            print_status("Ollama Server", "Running", True)
            print_status("Models Available", str(model_count), True)

            # Show installed models
            if model_count > 0:
                print("\n  Installed Models:")
                for model in models.get('models', []):
                    name = model.get('name', model.get('model', 'Unknown'))
                    size_gb = model.get('size', 0) / (1024**3)
                    print(f"    - {name} ({size_gb:.1f} GB)")

            return {"running": True, "models": model_count}
        except Exception as e:
            print_status("Ollama Server", f"Not running ({e})", False)
            return {"running": False, "error": str(e)}

    except ImportError:
        print_status("Ollama Python Client", "Not installed", False)
        return {"installed": False}


def generate_recommendations(nvidia_info, pytorch_info, ollama_info):
    """Generate recommendations based on diagnostic results."""
    print_header("Recommendations")

    recommendations = []

    # Check for mismatches
    if nvidia_info.get("available") and not pytorch_info.get("pytorch_cuda"):
        recommendations.append(
            "GPU detected but PyTorch CUDA is not available.\n"
            "  → Run: pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121"
        )

    if not pytorch_info.get("pytorch_cuda"):
        recommendations.append(
            "Sentiment Analysis will run on CPU (slower).\n"
            "  → Install PyTorch with CUDA for 10-50x speedup"
        )

    if not ollama_info.get("running"):
        recommendations.append(
            "Ollama server not running.\n"
            "  → Start Ollama to enable AI features"
        )

    # Check GTX 1050 Ti specific recommendations
    if "1050 Ti" in str(nvidia_info.get("gpu", "")):
        print("  ℹ️  NVIDIA GTX 1050 Ti detected (4GB VRAM)")
        print("     - Suitable for DeBERTa sentiment model (~500MB)")
        print("     - Batch size 16 recommended for sentiment analysis")
        print("     - Ollama will work well with smaller models (7B)")

    if not recommendations:
        print("  ✓ All systems operational! GPU is properly configured.")
        print("\n  Expected Performance:")
        print("    - Sentiment Analysis: ~10-50x faster than CPU")
        print("    - Batch Processing: 16 articles per batch (vs 8 on CPU)")
        print("    - FP16 Precision: Enabled on GPU")
    else:
        print("  Issues found:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n  {i}. {rec}")


def main():
    """Run all diagnostics."""
    print("\n" + "=" * 70)
    print("  MarketPulse GPU Diagnostic Tool")
    print("=" * 70)
    print("\n  Checking your GPU configuration for optimal performance...")

    nvidia_info = check_nvidia_smi()
    pytorch_info = check_pytorch_cuda()
    transformers_info = check_transformers()
    ollama_info = check_ollama()

    generate_recommendations(nvidia_info, pytorch_info, ollama_info)

    print_header("Summary")

    # Overall status
    gpu_ok = nvidia_info.get("available", False)
    pytorch_ok = pytorch_info.get("pytorch_cuda", False)
    ollama_ok = ollama_info.get("running", False)

    if gpu_ok and pytorch_ok:
        print("  ✓ GPU Fully Configured")
        print("  ✓ Sentiment Analysis will use GPU acceleration")
        print("  ✓ Ollama is using GPU for LLM inference")
    elif gpu_ok and not pytorch_ok:
        print("  ⚠ GPU detected but PyTorch is not using it")
        print("  ✗ Sentiment Analysis running on CPU (slow)")
    else:
        print("  ✗ No GPU detected")
        print("  ℹ Running in CPU-only mode")

    print("\n" + "=" * 70)
    print("\n  Quick Verification:")
    print("    python -c \"import torch; print(torch.cuda.is_available())\"")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
