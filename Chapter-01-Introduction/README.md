# Introduction to Agentic Apps

Welcome to the world of agentic applications! But first, what do we even mean with “agentic”? In the context of AI, an agentic app is one that exhibits autonomy, goal-directed behavior, and the ability to engage in reasoning loops. You might wonder, then what does "that" mean? Well, think about it this way, autonomy means that the app can operate independently without constant human intervention. A good example of that is a thermostat that can adjust the temperature based on the current conditions without you having to manually change it. 

Goal-directed behavior means that the app can set and pursue specific objectives. For instance, a navigation app that can find the best route to your destination based on traffic conditions is exhibiting goal-directed behavior.

Lastly, reasoning loops refer to the app's ability to think through problems, make decisions, and learn from its interactions. Think of a recommendation system that can analyze your preferences, suggest products, and then refine its suggestions based on your feedback. Such an app "reasons" through the information it has to provide better outcomes.

## The advent of chatbots and LLM-powered applications 

The last few years have seen rapid growth in AI applications such as ChatGPT. These applications use large language models (LLMs)—neural networks trained on vast amounts of text—to generate human-like responses. This has made AI accessible to many more people for writing, coding, brainstorming, and countless other tasks.

Early applications had clear limits: a model relied on its training data and couldn't check current information or act on a user's behalf. Connecting models to external data and tools changed that. A travel assistant, for example, can now check live train times instead of merely explaining how to find them. That connection between a model and the world is an important step toward agentic behavior, although keeping the tools reliable and their data fresh takes work.

## New ways of building apps - context engineering

As developers, we're used to learning new architectures, frameworks, and programming languages. Agentic apps add another design concern: deciding what information and capabilities a model should receive for each interaction.

Early on, much of the focus was on **prompt engineering**—crafting clear instructions to get a useful response from an LLM. For example, instead of asking, "Help with this support ticket," you might ask, "Summarize this support ticket in three bullets and suggest a polite reply." A better prompt gives the model a clearer task and output format.

Prompt engineering still matters, but a well-worded request isn't enough when the model needs information it doesn't have. Let's say the reply must also reflect the customer's order history, your current refund policy, and the tone the customer prefers. Supplying the right records, instructions, memory, and available actions is **context engineering**. It expands the focus from writing the prompt to designing the full context in which the model works. In short, prompt engineering improves the request; context engineering improves the whole interaction.

Think of a library: prompt engineering is knowing how to ask the librarian for the right book. Context engineering is designing the library, catalog, and reading room so the librarian can find the right material and help you use it.

## Where do we start as developers?

If you've never built an AI app before, it can be difficult to know where to start. There are new concepts to learn, as well as new relationships between them. This book will guide you through those concepts, starting with five building blocks:

- **Models** generate responses and help choose the next action. In a travel assistant, the model can turn "Get me home before 6 PM" into a plan.
- **Memory** carries useful information between interactions. The assistant might remember that you prefer trains and need step-free access, so you don't have to repeat those details.
- **Tools** let the app retrieve information or take action. A timetable service can provide live departures, while a booking service can reserve the selected journey.
- **Environment** is the setting in which the app operates, including the user, available services, current state, and rules. A cancelled train or a company spending limit can change which action is appropriate.
- **Evaluation** checks whether the interaction was useful, accurate, and safe. Tests might verify that the suggested route arrives on time, meets the accessibility requirement, and stays within budget.

Together, these parts turn a one-off model response into a more capable interaction. The model interprets the goal, memory adds personal context, tools connect to current information and actions, and the environment supplies real-world conditions and constraints. Evaluation then shows where the interaction succeeds or needs improvement. We'll explore each building block in the chapters ahead.

I hope you're excited to explore the world of agentic apps with me and start building your own. The journey may be challenging at times, but you'll be amazed at what you can create. So let's get started!