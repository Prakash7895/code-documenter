from dataclasses import dataclass
import re
import textwrap
from typing import List, Tuple
from openai import OpenAI
from core.types import Chunk
from core.utils import is_all_ok, strip_triple_backticks


@dataclass
class LLMConfig:
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.0
    max_tokens: int = 500
    system_prompt: str = "You are a concise, precise code documentation assistant."


class DocGenerator:
    def __init__(self, llm_client: OpenAI, config: LLMConfig = None):
        self.client = llm_client
        self.config = config

    def _build_context_text(
        self, related_chunks: List[Tuple[Chunk, float]], max_chars=3000
    ) -> str:
        parts = []
        for chunk, score in related_chunks:
            header = f"### {chunk.name or '<anon>'} - {chunk.file} lines {chunk.start}-{chunk.end} (score={score:.4f})"

            code = chunk.code
            if len(code) > 1500:
                head = code[:750]
                tail = code[-700:]
                code = head + "\n\n# ...TRUNCATED...\n\n" + tail
            parts.append(header + "\n```" + code + "\n```")

            if sum(len(p) for p in parts) > max_chars:
                break
        return "\n\n".join(parts)

    def _build_prompt(self, chunk: Chunk, related_context: str) -> List[dict]:
        instruction = f"""
        You will create a focused, accurate Markdown documentation entry for a single function or class.
        Output MUST be valid Markdown without extra commentary.
        """

        user_section = textwrap.dedent(
            f"""
                Target chunk:
                - file: {chunk.file}
                - function/class name: {chunk.name or '<anon>'}
                - lines: {chunk.start}-{chunk.end}

                Code:
                ```{chunk.lang}
                {chunk.code}
                ```

                Related context (other functions/classes that may help):
                {related_context}

                Task (produce Markdown):
                1) One-line summary.
                2) Longer description (2-4 short paragraphs).
                3) Parameters: list each param and describe expected type/meaning if inferable.
                4) Return value(s): describe what is returned and possible edge conditions.
                5) Side effects / exceptions / important notes.
                6) Small usage example (short code block).
                7) If you are uncertain about types or behavior, say so explicitly and mark uncertain lines.

                Strict requirements:
                - Return ONLY Markdown content (no JSON, no analysis).
                - Do NOT wrap the full output in ``` or ```markdown fences — return plain Markdown text.
                - Keep output length under ~{self.config.max_tokens * 4} tokens.
            """
        )

        # messages for chat API
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": instruction.strip()},
            {"role": "user", "content": user_section.strip()},
        ]
        return messages

    def generate_function_md(
        self,
        chunk: Chunk,
        related_chunks: List[Tuple[Chunk, float]],
        validate: bool = True,
    ) -> str:
        context_text = self._build_context_text(related_chunks)

        messages = self._build_prompt(chunk, context_text)

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        raw_md = response.choices[0].message.content.strip()
        md = strip_triple_backticks(raw_md)

        if validate:
            validation_prompt = (
                "Validate the Markdown you just produced against the code. "
                "List any lines or symbols in the code you could not confidently explain, "
                "or reply only 'ALL_OK' if everything is consistent. "
                "Return plain text (do not wrap in ``` blocks)."
            )
            val_msgs = [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": validation_prompt},
                {
                    "role": "user",
                    "content": "Code:\n```\n"
                    + chunk.code
                    + "\n```\n\nGenerated doc:\n"
                    + md,
                },
            ]
            val_resp = self.client.chat.completions.create(
                model=self.config.model,
                messages=val_msgs,
                temperature=0.0,
                max_tokens=150,
            )
            raw_val = val_resp.choices[0].message.content.strip()
            val_text = strip_triple_backticks(raw_val)
            # if validation flagged issues, append a short note at the bottom of md
            if not is_all_ok(val_text):
                cleaned = re.sub(
                    r"^\s*Validation\s*result\s*:\s*", "", val_text, flags=re.I
                ).strip()
                md = (
                    md
                    + "\n\n> **SELF-CHECK:** The generator found possible issues:\n\n"
                    + cleaned
                )

        return md
