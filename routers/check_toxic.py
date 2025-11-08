from fastapi import APIRouter, Query as QueryParam
from models import ToxicApiResponse
from transformers import pipeline
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "ml-models", "toxic-model"))

toxic_router = APIRouter(tags=["toxicity"])

# load model + tokenizer locally
toxic_model = pipeline(
    "text-classification",
    model=LOCAL_MODEL_PATH,
    tokenizer=LOCAL_MODEL_PATH
)

@toxic_router.get("/toxicity/check-toxic", response_model=ToxicApiResponse)
async def check_toxic(text: str = QueryParam(..., description="Text to check for toxicity")):
    result = toxic_model(text)[0]
    
    # this model uses label "hate" if inappropriate
    is_flagged = result["label"].lower() in ["toxic", "obscene", "insult", "threat"] and result["score"] > 0.80
    
    return ToxicApiResponse(
        input=text,
        is_flagged=is_flagged,
        model_label=result["label"],
        score=result["score"]
    )
