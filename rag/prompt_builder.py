"""Prompt templates for all mentor response modes."""

from __future__ import annotations

from enum import Enum
from typing import Any

from rag.retriever import RetrievedChunk


class ResponseMode(str, Enum):
    HINT = "hint"
    EXPLAIN = "explain"
    COMPLEXITY = "complexity"
    SIMILAR = "similar"
    PATTERN = "pattern"
    BRUTEFORCE = "bruteforce"
    OPTIMAL = "optimal"
    MISTAKE = "mistake"
    STUCK = "stuck"
    INTERVIEW = "interview"
    THINK = "think"
    CHECK = "check"
    EDGE = "edge"
    DRYRUN = "dryrun"
    MYSTRATEGY = "mystrategy"
    NEET = "neet"
    COMPARE = "compare"
    RECALL = "recall"
    ROAST = "roast"
    ELI5 = "eli5"
    COMPANY = "company"
    VISUAL = "visual"


MODE_HEADERS: dict[str, str] = {
    "hint": "Hint",
    "explain": "Explanation",
    "complexity": "Complexity",
    "similar": "Similar Problems",
    "pattern": "Pattern",
    "bruteforce": "Brute Force",
    "optimal": "Optimal Approach",
    "mistake": "Common Mistakes",
    "stuck": "Stuck Helper",
    "interview": "Interview Mode",
    "think": "Think Aloud",
    "check": "Code Review",
    "edge": "Edge Cases",
    "dryrun": "Dry Run",
    "mystrategy": "Your Strategy",
    "neet": "NeetCode View",
    "compare": "Compare Approaches",
    "recall": "Quick Recall",
    "roast": "Friendly Roast",
    "eli5": "ELI5",
    "company": "Interview Lens",
    "visual": "Visual Flow",
}


SYSTEM_PROMPT = """You are LeetCode Mentor, an expert coding tutor.
You help users learn DSA concepts without doing their homework for them.
Be concise, accurate, and encouraging. Use code examples only when helpful.
Never reveal full solutions in hint or think modes unless explicitly asked."""


MODE_INSTRUCTIONS: dict[ResponseMode, str] = {
    ResponseMode.HINT: (
        "Give a helpful nudge toward the solution. Mention the key insight or pattern "
        "but do NOT write the full solution or complete code. Max 150 words."
    ),
    ResponseMode.EXPLAIN: (
        "Provide a clear step-by-step walkthrough. Cover approach, algorithm, and a "
        "concise code outline in the user's preferred language. Max 400 words."
    ),
    ResponseMode.COMPLEXITY: (
        "Analyze time and space complexity of the optimal approach with trade-offs. Max 200 words."
    ),
    ResponseMode.SIMILAR: (
        "Suggest 3-5 related LeetCode problems with difficulty and why each helps. Max 250 words."
    ),
    ResponseMode.PATTERN: (
        "Name and explain ONLY the DSA pattern (e.g. sliding window, two pointers). "
        "Do NOT give the full solution. Max 120 words."
    ),
    ResponseMode.BRUTEFORCE: (
        "Explain the brute force approach first, then briefly mention why we can do better. Max 250 words."
    ),
    ResponseMode.OPTIMAL: (
        "Explain only the optimal approach and why it works. Include brief code outline. Max 300 words."
    ),
    ResponseMode.MISTAKE: (
        "List 4-6 common mistakes learners make on this problem and how to avoid them. Max 200 words."
    ),
    ResponseMode.STUCK: (
        "The user is stuck. Use conversation context. Give ONE small nudge and ONE guiding question. "
        "Do not reveal the full answer. Max 120 words."
    ),
    ResponseMode.INTERVIEW: (
        "Act as an interviewer. Ask 2-3 probing questions, give minimal hints, evaluate thinking. Max 250 words."
    ),
    ResponseMode.THINK: (
        "Ask 3-5 guiding questions only. Do NOT provide answers or code. Max 150 words."
    ),
    ResponseMode.CHECK: (
        "Review the user's code or approach in the user message. Point out bugs, complexity, and improvements. "
        "Be constructive. Max 300 words."
    ),
    ResponseMode.EDGE: (
        "List important edge cases and 3-5 concrete test cases with expected outcomes. Max 250 words."
    ),
    ResponseMode.DRYRUN: (
        "Pick a concrete example input and trace the optimal algorithm step by step. Max 300 words."
    ),
    ResponseMode.MYSTRATEGY: (
        "Answer using the user's personal strategy notes from context when available. Max 250 words."
    ),
    ResponseMode.NEET: (
        "Explain in the style of a NeetCode walkthrough using transcript context. Max 300 words."
    ),
    ResponseMode.COMPARE: (
        "Compare the user's strategy (from context) vs the optimal approach. Highlight gaps and wins. Max 300 words."
    ),
    ResponseMode.RECALL: (
        "Help the user quickly revise this problem: key idea, pattern, complexity, one-liner reminder. Max 200 words."
    ),
    ResponseMode.ROAST: (
        "Playfully roast a naive or wrong approach, then give a constructive fix. Keep it friendly. Max 200 words."
    ),
    ResponseMode.ELI5: (
        "Explain the problem like the user is five years old. No jargon. Max 180 words."
    ),
    ResponseMode.COMPANY: (
        "Explain how this problem might be asked in a top tech interview and what interviewers look for. Max 220 words."
    ),
    ResponseMode.VISUAL: (
        "Explain using a simple ASCII diagram or flow. Keep text clear and structured. Max 280 words."
    ),
}


class PromptBuilder:
    def build(
        self,
        mode: ResponseMode,
        problem_title: str,
        problem_slug: str,
        context_chunks: list[RetrievedChunk],
        user_message: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        user_prefs: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        context = self._format_context(context_chunks)
        instruction = MODE_INSTRUCTIONS[mode]
        prefs = user_prefs or {}
        lang = prefs.get("language", "python")
        level = prefs.get("level", "intermediate")

        user_prompt = f"""Problem: {problem_title} (slug: {problem_slug})
User skill level: {level}
Preferred code language: {lang}

Retrieved context:
{context}

User request: {user_message or f'Provide a {mode.value} for this problem.'}

Instructions: {instruction}"""

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "(No retrieved context — answer from general DSA knowledge.)"
        parts: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source", "unknown")
            title = chunk.metadata.get("title", "")
            parts.append(f"[{i}] ({source}) {title} [score={chunk.score}]\n{chunk.text}")
        return "\n\n---\n\n".join(parts)
