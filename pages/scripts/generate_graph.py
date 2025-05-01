# %%
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain import hub
from uuid import uuid4
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver
import re
from PIL import Image
import base64
import io
import pandas as pd
import os

# %% Output class, Prompt Definition


class FoodItem(BaseModel):
    food_item: str = Field(..., description="Name of the identified food")
    portion: str = Field(..., description="Estimated portion size, e.g., 1 cup, 150g")
    calories: int = Field(..., description="Estimated calorie content")
    protein_g: float = Field(..., description="Estimated protein in grams")
    fat_g: float = Field(..., description="Estimated total fat in grams")
    saturated_fat_g: float = Field(..., description="Estimated saturated fat in grams")
    carbs_g: float = Field(..., description="Estimated carbohydrate content in grams")


class NutritionEstimate(BaseModel):
    items: List[FoodItem]
    total: FoodItem


prompt = """
You are a food nutrition expert.

Estimate the nutrition of the meal in the provided image.

1. Identify visible food items.
2. Estimate portion size for each.
3. Provide the following for each item:
   - Calories (kcal)
   - Protein (g)
   - Fat (g)
   - Saturated Fat (g)
   - Carbohydrates (g)
4. Provide a total combined nutritional summary for the entire meal.

If any assumptions are made (e.g., portion or food type), estimate them reasonably.
"""

# %% LLM Creation
llm = ChatOpenAI(
    model="gpt-4o-mini",  # or "gpt-4o-mini" if available in your org
    temperature=0,
    api_key=os.environ.get('OPENAI_API_KEY')
)

llm_with_output = llm.with_structured_output(NutritionEstimate)


# %% Graph Build
class State(BaseModel):
    image_path: str
    feedback: Optional[str] = None
    llm_output: Optional[NutritionEstimate] = None  # 已解析后的 Pydantic 对象
    feedback_history: List[str] = []


def init_recognition_node(state: State):
    with open(state.image_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode()
        b64_img_url = f"data:image/png;base64,{b64_img}"
    response = llm_with_output.invoke([
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": b64_img_url}}
        ]}
    ])
    return {'llm_output': response, 'feedback_history': []}


def user_feedback_node(state: State):
    with open(state.image_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode()
        b64_img_url = f"data:image/png;base64,{b64_img}"
    feedback = state.feedback
    prev_result = state.llm_output

    fb_prompt = f"""
    You are a food recognition expert.

    This is the previous recognition output:
    {prev_result.model_dump_json(indent=2)}

    The user provided the following correction:
    "{feedback}"

    Please re-evaluate the image and update the nutrition estimates accordingly.
    """
    res = llm_with_output.invoke([
        {"role": "user", "content": [
            {"type": "text", "text": fb_prompt},
            {"type": "image_url", "image_url": {"url": b64_img_url}}
        ]}
    ])
    hist = state.feedback_history + [feedback]

    return {"llm_output": res, "feedback_history": hist}


def build_graph():
    sg = StateGraph(State)
    sg.add_node("init_recognition", init_recognition_node)
    sg.add_node("user_feedback", user_feedback_node)
    # 流程: initial → feedback (可循环) → END
    sg.set_entry_point("init_recognition")
    sg.add_edge("init_recognition", "user_feedback")
    sg.add_conditional_edges(
        "user_feedback",
        lambda s: END if len(s.feedback_history) >= 3 else "user_feedback"
    )
    saver = MemorySaver()  # 本地持久化
    return sg.compile(checkpointer=saver)


graph = build_graph()
