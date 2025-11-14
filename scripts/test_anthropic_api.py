#!/usr/bin/env python3
import anthropic
import sys
import os

# Get API key from environment variable
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: ANTHROPIC_API_KEY environment variable not set")
    sys.exit(1)

print(f"[DEBUG] API key found (length: {len(api_key)})")

# Default model, can be overridden via command line
model = sys.argv[1] if len(sys.argv) > 1 else "claude-sonnet-4-20250514"
message_text = sys.argv[2] if len(sys.argv) > 2 else "Hello"

print(f"[DEBUG] Testing model: {model}")
print(f"[DEBUG] Message: {message_text}")

client = anthropic.Anthropic(api_key=api_key)

try:
    print(f"[DEBUG] Sending request...")
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": message_text}
        ]
    )
    print(f"✓ Success with {model}")
    print(f"\nResponse:\n{message.content[0].text}")
except Exception as e:
    print(f"✗ Error with {model}:")
    print(f"{type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)