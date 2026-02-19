"""Pydantic models for structured LLM extraction."""

from pydantic import BaseModel


class SubTopic(BaseModel):
    name: str
    description: str


class Topic(BaseModel):
    name: str
    description: str
    sub_topics: list[SubTopic] = []


class TopicExtraction(BaseModel):
    topics: list[Topic]
