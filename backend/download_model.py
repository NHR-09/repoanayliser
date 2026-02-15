import os
import urllib.request
from pathlib import Path

def progress_hook(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = min(100, (downloaded / total_size) * 100)
    mb_downloaded = downloaded / (1024 * 1024)
    mb_total = total_size / (1024 * 1024)
    print(f"\rDownloading: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)", end="")

model_url = "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz"
cache_dir = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
cache_dir.mkdir(parents=True, exist_ok=True)
model_path = cache_dir / "onnx.tar.gz"

print(f"Downloading model to: {model_path}")
print("This may take 5-10 minutes...\n")

urllib.request.urlretrieve(model_url, model_path, progress_hook)

print("\n✅ Model downloaded successfully!")
print("Restart the server: python main.py")
