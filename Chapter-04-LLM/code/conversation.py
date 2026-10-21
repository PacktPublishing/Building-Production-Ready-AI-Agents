from ollama import chat

model = 'phi3:mini'
greeting = "Type anything to start the conversation with the model> "
prompt = input(greeting)

content = ''

messages = [
    { 'role': 'system', 'content': 'You are a helpful assistant that remembers the user\'s name and uses it in the conversation.' },
    { 'role': 'user', 'content': 'My name is Alice.' },
    {'role': 'user', 'content': prompt}
]

while True:
    stream = chat(
        model=model,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        if chunk.message.content:
            print(chunk.message.content, end='', flush=True)
            content += chunk.message.content

    print("\n[Done responding]\n")
    prompt = input(greeting)
    messages.append({'role': 'user', 'content': prompt})