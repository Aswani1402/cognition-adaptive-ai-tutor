class BehaviourBuffer:
    """
    Keeps last N feature vectors per student for behaviour LSTM.
    Stores sequences in memory (for demo). Later you can persist in DB if needed.
    """
    def __init__(self, seq_len: int = 20):
        self.seq_len = seq_len
        self.buffers = {}  # student_id -> list[list[float]]

    def add(self, student_id: str, feat_vec):
        """
        feat_vec: list[float] (one timestep feature vector)
        returns: updated sequence (last seq_len vectors)
        """
        buf = self.buffers.get(student_id, [])
        buf.append(feat_vec)
        buf = buf[-self.seq_len:]
        self.buffers[student_id] = buf
        return buf

    def ready(self, student_id: str) -> bool:
        return len(self.buffers.get(student_id, [])) >= self.seq_len

    def get(self, student_id: str):
        return self.buffers.get(student_id, [])