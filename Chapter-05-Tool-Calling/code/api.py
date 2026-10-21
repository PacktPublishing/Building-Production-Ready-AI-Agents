import asyncio
import inspect

import ollama
from ollama import ChatResponse
from tools import (
    add_two_numbers,
    add_two_numbers_tool,
    get_people_tool,
    get_persons,
    get_products,
    get_products_tool,
    get_weather,
    get_weather_tool,
    subtract_two_numbers,
    subtract_two_numbers_tool,
)

model = 'llama3.1'

messages = [
    {'role': 'system', 'content': 'You are a helpful assistant that can perform basic math operations and fetch data from the Star Wars API and Open-Meteo API and also fetch data from the products database. Use the provided tools to answer user questions.'},
]

available_functions = {
  'add_two_numbers': add_two_numbers,
  'subtract_two_numbers': subtract_two_numbers,
  'get_persons': get_persons,
  'get_weather': get_weather,
  'get_products': get_products,
}

def log(str:str):
   print(f"[LOG] {str}")

async def main(prompt: str):
  log(f"Running prompt: {prompt}")
  client = ollama.AsyncClient()

  messages.append({'role': 'user', 'content': prompt})

  response: ChatResponse = await client.chat(
    model,
    messages=messages,
    tools=[
       add_two_numbers_tool, 
       subtract_two_numbers_tool, 
       get_people_tool, 
       get_weather_tool,
       get_products_tool
    ],
  )

  if response.message.tool_calls:
    # Add the model's tool call message to history
    messages.append(response.message)
    
    # There may be multiple tool calls in the response
    for tool in response.message.tool_calls:
      # Ensure the function is available, and then call it
      if function_to_call := available_functions.get(tool.function.name):
        log(f"Calling function: {tool.function.name}")
        log(f"Arguments: {tool.function.arguments}")
        result = function_to_call(**tool.function.arguments)
        if inspect.isawaitable(result):
          output = await result
        else:
          output = result
        log(f"Function output: {output}")
        
        # Format the output for better LLM interpretation
        if isinstance(output, list):
          formatted_output = ", ".join(str(item) for item in output)
        else:
          formatted_output = str(output)
        
        # Add each tool's output to messages immediately
        messages.append({'role': 'tool', 'content': formatted_output, 'name': tool.function.name})
      else:
        log(f"Function {tool.function.name} not found")

    # Get final response from model with all function outputs
    final_response = await client.chat(model, messages=messages)
    print('Final response:', final_response.message.content)

  else:
    print('No tool calls returned from model')


if __name__ == '__main__':
  try:
    prompt = input("Enter your prompt: ")
    asyncio.run(main(prompt))
  except KeyboardInterrupt:
    print('\nGoodbye!')