"""
Threaded prediction service that generates word predictions without blocking the main UI thread.
"""
import random
import threading
from typing import Callable, Optional
from queue import Queue

from pisak.predictions.dummy_predictions import available_words, N_WORDS
from pisak.predictions.beam_search import create_beam_searcher, WordPredictionBeamSearch


class PredictionService:
    """
    Service that generates word predictions in a separate thread.
    This ensures that prediction generation doesn't block UI operations like scanning.
    """
    
    def __init__(self, n_words: int = N_WORDS, use_real_model: bool = True, 
                 model_dir: str = None, beam_width: int = 25, max_word_length: int = 10):
        """
        Initialize the prediction service.
        
        :param n_words: Number of words to predict
        :param use_real_model: If True, use LSTM model. If False, use dummy predictions.
        :param model_dir: Directory containing model.pt and spm_pl.model. If None, uses predictions directory.
        :param beam_width: Maximum number of partial words to keep in beam (only used with real model)
        :param max_word_length: Maximum number of tokens per word (only used with real model)
        """
        self._n_words = n_words
        self._use_real_model = use_real_model
        self._request_queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._callback: Optional[Callable[[list[str]], None]] = None
        self._beam_searcher: Optional[WordPredictionBeamSearch] = None
        
        # Initialize beam searcher if using real model
        if self._use_real_model:
            try:
                self._beam_searcher = create_beam_searcher(
                    model_dir=model_dir,
                    beam_width=beam_width,
                    max_word_length=max_word_length
                )
            except Exception as e:
                print(f"Warning: Could not load real model: {e}")
                print("Falling back to dummy predictions.")
                self._use_real_model = False
        
    def start(self):
        """Start the worker thread"""
        if self._running:
            return
            
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
    
    def stop(self):
        """Stop the worker thread"""
        self._running = False
        if self._worker_thread:
            self._request_queue.put(None)  # Signal to stop
            self._worker_thread.join(timeout=1.0)
    
    def set_callback(self, callback: Callable[[list[str]], None]):
        """
        Set the callback function that will be called with predictions.
        
        :param callback: Function that takes a list of predicted words
        """
        self._callback = callback
    
    def request_predictions(self, text: str, cursor_position: int):
        """
        Request new predictions based on current text and cursor position.
        This is non-blocking - predictions will be delivered via callback.
        Multiple rapid requests will be deduplicated - only the latest will be processed.
        
        :param text: Current text content
        :param cursor_position: Current cursor position
        """
        # Clear any pending requests and add only the latest one
        # This prevents duplicate predictions when multiple text changes happen rapidly
        while not self._request_queue.empty():
            try:
                self._request_queue.get_nowait()
            except:
                break
        
        # Put the latest request in queue (non-blocking)
        self._request_queue.put({
            'text': text,
            'cursor_position': cursor_position
        })
    
    def _worker(self):
        """Worker thread that processes prediction requests"""
        while self._running:
            try:
                # Wait for request (blocking)
                request = self._request_queue.get(timeout=0.1)
                
                if request is None:  # Stop signal
                    break
                
                # Generate predictions (this could be a complex operation in the future)
                predictions = self._generate_predictions(
                    request['text'], 
                    request['cursor_position']
                )
                
                # Deliver results via callback (in worker thread)
                if self._callback:
                    self._callback(predictions)
                    
            except Exception as e:
                # Queue.get timeout or other errors - just continue
                continue
    
    def _generate_predictions(self, text: str, cursor_position: int) -> list[str]:
        """
        Generate word predictions based on current text and cursor position.
        Uses beam search with LSTM model if available, otherwise falls back to dummy predictions.
        
        :param text: Current text content
        :param cursor_position: Current cursor position
        :return: List of predicted words
        """
        if self._use_real_model and self._beam_searcher is not None:
            # Use real model with beam search
            try:
                # Get context up to cursor position
                context = text[:cursor_position] if cursor_position > 0 else text
                
                # Get top k words using beam search
                top_words = self._beam_searcher.get_top_k_words(context, k=self._n_words)
                
                # Extract just the word texts
                predictions = [word.upper() for word, prob, num_tokens in top_words]
                
                # Pad with dummy words if we got fewer than requested
                if len(predictions) < self._n_words and available_words:
                    remaining = self._n_words - len(predictions)
                    dummy_words = random.sample(list(available_words), 
                                              min(remaining, len(available_words)))
                    predictions.extend(dummy_words)
                
                return predictions[:self._n_words]
            except Exception as e:
                print(f"Error generating predictions with real model: {e}")
                # Fall through to dummy predictions
                pass
        
        # Fall back to dummy predictions
        # Simulate processing delay (300ms) to test non-blocking behavior
        # time.sleep(0.3)
        
        if not available_words:
            return [f"WORD{i+1}" for i in range(self._n_words)]
        
        # Sample random words
        sample_size = min(self._n_words, len(available_words))
        predictions = random.sample(list(available_words), sample_size)
        
        return predictions

