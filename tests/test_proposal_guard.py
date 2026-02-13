"""
Tests for proposal comment_summary validation and normalize_issue_text (Urgency kept, timestamps dropped).
Run from repo root: python -m pytest tests/test_proposal_guard.py -v  or  python -m unittest tests.test_proposal_guard
"""
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.run import validate_comment_summary, normalize_issue_text, triage_issue, answer_from_intermediate


class TestValidateCommentSummary(unittest.TestCase):
    """Proposal comment_summary must not introduce user IDs, quoted names, durations, or entities not in issue."""

    def test_rejects_user_id_not_in_issue(self) -> None:
        """When proposal includes 'u001' but issue_text_normalized does NOT, validation rejects."""
        issue = "Need access to the shared drive for my team."
        proposal = "User u001 needs Viewer access to the folder."
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertFalse(ok)
        self.assertIn("user_id", reason)

    def test_allows_user_id_when_in_issue(self) -> None:
        """When issue contains u001, proposal may mention it."""
        issue = "User u001 requested Viewer access to Q1 Budget."
        proposal = "Proposed: Grant u001 Viewer access to Q1 Budget."
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertTrue(ok, reason)

    def test_allows_quoted_and_duration_when_in_issue(self) -> None:
        """When issue_text_normalized includes \"Q1 Budget\" and '30 days', proposal may include them (double-quoted allow)."""
        issue = 'Request: Read access to "Q1 Budget" folder for 30 days.'
        proposal = 'Proposed: Grant access to "Q1 Budget" for 30 days with justification.'
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertTrue(ok, reason)

    def test_rejects_quoted_entity_not_in_issue(self) -> None:
        """Proposal must not introduce quoted folder/resource names not in issue."""
        issue = "Need access to a shared folder."
        proposal = 'Proposed: Grant access to "Q1 Budget" folder.'
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertFalse(ok)
        self.assertIn("quoted", reason)

    def test_rejects_single_quoted_entity_not_in_issue(self) -> None:
        """Proposal must not introduce single-quoted entities not in issue (same guard as double quotes)."""
        issue = "Need access to a shared folder."
        proposal = "Proposed: Grant access to 'Q1 Budget' folder."
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertFalse(ok)
        self.assertIn("quoted", reason)

    def test_rejects_duration_not_in_issue(self) -> None:
        """Proposal must not introduce duration (e.g. 30 days) not in issue."""
        issue = "Need access to the shared drive."
        proposal = "Proposed: Grant access for 30 days."
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertFalse(ok)
        self.assertIn("duration", reason)

    def test_rejects_too_long(self) -> None:
        """comment_summary over 200 chars is rejected."""
        issue = "Need access."
        proposal = "A" * 201
        ok, reason = validate_comment_summary(proposal, issue)
        self.assertFalse(ok)
        self.assertIn("too_long", reason)


class TestAnswerFromIntermediateStepCitations(unittest.TestCase):
    """answer_from_intermediate appends step-level citations from source_map when source_ids present."""

    def test_step_line_includes_citation_suffix_from_source_ids(self) -> None:
        intermediate = {
            "summary_steps": [
                {"step": "Verify VPN settings.", "rationale": "Recommended by runbook.", "source_ids": ["S1", "S2"]},
                {"step": "Restart client.", "rationale": "If still failing.", "source_ids": []},
            ],
            "clarifying_question": "",
            "confidence_level": "Medium",
            "confidence_reason": "test",
        }
        source_map = {
            "S1": {"doc_name": "rb-001-vpn.md", "anchor": "#common-issues", "heading": "Common Issues", "tier": "public"},
            "S2": {"doc_name": "rb-002-mfa.md", "anchor": "#troubleshoot", "heading": "Troubleshooting", "tier": "internal"},
        }
        answer_text, _ = answer_from_intermediate(intermediate, source_map=source_map)
        self.assertIn("(public:rb-001-vpn.md#common-issues, internal:rb-002-mfa.md#troubleshoot)", answer_text)
        self.assertIn("Verify VPN settings.", answer_text)
        self.assertIn("Restart client.", answer_text)
        self.assertNotIn("Restart client. (", answer_text)

    def test_step_without_source_ids_has_no_citation_suffix(self) -> None:
        intermediate = {
            "summary_steps": [
                {"step": "Escalate to IT.", "rationale": "No runbook match.", "source_ids": []},
            ],
            "clarifying_question": "",
            "confidence_level": "Low",
            "confidence_reason": "test",
        }
        source_map = {"S1": {"doc_name": "rb-001.md", "anchor": "#x", "heading": "X", "tier": "restricted"}}
        answer_text, _ = answer_from_intermediate(intermediate, source_map=source_map)
        self.assertIn("Escalate to IT.", answer_text)
        self.assertNotIn("(restricted:rb-001.md#x)", answer_text)


class TestNormalizeIssueTextUrgencyAndTimestamps(unittest.TestCase):
    """normalize_issue_text keeps Urgency section and drops Incident/Request Timestamp and Needed by."""

    def test_keeps_urgency_section(self) -> None:
        body = (
            "[IT] Access request\n\n"
            "### Request Type\nAccess\n\n"
            "### Urgency\nMedium\n\n"
            "### Description\nNeed access to shared drive.\n\n"
            "### Incident/Request Timestamp\n2026-01-27 14:00\n\n"
            "### Needed by / Target Resolution Date\n2026-01-30"
        )
        out = normalize_issue_text(body, "github_issue")
        self.assertIn("Urgency", out)
        self.assertIn("Medium", out)
        self.assertIn("Description", out)
        self.assertIn("Need access", out)

    def test_drops_incident_timestamp_and_needed_by(self) -> None:
        body = (
            "Title\n\n"
            "### Urgency\nHigh\n\n"
            "### Incident/Request Timestamp\n2026-01-27 14:00\n\n"
            "### Needed by / Target Resolution Date\n2026-01-30"
        )
        out = normalize_issue_text(body, "github_issue")
        self.assertNotIn("2026-01-27", out)
        self.assertNotIn("2026-01-30", out)
        self.assertNotIn("Incident/Request Timestamp", out)
        self.assertNotIn("Needed by", out)

    def test_urgency_content_preserved_for_triage(self) -> None:
        """Urgency value is kept so triage_issue can set priority from it."""
        body = (
            "Issue\n\n"
            "### Urgency\nMedium\n\n"
            "### Description\nVPN failed."
        )
        out = normalize_issue_text(body, "github_issue")
        self.assertIn("Medium", out)
        self.assertIn("Urgency", out)


class TestTriagePriorityFromUrgency(unittest.TestCase):
    """triage_issue(..., source='github_issue') uses explicit Urgency section for priority."""

    def test_priority_medium_when_urgency_medium_in_issue(self) -> None:
        """When normalized issue contains ### Urgency and Medium, triage priority is Medium."""
        body = (
            "Access request\n\n"
            "### Urgency\nMedium\n\n"
            "### Description\nNeed access to shared drive."
        )
        normalized = normalize_issue_text(body, "github_issue")
        triage = triage_issue(normalized, source="github_issue")
        self.assertEqual(triage.get("priority"), "Medium")

    def test_priority_low_without_urgency_section(self) -> None:
        """Without explicit Urgency section, priority falls back to keyword (Low if no match)."""
        body = "General question.\n\n### Description\nWhere is the policy doc?"
        normalized = normalize_issue_text(body, "github_issue")
        triage = triage_issue(normalized, source="github_issue")
        self.assertEqual(triage.get("priority"), "Low")


if __name__ == "__main__":
    unittest.main()
