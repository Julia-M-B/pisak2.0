"""
Handler that connects text display changes to word prediction updates.
Uses Qt signals to safely update UI from worker thread.
"""
from PySide6.QtCore import QObject, Signal, Slot

from pisak.events import AppEvent, AppEventType
from pisak.predictions.prediction_service import PredictionService
from pisak.components.word_column_component import WordColumnComponent


class PredictionHandler(QObject):
    """
    Handler that listens to text display changes and updates word predictions.
    Uses Qt signals to safely bridge worker thread and UI thread.
    """
    
    # Signal emitted when new predictions are ready (thread-safe)
    predictions_ready = Signal(list)
    
    def __init__(self, word_column: WordColumnComponent, n_words: int = 10):
        """
        Initialize the prediction handler.
        
        :param word_column: The WordColumnComponent to update with predictions
        :param n_words: Number of words to predict
        """
        super().__init__()
        self._word_column = word_column
        self._prediction_service = PredictionService(n_words=n_words)
        
        # Connect signal to slot for thread-safe UI updates
        self.predictions_ready.connect(self._update_word_column)
        
        # Set callback for prediction service
        self._prediction_service.set_callback(self._on_predictions_ready)
        
        # Start the prediction service thread
        self._prediction_service.start()
    
    def handle_event(self, event: AppEvent) -> None:
        """
        Handle TEXT_CHANGED events from PisakDisplay.
        
        :param event: The event to handle
        """
        if event.type == AppEventType.TEXT_CHANGED:
            data = event.data
            if isinstance(data, dict):
                text = data.get('text', '')
                cursor_position = data.get('cursor_position', 0)
                
                # Request predictions (non-blocking)
                self._prediction_service.request_predictions(text, cursor_position)
    
    def _on_predictions_ready(self, predictions: list[str]):
        """
        Callback called by prediction service (in worker thread).
        Emits signal to safely update UI.
        
        :param predictions: List of predicted words
        """
        # Emit signal (thread-safe way to communicate with UI thread)
        self.predictions_ready.emit(predictions)
    
    @Slot(list)
    def _update_word_column(self, predictions: list[str]):
        """
        Update word column with new predictions (runs in UI thread).
        
        :param predictions: List of predicted words
        """
        self._word_column.update_words(predictions)
    
    def stop(self):
        """Stop the prediction service"""
        self._prediction_service.stop()


