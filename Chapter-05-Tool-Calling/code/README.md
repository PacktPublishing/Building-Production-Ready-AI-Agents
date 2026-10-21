This README provides instructions on how to run the samples in this chapter, which demonstrate how to call tools from a language model using the Ollama client.

## Prerequisites

To run samples in this chapter, you will need Python 3.12 or later and the Ollama CLI installed with an Ollama server running. You can find instructions for installing and running Ollama in the [Ollama documentation](https://ollama.com/docs/installation).

The focused `tool.py` example uses `mistral`, while the complete `api.py` application uses `llama3.1`. Pull both models before running the samples:

```bash
ollama pull mistral
ollama pull llama3.1
```

## Install dependencies

From this `code` directory, install the dependencies declared in `pyproject.toml`:

```bash
uv sync
```

This installs both the `ollama` client and `requests`, which the weather API tool requires.

If you are not using `uv`, create and activate a virtual environment, then install the same packages with pip:

```bash
python -m pip install ollama requests
```

## Run sample

```sh
uv run api.py
```

You should see the following output:

```text
Enter your prompt:
```

Type the following input to see weather API being called:

```text
What is the weather in London?
```

You should see output similar to:

```text
[LOG] Running prompt: tell me the weather in London
[LOG] Calling function: get_weather
[LOG] Arguments: {'place': 'London'}
[LOG] Function output:
==================================================
🌍 Weather for London
==================================================
📍 Location: 51.51147°N, -0.13078308°E
⛰️  Elevation: 16.0m
⏰ Time: 2026-03-10T21:45 (GMT)

🌙 Night
🌡️  Temperature: 10.9°C
🌤️  Condition: Overcast
💨 Wind Speed: 19.1 km/h
🧭 Wind Direction: 206°
==================================================
```

