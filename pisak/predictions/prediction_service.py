"""
Threaded prediction service that generates word predictions without blocking the main UI thread.
"""
import random
import threading
import time
from typing import Callable, Optional
from queue import Queue

from pisak.predictions.dummy_predictions import available_words, N_WORDS


class PredictionService:
    """
    Service that generates word predictions in a separate thread.
    This ensures that prediction generation doesn't block UI operations like scanning.
    """
    
    def __init__(self, n_words: int = N_WORDS):
        """
        Initialize the prediction service.
        
        :param n_words: Number of words to predict
        """
        self._n_words = n_words
        self._request_queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._callback: Optional[Callable[[list[str]], None]] = None
        
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
        Currently returns random words, but can be extended for more sophisticated predictions.
        
        :param text: Current text content
        :param cursor_position: Current cursor position
        :return: List of predicted words
        """
        # Simulate processing delay (300ms) to test non-blocking behavior
        time.sleep(0.3)
        
        # For now, just return random words from available_words
        # In the future, this could analyze the text and provide context-aware predictions
        
        if not available_words:
            return [f"WORD{i+1}" for i in range(self._n_words)]
        
        # Sample random words
        sample_size = min(self._n_words, len(available_words))
        predictions = random.sample(list(available_words), sample_size)
        
        return predictions

