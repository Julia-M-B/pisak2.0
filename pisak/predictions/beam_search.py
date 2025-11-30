import heapq
import math
from typing import List, Tuple, Dict, Union
from dataclasses import dataclass, field
import unicodedata
import re

CLEAN_REGEX = re.compile(r"[^a-ząćęłńóśźż0-9\s]")
MULTIPLE_WHITESPACE = re.compile(r"[ \t]+")


@dataclass(
    order=True)  # order=True automatycznie tworzy dunder methods pozwalajace porownywac dwa obiekty typu BeamItem
class BeamItem:
    """Represents a partial word being explored in the beam.

    Attributes:
        neg_log_prob: Negative log probability (for max-heap using min-heap)
        tokens: List of token IDs forming this partial word
        text: Human-readable text of the partial word
    """
    # prawdopodobienstwo: [0, 1] -> logarytm z tego: [-inf (token o prawdop. 0), 0 (token o prawdop. 1)]
    # jak teraz zamienimy to na negative number to tokeny majace najmniejsze prawdopodobienstwo pojawienia sie
    # beda mialy najwyzsza wartosc - co jest idealna sytuacja, jesli korzystamy z min-heap (domyslna implementaxja z heapq)
    # bo elementy najmniejsze beda na poczatku, a najwieksze - na koncu
    neg_log_prob_normalised: float
    neg_log_prob: float = field(compare=False)
    tokens: List[int] = field(compare=False)  # tego nie chcemy porownywac
    text: str = field(compare=False)  # tego tez nie chcemy porownywac


@dataclass(order=True)
class CompletedWord:
    """Represents a completed word with its probability.

    Attributes:
        neg_log_prob: Negative log probability
        tokens: List of token IDs forming the complete word
        text: Human-readable text of the word
        probability: Actual probability (exp of negative neg_log_prob)
    """
    # prawdopodobienstwo: [0, 1] -> logarytm z tego: [-inf (token o prawdop. 0), 0 (token o prawdop. 1)]
    # jak teraz zamienimy to na negative number to tokeny majace najmniejsze prawdopodobienstwo pojawienia sie
    # beda mialy najwyzsza wartosc - co jest idealna sytuacja, jesli korzystamy z min-heap (domyslna implementaxja z heapq)
    # bo elementy najmniejsze beda na poczatku, a najwieksze - na koncu
    neg_log_prob_normalised: float
    tokens: List[int] = field(compare=False)
    text: str = field(compare=False)
    probability: float = field(compare=False)


class WordPredictionBeamSearch:
    """Efficient beam search for finding top-K most probable next words."""

    def __init__(self, model, tokenizer, beam_width: int = 30,
                 max_word_length: int = 10):
        """
        Args:
            model: LSTM model with predict() method that returns token probabilities
            tokenizer: Tokenizer with decode() and check if token starts word
            beam_width: Maximum number of partial words to keep in beam
            max_word_length: Maximum number of tokens per word (prunes longer words)
        """
        self.model = model
        self.tokenizer = tokenizer
        self.beam_width = beam_width
        self.max_word_length = max_word_length
        self.inference_count = 0
        self.start_new_word_char: str = "▁"
        self.penalty_value = 5
        self.alpha = 0.6

    def starts_new_word(self, token_id: int) -> bool:
        """Check if a token starts a new word (piece starts with '▁' marker)."""
        token_piece = self.tokenizer.id_to_piece(token_id)
        return token_piece.startswith(self.start_new_word_char)

    # @staticmethod
    # def is_special_token(token_id: int) -> bool:
    #     return token_id <= 3

    def contains_letters_only(self, token_id: int) -> bool:
        token_text = self.tokenizer.decode([token_id])
        return token_text.isalpha()

    def get_top_k_words(self, context_text: str, k: int = 5) -> List[
        Tuple[str, float, int]]:
        """
        Find top-K most probable next complete words.

        Args:
            context_text: Input text to predict next word from
            k: Number of top words to return

        Returns:
            List of (word_text, probability, num_inferences) tuples
        """
        # Reset inference counter
        self.inference_count = 0

        # Encode context
        context_text = self._clean_context_text(context_text)
        context_text, unfinished_word = self._extract_unfinished_word(
            context_text)
        context_tokens = self.tokenizer.encode(context_text)
        
        # Initialize beam based on whether we have an unfinished word
        if unfinished_word:
            # If we have an unfinished word, initialize beam with that prefix
            unfinished_tokens = self.tokenizer.encode(unfinished_word)
            unfinished_text = unfinished_word
            beam = [
                BeamItem(neg_log_prob_normalised=0.0, neg_log_prob=0.0, 
                        tokens=unfinished_tokens, text=unfinished_text)]
        else:
            # If no unfinished word, start with empty prefix
            beam = [
                BeamItem(neg_log_prob_normalised=0.0, neg_log_prob=0.0, tokens=[],
                         text="")]
        completed_words = []
        completed_words_texts = []

        # Cache for token probabilities: (context + prefix) -> token_probs
        prob_cache: Dict[Tuple[int, ...], List[Tuple[int, float]]] = {}
        
        # Track explored prefixes to avoid cycles (only mark as explored after processing)
        explored_prefixes: set[Tuple[int, ...]] = set()
        
        # Track prefixes currently in beam to avoid duplicates
        beam_prefixes: set[Tuple[int, ...]] = set()
        # Initialize with starting prefix
        if unfinished_word:
            initial_tokens = self.tokenizer.encode(unfinished_word)
            beam_prefixes.add(tuple(context_tokens + initial_tokens))
        else:
            beam_prefixes.add(tuple(context_tokens + []))

        print(f"Starting beam search for: '{context_text}'")
        print(
            f"Beam width: {self.beam_width}, Max word length: {self.max_word_length}\n")

        iteration = 0
        max_iterations = k * self.beam_width * 10  # Safety limit to prevent infinite loops

        # Continue until we have k completed words or beam is exhausted
        while beam and len(completed_words) < k and iteration < max_iterations:
            iteration += 1
            print(f"=== Iteration {iteration} ===")
            print(
                f"Beam size: {len(beam)}, Completed words: {len(completed_words)}")

            # Pop the most promising partial word (lowest neg_log_prob = highest prob)
            prefix_texts = [prefix.text for prefix in beam]
            current = heapq.heappop(beam)
            current_log_prob = -current.neg_log_prob

            print(
                f"\nExploring prefix: '{current.text}' (tokens: {current.tokens})")
            print(
                f"  Cumulative log prob: {current_log_prob:.4f} (prob: {math.exp(current_log_prob):.6f})")

            # Prune: Skip if prefix is too long (unlikely to be a real word)
            if len(current.tokens) >= self.max_word_length:
                print(f"  → Pruned (exceeds max length {self.max_word_length})")
                continue

            # Create cache key for this context + prefix
            # context_tokens is the finished context, current.tokens is the prefix we're building
            cache_key = tuple(context_tokens + current.tokens)
            
            # Skip if we've already explored this exact prefix
            if cache_key in explored_prefixes:
                print(f"  → Skipping (already explored)")
                continue
            
            # Mark this prefix as explored (we're about to process it)
            explored_prefixes.add(cache_key)
            # Remove from beam_prefixes since we're processing it now
            beam_prefixes.discard(cache_key)

            # Get next token probabilities (use cache if available)
            if cache_key in prob_cache:
                top_next_tokens = prob_cache[cache_key]
                print(f"  → Using cached probabilities")
            else:
                # Run model inference
                token_probs = self.model.predict(
                    context_tokens + current.tokens)
                self.inference_count += 1

                # Get top beam_width tokens
                top_next_tokens = self._get_top_tokens(token_probs,
                                                       self.beam_width)
                prob_cache[cache_key] = top_next_tokens

                print(f"  → Inference #{self.inference_count}")

            print(f"  Exploring {len(top_next_tokens)} next tokens:")

            # Expand beam with each possible next token
            for token_id, token_prob in top_next_tokens:
                if not self.contains_letters_only(token_id):
                    continue

                if self.starts_new_word(token_id):
                    # If we have an unfinished word, this token completes it
                    if unfinished_word:
                        # Complete the current word (which includes the unfinished prefix)
                        completed_word = self._create_complete_word(current)
                        if completed_word:
                            # The text already includes the unfinished word prefix
                            if completed_word.text not in completed_words_texts:
                                heapq.heappush(completed_words, completed_word)
                                completed_words_texts.append(completed_word.text)
                                print(
                                    f"    ✓ '{self.tokenizer.id_to_piece(token_id)}' → COMPLETE WORD: '{completed_word.text}' "
                                    f"(prob: {completed_word.probability:.6f})")
                        # Don't start building a new word - we're only completing the unfinished one
                    else:
                        # No unfinished word - we can start building new words
                        # If we have a partial word to complete, complete it first
                        if current.text.strip():  # Only complete if we have a non-empty prefix
                            completed_word = self._create_complete_word(current)
                            if completed_word:
                                if completed_word.text not in completed_words_texts:
                                    heapq.heappush(completed_words, completed_word)
                                    completed_words_texts.append(completed_word.text)
                                    print(
                                        f"    ✓ '{self.tokenizer.id_to_piece(token_id)}' → COMPLETE WORD: '{completed_word.text}' "
                                        f"(prob: {completed_word.probability:.6f})")
                        
                        # Now start building the new word with this token
                        # Decode the token - SentencePiece will handle the ▁ marker appropriately
                        token_text = self.tokenizer.decode([token_id])
                        # Remove leading whitespace that might come from the ▁ marker
                        token_text = token_text.lstrip()
                        
                        # Create new beam item starting fresh for the new word
                        new_tokens = [token_id]
                        new_log_prob = -math.log(token_prob)
                        new_log_prob_normalised = new_log_prob * (self.penalty_value + len(
                            new_tokens) ** self.alpha / (self.penalty_value + 1) ** self.alpha)
                        
                        new_item = BeamItem(
                            neg_log_prob_normalised=new_log_prob_normalised,
                            neg_log_prob=new_log_prob,
                            tokens=new_tokens,
                            text=token_text
                        )
                        
                        # Check if this prefix is already in beam or already explored
                        new_cache_key = tuple(context_tokens + new_tokens)
                        if new_cache_key not in beam_prefixes and new_cache_key not in explored_prefixes:
                            heapq.heappush(beam, new_item)
                            beam_prefixes.add(new_cache_key)
                            print(f"    + '{self.tokenizer.id_to_piece(token_id)}' → Start new word: '{new_item.text}' "
                                  f"(prob: {math.exp(-new_item.neg_log_prob):.6f})")
                        else:
                            print(f"    - '{self.tokenizer.id_to_piece(token_id)}' → Skipped (already in beam or explored)")
                else:
                    # Word continues, add to beam
                    new_item = self._create_new_beam_prefix(current, token_id, token_prob)
                    # Check if this prefix is already in beam or already explored
                    new_cache_key = tuple(context_tokens + new_item.tokens)
                    if new_cache_key not in beam_prefixes and new_cache_key not in explored_prefixes:
                        heapq.heappush(beam, new_item)
                        beam_prefixes.add(new_cache_key)
                        print(f"    + '{self.tokenizer.id_to_piece(token_id)}' → Continue: '{new_item.text}' "
                              f"(prob: {math.exp(-new_item.neg_log_prob):.6f})")
                    else:
                        print(f"    - '{self.tokenizer.id_to_piece(token_id)}' → Skipped (already in beam or explored)")

            # Prune beam to width (keep only top beam_width items)
            beam = heapq.nsmallest(self.beam_width, beam)
            print(f"\n  Beam pruned to {self.beam_width} items")

        print(f"\n{'=' * 50}")
        if iteration >= max_iterations:
            print(f"Search stopped: reached maximum iterations ({max_iterations})")
        else:
            print(f"Search complete!")
        print(f"Total iterations: {iteration}")
        print(f"Total inferences: {self.inference_count}")
        print(f"Completed words found: {len(completed_words)}")

        # Return top k completed words
        top_words = heapq.nsmallest(k, completed_words)

        results = [
            (word.text, word.probability, len(word.tokens))
            for word in top_words
        ]

        return results

    @staticmethod
    def _get_top_tokens(token_probs: List[float], k: int) -> List[
        Tuple[int, float]]:
        """Get top-k tokens by probability."""
        # Create list of (token_id, probability)
        token_prob_pairs = [(i, prob) for i, prob in enumerate(token_probs)]
        # Sort by probability (descending) and take top k
        top_k = sorted(token_prob_pairs, key=lambda x: x[1], reverse=True)[:k]
        return top_k

    @staticmethod
    def _clean_context_text(context_text: str) -> str:
        context_text = context_text.lower()
        context_text = unicodedata.normalize("NFC", context_text)
        context_text = CLEAN_REGEX.sub("", context_text)
        context_text = MULTIPLE_WHITESPACE.sub(" ", context_text)
        return context_text

    @staticmethod
    def _extract_unfinished_word(context_text: str) -> [str, str]:
        # if context text is empty or ends with a space, all words are finished
        if not context_text or context_text[-1] == " ":
            return context_text, ""
        words = context_text.split(" ")
        if len(words) == 1:
            return "", words[0]
        return " ".join(words[:-1]), " " + words[-1]

    @staticmethod
    def _create_complete_word(current_prefix: BeamItem) -> CompletedWord | None:
        word_text = current_prefix.text.strip()
        if word_text:
            word_neg_log_prob = current_prefix.neg_log_prob_normalised
            word_tokens = current_prefix.tokens
            word_probability = math.exp(-current_prefix.neg_log_prob)
            return CompletedWord(neg_log_prob_normalised=word_neg_log_prob,
                                 tokens=word_tokens,
                                 text=word_text,
                                 probability=word_probability)
        return None

    def _create_new_beam_prefix(self, current_prefix: BeamItem, token_id: int,
                                token_prob: float) -> BeamItem | None:
        token_text = self.tokenizer.decode([token_id])
        new_tokens = current_prefix.tokens + [token_id]
        new_text = current_prefix.text + token_text
        new_log_prob = current_prefix.neg_log_prob - math.log(token_prob)
        new_log_prob_normalised = new_log_prob * (self.penalty_value + len(
            new_tokens) ** self.alpha / (self.penalty_value + 1) ** self.alpha)
        return BeamItem(
            neg_log_prob_normalised=new_log_prob_normalised,
            neg_log_prob=new_log_prob,
            tokens=new_tokens,
            text=new_text
        )


# ============================================================================
# REAL MODEL AND TOKENIZER LOADING
# ============================================================================

try:
    from pisak.predictions.model_loader import load_model_and_tokenizer

    _MODEL_LOADER_AVAILABLE = True
except ImportError:
    _MODEL_LOADER_AVAILABLE = False
    print(
        "Warning: model_loader not available. Install torch and sentencepiece to use real model.")


def create_beam_searcher(model_dir: str = None, beam_width: int = 30,
                         max_word_length: int = 5, device: str = None):
    """
    Create a beam searcher with real model and tokenizer.
    
    Args:
        model_dir: Directory containing model.pt and spm_pl.model. If None, uses predictions directory.
        beam_width: Maximum number of partial words to keep in beam
        max_word_length: Maximum number of tokens per word
        device: Device to run model on ('cpu' or 'cuda'). If None, auto-detect.
        
    Returns:
        WordPredictionBeamSearch instance
    """
    if not _MODEL_LOADER_AVAILABLE:
        raise ImportError(
            "model_loader not available. Install torch and sentencepiece.")

    model, tokenizer = load_model_and_tokenizer(model_dir=model_dir,
                                                device=device)

    return WordPredictionBeamSearch(
        model=model,
        tokenizer=tokenizer,
        beam_width=beam_width,
        max_word_length=max_word_length
    )


# ============================================================================
# DEMO: Mock Model and Tokenizer
# ============================================================================

class MockTokenizer:
    """Simple mock tokenizer for demonstration."""

    def __init__(self):
        # Vocabulary: word tokens start with '_'
        self.vocab = {
            0: "_the", 1: "_cat", 2: "_dog", 3: "_sat", 4: "_on",
            5: "_mat", 6: "_run", 7: "_ning", 8: "_quick", 9: "_ly",
            10: "_jump", 11: "_ed", 12: "_walk", 13: "_s", 14: "_beautiful",
            15: "_ly", 16: "ing", 17: "s", 18: "ed"
        }
        self.id_to_token = self.vocab
        self.token_to_id = {v: k for k, v in self.vocab.items()}

    def encode(self, text: str) -> List[int]:
        """Simple encoding (just for demo)."""
        words = text.strip().split()
        return [self.token_to_id.get(f"_{w}", 0) for w in words]

    def decode(self, token_ids: List[int]) -> str:
        """Decode token IDs to text."""
        return ''.join([self.id_to_token.get(tid, '?') for tid in token_ids])


class MockLSTMModel:
    """Mock LSTM model that returns probability distributions."""

    def __init__(self, vocab_size: int = 19):
        self.vocab_size = vocab_size

    def predict(self, context_tokens: List[int]) -> List[float]:
        """Return mock probability distribution over next tokens."""
        import random
        random.seed(sum(context_tokens) + len(context_tokens))

        # Generate mock probabilities
        probs = [random.random() for _ in range(self.vocab_size)]

        # Normalize to sum to 1
        total = sum(probs)
        probs = [p / total for p in probs]

        return probs


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    import sys

    # Try to use real model, fall back to mock if not available
    if _MODEL_LOADER_AVAILABLE:
        try:
            print("Loading real LSTM model and tokenizer...")
            searcher = create_beam_searcher(beam_width=15, max_word_length=4)
            print("Model loaded successfully!\n")
        except Exception as e:
            print(f"Error loading real model: {e}")
            print("Falling back to mock model...\n")
            # Fall back to mock
            tokenizer = MockTokenizer()
            model = MockLSTMModel()
            searcher = WordPredictionBeamSearch(
                model=model,
                tokenizer=tokenizer,
                beam_width=15,
                max_word_length=4
            )
    else:
        print(
            "Using mock model (install torch and sentencepiece for real model)...\n")
        tokenizer = MockTokenizer()
        model = MockLSTMModel()
        searcher = WordPredictionBeamSearch(
            model=model,
            tokenizer=tokenizer,
            beam_width=15,
            max_word_length=4
        )

    # Find top 5 most probable next words
    context = "the cat" if len(sys.argv) < 2 else sys.argv[1]
    top_words = searcher.get_top_k_words(context, k=5)

    print(f"\n{'=' * 50}")
    print(f"TOP 5 PREDICTED NEXT WORDS after '{context}':")
    print(f"{'=' * 50}")
    for i, (word, prob, num_tokens) in enumerate(top_words, 1):
        print(f"{i}. '{word}' - probability: {prob:.6f} ({num_tokens} tokens)")

    print(f"\nTotal model inferences: {searcher.inference_count}")
