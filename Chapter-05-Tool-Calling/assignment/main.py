import asyncio
import inspect

from ollama import chat

from ollama import ChatResponse
from pydantic import BaseModel

model = 'mistral'

class CalculationResult(BaseModel):
    result: str

def log(str:str):
   print(f"[LOG] {str}")

def add_two_numbers(a: int, b: int) -> int:
  """
  Add two numbers

  Args:
      a (int): The first number
      b (int): The second number

  Returns:
      int: The sum of the two numbers
  """
  return a + b

add_two_numbers_tool = {
  'type': 'function',
  'function': {
    'name': 'add_two_numbers',
    'description': 'Add two numbers',
    'parameters': {
      'type': 'object',
      'required': ['a', 'b'],
      'properties': {
        'a': {'type': 'integer', 'description': 'The first number'},
        'b': {'type': 'integer', 'description': 'The second number'},
      },
    },
  },
}   

messages = [
    {'role': 'system', 'content': 'You are a helpful assistant that can call tools to answer user questions.'}
]

available_functions = {
    'add_two_numbers': add_two_numbers,
}

async def main():

    prompt = input("Enter your prompt: ")
    messages.append({'role': 'user', 'content': prompt})

    response: ChatResponse = chat(
        model,
        messages=messages,
        tools=[
          add_two_numbers_tool
        ]
    )
    
    if response.message.tool_calls:
        # Add the model's tool call message to history
        messages.append({'role': 'assistant', 'content': response.message.content})

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
        final_response = chat(
            model, messages=messages, format=CalculationResult.model_json_schema()
        )

        description = CalculationResult.model_validate_json(final_response.message.content)

        print('Final response:', description.result)

    else:
        print('No tool calls returned from model')

if __name__ == '__main__':
    asyncio.run(main())