"""
Export sentence-transformers model to ONNX format for offline CPU inference.

This script exports the all-MiniLM-L6-v2 model to ONNX format, which can then
be used for fast CPU-only embeddings without requiring PyTorch or GPU.
"""
from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer
import os

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
OUT_DIR = "vendor/embedder_minilm_l6_v2"

def main():
    print(f"Exporting {MODEL_ID} to ONNX format...")
    print(f"Output directory: {OUT_DIR}")
    
    # Create output directory
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Export tokenizer
    print("\n[1/2] Exporting tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.save_pretrained(OUT_DIR)
    print(f"  Tokenizer saved to {OUT_DIR}")
    
    # Export model to ONNX
    print("\n[2/2] Exporting model to ONNX...")
    model = ORTModelForFeatureExtraction.from_pretrained(
        MODEL_ID,
        export=True,
    )
    model.save_pretrained(OUT_DIR)
    print(f"  Model saved to {OUT_DIR}")
    
    # List exported files
    print(f"\nExported files in {OUT_DIR}:")
    for file in sorted(os.listdir(OUT_DIR)):
        size = os.path.getsize(os.path.join(OUT_DIR, file))
        print(f"  {file} ({size:,} bytes)")
    
    print(f"\n[SUCCESS] Export complete! Model ready at: {OUT_DIR}")

if __name__ == "__main__":
    main()

