"""
Export sentence-transformers model to ONNX format for offline CPU inference.

This script can export multiple embedding models:
- all-MiniLM-L6-v2 (default, fast baseline)
- BAAI/bge-small-en-v1.5 (recommended, better quality)
- Other sentence-transformers models

Usage:
    python tools/export_embedder_onnx.py                    # Exports MiniLM-L6-v2 (default)
    python tools/export_embedder_onnx.py --model bge-small  # Exports BGE-small-en-v1.5
"""
from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer
import os
import argparse

# Model configurations
MODELS = {
    'minilm': {
        'id': 'sentence-transformers/all-MiniLM-L6-v2',
        'dir': 'vendor/embedder_minilm_l6_v2',
        'description': 'MiniLM-L6-v2 (fast baseline, 384 dims)',
    },
    'bge-small': {
        'id': 'BAAI/bge-small-en-v1.5',
        'dir': 'vendor/embedder_bge_small_v1_5',
        'description': 'BGE-small-en-v1.5 (better quality, 384 dims)',
    },
}

def main():
    parser = argparse.ArgumentParser(description='Export embedding model to ONNX format')
    parser.add_argument(
        '--model',
        choices=list(MODELS.keys()),
        default='minilm',
        help='Model to export (default: minilm)',
    )
    args = parser.parse_args()
    
    config = MODELS[args.model]
    model_id = config['id']
    out_dir = config['dir']
    
    print(f"Exporting {model_id}")
    print(f"Description: {config['description']}")
    print(f"Output directory: {out_dir}")
    
    # Create output directory
    os.makedirs(out_dir, exist_ok=True)
    
    # Export tokenizer
    print("\n[1/2] Exporting tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(out_dir)
    print(f"  Tokenizer saved to {out_dir}")
    
    # Export model to ONNX
    print("\n[2/2] Exporting model to ONNX...")
    print("  This may take a few minutes...")
    model = ORTModelForFeatureExtraction.from_pretrained(
        model_id,
        export=True,
    )
    model.save_pretrained(out_dir)
    print(f"  Model saved to {out_dir}")
    
    # List exported files
    print(f"\nExported files in {out_dir}:")
    total_size = 0
    for file in sorted(os.listdir(out_dir)):
        size = os.path.getsize(os.path.join(out_dir, file))
        total_size += size
        print(f"  {file} ({size:,} bytes)")
    print(f"\nTotal size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    
    print(f"\n[SUCCESS] Export complete! Model ready at: {out_dir}")
    print(f"\nTo use this model, update backend/vectordb/service.py:")
    print(f"  Change get_embedder() to load from '{out_dir}'")

if __name__ == "__main__":
    main()

