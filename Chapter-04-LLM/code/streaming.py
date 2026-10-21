from ollama import chat

model = 'phi3:mini'
greeting = "Type anything to start the conversation with the model> "
prompt = input(greeting)

content = ''

while True:
    stream = chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        stream=True,
    )

    for chunk in stream:
        if chunk.message.content:
            print(chunk.message.content, end='', flush=True)
            content += chunk.message.content

    print("\n[Done responding]\n")
    prompt = input(greeting)
