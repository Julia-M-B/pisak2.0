"""
Model loader and tokenizer wrapper for LSTM language model.
"""

import os
from pathlib import Path
from typing import List

import sentencepiece as spm
import torch
import torch.nn as nn

from aac_app.logging_config import get_module_logger
from aac_app.predictions.model_store import resolve_model_file
from aac_app.settings import DEFAULT_PREDICTION_MODEL_NAME

logger = get_module_logger(file_name="predictions", logger_name=__name__)
MODEL_NAME_ENV_VAR = "APP_MODEL_NAME"


class LSTMLanguageModel(nn.Module):
    """LSTM Language Model architecture."""

    def __init__(
        self,
        vocab_size: int,
        emb_dim: int = 320,
        hidden_dim: int = 512,
        n_layers: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.emb_dim = emb_dim
        self.hidden_dim = hidden_dim
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            input_size=emb_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        if self.emb_dim != self.hidden_dim:
            self.projection = nn.Linear(hidden_dim, emb_dim, bias=False)
        self.output = nn.Linear(emb_dim, vocab_size)
        self.output.weight = self.embedding.weight

    def forward(self, input_ids: torch.LongTensor, hidden=None):
        # input_ids: (batch, seq_len)
        emb = self.embedding(input_ids)  # (batch, seq_len, emb_dim)
        out, hidden = self.lstm(emb, hidden)  # out: (batch, seq_len, hidden)
        if self.emb_dim != self.hidden_dim:
            out = self.projection(out)
        logits = self.output(out)  # (batch, seq_len, vocab)
        return logits, hidden


class LSTMModelWrapper:
    """
    Wrapper for LSTM model that provides predict() method for beam search.
    """

    def __init__(self, model_path: str, device: str = None, seq_len: int = 256):
        """
        Initialize the model wrapper.

        Args:
            model_path: Path to model.pt file
            device: Device to run model on ('cpu' or 'cuda'). If None, defaults to
                    'cpu' (GPU auto-detection is intentionally disabled for now).
            seq_len: Maximum context length; longer contexts are trimmed to the last seq_len tokens.
        """
        if device is None:
            # GPU auto-detection deliberately disabled; re-enable with:
            # device = "cuda" if torch.cuda.is_available() else "cpu"
            device = "cpu"
        self.device = torch.device(device)

        # Load model state dict
        state_dict = torch.load(model_path, map_location=self.device)

        # Infer model architecture from state dict
        # Get vocab_size from embedding weight
        if "embedding.weight" in state_dict:
            vocab_size = state_dict["embedding.weight"].shape[0]
        else:
            raise ValueError("Could not infer vocab_size from state dict")

        # Get other hyperparameters from state dict
        emb_dim = state_dict["embedding.weight"].shape[1]
        if "lstm.weight_ih_l0" in state_dict:
            # LSTM input size is 1/4 of weight_ih_l0 (because it's 4 gates)
            hidden_dim = state_dict["lstm.weight_ih_l0"].shape[0] // 4
        else:
            hidden_dim = 512  # default

        # Count LSTM layers
        n_layers = 0
        while f"lstm.weight_ih_l{n_layers}" in state_dict:
            n_layers += 1
        if n_layers == 0:
            n_layers = 3  # default

        # Create model
        self.model = LSTMLanguageModel(
            vocab_size=vocab_size,
            emb_dim=emb_dim,
            hidden_dim=hidden_dim,
            n_layers=n_layers,
        )

        self.model.load_state_dict(state_dict, strict=True)
        self.model.to(self.device)
        self.model.eval()

        self.vocab_size = vocab_size
        self.seq_len = seq_len

    def predict(self, context_tokens: List[int]) -> List[float]:
        """
        Predict next token probabilities given context tokens.

        Args:
            context_tokens: List of token IDs representing the context

        Returns:
            List of probabilities for each token in vocabulary
        """
        if not context_tokens:
            # If no context, return uniform distribution
            return [1.0 / self.vocab_size] * self.vocab_size

        # trim context tokens to proper sequence length
        context_tokens = context_tokens[-self.seq_len :]

        # Convert to tensor and add batch dimension
        input_ids = torch.LongTensor([context_tokens]).to(self.device)

        with torch.no_grad():
            # Get logits for the last position
            logits, _ = self.model(input_ids)
            # logits shape: (batch=1, seq_len, vocab_size)
            # Get logits for the last token position
            last_logits = logits[0, -1, :]  # (vocab_size,)

            # Convert to probabilities using softmax
            probs = torch.softmax(last_logits, dim=0)

            # Convert to list
            return probs.cpu().tolist()


class SentencePieceTokenizer:
    """
    Wrapper for SentencePiece tokenizer.
    """

    def __init__(self, model_path: str):
        """
        Initialize the tokenizer.

        Args:
            model_path: Path to .model file (e.g., spm_pl.model)
        """
        self.sp = spm.SentencePieceProcessor()
        self.sp.load(model_path)
        self.vocab_size = self.sp.get_piece_size()
        self.id2piece = {i: self.id_to_piece(i) for i in range(self.vocab_size)}
        self.piece2id = {v: k for k, v in self.id2piece.items()}

    def encode(self, text: str) -> List[int]:
        """
        Encode text to token IDs.

        Args:
            text: Input text string

        Returns:
            List of token IDs
        """
        return self.sp.encode(text, out_type=int)

    def decode(self, token_ids: List[int]) -> str:
        """
        Decode token IDs to text.

        Args:
            token_ids: List of token IDs

        Returns:
            Decoded text string
        """
        return self.sp.decode(token_ids)

    def encode_as_pieces(self, text):
        return self.sp.encode_as_pieces(text)

    def id_to_piece(self, token: int) -> str:
        return self.sp.id_to_piece(token)

    def get_piece_size(self) -> int:
        return self.sp.get_piece_size()


def load_model_and_tokenizer(
    model_dir: str = None,
    device: str = None,
    seq_len: int = 128,
    model_name: str | None = None,
):
    """
    Convenience function to load both model and tokenizer.

    Files are located through `aac_app.predictions.model_store`, which checks the
    bundled models directory and the per-user cache and downloads large weights on
    first use. Pass `model_dir` to load from a specific directory instead.

    Args:
        model_dir: Directory containing the model and spm_pl.model files. If None,
                   files are resolved (and downloaded if needed) via the model store.
        device: Device to run model on. If None, defaults to CPU.
        model_name: Model filename. If None, uses the APP_MODEL_NAME env var
                    and falls back to the config default.

    Returns:
        Tuple of (model_wrapper, tokenizer)
    """
    if model_name is None:
        model_name = os.getenv(MODEL_NAME_ENV_VAR, DEFAULT_PREDICTION_MODEL_NAME)

    if model_dir is not None:
        # Explicit directory: use it as-is, no download.
        model_path = Path(model_dir) / model_name
        tokenizer_path = Path(model_dir) / "spm_pl.model"
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not tokenizer_path.exists():
            raise FileNotFoundError(f"Tokenizer file not found: {tokenizer_path}")
    else:
        # Resolve via the store: bundled -> cache -> download.
        model_path = resolve_model_file(model_name)
        tokenizer_path = resolve_model_file("spm_pl.model")

    model = LSTMModelWrapper(str(model_path), device=device, seq_len=seq_len)
    tokenizer = SentencePieceTokenizer(str(tokenizer_path))

    return model, tokenizer


def main():
    model, tokenizer = load_model_and_tokenizer(device="cpu")
    text2 = " tokenizer "
    logger.debug("%s", tokenizer.encode_as_pieces(text2))


if __name__ == "__main__":
    main()
