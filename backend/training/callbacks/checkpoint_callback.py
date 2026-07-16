import os
from typing import Any
from utils.checkpoint import save_checkpoint

class CheckpointCallback:
    """
    Checkpoint callback to save model checkpoints during training.
    """
    def __init__(self, checkpoints_dir: str, save_best_only: bool = True):
        self.checkpoints_dir = checkpoints_dir
        self.save_best_only = save_best_only
        self.best_val_loss = float("inf")
        os.makedirs(checkpoints_dir, exist_ok=True)

    def on_epoch_end(self, epoch: int, model: Any, optimizer: Any, val_loss: float, metrics: dict) -> None:
        """Saves checkpoints."""
        state = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict() if optimizer else None,
            "val_loss": val_loss,
            "metrics": metrics
        }
        
        # Always save last checkpoint
        last_path = os.path.join(self.checkpoints_dir, "last_model.pt")
        save_checkpoint(state, last_path)
        
        # Save best if validation loss improves
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            best_path = os.path.join(self.checkpoints_dir, "best_model.pt")
            save_checkpoint(state, best_path)
