import torch
import torch.nn as nn

class RNNClassifier(nn.Module):
    """
    Standard Recurrent Neural Network (RNN) sequence model for legal text sensitivity.
    """
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int,
        hidden_dim: int,
        output_dim: int,
        num_layers: int = 1,
        dropout: float = 0.2
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.rnn = nn.RNN(
            embedding_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, text: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        # text shape: [batch_size, seq_length]
        embedded = self.dropout(self.embedding(text)) # [batch_size, seq_length, embedding_dim]
        output, hidden = self.rnn(embedded)           # [batch_size, seq_length, hidden_dim]
        # Use final time step representation
        last_step = output[:, -1, :]                  # [batch_size, hidden_dim]
        return self.fc(last_step)
