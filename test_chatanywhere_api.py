from openai import OpenAI

client = OpenAI(
    base_url='https://api.nuwaapi.com/v1',
    api_key='sk-uQdj1sORHbo68JQmbKGy1srAqJP8xnIs9jHe6uO3iIrKaSO3'
)

models = [
    "gpt-4o", "gpt-4", "gpt-3.5-turbo",
    "gemini-2.5-flash-thinking", "gemini-2.0-flash-thinking"
]

for model in models:
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        print(f"✅ {model}: 支持")
    except Exception as e:
        print(f"❌ {model}: {str(e)[:100]}")