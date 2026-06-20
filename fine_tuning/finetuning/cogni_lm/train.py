import torch
import torch.nn as nn
import torch.optim as optim

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
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# training loop
print("Training started...")

for epoch in range(3):  # keep small
    total_loss = 0

    for text in data[:200]:   # small subset (fast training)
        tokens = tokenizer.encode(text)

        if len(tokens) < 2:
            continue

        x = torch.tensor(tokens[:-1]).unsqueeze(0)
        y = torch.tensor(tokens[1:]).unsqueeze(0)

        output = model(x)

        loss = criterion(output.view(-1, vocab_size), y.view(-1))

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss:.2f}")

# save model
torch.save(model.state_dict(), "cogni_lm/model.pt")

print("Training complete. Model saved.")