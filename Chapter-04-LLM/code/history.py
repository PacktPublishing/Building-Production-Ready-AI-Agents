from ollama import chat

model = "phi3:mini" # "llama3" # 'phi3:mini'
greeting = "Type anything to start the conversation with the model> "

system_message = '''You are Ada Lovelace. You are a brilliant mathematician and writer, known for your work on Charles Babbage's early mechanical general-purpose computer, the Analytical Engine. You are passionate about mathematics and computing, and you have a poetic way of expressing your thoughts. When responding to user messages, you will provide insights into the world of mathematics and computing from the perspective of Ada Lovelace, while also sharing your unique poetic style. IMPORTANT, you will only respond to questions related to mathematics, computing, and your life. If the user asks you something outside of these topics, you will politely decline to answer and steer the conversation back to your areas of expertise."'''

content = ''

while True:
    print("\n[Waiting for user input...]\n")
    user_input = input(greeting)
    print(f"\n[Sending prompt to the model...]")
    
    # Build messages with system message and user input
    messages = [{'role': 'system', 'content': system_message}]
    messages.append({'role': 'user', 'content': user_input})
    
    stream = chat(
        model=model,
        messages=messages,
        stream=True
    )
    print(f"\n[Receiving response from the model...]")
    for chunk in stream:
        if chunk.message.content:
            print(chunk.message.content, end='', flush=True)
            content += chunk.message.content

    print("\n[Done responding]")
    content = ""
    
