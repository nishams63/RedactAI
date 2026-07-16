import logging

logger = logging.getLogger("redactai.dl.training")

class LoggingCallback:
    """
    Logging callback to print and track epoch loss and learning metrics.
    """
    def on_epoch_end(self, epoch: int, train_loss: float, val_loss: float, metrics: dict) -> None:
        accuracy = metrics.get("accuracy", 0.0)
        f1 = metrics.get("f1_macro", 0.0)
        logger.info(
            f"Epoch {epoch} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
            f"Val Accuracy: {accuracy:.4f} | Val F1: {f1:.4f}"
        )
        
    def on_step(self, step: int, loss: float) -> None:
        if step % 20 == 0:
            logger.debug(f"Step {step} | Loss: {loss:.4f}")
            
    def on_training_end(self, duration: float) -> None:
        logger.info(f"Training completed in {duration:.2f} seconds.")
