import heapq
import math
from typing import List, Tuple, Dict
from dataclasses import dataclass, field


@dataclass(order=True)  # order=True automatycznie tworzy dunder methods pozwalajace porownywac dwa obiekty typu BeamItem
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
    neg_log_prob: float
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
    neg_log_prob: float
    tokens: List[int] = field(compare=False)
    text: str = field(compare=False)
    probability: float = field(compare=False)


class WordPredictionBeamSearch:
    """Efficient beam search for finding top-K most probable next words."""

    def __init__(self, model, tokenizer, beam_width: int = 30, max_word_length: int = 5):
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
        self._start_new_word_char: str = "▁"

    def starts_new_word(self, token_id: int) -> bool:
        """Check if a token starts a new word (has '_' marker)."""
        token_text = self.tokenizer.decode([token_id])
        return token_text.startswith(self._start_new_word_char) or token_text.startswith(" ")

    def get_top_k_words(self, context_text: str, k: int = 10) -> List[Tuple[str, float, int]]:
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
        context_tokens = self.tokenizer.encode(context_text)

        # Initialize beam with empty prefix (log_prob = 0)
        beam = [BeamItem(neg_log_prob=0.0, tokens=[], text="")]
        completed_words = []

        # Cache for token probabilities: (context + prefix) -> token_probs
        prob_cache: Dict[Tuple[int, ...], List[Tuple[int, float]]] = {}

        print(f"Starting beam search for: '{context_text}'")
        print(f"Beam width: {self.beam_width}, Max word length: {self.max_word_length}\n")

        iteration = 0

        # Continue until we have k completed words or beam is exhausted
        while beam and len(completed_words) < k:
            iteration += 1
            print(f"=== Iteration {iteration} ===")
            print(f"Beam size: {len(beam)}, Completed words: {len(completed_words)}")

            # Pop the most promising partial word (lowest neg_log_prob = highest prob)
            current = heapq.heappop(beam)
            current_log_prob = -current.neg_log_prob

            print(f"\nExploring prefix: '{current.text}' (tokens: {current.tokens})")
            print(f"  Cumulative log prob: {current_log_prob:.4f} (prob: {math.exp(current_log_prob):.6f})")

            # Prune: Skip if prefix is too long (unlikely to be a real word)
            if len(current.tokens) >= self.max_word_length:
                print(f"  → Pruned (exceeds max length {self.max_word_length})")
                continue

            # Create cache key for this context + prefix
            cache_key = tuple(context_tokens + current.tokens)

            # Get next token probabilities (use cache if available)
            if cache_key in prob_cache:
                top_next_tokens = prob_cache[cache_key]
                print(f"  → Using cached probabilities")
            else:
                # Run model inference
                token_probs = self.model.predict(context_tokens + current.tokens)
                self.inference_count += 1

                # Get top beam_width tokens
                top_next_tokens = self._get_top_tokens(token_probs, self.beam_width)
                prob_cache[cache_key] = top_next_tokens

                print(f"  → Inference #{self.inference_count}")

            print(f"  Exploring {len(top_next_tokens)} next tokens:")

            # Expand beam with each possible next token
            for token_id, token_prob in top_next_tokens:
                token_text = self.tokenizer.decode([token_id])
                new_tokens = current.tokens + [token_id]
                new_text = current.text + token_text.replace('_', ' ').strip()
                new_log_prob = current_log_prob + math.log(token_prob)

                # Check if this token completes a word
                if self.starts_new_word(token_id):
                    # Word is complete!
                    completed_word = CompletedWord(
                        neg_log_prob=-new_log_prob,
                        tokens=current.tokens,  # Don't include the new-word-starting token
                        text=current.text.strip(),
                        probability=math.exp(current_log_prob)  # Prob before the new word token
                    )

                    if completed_word.text:  # Ensure non-empty word
                        heapq.heappush(completed_words, completed_word)
                        print(f"    ✓ '{token_text}' → COMPLETE WORD: '{completed_word.text}' "
                              f"(prob: {completed_word.probability:.6f})")
                else:
                    # Word continues, add to beam
                    new_item = BeamItem(
                        neg_log_prob=-new_log_prob,
                        tokens=new_tokens,
                        text=new_text
                    )
                    heapq.heappush(beam, new_item)
                    print(f"    + '{token_text}' → Continue: '{new_text}' "
                          f"(prob: {math.exp(new_log_prob):.6f})")

            # Prune beam to width (keep only top beam_width items)
            if len(beam) > self.beam_width:
                beam = heapq.nsmallest(self.beam_width, beam)
                print(f"\n  Beam pruned to {self.beam_width} items")

        print(f"\n{'=' * 50}")
        print(f"Search complete!")
        print(f"Total inferences: {self.inference_count}")
        print(f"Completed words found: {len(completed_words)}")

        # Return top k completed words
        top_words = heapq.nsmallest(k, completed_words)

        results = [
            (word.text, word.probability, len(word.tokens))
            for word in top_words
        ]

        return results

    def _get_top_tokens(self, token_probs: List[float], k: int) -> List[Tuple[int, float]]:
        """Get top-k tokens by probability."""
        # Create list of (token_id, probability)
        token_prob_pairs = [(i, prob) for i, prob in enumerate(token_probs)]
        # Sort by probability (descending) and take top k
        top_k = sorted(token_prob_pairs, key=lambda x: x[1], reverse=True)[:k]
        return top_k

# ============================================================================
# PREDICTION
# ============================================================================

def predict(text):
    pass

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
    # Initialize mock model and tokenizer
    tokenizer = MockTokenizer()
    model = MockLSTMModel()

    # Create beam search
    searcher = WordPredictionBeamSearch(
        model=model,
        tokenizer=tokenizer,
        beam_width=15,
        max_word_length=4
    )

    # Find top 5 most probable next words
    context = "the cat"
    top_words = searcher.get_top_k_words(context, k=5)

    print(f"\n{'=' * 50}")
    print(f"TOP 5 PREDICTED NEXT WORDS after '{context}':")
    print(f"{'=' * 50}")
    for i, (word, prob, num_tokens) in enumerate(top_words, 1):
        print(f"{i}. '{word}' - probability: {prob:.6f} ({num_tokens} tokens)")

    print(f"\nTotal model inferences: {searcher.inference_count}")