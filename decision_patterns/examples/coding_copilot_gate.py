"""
Reusable #policy recipe: "When should an AI coding assistant interrupt?"
Zero StudyMind-specific imports. Works for IDE copilots, code reviewers, and pair-programming agents.

Drop ProactivityGate into your agent loop:
  - Developer in flow -> Stay silent (protects focus, 0 tokens).
  - Developer stuck / wrong path -> Escalates gently: Nudge -> Margin Note -> Hint -> Next Step.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.decider.client import DeciderClient
from backend.app.decider.patterns import ProactivityGate


def main():
    # 1. Initialize client and gate (using local Decider server or offline heuristic fallback)
    client = DeciderClient("http://127.0.0.1:8099", allow_fallback=True)
    gate = ProactivityGate(
        client=client,
        shield=0.60,             # Protects developer flow when P(productive_struggle) >= 0.60
        hysteresis_ticks=3,       # Requires 3 consecutive ticks on wrong path before speaking
        base_cooldown=15.0,       # Minimum 15s between spoken interruptions
        max_budget=4,             # Hard cap of 4 spoken interventions per coding session
    )

    # Scenario A: Developer actively writing a function in flow
    dev_state_flow = (
        "--- TASK ---\nImplement LRU Cache with O(1) get and put.\n\n"
        "--- IDE BUFFER ---\n"
        "class LRUCache:\n"
        "    def __init__(self, capacity: int):\n"
        "        self.capacity = capacity\n"
        "        self.cache = {}\n"
        "        self.head = Node(0, 0)\n"
        "        self.tail = Node(0, 0)\n"
        "        self.head.next = self.tail\n"
        "        self.tail.prev = self.head\n"
    )
    res_flow = gate.evaluate(dev_state_flow, task="LRU Cache")
    print(f"[Scenario A - In Flow] Action: {res_flow.action.upper()} (Rung {res_flow.rung})")
    print(f"  Reason: {res_flow.held_back_by} (Tokens spent: 0)\n")

    # Scenario B: Developer stuck on wrong path for 3 ticks
    dev_state_stuck = (
        "--- TASK ---\nImplement LRU Cache with O(1) get and put.\n\n"
        "--- IDE BUFFER ---\n"
        "class LRUCache:\n"
        "    # wait, dict keys are not ordered in Python 2 or what?\n"
        "    # this is wrong... deleting from middle of array is O(n)\n"
        "    pass\n"
    )
    for tick in range(1, 4):
        res_stuck = gate.evaluate(dev_state_stuck, task="LRU Cache")
        print(f"[Scenario B - Stuck Tick {tick}] Action: {res_stuck.action.upper()} (Rung {res_stuck.rung})")
        if res_stuck.held_back_by:
            print(f"  Held by: {res_stuck.held_back_by}")
        elif res_stuck.spoken:
            print(f"  Spoke: Copilot provides margin note (Target Rung: {res_stuck.rung})")


if __name__ == "__main__":
    main()
