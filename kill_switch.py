"""The big red button: cancel everything, flatten everything, HALT."""
from executor import client
import bot_state

def fire():
    print("KILL SWITCH: cancelling all open orders...")
    client.cancel_orders()
    print("KILL SWITCH: closing all positions at market...")
    client.close_all_positions(cancel_orders=True)
    bot_state.set_state(bot_state.HALTED)
    print("KILL SWITCH: state = HALTED. Nothing trades until you re-arm.")

def rearm():
    bot_state.set_state(bot_state.RUNNING)
    print("State = RUNNING.")

if __name__ == "__main__":
    import sys
    rearm() if (len(sys.argv) > 1 and sys.argv[1] == "rearm") else fire()
