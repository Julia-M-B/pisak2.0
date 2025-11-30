"""
Model loader and tokenizer wrapper for LSTM language model.
"""
import os
import torch
import torch.nn as nn
import sentencepiece as spm
from typing import List


class LSTMLanguageModel(nn.Module):
    """LSTM Language Model architecture."""
    
    def __init__(self, vocab_size: int, emb_dim: int = 512, hidden_dim: int = 512, 
                 n_layers: int = 3, dropout: float = 0.1):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.lstm = nn.LSTM(input_size=emb_dim, hidden_size=hidden_dim, 
                           num_layers=n_layers, batch_first=True, 
                           dropout=dropout if n_layers > 1 else 0.0)
        self.output = nn.Linear(hidden_dim, vocab_size)
        self.output.weight = self.embedding.weight

    def forward(self, input_ids: torch.LongTensor, hidden=None):
        # input_ids: (batch, seq_len)
        emb = self.embedding(input_ids)  # (batch, seq_len, emb_dim)
        out, hidden = self.lstm(emb, hidden)  # out: (batch, seq_len, hidden)
        logits = self.output(out)  # (batch, seq_len, vocab)
        return logits, hidden


class LSTMModelWrapper:
    """
    Wrapper for LSTM model that provides predict() method for beam search.
    """
    
    def __init__(self, model_path: str, device: str = None):
        """
        Initialize the model wrapper.
        
        Args:
            model_path: Path to model.pt file
            device: Device to run model on ('cpu' or 'cuda'). If None, auto-detect.
        """
        if device is None:
            # device = 'cuda' if torch.cuda.is_available() else 'cpu'
            device = 'cpu'
        self.device = torch.device(device)
        
        # Load model state dict
        state_dict = torch.load(model_path, map_location=self.device)

        # Infer model architecture from state dict
        # Get vocab_size from embedding weight
        if 'embedding.weight' in state_dict:
            vocab_size = state_dict['embedding.weight'].shape[0]
        else:
            raise ValueError("Could not infer vocab_size from state dict")

        # Get other hyperparameters from state dict
        emb_dim = state_dict['embedding.weight'].shape[1]
        if 'lstm.weight_ih_l0' in state_dict:
            # LSTM input size is 1/4 of weight_ih_l0 (because it's 4 gates)
            hidden_dim = state_dict['lstm.weight_ih_l0'].shape[0] // 4
        else:
            hidden_dim = 512  # default

        # Count LSTM layers
        n_layers = 0
        while f'lstm.weight_ih_l{n_layers}' in state_dict:
            n_layers += 1
        if n_layers == 0:
            n_layers = 3  # default

        # Check if weights are tied by checking if output.weight exists and is different from embedding.weight
        # If weights are tied, output.weight might not be in state_dict, or it might be the same as embedding.weight
        # weights_tied = False
        # if 'output.weight' in state_dict and 'embedding.weight' in state_dict:
        #     # Check if they are the same tensor (same memory location)
        #     output_weight = state_dict['output.weight']
        #     embedding_weight = state_dict['embedding.weight']
        #     # If shapes match and they're equal, weights might be tied
        #     if output_weight.shape == embedding_weight.shape:
        #         if torch.equal(output_weight, embedding_weight):
        #             weights_tied = True
        # elif 'output.weight' not in state_dict:
        #     # If output.weight is missing, weights are likely tied
        #     weights_tied = True
        
        # Create model
        self.model = LSTMLanguageModel(
            vocab_size=vocab_size,
            emb_dim=emb_dim,
            hidden_dim=hidden_dim,
            n_layers=n_layers
        )
        
        # Load state dict (with strict=False to handle potential mismatches)
        try:
            self.model.load_state_dict(state_dict, strict=True)
        except RuntimeError:
            # If strict loading fails, try without strict (might work if only tied weights differ)
            self.model.load_state_dict(state_dict, strict=False)
        self.model.to(self.device)
        self.model.eval()
        
        self.vocab_size = vocab_size
        self.seq_len = 32
    
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
        context_tokens = context_tokens[-self.seq_len:]
        
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


def load_model_and_tokenizer(model_dir: str = None, device: str = None):
    """
    Convenience function to load both model and tokenizer.
    
    Args:
        model_dir: Directory containing model.pt and spm_pl.model. 
                  If None, uses predictions directory.
        device: Device to run model on. If None, auto-detect.
        
    Returns:
        Tuple of (model_wrapper, tokenizer)
    """
    if model_dir is None:
        # Get directory of this file
        model_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_path = os.path.join(model_dir, 'model.pt')
    tokenizer_path = os.path.join(model_dir, 'spm_pl.model')
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer file not found: {tokenizer_path}")
    
    model = LSTMModelWrapper(model_path, device=device)
    tokenizer = SentencePieceTokenizer(tokenizer_path)
    
    return model, tokenizer

def main():
    model, tokenizer = load_model_and_tokenizer(device="cpu")
    text = "to jest test spacji i tego czy tokeny są poprawnie wyznaczone "
    text2 = " tokenizer "
    # pieces = tokenizer.encode_as_pieces(text2)
    # piece = tokenizer.id_to_piece(4)
    # print(piece.startswith("▁"))
    tokens = tokenizer.encode(text)
    tokens2 = tokenizer.encode(text2)

    print(tokenizer.encode_as_pieces(text2))

if __name__ == "__main__":
    main()
