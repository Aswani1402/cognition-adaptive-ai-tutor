import torch
from tokenizer import SimpleTokenizer
from dataset import load_data
from model import SimpleLLM

data = load_data("training_data/llm_tutor/tutor_train.jsonl")

tokenizer = SimpleTokenizer()
tokenizer.build_vocab(data)

vocab_size = len(tokenizer.word2id)

model = SimpleLLM(vocab_size)

sample = tokenizer.encode(data[0][:50])
sample = torch.tensor(sample).unsqueeze(0)

output = model(sample)

print("Output shape:", output.shape)