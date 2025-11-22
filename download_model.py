#!/usr/bin/env python3
"""Script to download the Llama-3.2-1B-Instruct GGUF model for local inference."""

from huggingface_hub import hf_hub_download
import os

def download_model():
    """Download the Llama-3.2-1B-Instruct-GGUF model."""
    # Model configuration
    model_name = "bartowski/Llama-3.2-1B-Instruct-GGUF"
    model_file = "Llama-3.2-1B-Instruct-Q6_K.gguf"  # Q6 for better accuracy while still tiny

    # Download directory
    download_path = os.path.join(os.path.expanduser("~"), ".ai_assistant", "models")
    os.makedirs(download_path, exist_ok=True)

    print(f"📥 Downloading {model_file} from {model_name}...")
    print(f"💾 Target directory: {download_path}")

    try:
        # Download the model
        model_path = hf_hub_download(
            repo_id=model_name,
            filename=model_file,
            local_dir=download_path,
            local_dir_use_symlinks=False  # Download actual file, not symlink
        )

        print(f"✅ Model downloaded successfully!")
        print(f"📁 Model saved to: {model_path}")

        # Verify the file exists and get its size
        if os.path.exists(model_path):
            file_size = os.path.getsize(model_path) / (1024 * 1024)  # Size in MB
            print(".1f")
        else:
            print("❌ Downloaded file not found!")

        return model_path

    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return None

if __name__ == "__main__":
    download_model()
