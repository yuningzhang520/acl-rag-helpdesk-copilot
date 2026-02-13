"""
Self-check tests for run.py GitHub comment parsing (stdlib only).
Run from repo root: python scripts/self_check.py  or  python -m unittest scripts.self_check
"""
import unittest
import sys
from pathlib import Path

# Ensure repo root on path when run as script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.run import (
    _parse_proposed_plan_struct_from_comment,
    _find_latest_proposed_plan_and_approve,
    _plan_title,
    normalize_issue_text,
    _citations_from_intermediate,
    _validate_intermediate_v2,
)


class TestParseProposedPlanStruct(unittest.TestCase):
    """Validate _parse_proposed_plan_struct_from_comment against fenced block variants."""

    def _body(self, fence: str, json_content: str) -> str:
        prefix = "### Proposed actions (struct)\n\n"
        return prefix + fence + "\n" + json_content + "\n```"

    def test_json_lowercase(self) -> None:
        body = self._body(
            "```json",
            '{"risk_level": "L2", "needs_approval": true, "approval_role_required": "IT Admin", "labels_to_add": ["cat:Access", "status:pending-approval"]}',
        )
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNotNone(out)
        self.assertIsInstance(out, dict)
        self.assertTrue(out.get("needs_approval"))
        self.assertEqual(out.get("labels_to_add"), ["cat:Access", "status:pending-approval"])

    def test_json_uppercase(self) -> None:
        body = self._body(
            "```JSON",
            '{"risk_level": "L1", "needs_approval": false, "approval_role_required": "N/A", "labels_to_add": ["cat:VPN", "status:triaged"]}',
        )
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNotNone(out)
        self.assertIsInstance(out, dict)
        self.assertFalse(out.get("needs_approval"))
        self.assertEqual(out.get("labels_to_add"), ["cat:VPN", "status:triaged"])

    def test_plain_fence(self) -> None:
        body = self._body(
            "```",
            '{"risk_level": "L2", "needs_approval": true, "approval_role_required": "IT Admin", "labels_to_add": ["prio:High"]}',
        )
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNotNone(out)
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("labels_to_add"), ["prio:High"])

    def test_heading_with_colon(self) -> None:
        body = "### Proposed actions (struct):\n\n```json\n{\"risk_level\": \"L1\", \"needs_approval\": false, \"approval_role_required\": \"N/A\", \"labels_to_add\": [\"cat:Other\"]}\n```"
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNotNone(out)
        self.assertEqual(out.get("labels_to_add"), ["cat:Other"])

    def test_missing_required_keys_returns_none(self) -> None:
        body = "### Proposed actions (struct)\n\n```json\n{}\n```"
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNone(out)

    def test_no_heading_returns_none(self) -> None:
        body = "```json\n{\"risk_level\": \"L1\", \"needs_approval\": true, \"approval_role_required\": null, \"labels_to_add\": [\"x\"]}\n```"
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNone(out)

    def test_struct_inside_details_block_parses(self) -> None:
        """Parsing still works when verbose sections are in a <details> collapsible."""
        body = (
            "## Proposed Plan (TRIAGED)\n\nShort summary.\n\n"
            "<details><summary>Details (evidence + struct)</summary>\n\n"
            "### Intermediate (evidence summary)\n\n```json\n{}\n```\n\n"
            "### Proposed actions (struct)\n\n```json\n"
            '{"risk_level": "L1", "needs_approval": false, "approval_role_required": "N/A", "labels_to_add": ["status:triaged"]}'
            "\n```\n\n</details>\n"
        )
        out = _parse_proposed_plan_struct_from_comment(body)
        self.assertIsNotNone(out)
        self.assertFalse(out.get("needs_approval"))
        self.assertEqual(out.get("labels_to_add"), ["status:triaged"])


class TestFindLatestProposedPlanAndApprove(unittest.TestCase):
    """Validate _find_latest_proposed_plan_and_approve finds latest plan then latest APPROVE after it."""

    def test_finds_latest_plan_and_approve_after_it(self) -> None:
        comments = [
            {"body": "Proposed Plan (PENDING APPROVAL)\n\n### Proposed actions (struct)\n```json\n{\"risk_level\": \"L2\", \"needs_approval\": true, \"approval_role_required\": \"IT Admin\", \"labels_to_add\": [\"cat:A\"]}\n```", "login": "bot"},
            {"body": "APPROVE", "login": "alice"},
            {"body": "Proposed Plan (TRIAGED)\n\n### Proposed actions (struct)\n```json\n{\"risk_level\": \"L1\", \"needs_approval\": false, \"approval_role_required\": \"N/A\", \"labels_to_add\": [\"cat:B\"]}\n```", "login": "bot"},
            {"body": "APPROVE", "login": "bob"},
        ]
        plan_comment, parsed_struct, approve_comment = _find_latest_proposed_plan_and_approve(comments)
        self.assertIsNotNone(plan_comment)
        self.assertIn("Proposed Plan (TRIAGED)", plan_comment.get("body", ""))
        self.assertIsNotNone(parsed_struct)
        self.assertEqual(parsed_struct.get("labels_to_add"), ["cat:B"])
        self.assertIsNotNone(approve_comment)
        self.assertEqual(approve_comment.get("login"), "bob")
        self.assertEqual(approve_comment.get("body").strip(), "APPROVE")

    def test_no_plan_returns_none_triple(self) -> None:
        comments = [{"body": "APPROVE", "login": "alice"}]
        plan_comment, parsed_struct, approve_comment = _find_latest_proposed_plan_and_approve(comments)
        self.assertIsNone(plan_comment)
        self.assertIsNone(parsed_struct)
        self.assertIsNone(approve_comment)

    def test_plan_but_no_approve_after(self) -> None:
        comments = [
            {"body": "APPROVE", "login": "alice"},
            {"body": "Proposed Plan (PENDING APPROVAL)\n\n### Proposed actions (struct)\n```json\n{\"risk_level\": \"L2\", \"needs_approval\": true, \"approval_role_required\": \"IT Admin\", \"labels_to_add\": [\"status:pending-approval\"]}\n```", "login": "bot"},
        ]
        plan_comment, parsed_struct, approve_comment = _find_latest_proposed_plan_and_approve(comments)
        self.assertIsNotNone(plan_comment)
        self.assertIsNotNone(parsed_struct)
        self.assertIsNone(approve_comment)


class TestPlanTitle(unittest.TestCase):
    """Plan comment title reflects needs_approval."""

    def test_plan_title_pending_when_needs_approval(self) -> None:
        self.assertEqual(_plan_title(True), "Proposed Plan (PENDING APPROVAL)")

    def test_plan_title_triaged_when_no_approval(self) -> None:
        self.assertEqual(_plan_title(False), "Proposed Plan (TRIAGED)")


class TestNormalizeIssueText(unittest.TestCase):
    """Minimal check: Issue Form body keeps System/App + Description, drops Incident Timestamp."""

    def test_issue_form_keeps_retrieval_sections_drops_timestamp(self) -> None:
        body = (
            "[IT] VPN keeps disconnecting\n\n"
            "### Request Type\nVPN\n\n"
            "### Urgency\nMedium\n\n"
            "### Impact scope\nOnly me\n\n"
            "### System / App\nCisco AnyConnect\n\n"
            "### Description\nCannot stay connected for more than 5 minutes.\n\n"
            "### Incident/Request Timestamp\n2026-01-27 14:00\n\n"
            "### Needed by / Target Resolution Date\n2026-01-30"
        )
        out = normalize_issue_text(body, "github_issue")
        self.assertIn("System / App", out)
        self.assertIn("Cisco AnyConnect", out)
        self.assertIn("Description", out)
        self.assertIn("Cannot stay connected", out)
        self.assertNotIn("Incident/Request Timestamp", out)
        self.assertNotIn("2026-01-27 14:00", out)


class TestCitationsFromIntermediate(unittest.TestCase):
    """Citations are built from evidence_bullets only, not summary_steps."""

    def test_citations_from_evidence_bullets_only(self) -> None:
        intermediate = {
            "summary_steps": [
                {"step": "Verify VPN", "rationale": "From S1 and S2", "source_ids": ["S1", "S2"]},
            ],
            "evidence_bullets": [
                {"text": "Check VPN settings.", "source_id": "S1"},
                {"text": "Restart client.", "source_id": "S2"},
            ],
            "clarifying_question": "",
            "confidence_level": "Medium",
            "confidence_reason": "test",
        }
        retrieved = [
            {"doc_path": "/docs/a.md", "heading": "A", "anchor": "#a", "tier": "public"},
            {"doc_path": "/docs/b.md", "heading": "B", "anchor": "#b", "tier": "internal"},
        ]
        out = _citations_from_intermediate(intermediate, retrieved)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["doc"], "/docs/a.md")
        self.assertEqual(out[1]["doc"], "/docs/b.md")

    def test_citations_ignore_summary_steps_source_ids(self) -> None:
        """Only evidence_bullets order/source_ids drive citations; summary_steps.S3 should not appear."""
        intermediate = {
            "summary_steps": [{"step": "X", "rationale": "Y", "source_ids": ["S3"]}],
            "evidence_bullets": [
                {"text": "From S1.", "source_id": "S1"},
                {"text": "From S2.", "source_id": "S2"},
            ],
            "clarifying_question": "",
            "confidence_level": "Low",
            "confidence_reason": "test",
        }
        retrieved = [
            {"doc_path": "/docs/1.md", "heading": "One", "anchor": "#one", "tier": "public"},
            {"doc_path": "/docs/2.md", "heading": "Two", "anchor": "#two", "tier": "public"},
            {"doc_path": "/docs/3.md", "heading": "Three", "anchor": "#three", "tier": "public"},
        ]
        out = _citations_from_intermediate(intermediate, retrieved)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["doc"], "/docs/1.md")
        self.assertEqual(out[1]["doc"], "/docs/2.md")


class TestValidateIntermediateV2(unittest.TestCase):
    """V2 validator rejects missing/empty step, rationale, source_ids."""

    def test_rejects_empty_step(self) -> None:
        source_map = {"S1": {"doc_name": "a.md", "anchor": "#a", "heading": "A"}}
        obj = {
            "summary_steps": [
                {"step": "", "rationale": "r", "source_ids": ["S1"]},
                {"step": "s2", "rationale": "r2", "source_ids": ["S1"]},
            ],
            "evidence_bullets": [{"text": "t1", "source_id": "S1"}, {"text": "t2", "source_id": "S1"}],
            "clarifying_question": "",
            "confidence_level": "Medium",
            "confidence_reason": "x",
        }
        ok, reason = _validate_intermediate_v2(obj, source_map)
        self.assertFalse(ok)
        self.assertIn("step", reason)

    def test_rejects_empty_rationale(self) -> None:
        source_map = {"S1": {"doc_name": "a.md", "anchor": "#a", "heading": "A"}}
        obj = {
            "summary_steps": [
                {"step": "s1", "rationale": "", "source_ids": ["S1"]},
                {"step": "s2", "rationale": "r2", "source_ids": ["S1"]},
            ],
            "evidence_bullets": [{"text": "t1", "source_id": "S1"}, {"text": "t2", "source_id": "S1"}],
            "clarifying_question": "",
            "confidence_level": "Medium",
            "confidence_reason": "x",
        }
        ok, reason = _validate_intermediate_v2(obj, source_map)
        self.assertFalse(ok)
        self.assertIn("rationale", reason)

    def test_allows_empty_source_ids_when_sources_exist(self) -> None:
        """Empty source_ids in summary_steps is allowed when step starts with a known verb."""
        source_map = {"S1": {"doc_name": "a.md", "anchor": "#a", "heading": "A"}}
        obj = {
            "summary_steps": [
                {"step": "Verify the connection.", "rationale": "r1", "source_ids": []},
                {"step": "s2", "rationale": "r2", "source_ids": ["S1"]},
            ],
            "evidence_bullets": [{"text": "t1", "source_id": "S1"}, {"text": "t2", "source_id": "S1"}],
            "clarifying_question": "",
            "confidence_level": "Medium",
            "confidence_reason": "x",
        }
        ok, reason = _validate_intermediate_v2(obj, source_map)
        self.assertTrue(ok, reason)

if __name__ == "__main__":
    unittest.main()
