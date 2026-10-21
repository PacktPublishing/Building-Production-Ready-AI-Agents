"""Example usage of LLM ReAct Agent"""
import sys
from agent import LLMReActAgent
from stock_agent import STOCK_TOOLS, STOCK_OBSERVATIONS
from thermostat_agent import THERMOSTAT_TOOLS, THERMOSTAT_OBSERVATIONS
from blackjack_agent import BLACKJACK_TOOLS, BLACKJACK_OBSERVATIONS


def run_stock_trading_example():
    """Run a stock trading decision agent"""
    print("\n" + "█"*70)
    print("█" + " Stock Trading ReAct Agent Example ".center(70, "█"))
    print("█"*70)
    
    agent = LLMReActAgent(tools=STOCK_TOOLS, model="llama3.1:latest")
    
    agent.run_agent_loop(STOCK_OBSERVATIONS, num_actions_per_cycle=4)


def run_thermostat_example():
    """Run a thermostat control agent"""
    print("\n" + "█"*70)
    print("█" + " Thermostat Control ReAct Agent Example ".center(70, "█"))
    print("█"*70)
    
    agent = LLMReActAgent(tools=THERMOSTAT_TOOLS, model="llama3.1:latest")
    
    agent.run_agent_loop(THERMOSTAT_OBSERVATIONS, num_actions_per_cycle=3)


def run_blackjack_example():
    """Run a blackjack decision agent"""
    print("\n" + "█"*70)
    print("█" + " Blackjack ReAct Agent Example ".center(70, "█"))
    print("█"*70)

    agent = LLMReActAgent(tools=BLACKJACK_TOOLS, model="llama3.1:latest")

    agent.run_agent_loop(BLACKJACK_OBSERVATIONS, num_actions_per_cycle=12)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "thermostat":
        run_thermostat_example()
    elif len(sys.argv) > 1 and sys.argv[1] == "blackjack":
        run_blackjack_example()
    else:
        run_stock_trading_example()
