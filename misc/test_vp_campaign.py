"""Critical offline tests for paid-request limits and submission integrity."""
import copy
import unittest
from misc import vp_campaign as c


def state():
    return {"jobs": {}, "status": "ready"}


def job(provider="Anthropic", phase="opus_screen", n=2000):
    return {"provider": provider, "phase": phase, "n": n,
            "attempted_at": None, "reservation_micro": 0}


class BudgetTests(unittest.TestCase):
    def test_entire_authorized_campaign_fits_both_caps(self):
        s = state()
        for phase, (_, _, limits) in c.PHASES.items():
            for provider, n in limits.items():
                if not n:
                    continue
                j = job(provider, phase, n)
                j["reservation_micro"] = c.budget_gate(s, j)
                j["attempted_at"] = "submitted"
                s["jobs"][provider + phase] = j
        self.assertEqual(sum(j["reservation_micro"] for j in s["jobs"].values()
                             if j["provider"] == "Anthropic"), 916_648_000)
        self.assertEqual(sum(j["reservation_micro"] for j in s["jobs"].values()
                             if j["provider"] == "OpenAI"), 1_776_100_000)

    def test_replay_and_unknown_submission_rejected(self):
        j = job(); j["attempted_at"] = "possibly submitted"
        with self.assertRaisesRegex(ValueError, "never replay"):
            c.budget_gate(state(), j)

    def test_phase_limit_includes_previous_jobs(self):
        s = state(); earlier = job(n=6000); earlier["attempted_at"] = "submitted"
        earlier["reservation_micro"] = 257_760_000
        s["jobs"]["previous"] = earlier
        with self.assertRaisesRegex(ValueError, "phase allowance"):
            c.budget_gate(s, job(n=1))

    def test_other_phase_reservations_cannot_consume_final_budget(self):
        s = state(); earlier = job(n=0); earlier["attempted_at"] = "submitted"
        earlier["reservation_micro"] = 100_000_000
        s["jobs"]["extra"] = earlier
        with self.assertRaisesRegex(ValueError, "protected"):
            c.budget_gate(s, job())

    def test_hard_cap_and_halt(self):
        s = state(); earlier = job(n=0); earlier["attempted_at"] = "submitted"
        earlier["reservation_micro"] = 1_000_000_000
        s["jobs"]["previous"] = earlier
        with self.assertRaisesRegex(ValueError, "Hard provider budget"):
            c.budget_gate(s, job(n=1))
        s = state(); s["status"] = "halted_token_policy_violation"
        with self.assertRaisesRegex(ValueError, "halted"):
            c.budget_gate(s, job())

    def test_identical_provider_prompts_and_request_tampering(self):
        task = {"id": "test", "dhatu": {"aupadeshika": "BU", "gana": "Bhvadi", "artha": "sattAyAm"},
                "morphology": {"lakara": "Lat", "prayoga": "Kartari", "purusha": "Prathama", "vacana": "Eka"}}
        a = c.request(task, "Anthropic", "confirm", 0)
        o = c.request(task, "OpenAI", "confirm", 0)
        self.assertEqual(a["params"]["messages"][0]["content"], o["body"]["input"][0]["content"])
        for field, value in (("max_output_tokens", 128000), ("model", "different-model"), ("tools", [{"type": "web_search"}])):
            edited = copy.deepcopy(o); edited["body"][field] = value
            with self.assertRaisesRegex(ValueError, "Request differs"):
                c.validate_requests([task], [edited], "OpenAI", "confirm")


if __name__ == "__main__":
    unittest.main()
