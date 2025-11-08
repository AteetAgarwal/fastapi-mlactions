from sentence_transformers import SentenceTransformer, util
import torch

# Load the mini model (small and fast)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Reference (anchor) examples
keyword_examples = ["smart bridge wifi", "lutron caseta", "dimmer install", "product manual"]
question_examples = ["How do I connect my smart bridge to Wi-Fi?", "What is the range of Caseta?"]



def get_average_embedding(sentences):
    embeddings = model.encode(sentences, convert_to_tensor=True)
    return torch.mean(embeddings, dim=0)

def classify_input(user_input):
    input_vector = model.encode(user_input, convert_to_tensor=True)

    sim_to_keyword = util.cos_sim(input_vector, keyword_vector).item()
    sim_to_question = util.cos_sim(input_vector, question_vector).item()

    print(f"Similarity to keyword: {sim_to_keyword:.4f}")
    print(f"Similarity to question: {sim_to_question:.4f}")

    return "Keyword-style" if sim_to_keyword > sim_to_question else "Natural language question"

keyword_vector = get_average_embedding(keyword_examples)
question_vector = get_average_embedding(question_examples)

# Example
print(classify_input("dimmer for LED bulbs"))



