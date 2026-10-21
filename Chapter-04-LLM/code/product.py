from ollama import chat

model = 'llama3'

options = {
    'temperature': 0.7,  # Adjust creativity (0.0 - 1.0)
    'top_p': 0.9,        # Adjust diversity (0.0 - 1.0)
}

content = ''

print("Welcome to the product description generator! Type your product details to get started.\n")

while True:
    title = input("What's your product title: ")
    description = input("What's your product description: ")
    message = f"Product title: {title}\nProduct description: {description}"


    print("[Generating product description...]\n")
    stream = chat(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant helping with product descriptions. You MUST keep to a one paragraph response'},
            {'role': 'user', 'content': message}
        ],
        stream=True,
        options=options,
    )

    for chunk in stream:
        if chunk.message.content:
            print(chunk.message.content, end='', flush=True)
            content += chunk.message.content

    print("[Done responding]\n")
