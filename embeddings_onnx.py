"""
Offline CPU-only embeddings provider using ONNX runtime.

This module provides fast, deterministic embeddings without requiring:
- PyTorch
- GPU
- External API calls
- Network connectivity

Uses the exported ONNX model from tools/export_embedder_onnx.py
"""
from __future__ import annotations

import os
import sys
import hashlib
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


def _resource_path(rel_path: str) -> str:
    """
    Works in dev and PyInstaller one-folder/one-file.
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)


def _mean_pool(last_hidden: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    """
    Mean pooling over sequence length dimension.
    
    Args:
        last_hidden: [B, T, H] - hidden states from model
        attention_mask: [B, T] - attention mask (1 for real tokens, 0 for padding)
    
    Returns:
        [B, H] - pooled embeddings
    """
    # Convert mask to float and add dimension: [B, T] -> [B, T, 1]
    mask = attention_mask.astype(np.float32)[:, :, None]
    
    # Sum hidden states weighted by mask: [B, T, H] -> [B, H]
    summed = (last_hidden * mask).sum(axis=1)
    
    # Count non-padding tokens per batch item: [B, T, 1] -> [B, 1]
    counts = mask.sum(axis=1).clip(min=1e-9)
    
    # Mean pool: [B, H] / [B, 1] -> [B, H]
    return summed / counts


@dataclass
class OfflineEmbedder:
    """CPU-only embeddings provider using ONNX runtime."""
    
    session: ort.InferenceSession
    tokenizer: Tokenizer
    max_length: int = 256
    
    @staticmethod
    def load(model_dir: str = "vendor/embedder_bge_small_v1_5") -> "OfflineEmbedder":
        """
        Load the ONNX model and tokenizer.
        
        Args:
            model_dir: Path to directory containing model.onnx and tokenizer.json
        
        Returns:
            OfflineEmbedder instance
        """
        model_path = _resource_path(os.path.join(model_dir, "model.onnx"))
        tok_path = _resource_path(os.path.join(model_dir, "tokenizer.json"))
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                f"Run tools/export_embedder_onnx.py first to export the model."
            )
        if not os.path.exists(tok_path):
            raise FileNotFoundError(
                f"Tokenizer not found at {tok_path}. "
                f"Run tools/export_embedder_onnx.py first to export the model."
            )
        
        # Configure ONNX runtime for CPU
        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 0  # Use all available threads
        sess_opts.inter_op_num_threads = 0
        
        session = ort.InferenceSession(
            model_path,
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        
        tokenizer = Tokenizer.from_file(tok_path)
        
        return OfflineEmbedder(session=session, tokenizer=tokenizer)
    
    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch
        
        Returns:
            np.ndarray of shape [N, H] where N is len(texts) and H is embedding dimension
            Embeddings are L2-normalized for cosine similarity.
        """
        all_vecs: List[np.ndarray] = []
        
        # Determine input names (robust across different export formats)
        inps = {i.name: i for i in self.session.get_inputs()}
        
        # Common input names (fallback to first/second/third if not found)
        input_ids_name = "input_ids" if "input_ids" in inps else list(inps.keys())[0]
        attn_name = "attention_mask" if "attention_mask" in inps else list(inps.keys())[1]
        token_type_ids_name = "token_type_ids" if "token_type_ids" in inps else None
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Tokenize batch
            encs = self.tokenizer.encode_batch(batch)
            
            # Prepare input arrays
            batch_size_actual = len(encs)
            input_ids = np.zeros((batch_size_actual, self.max_length), dtype=np.int64)
            attention = np.zeros((batch_size_actual, self.max_length), dtype=np.int64)
            token_type_ids = np.zeros((batch_size_actual, self.max_length), dtype=np.int64) if token_type_ids_name else None
            
            # Fill arrays with tokenized data
            for r, e in enumerate(encs):
                ids = e.ids[:self.max_length]
                input_ids[r, :len(ids)] = np.array(ids, dtype=np.int64)
                attention[r, :len(ids)] = 1
                if token_type_ids is not None:
                    token_type_ids[r, :len(ids)] = 0  # Usually all zeros for single sequence
            
            # Build input dict
            input_dict = {
                input_ids_name: input_ids,
                attn_name: attention,
            }
            if token_type_ids_name and token_type_ids is not None:
                input_dict[token_type_ids_name] = token_type_ids
            
            # Run inference
            outputs = self.session.run(None, input_dict)
            
            # Extract last hidden state: [B, T, H]
            last_hidden = outputs[0].astype(np.float32)
            
            # Mean pool: [B, T, H] -> [B, H]
            pooled = _mean_pool(last_hidden, attention)
            
            # L2 normalize for cosine similarity
            norms = np.linalg.norm(pooled, axis=1, keepdims=True) + 1e-12
            pooled = pooled / norms
            
            all_vecs.append(pooled)
        
        # Concatenate all batches: [N, H]
        return np.vstack(all_vecs)
    
    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Single text string
        
        Returns:
            np.ndarray of shape [H] - single embedding vector
        """
        result = self.embed([text], batch_size=1)
        return result[0]  # Return first (and only) embedding


def get_text_hash(text: str) -> str:
    """Generate SHA-256 hash for text caching."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


if __name__ == "__main__":
    # Quick test
    print("Loading ONNX embedder...")
    embedder = OfflineEmbedder.load()
    
    test_texts = [
        "This is a test sentence.",
        "Another test sentence for embedding.",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    print(f"\nEmbedding {len(test_texts)} texts...")
    embeddings = embedder.embed(test_texts)
    
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    
    # Test cosine similarity
    sim = np.dot(embeddings[0], embeddings[1])
    print(f"\nCosine similarity between first two texts: {sim:.4f}")
    
    print("\n[SUCCESS] ONNX embedder working correctly!")

