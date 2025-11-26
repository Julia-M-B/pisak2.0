"""
Handler that connects text display changes to word prediction updates.
Uses internal event system with thread-safe adapter to update UI from worker thread.
"""
from PySide6.QtCore import QObject, Signal, Slot

from pisak.events import AppEvent, AppEventType
from pisak.predictions.prediction_service import PredictionService
from pisak.components.column_components import WordColumnComponent
from pisak.emitters import EventEmitter


class ThreadSafeEventAdapter(QObject, EventEmitter):
    """
    Adapter that safely bridges worker thread events to main UI thread using Qt signals internally.
    Exposes event-driven API while ensuring thread-safety for UI updates.
    """
    
    # Internal signal for thread-safe communication (Qt handles the thread switching)
    _predictions_signal = Signal(list)
    
    def __init__(self):
        QObject.__init__(self)
        EventEmitter.__init__(self)
        # Connect internal signal to the event emitter
        self._predictions_signal.connect(self._emit_predictions_event)
    
    def emit_from_worker_thread(self, predictions: list[str]):
        """
        Called from worker thread. Uses Qt signals to safely switch to main thread.
        
        :param predictions: List of predicted words
        """
        # Qt's signal-slot mechanism handles the thread switching
        self._predictions_signal.emit(predictions)
    
    @Slot(list)
    def _emit_predictions_event(self, predictions: list[str]):
        """
        Runs in main UI thread. Emits AppEvent to all subscribed handlers.
        
        :param predictions: List of predicted words
        """
        # Now we're in the main thread, safe to emit events that update UI
        event = AppEvent(AppEventType.PREDICTIONS_READY, predictions)
        self.emit_event(event)


class PredictionHandler:
    """
    Handler that listens to text display changes and updates word predictions.
    Uses thread-safe event adapter to bridge worker thread and UI thread.
    """
    
    def __init__(self, word_column: WordColumnComponent, n_words: int = 10):
        """
        Initialize the prediction handler.
        
        :param word_column: The WordColumnComponent to update with predictions
        :param n_words: Number of words to predict
        """
        self._word_column = word_column
        self._prediction_service = PredictionService(n_words=n_words)
        
        # Create thread-safe adapter for predictions
        self._prediction_adapter = ThreadSafeEventAdapter()
        
        # Subscribe word column updater to adapter events
        self._prediction_adapter.subscribe(WordColumnUpdater(word_column))
        
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
        Uses thread-safe adapter to communicate with UI thread.
        
        :param predictions: List of predicted words
        """
        # Use adapter to safely switch to main thread and emit event
        self._prediction_adapter.emit_from_worker_thread(predictions)
    
    def stop(self):
        """Stop the prediction service"""
        self._prediction_service.stop()


class WordColumnUpdater:
    """
    Handler that updates word column when predictions are ready.
    This runs in the main UI thread (ensured by ThreadSafeEventAdapter).
    """
    
    def __init__(self, word_column: WordColumnComponent):
        self._word_column = word_column
    
    def handle_event(self, event: AppEvent) -> None:
        """
        Handle PREDICTIONS_READY events.
        
        :param event: The event to handle
        """
        if event.type == AppEventType.PREDICTIONS_READY:
            predictions = event.data
            if isinstance(predictions, list):
                self._word_column.update_words(predictions)


