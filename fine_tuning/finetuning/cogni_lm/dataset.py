import json

def load_data(path):
    texts = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            texts.append(row["input"] + " " + row["output"])

    return texts