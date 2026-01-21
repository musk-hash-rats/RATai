from dotenv import load_dotenv
import os
import sys

# Load env
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

print("--- TOKEN INSPECTOR ---")
if not token:
    print("❌ TOKEN IS EMPTY OR NULL")
    sys.exit(1)

print(f"Token Found: Yes")
print(f"Length: {len(token)}")
print(f"First 5 chars: {token[:5]}")
print(f"Last 5 chars: {token[-5:]}")

# Check for hidden whitespace/newlines
has_whitespace = any(c.isspace() for c in token)
print(f"Contains Whitespace? {'YES ❌' if has_whitespace else 'NO ✅'}")

# Print raw representation to see escape chars
print(f"Raw repr: {repr(token)}")

print("\nIf 'Raw repr' shows '\\n', '\\r', or extra spaces inside the quotes, that is the bug.")
print("If the token looks perfect here, then the issue IS the token validity on Discord's side.")
