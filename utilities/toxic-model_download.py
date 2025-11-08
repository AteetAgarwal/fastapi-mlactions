from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

MODEL_ID = "martin-ha/toxic-comment-model"
TARGET_DIR = "./ml-models/toxic-model"  # put inside repo

os.makedirs(TARGET_DIR, exist_ok=True)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)

tokenizer.save_pretrained(TARGET_DIR)
model.save_pretrained(TARGET_DIR)
