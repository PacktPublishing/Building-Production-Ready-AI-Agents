from ollama import chat

model = 'phi3:mini'

def generate_response_stream(user_prompt: str, context: str):
    """Stream a response from Ollama based on RAG context and user prompt."""
    system_message = (
        "You are a helpful assistant. Answer the user's question using ONLY the context provided below. "
        "Do not add information beyond what is in the context. Keep your answer concise and closely aligned "
        "with the source material. If the context doesn't contain relevant information, say so.\n\n"
        f"Context:\n{context}"
    )

    stream = chat(model=model, messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt},
    ], stream=True)

    for chunk in stream:
        if chunk.message.content:
            yield chunk.message.content