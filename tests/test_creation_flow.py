"""Necessary approval/state checks and evidence reuse; never calls external services."""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import agent
import creation_flow as flow
from style_cards import get_preset
from test_agent import MockIMA, MockModel, PRODUCT


class CreationFlowTests(unittest.TestCase):
    def setUp(self):
        self.request = dict(product=PRODUCT, audience="职场办公人群", scenario="职场办公",
                            platform="门店朋友圈", goal="到店体验", requirements="")
        self.card = get_preset("专业可信")
        self.state = flow.confirm_style(flow.confirm_brief(self.request), self.request, self.card)

    def test_changes_to_request_and_style_require_confirmation(self):
        changed = {**self.request, "platform": "微信公众号"}
        with self.assertRaises(flow.FlowError):
            flow.check_style(self.state, changed, self.card)
        with self.assertRaises(flow.FlowError):
            flow.check_style(self.state, self.request, {**self.card, "tone": "口语化"})
        with self.assertRaises(flow.FlowError):
            flow.confirm_style(self.state, self.request, self.card, "少用感叹号", "新的参考文案", "old")

    def test_idea_never_composes_and_approved_final_reuses_reviewed_facts(self):
        with tempfile.TemporaryDirectory() as folder:
            picture = Path(folder) / "test.png"
            Image.new("RGB", (20, 14), "teal").save(picture)
            ima, model = MockIMA(picture), MockModel()
            model.draft["tags"] = []
            with patch("agent._ima", return_value=ima), patch("agent.LLMClient", return_value=model), patch(
                    "requests.sessions.Session.request", side_effect=AssertionError("No network")), patch.dict(
                    os.environ, {"LLM_API_KEY": "synthetic-key", "LLM_BASE_URL": "https://synthetic.example/v1"}):
                idea = agent.run_task(**self.request, phase="plan", style_card=self.card)
                self.assertEqual(idea["status"], "plan_ready", idea)
                self.assertEqual([p for p, _ in model.calls], ["extract", "fact_review"])
                state = flow.attach_idea(self.state, idea)
                self.assertNotIn("text", state["prepared"]["sources"][0])
                plan = idea["plan"]
                with self.assertRaises(flow.FlowError):
                    flow.generation_args(state, self.request, self.card, plan)
                state = flow.confirm_plan(state, self.request, self.card, plan)
                edited = {**plan, "angle": "改成简洁的门店邀请"}
                with self.assertRaises(flow.FlowError):
                    flow.generation_args(state, self.request, self.card, edited)
                kwargs = flow.generation_args(state, self.request, self.card, plan)
                result = agent.run_task(**self.request, **kwargs)
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual(len(ima.retrieve_calls), 1)
                compose = next(payload for stage, payload in model.calls if stage == "compose")
                self.assertEqual(compose["style_card"], self.card)
                self.assertEqual(compose["approved_plan"], plan)
                self.assertNotIn("reference", compose)
                self.assertTrue(Path(result["export_html"]).is_file())
                self.assertTrue(Path(result["export_bundle"]).is_file())

    def test_expired_plan_and_platform_failures_cannot_be_confirmed(self):
        plan = dict(angle="使用任务切入", outline="场景、依据、建议", images="I1主视觉", action="到店咨询", boundaries="按实际款式确认")
        state = deepcopy(self.state)
        state["prepared"] = dict(input_key=flow.request_key(self.request), style_key=state["style_key"], created_at=1)
        with self.assertRaises(flow.FlowError):
            flow.confirm_plan(state, self.request, self.card, plan)
        import time
        state["prepared"]["created_at"] = time.time()
        state = flow.confirm_plan(state, self.request, self.card, plan)
        state = flow.attach_final(state, dict(status="ready", copy_text="待改稿", checks={"platform_ready": False}))
        draft_confirmed = flow.confirm_final(state, self.request, self.card, plan)
        self.assertEqual(draft_confirmed["stage"], "final_confirmed")
        self.assertTrue(draft_confirmed["final_draft"])
        state["final_result"]["checks"]["platform_ready"] = True
        confirmed = flow.confirm_final(state, self.request, self.card, plan)
        self.assertEqual(confirmed["stage"], "final_confirmed")
        self.assertFalse(confirmed["final_draft"])


if __name__ == "__main__":
    unittest.main()
