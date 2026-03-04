import unittest

from msfang.models import Gate, TicketState
from msfang.state_machine import TicketStateMachine


class StateMachineTests(unittest.TestCase):
    def test_happy_path_close(self):
        m = TicketStateMachine()
        s = TicketState(ticket_id="t1", success_criteria=["done"])

        s = m.preflight(s)
        s = m.plan(s)
        s = m.execute(s)
        s = m.critic(s, gate=Gate.GREEN)
        s = m.janitor(s, janitor_commit_id="j1")
        s = m.close(s)

        self.assertEqual(s.phase.value, "closed")
        self.assertEqual(s.status.value, "complete")

    def test_red_on_strike_threshold(self):
        m = TicketStateMachine(strike_threshold_red=3)
        s = TicketState(ticket_id="t2")
        s = m.plan(m.preflight(s))
        s = m.execute(s)
        s = m.critic(s, gate=Gate.AMBER, strikes_increment=3)
        self.assertEqual(s.gate.value, "red")
        self.assertEqual(s.status.value, "blocked")

    def test_undo(self):
        m = TicketStateMachine()
        s = TicketState(ticket_id="t3")
        s = m.preflight(s)
        s = m.plan(s)
        s = m.undo(s)
        self.assertEqual(s.phase.value, "preflight")


if __name__ == "__main__":
    unittest.main()
