import google.generativeai as genai
from utils.env_loader import load_env_manual

env = load_env_manual()
api_key = env.get("GEMINI_API_KEY")

if not api_key:
    print("❌ No API Key found.")
else:
    genai.configure(api_key=api_key)
    print("--- Available Models for generateContent ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
