import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY was not found in the .env file."
    )

print("Gemini API key loaded successfully.")
print("Key is not displayed for security.")