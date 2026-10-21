This code contains an LLM app using a tool.

## Prerequisites

To run samples in this chapter, you will need to have the Ollama CLI installed and an Ollama server running. You can find instructions for installing and running Ollama in the [Ollama documentation](https://ollama.com/docs/installation).

You should have mistral downloaded and available in your local Ollama server. You can run the following command to pull the model:

```bash
ollama pull mistral
```

## Setup

Create a virtual environment and activate it:

```sh
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate    
```

OR use uv:

```sh
uv init
```

## Install

```sh
pip install ollama pydantic
```

OR use uv:

```sh
uv add ollama pydantic
```

## Run sample

```sh
python main.py
```

OR use uv:

```sh
uv run main.py
```

you should see the following output given an input of "add 4 and 2":

```text
Enter your prompt: add 4 and 2
[LOG] Calling function: add_two_numbers
[LOG] Arguments: {'a': 4, 'b': 2}
[LOG] Function output: 6
Final response: The sum of 4 and 2 is 6.
```