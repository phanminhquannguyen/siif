

import os
from openai import OpenAI
import google.generativeai as genai
from huggingface_hub import InferenceClient
# ---------------- LLM callers ----------------
'''Try to find a free version that we can use :)'''
def call_openai_json(prompt: str, model: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key: raise SystemExit("Set OPENAI_API_KEY or use another provider.")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model, messages=[{"role":"user","content":prompt}],
        max_tokens=800, temperature=0.0
    )
    return resp.choices[0].message.content

def call_gemini_json(prompt: str, model: str = "gemini-2.0-flash") -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GOOGLE_API_KEY or use another provider.")
    genai.configure(api_key=api_key)
    resp = genai.GenerativeModel(model).generate_content(
        prompt, generation_config={"response_mime_type":"application/json"}
    )
    return resp.text

def call_hf_json(prompt: str, model: str) -> str:
    api_key = os.environ.get("HUGGINGFACE_API_KEY")
    if not api_key: raise SystemExit("Set HUGGINGFACE_API_KEY or use another provider.")
    client = InferenceClient(model=model, token=api_key)
    resp = client.chat_completion(messages=[{"role":"user","content":prompt}],
                                  max_tokens=800, temperature=0.0)
    return resp.choices[0].message["content"]


import os
from openai import OpenAI

def call_deepseek_json(prompt: str, model: str = "deepseek-chat") -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("Set DEEPSEEK_API_KEY or use another provider.")
    
    # DeepSeek is OpenAI-compatible, just change base_url
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        # request strict JSON-style output
        response_format={"type": "json_object"}
    )
    
    return resp.choices[0].message.content

def call_llm_json(prompt: str, model: str) -> str:
    if os.environ.get("DEEPSEEK_API_KEY") and model.startswith("deepseek"):
        return call_deepseek_json(prompt, model)
    if os.environ.get("OPENAI_API_KEY") and model.startswith("gpt"):
        return call_openai_json(prompt, model)
    if os.environ.get("GOOGLE_API_KEY") and model.lower().startswith("gemini"):
        return call_gemini_json(prompt, model)
    if os.environ.get("HUGGINGFACE_API_KEY") and ("/" in model):
        return call_hf_json(prompt, model)
    raise SystemExit(
        "No valid provider: set DEEPSEEK_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, or HUGGINGFACE_API_KEY."
    )