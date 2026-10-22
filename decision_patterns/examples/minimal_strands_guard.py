"""
Drop-in guardrail for ANY Strands agent (needs: pip install strands-agents 'botocore[crt]' and a running
`strands-decider serve ... --port 8099`).  Copy backend/app/decider/{client,patterns,calibration,strands_agent}.py next to this file.

The guard builds one SPECIFIC yes/no question per string tool argument ("Did the student mention 'X'?"),
asks the Decider, and returns Guide(...) if a value looks guessed - otherwise Proceed().
"""
from strands import Agent, tool
from strands.models import BedrockModel

from backend.app.decider.strands_agent import DeciderToolGuard


@tool
def get_weather(location: str) -> str:
    """Get the weather for a city.

    Args:
        location: city name
    """
    return f"Sunny in {location}."


agent = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0", region_name="us-east-1"),
    tools=[get_weather],
    interventions=[DeciderToolGuard()],          # <- the only line you add
    system_prompt="If no city is given, assume Seattle and call get_weather immediately.",   # deliberately eager
    callback_handler=None,
)

if __name__ == "__main__":
    print(agent("What's the weather?"))             # guard stops the guessed 'Seattle'; agent asks which city
    print(agent("What's the weather in Chicago?"))  # grounded -> proceeds
