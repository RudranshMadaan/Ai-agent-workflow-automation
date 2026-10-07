try:
    from openai import OpenAI
except ImportError:
    OpenAI = object
import json

class LLMTool:
    def __init__(self, client: OpenAI | None, model: str):
        self.client, self.model = client, model

    def generate(self, system: str, user: str):
        if not self.client:
            return "LLM unavailable: deterministic validation completed; missing fields were not invented."
        r = self.client.responses.create(model=self.model, instructions=system, input=user)
        return r.output_text

    def classify(self, system: str, user: str):
        if not self.client:
            return None
        r = self.client.responses.create(model=self.model, instructions=system, input=user)
        return r.output_text
