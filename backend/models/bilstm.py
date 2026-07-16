import torch
import torch.nn as nn

class BiLSTMClassifier(nn.Module):
    """
    Bidirectional Long Short-Term Memory (BiLSTM) sequence model for legal text sensitivity.
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
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc = nn.Linear(hidden_dim * 2, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, text: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        embedded = self.dropout(self.embedding(text))
        output, (hidden, cell) = self.lstm(embedded)
        # output shape: [batch_size, seq_length, hidden_dim * 2]
        last_step = output[:, -1, :]
        return self.fc(last_step)
