from ollama import chat
from ollama import ChatResponse

model = 'phi3:mini'
greeting = "Type anything to start the conversation with the model> "
prompt = ""

prompt = input(greeting)

while True:
    response: ChatResponse = chat(model=model, messages=[
    {
        'role': 'user',
        'content': prompt,
    },
    ])

    print(response.message.content)
    prompt = input(greeting)