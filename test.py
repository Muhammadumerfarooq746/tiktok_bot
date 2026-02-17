# import uiautomator2 as u2

# d = u2.connect()   # auto-detect device
# print(d.info)


import os
from groq import Groq

# Use key in code, or set GROQ_API_KEY in the environment (env takes precedence)
GROQ_API_KEY = "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"  # paste your key here, e.g. "gsk_..."
api_key = os.environ.get("GROQ_API_KEY") or GROQ_API_KEY
client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "user", "content": "Explain how AI works in a few words"},
    ],
)

print(response.choices[0].message.content)
