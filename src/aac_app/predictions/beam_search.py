import heapq
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Tuple

from aac_app.logging_config import get_module_logger

CLEAN_REGEX = re.compile(r"[^a-ząćęłńóśźż0-9\s]")
MULTIPLE_WHITESPACE = re.compile(r"[ \t\n]+")

logger = get_module_logger(file_name="predictions", logger_name=__name__)


@dataclass(
    order=True
)  # order=True automatically creates dunder methods allowing two BeamItem objects to be compared
class BeamItem:
    """Represents a partial word being explored in the beam.

    Attributes:
        neg_log_prob: Negative log probability (for max-heap using min-heap)
        tokens: List of token IDs forming this partial word
        text: Human-readable text of the partial word
    """

    # probability: [0, 1] -> its logarithm: [-inf (token with prob. 0), 0 (token with prob. 1)]
    # if we now turn it into a negative number, tokens with the lowest probability of appearing
    # will have the highest value - which is ideal when using a min-heap (the default heapq implementation)
    # because the smallest elements are at the beginning and the largest at the end
    neg_log_prob_normalised: float
    neg_log_prob: float = field(compare=False)
    tokens: List[int] = field(compare=False)  # we do not want to compare this
    text: str = field(compare=False)  # we do not want to compare this either


@dataclass(order=True)
class CompletedWord:
    """Represents a completed word with its probability.

    Attributes:
        neg_log_prob: Negative log probability
        tokens: List of token IDs forming the complete word
        text: Human-readable text of the word
        probability: Actual probability (exp of negative neg_log_prob)
    """

    # probability: [0, 1] -> its logarithm: [-inf (token with prob. 0), 0 (token with prob. 1)]
    # if we now turn it into a negative number, tokens with the lowest probability of appearing
    # will have the highest value - which is ideal when using a min-heap (the default heapq implementation)
    # because the smallest elements are at the beginning and the largest at the end
    neg_log_prob_normalised: float
    tokens: List[int] = field(compare=False)
    text: str = field(compare=False)
    probability: float = field(compare=False)


class WordPredictionBeamSearch:
    """Efficient beam search for finding top-K most probable next words."""

    def __init__(
        self,
        model,
        tokenizer,
        beam_width: int = 50,
        max_word_length: int = 15,
        alpha: float = 0.2,
    ):
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
        self.alpha = alpha

    def starts_new_word(self, token_id: int) -> bool:
        """Check if a token starts a new word (piece starts with '▁' marker)."""
        token_piece = self.tokenizer.id_to_piece(token_id)
        return token_piece.startswith(self.start_new_word_char)

    def contains_letters_only(self, token_id: int) -> bool:
        token_text = self.tokenizer.decode([token_id])
        return token_text.isalpha()

    def get_top_k_words(
        self, context_text: str, k: int = 5
    ) -> List[Tuple[str, float, int]]:
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
        context_text, unfinished_word = self._extract_unfinished_word(context_text)
        context_tokens = self.tokenizer.encode(context_text)

        beam = [
            BeamItem(neg_log_prob_normalised=0.0, neg_log_prob=0.0, tokens=[], text="")
        ]
        completed_words = []
        completed_words_texts = []

        # Track explored prefixes to avoid cycles (only mark as explored after processing)
        explored_prefixes: set[Tuple[int, ...]] = set()

        logger.debug("Starting beam search for: '%s'", context_text)
        logger.debug(
            "Beam width: %s, Max word length: %s", self.beam_width, self.max_word_length
        )

        iteration = 0
        max_iterations = (
            k * self.beam_width * 10
        )  # Safety limit to prevent infinite loops

        # if unfinished word, get only matching tokens, that starts new word
        if unfinished_word:
            # Pop the most promising partial word (lowest neg_log_prob = highest prob)
            current = heapq.heappop(beam)
            current_log_prob_normalised = -current.neg_log_prob_normalised

            logger.debug(
                "Exploring prefix: '%s' (tokens: %s)", current.text, current.tokens
            )
            logger.debug(
                "  Cumulative log prob: %.4f (prob: %.6f)",
                current_log_prob_normalised,
                math.exp(current_log_prob_normalised),
            )

            # Mark this prefix as explored (we're about to process it)
            explored_prefixes.add(tuple(current.tokens))

            # Run model inference
            token_probs = self.model.predict(context_tokens + current.tokens)
            self.inference_count += 1

            top_next_tokens = self._get_top_matching_tokens(
                token_probs,
                self.beam_width,
                current.text,
                unfinished_word,
                beam_init=True,
            )

            # Expand beam with each possible next token
            for token_id, token_prob in top_next_tokens:
                new_item = self._create_new_beam_prefix(current, token_id, token_prob)
                if tuple(new_item.tokens) not in explored_prefixes:
                    heapq.heappush(beam, new_item)
                    logger.debug(
                        "    + '%s' → Continue: '%s' (prob: %.6f)",
                        self.tokenizer.id_to_piece(token_id),
                        new_item.text,
                        math.exp(-new_item.neg_log_prob_normalised),
                    )

            # Prune beam to width (keep only top beam_width items)
            beam = heapq.nsmallest(self.beam_width, beam)
            logger.debug("  Beam pruned to %s items", self.beam_width)

        # Continue until we have k completed words or beam is exhausted
        while beam and len(completed_words) < (k * 2) and iteration < max_iterations:
            iteration += 1
            logger.debug("=== Iteration %s ===", iteration)
            logger.debug(
                "Beam size: %s, Completed words: %s", len(beam), len(completed_words)
            )

            # Pop the most promising partial word (lowest neg_log_prob = highest prob)
            current = heapq.heappop(beam)
            current_log_prob_normalised = -current.neg_log_prob_normalised

            logger.debug(
                "Exploring prefix: '%s' (tokens: %s)", current.text, current.tokens
            )
            logger.debug(
                "  Cumulative log prob: %.4f (prob: %.6f)",
                current_log_prob_normalised,
                math.exp(current_log_prob_normalised),
            )

            # Prune: Skip if prefix is too long (unlikely to be a real word)
            if len(current.tokens) > self.max_word_length:
                logger.debug("  → Pruned (exceeds max length %s)", self.max_word_length)
                continue

            if tuple(current.tokens) in explored_prefixes:
                logger.debug("  → Skipping (already explored)")
                continue

            # Mark this prefix as explored (we're about to process it)
            explored_prefixes.add(tuple(current.tokens))

            # Run model inference
            token_probs = self.model.predict(context_tokens + current.tokens)
            self.inference_count += 1

            # Get top beam_width tokens
            if unfinished_word:
                top_next_tokens = self._get_top_matching_tokens(
                    token_probs,
                    self.beam_width,
                    current.text,
                    unfinished_word,
                    beam_init=False,
                )
            else:
                top_next_tokens = self._get_top_tokens(token_probs, self.beam_width)

            logger.debug("  → Inference #%s", self.inference_count)

            logger.debug("  Exploring %s next tokens:", len(top_next_tokens))

            # Expand beam with each possible next token
            for token_id, token_prob in top_next_tokens:
                if not self.contains_letters_only(token_id):
                    continue

                if self.starts_new_word(token_id):
                    # If we have a partial word to complete, complete it first
                    if (
                        current.text.strip()
                    ):  # Only complete if we have a non-empty prefix
                        completed_word = self._create_complete_word(current)
                        if completed_word:
                            if completed_word.text not in completed_words_texts:
                                heapq.heappush(completed_words, completed_word)
                                completed_words_texts.append(completed_word.text)
                                logger.debug(
                                    "    ✓ '%s' → COMPLETE WORD: '%s' (prob: %.6f)",
                                    self.tokenizer.id_to_piece(token_id),
                                    completed_word.text,
                                    completed_word.probability,
                                )

                    # no prefixes were made yet; we have to create first prefixes
                    else:
                        new_item = self._create_new_beam_prefix(
                            current, token_id, token_prob
                        )
                        if tuple(new_item.tokens) not in explored_prefixes:
                            heapq.heappush(beam, new_item)
                            logger.debug(
                                "    + '%s' → Continue: '%s' (prob: %.6f)",
                                self.tokenizer.id_to_piece(token_id),
                                new_item.text,
                                math.exp(-new_item.neg_log_prob_normalised),
                            )

                else:
                    # Word continues, add to beam
                    new_item = self._create_new_beam_prefix(
                        current, token_id, token_prob
                    )
                    if tuple(new_item.tokens) not in explored_prefixes:
                        heapq.heappush(beam, new_item)
                        logger.debug(
                            "    + '%s' → Continue: '%s' (prob: %.6f)",
                            self.tokenizer.id_to_piece(token_id),
                            new_item.text,
                            math.exp(-new_item.neg_log_prob_normalised),
                        )
                    else:
                        logger.debug(
                            "    - '%s' → Skipped (already in beam or explored)",
                            self.tokenizer.id_to_piece(token_id),
                        )

            # Prune beam to width (keep only top beam_width items)
            beam = heapq.nsmallest(self.beam_width, beam)
            logger.debug("  Beam pruned to %s items", self.beam_width)

        if iteration >= max_iterations:
            logger.debug(
                "Search stopped: reached maximum iterations (%s)", max_iterations
            )
        else:
            logger.debug("Search complete!")
        logger.debug("Total iterations: %s", iteration)
        logger.debug("Total inferences: %s", self.inference_count)
        logger.debug("Completed words found: %s", len(completed_words))

        # Return top k completed words
        top_words = heapq.nsmallest(k, completed_words)

        results = [
            (word.text, word.probability, len(word.tokens)) for word in top_words
        ]

        return results

    def _get_top_matching_tokens(
        self,
        token_probs: List[float],
        k: int,
        current_prefix: str,
        unfinished_word: str,
        beam_init: bool = False,
    ) -> List[Tuple[int, float]]:
        unfinished_word = unfinished_word.strip()
        if beam_init and not unfinished_word.startswith(self.start_new_word_char):
            unfinished_word = self.start_new_word_char + unfinished_word

        # Walk ids and pieces together: building a {piece: prob} dict for the whole
        # vocabulary on every call allocated a dict per beam step and forced a
        # reverse piece->id lookup, even though the id is right here.
        candidates = (
            (token_id, prob)
            for (token_id, piece), prob in zip(
                self.tokenizer.id2piece.items(), token_probs
            )
            if (current_prefix + piece).startswith(unfinished_word)
            or unfinished_word.startswith(current_prefix + piece)
        )

        # nlargest keeps only k items instead of sorting the whole vocabulary.
        return heapq.nlargest(k, candidates, key=lambda pair: pair[1])

    @staticmethod
    def _get_top_tokens(token_probs: List[float], k: int) -> List[Tuple[int, float]]:
        """Get top-k tokens by probability."""
        # nlargest is O(n log k); sorting the full vocabulary to then discard all
        # but k entries was the most expensive step of each beam iteration.
        return heapq.nlargest(k, enumerate(token_probs), key=lambda pair: pair[1])

    def get_word_probability(self, context_text: str, next_word: str):
        context_text = context_text.strip()
        next_word = " " + next_word.strip()
        context_tokens = self.tokenizer.encode(context_text)
        word_tokens = self.tokenizer.encode(next_word)
        log_prob = 0
        for i in range(len(word_tokens)):
            tokens_probs = self.model.predict(context_tokens + word_tokens[:i])
            prob = tokens_probs[word_tokens[i]]
            log_prob += math.log(prob)
        return math.exp(log_prob / (len(word_tokens) ** self.alpha))

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
        words = context_text.split()
        return " ".join(words[:-1]), words[-1]

    @staticmethod
    def _create_complete_word(current_prefix: BeamItem) -> CompletedWord | None:
        word_text = current_prefix.text.strip()
        if word_text:
            word_neg_log_prob_normalised = current_prefix.neg_log_prob_normalised
            word_tokens = current_prefix.tokens
            word_probability = math.exp(-current_prefix.neg_log_prob_normalised)
            return CompletedWord(
                neg_log_prob_normalised=word_neg_log_prob_normalised,
                tokens=word_tokens,
                text=word_text,
                probability=word_probability,
            )
        return None

    def _create_new_beam_prefix(
        self, current_prefix: BeamItem, token_id: int, token_prob: float
    ) -> BeamItem | None:
        new_tokens = current_prefix.tokens + [token_id]
        new_text = current_prefix.text + self.tokenizer.decode([token_id])
        new_log_prob = current_prefix.neg_log_prob - math.log(token_prob)
        new_log_prob_normalised = new_log_prob / (len(new_tokens) ** self.alpha)
        return BeamItem(
            neg_log_prob_normalised=new_log_prob_normalised,
            neg_log_prob=new_log_prob,
            tokens=new_tokens,
            text=new_text,
        )


def create_beam_searcher(
    model_dir: str = None,
    beam_width: int = 30,
    max_word_length: int = 5,
    device: str = None,
    alpha: float = 0.2,
    seq_len: int = 256,
):
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
    from aac_app.predictions.model_loader import load_model_and_tokenizer

    model, tokenizer = load_model_and_tokenizer(
        model_dir=model_dir, device=device, seq_len=seq_len
    )

    return WordPredictionBeamSearch(
        model=model,
        tokenizer=tokenizer,
        beam_width=beam_width,
        max_word_length=max_word_length,
        alpha=alpha,
    )


if __name__ == "__main__":

    logger.debug("Loading real LSTM model and tokenizer...")
    searcher = create_beam_searcher(model_dir="../", beam_width=50, max_word_length=10)
    logger.debug("Model loaded successfully!")

    # Find top 5 most probable next words
    context = "chciałabym powiedzieć, że choć przedstawienie było wielce interesujące, to nie było na "
    top_words = searcher.get_top_k_words(context, k=5)

    logger.debug("%s", "=" * 50)
    logger.debug("TOP 5 PREDICTED NEXT WORDS after '%s':", context)
    logger.debug("%s", "=" * 50)
    for i, (word, prob, num_tokens) in enumerate(top_words, 1):
        logger.debug(
            "%s. '%s' - probability: %.6f (%s tokens)", i, word, prob, num_tokens
        )

    logger.debug("Total model inferences: %s", searcher.inference_count)
