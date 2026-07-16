class EarlyStoppingCallback:
    """
    Early stopping callback to halt training when validation loss stops improving.
    """
    def __init__(self, patience: int = 2, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float("inf")
        self.counter = 0
        self.should_stop = False

    def on_epoch_end(self, epoch: int, val_loss: float) -> bool:
        """
        Check if training should stop. Returns True if training should stop.
        """
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
        return self.should_stop
