"""Step B: LLM-based extraction of Topics and Sub-Topics from curriculum text."""

import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are an expert curriculum designer. I will give you a text from a science curriculum.

Definitions:
- Topic: An abstract concept taught in a session.
- Sub-Topic: Fine-grained content explained in detail.

Task: Extract all Topics and Sub-Topics from the text below.
Output strictly in JSON format:
{
  "topics": [
    {
      "name": "...",
      "description": "...",
      "sub_topics": [
        {"name": "...", "description": "..."}
      ]
    }
  ]
}"""


def extract_topics(text: str, model: str = "gpt-4o") -> dict:
    llm = ChatOpenAI(model=model, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{text}"),
    ])
    chain = prompt | llm
    response = chain.invoke({"text": text})
    return json.loads(response.content)
