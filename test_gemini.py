import google.generativeai as genai
import os
from utils.env_loader import load_env_manual

print("--- GEMINI DIAGNOSTIC ---")

# 1. Load Key
env = load_env_manual()
api_key = env.get("GEMINI_API_KEY")
print(f"1. API Key Loaded: {'YES ✅' if api_key else 'NO ❌'}")
if api_key:
    print(f"   Key Start: {api_key[:5]}...")

# 2. Configure
try:
    genai.configure(api_key=api_key)
    print("2. Configuration: SUCCESS")
except Exception as e:
    print(f"2. Configuration: FAILED ({e})")

# 3. Test Model Creation (checking system_instruction support)
try:
    print("3. Testing Model Init with system_instruction...")
    model = genai.GenerativeModel("gemini-pro", system_instruction="You are a test bot.")
    print("   Model Init: SUCCESS ✅")
except TypeError as e:
    print(f"   Model Init: FAILED ❌ (Likely old library version)")
    print(f"   Error: {e}")
    print("   -> Will recommend refactoring to legacy prompt mode.")
except Exception as e:
    print(f"   Model Init: FAILED ({e})")

# 4. Test Generation (if init worked)
if 'model' in locals():
    try:
        print("4. Testing Generation...")
        resp = model.generate_content("Hello, are you working?")
        print(f"   Generation: SUCCESS ✅ (Response: {resp.text})")
    except Exception as e:
        print(f"   Generation: FAILED ({e})")

print("-------------------------")
