import heapq
import math
from typing import Any, List, Optional, Tuple
from dataclasses import dataclass, field
import unicodedata
import re

from app.predictions.trie import PolishWordTrie

CLEAN_REGEX = re.compile(r"[^a-ząćęłńóśźż0-9\s]")
MULTIPLE_WHITESPACE = re.compile(r"[ \t\n]+")


@dataclass(order=True)
class BeamItem:
    neg_log_prob_normalised: float
    neg_log_prob: float = field(compare=False)
    tokens: List[int] = field(compare=False)
    text: str = field(compare=False)


@dataclass(order=True)
class CompletedWord:
    neg_log_prob_normalised: float
    tokens: List[int] = field(compare=False)
    text: str = field(compare=False)
    probability: float = field(compare=False)


class WordPredictionBeamSearch:
    """
    Prefix-guided beam search with three-tier fallback strategy:

      Tier 1 — Normal beam search with dictionary pruning (beam_width)
      Tier 2 — Wider beam search if tier 1 finds fewer than k words
               (beam_width * fallback_multipliers[0], then * [1], ...)
      Tier 3 — Return the k most frequent dictionary words if all beam
               attempts find nothing at all

    Tier 3 is a last resort for unusual contexts where the model's top
    predictions all fail the dictionary filter even with a wide beam.
    The most frequent words are preloaded from the CSV at startup so
    tier 3 adds zero latency.
    """

    def __init__(
        self,
        model,
        tokenizer,
        beam_width: int = 10,
        max_word_length: int = 10,
        alpha: float = 0.2,
        dictionary: Optional[PolishWordTrie] = None,
        fallback_multipliers: List[int] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.beam_width = beam_width
        self.max_word_length = max_word_length
        self.inference_count = 0
        self.start_new_word_char: str = "▁"
        self.alpha = alpha
        self.dictionary = dictionary
        self.fallback_multipliers = fallback_multipliers or [2, 4]

        vocab_size = tokenizer.get_piece_size()
        self._id_to_piece: List[str] = [
            tokenizer.id_to_piece(i) for i in range(vocab_size)
        ]

    def starts_new_word(self, token_id: int) -> bool:
        return self._id_to_piece[token_id].startswith(self.start_new_word_char)

    def contains_letters_only(self, token_id: int) -> bool:
        return self.tokenizer.decode([token_id]).isalpha()

    # ------------------------------------------------------------------
    # Trie helpers
    # ------------------------------------------------------------------

    def _is_valid_prefix(self, partial_text: str) -> bool:
        if self.dictionary is None:
            return True
        clean = partial_text.strip().lower()
        if not clean:
            return True
        return self.dictionary.is_valid_prefix(clean)

    def _is_valid_word(self, word_text: str) -> bool:
        if self.dictionary is None:
            return True
        return self.dictionary.is_word(word_text.strip().lower())

    # ------------------------------------------------------------------
    # Frequency fallback — tier 3
    # ------------------------------------------------------------------

    def _frequency_fallback(self, k: int) -> List[Tuple[str, float, int]]:
        """
        Return the k most frequent dictionary words with probability=0.0
        and num_tokens=0 to signal that these are fallback predictions,
        not beam search results.

        probability=0.0 is intentional — the model assigned no confident
        probability to these words, so reporting a score would be misleading.
        The caller can check probability == 0.0 to detect fallback results.
        """
        if self.dictionary is None or not self.dictionary.top_n_words:
            return []
        fallback = self.dictionary.top_n_words[:k]
        print(f"[fallback-tier3] Returning {len(fallback)} most frequent words.")
        return [(word, 0.0, 0) for word in fallback]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_top_k_words(self, context_text: str, k: int = 5) -> List[
            Tuple[str, float, int]]:
        """
        Find top-K most probable next complete words.

        Returns (word, probability, num_tokens) tuples.
        probability == 0.0 and num_tokens == 0 signals a tier-3 fallback result.
        """
        self.inference_count = 0

        # Pre-process context once — reused across all fallback attempts
        clean_context = self._clean_context_text(context_text)
        clean_context, unfinished_word = self._extract_unfinished_word(clean_context)
        context_tokens = self.tokenizer.encode(clean_context)
        context_probs, context_hidden = self._prime_context(context_tokens)
        self.inference_count += 1

        # Tier 1: normal beam search
        results = self._search(
            context_probs, context_hidden, unfinished_word, k, self.beam_width
        )
        if len(results) >= k:
            return results

        # Tier 2: progressively wider beams
        for multiplier in self.fallback_multipliers:
            wider_beam = self.beam_width * multiplier
            print(f"[fallback-tier2] {len(results)}/{k} words found. "
                  f"Retrying with beam_width={wider_beam}...")
            results = self._search(
                context_probs, context_hidden, unfinished_word, k, wider_beam
            )
            if len(results) >= k:
                return results

        # Tier 3: most frequent words from dictionary
        if not results:
            return self._frequency_fallback(k)

        # Partial results from beam + top-up from frequency list to reach k
        if len(results) < k and self.dictionary and self.dictionary.top_n_words:
            found_words = {w for w, _, _ in results}
            needed = k - len(results)
            topup = [
                (word, 0.0, 0)
                for word in self.dictionary.top_n_words
                if word not in found_words
            ][:needed]
            if topup:
                print(f"[fallback-tier3] Topping up {len(topup)} word(s) "
                      f"from frequency list to reach k={k}.")
            results = results + topup

        return results

    # ------------------------------------------------------------------
    # Core beam search
    # ------------------------------------------------------------------

    def _search(
        self,
        context_probs: List[float],
        context_hidden: Any,
        unfinished_word: str,
        k: int,
        beam_width: int,
    ) -> List[Tuple[str, float, int]]:
        """Single beam search pass. Context is never reprocessed here."""
        beam: List[BeamItem] = [
            BeamItem(neg_log_prob_normalised=0.0, neg_log_prob=0.0,
                     tokens=[], text="")
        ]
        completed_words: List[CompletedWord] = []
        completed_words_texts: List[str] = []
        explored_prefixes: set = set()

        max_iterations = k * beam_width * 10
        iteration = 0

        if unfinished_word:
            current = heapq.heappop(beam)
            explored_prefixes.add(tuple(current.tokens))

            top_tokens = self._get_top_matching_tokens(
                context_probs, beam_width, current.text,
                unfinished_word, beam_init=True
            )
            for token_id, token_prob in top_tokens:
                new_item = self._create_new_beam_prefix(current, token_id, token_prob)
                if tuple(new_item.tokens) not in explored_prefixes \
                        and self._is_valid_prefix(new_item.text):
                    heapq.heappush(beam, new_item)

            beam = heapq.nsmallest(beam_width, beam)

        while beam and len(completed_words) < (k * 2) and iteration < max_iterations:
            iteration += 1

            current = heapq.heappop(beam)

            if len(current.tokens) > self.max_word_length:
                continue
            if tuple(current.tokens) in explored_prefixes:
                continue

            explored_prefixes.add(tuple(current.tokens))

            if current.tokens:
                token_probs, _ = self.model.predict_with_state(
                    current.tokens, context_hidden
                )
            else:
                token_probs = context_probs

            self.inference_count += 1

            if unfinished_word:
                top_tokens = self._get_top_matching_tokens(
                    token_probs, beam_width, current.text,
                    unfinished_word, beam_init=False
                )
            else:
                top_tokens = self._get_top_tokens(token_probs, beam_width)

            for token_id, token_prob in top_tokens:
                if not self.contains_letters_only(token_id):
                    continue

                if self.starts_new_word(token_id):
                    if current.text.strip():
                        if self._is_valid_word(current.text):
                            completed = self._create_complete_word(current)
                            if completed and completed.text not in completed_words_texts:
                                heapq.heappush(completed_words, completed)
                                completed_words_texts.append(completed.text)
                    else:
                        new_item = self._create_new_beam_prefix(
                            current, token_id, token_prob
                        )
                        if tuple(new_item.tokens) not in explored_prefixes \
                                and self._is_valid_prefix(new_item.text):
                            heapq.heappush(beam, new_item)
                else:
                    new_item = self._create_new_beam_prefix(
                        current, token_id, token_prob
                    )
                    if tuple(new_item.tokens) not in explored_prefixes \
                            and self._is_valid_prefix(new_item.text):
                        heapq.heappush(beam, new_item)

            beam = heapq.nsmallest(beam_width, beam)

        # print(f"Search done: {iteration} iterations, "
        #       f"{self.inference_count} inferences, "
        #       f"{len(completed_words)} valid words (beam_width={beam_width})")

        top_words = heapq.nsmallest(k, completed_words)
        return [(w.text, w.probability, len(w.tokens)) for w in top_words]

    # ------------------------------------------------------------------
    # Context caching
    # ------------------------------------------------------------------

    def _prime_context(
            self, context_tokens: List[int]
    ) -> Tuple[List[float], Any]:
        if not context_tokens:
            probs = [1.0 / self.model.vocab_size] * self.model.vocab_size
            return probs, None
        probs, hidden = self.model.predict_with_state(context_tokens, None)
        return probs, hidden

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def _get_top_matching_tokens(
            self, token_probs, k, current_prefix, unfinished_word,
            beam_init=False
    ) -> List[Tuple[int, float]]:
        unfinished_word = unfinished_word.strip()
        if beam_init and not unfinished_word.startswith(self.start_new_word_char):
            unfinished_word = self.start_new_word_char + unfinished_word

        candidates = []
        for token_id, prob in enumerate(token_probs):
            piece = self._id_to_piece[token_id]
            new_prefix = current_prefix + piece
            if (
                new_prefix.startswith(unfinished_word)
                or unfinished_word.startswith(new_prefix)
            ):
                candidates.append((token_id, prob))

        return heapq.nlargest(k, candidates, key=lambda x: x[1])

    @staticmethod
    def _get_top_tokens(token_probs, k) -> List[Tuple[int, float]]:
        return heapq.nlargest(k, enumerate(token_probs), key=lambda x: x[1])

    # ------------------------------------------------------------------
    # Beam item construction  (unchanged)
    # ------------------------------------------------------------------

    def _create_new_beam_prefix(
            self, current: BeamItem, token_id: int, token_prob: float
    ) -> BeamItem:
        new_tokens = current.tokens + [token_id]
        new_text = current.text + self.tokenizer.decode([token_id])
        new_log_prob = current.neg_log_prob - math.log(max(token_prob, 1e-12))
        new_log_prob_norm = new_log_prob / (len(new_tokens) ** self.alpha)
        return BeamItem(
            neg_log_prob_normalised=new_log_prob_norm,
            neg_log_prob=new_log_prob,
            tokens=new_tokens,
            text=new_text,
        )

    @staticmethod
    def _create_complete_word(current: BeamItem) -> Optional[CompletedWord]:
        word_text = current.text.strip()
        if not word_text:
            return None
        return CompletedWord(
            neg_log_prob_normalised=current.neg_log_prob_normalised,
            tokens=current.tokens,
            text=word_text,
            probability=math.exp(-current.neg_log_prob_normalised),
        )

    # ------------------------------------------------------------------
    # Word probability scorer
    # ------------------------------------------------------------------

    def get_word_probability(self, context_text: str, next_word: str) -> float:
        context_text = context_text.strip()
        next_word = " " + next_word.strip()
        context_tokens = self.tokenizer.encode(context_text)
        word_tokens = self.tokenizer.encode(next_word)

        _, context_hidden = self._prime_context(context_tokens)

        log_prob = 0.0
        for i, target_id in enumerate(word_tokens):
            probs, _ = self.model.predict_with_state(
                word_tokens[:i], context_hidden
            )
            log_prob += math.log(max(probs[target_id], 1e-12))

        return math.exp(log_prob / (len(word_tokens) ** self.alpha))

    # ------------------------------------------------------------------
    # Text utilities  (unchanged)
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_context_text(context_text: str) -> str:
        context_text = context_text.lower()
        context_text = unicodedata.normalize("NFC", context_text)
        context_text = CLEAN_REGEX.sub("", context_text)
        context_text = MULTIPLE_WHITESPACE.sub(" ", context_text)
        return context_text

    @staticmethod
    def _extract_unfinished_word(context_text: str) -> [str, str]:
        if not context_text or context_text[-1] == " ":
            return context_text, ""
        words = context_text.split()
        return " ".join(words[:-1]), words[-1]


def create_beam_searcher(
    model_dir: str = None,
    beam_width: int = 25,
    max_word_length: int = 5,
    device: str = None,
    alpha: float = 0.0,
    seq_len: int = 64,
    model_name: str = "model.pt",
    dictionary_csv: str = None,
    fallback_multipliers: List[int] = None,
    top_n_fallback: int = 100,
):
    from app.predictions.model_loader import load_model_and_tokenizer

    model, tokenizer = load_model_and_tokenizer(
        model_dir=model_dir, device=device,
        seq_len=seq_len, model_name=model_name,
    )

    dictionary = None
    if dictionary_csv:
        dictionary = PolishWordTrie.from_csv(
            dictionary_csv,
            top_n_fallback=top_n_fallback,
        )

    return WordPredictionBeamSearch(
        model=model,
        tokenizer=tokenizer,
        beam_width=beam_width,
        max_word_length=max_word_length,
        alpha=alpha,
        dictionary=dictionary,
        fallback_multipliers=fallback_multipliers or [2, 4],
    )


if __name__ == "__main__":
    import time

    print("Loading model and tokenizer...")
    searcher = create_beam_searcher(
        model_dir="../",
        beam_width=10,
        max_word_length=10,
        dictionary_csv="unigrams200k.csv",
        top_n_fallback=100,
    )
    print("Ready.\n")

    context = "chociaż mam prawie trzydzieści lat cały czas czuję się "

    t0 = time.perf_counter()
    for _ in range(20):
        searcher.get_top_k_words(context, k=5)
    print(f"avg: {(time.perf_counter() - t0) / 20 * 1000:.1f} ms per call")

    top_words = searcher.get_top_k_words(context, k=5)

    print(f"\n{'=' * 50}")
    print(f"TOP 5 PREDICTED NEXT WORDS after '{context}':")
    print(f"{'=' * 50}")
    for i, (word, prob, num_tokens) in enumerate(top_words, 1):
        fallback_marker = " [frequency fallback]" if prob == 0.0 else ""
        print(f"{i}. '{word}' - probability: {prob:.6f} "
              f"({num_tokens} tokens){fallback_marker}")

    print(f"\nTotal model inferences: {searcher.inference_count}")