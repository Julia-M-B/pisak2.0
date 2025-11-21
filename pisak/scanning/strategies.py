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
