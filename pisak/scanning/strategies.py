class BaseStrategy:
    """Base implementation for scanning strategies"""
    
    def reset_scan(self, item):
        """Default implementation - return parent widget"""
        return item.parentWidget()


class BackToParentStrategy(BaseStrategy):
    """Strategy that resets scanning to the parent widget"""
    
    def reset_scan(self, item):
        return item.parentWidget()


class TopStrategy(BaseStrategy):
    """Strategy that keeps scanning at the current level"""
    
    def reset_scan(self, item):
        return item


class BackNLevelsStrategy(BaseStrategy):
    def __init__(self, n: int = 2):
        super().__init__()
        self._n = n  # dla n = 1 to jest strategia BackToParentStrategy

    def reset_scan(self, item):
        for _ in range(self._n):
            item = item.parentWidget()
        return item
