from __future__ import annotations

import torch


def predict_mastery_simple(
    inter_tensor: torch.Tensor,
    target_tensor: torch.Tensor,
    num_skills: int,
) -> torch.Tensor:
    """
    Lightweight fallback mastery predictor.

    Returns a tensor shaped like [batch, seq_len], where each value is a simple
    estimated mastery score based on cumulative correctness for the sequence.
    """

    batch_size, seq_len = inter_tensor.shape
    probs = torch.zeros((batch_size, seq_len), dtype=torch.float32)

    for b in range(batch_size):
        correct_count = 0

        for t in range(seq_len):
            inter_id = int(inter_tensor[b, t].item())

            # Based on your encoding:
            # inter_id = cid * 2 + correct
            correct = inter_id % 2

            if correct == 1:
                correct_count += 1

            probs[b, t] = correct_count / (t + 1)

    return probs