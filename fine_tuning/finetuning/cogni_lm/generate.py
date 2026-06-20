import torch

from tokenizer import SimpleTokenizer
from dataset import load_data
from model import SimpleLLM


# load data
data = load_data("training_data/llm_tutor/tutor_train.jsonl")

# tokenizer
tokenizer = SimpleTokenizer()
tokenizer.build_vocab(data)

vocab_size = len(tokenizer.word2id)

# model
model = SimpleLLM(vocab_size)
model.load_state_dict(torch.load("cogni_lm/model.pt"))
model.eval()


def generate_text(start_text, max_len=20, temperature=0.8, top_k=10, repetition_penalty=1.1):
    tokens = tokenizer.encode(start_text)

    for _ in range(max_len):
        x = torch.tensor(tokens).unsqueeze(0)

        with torch.no_grad():
            output = model(x)

        logits = output[0, -1]

        # 🔥 repetition penalty
        for t in set(tokens):
            logits[t] /= repetition_penalty

        # 🔥 temperature scaling
        logits = logits / temperature

        # 🔥 top-k filtering
        top_k_values, top_k_indices = torch.topk(logits, top_k)
        probs = torch.softmax(top_k_values, dim=0)

        # sample from top-k
        next_token = top_k_indices[torch.multinomial(probs, 1).item()].item()

        tokens.append(next_token)

    return tokenizer.decode(tokens)


# test
if __name__ == "__main__":
    text = generate_text("Variables are", max_len=20)
    print("Generated:", text)