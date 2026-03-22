from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI
from loguru import logger

from src.config import AppConfig, get_api_key
from src.advisor.prompt_builder import load_system_prompt, build_user_prompt
from src.parser.game_state import GameState


class AdvisorEngine:
    """LLM-powered duel advisor."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._client: OpenAI | None = None
        self._system_prompt = load_system_prompt()

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if self.config.llm.provider == "deepseek":
                cfg = self.config.llm.deepseek
                self._client = OpenAI(
                    api_key=get_api_key(),
                    base_url=cfg.base_url,
                )
            else:
                cfg = self.config.llm.ollama
                self._client = OpenAI(
                    api_key="ollama",
                    base_url=f"{cfg.base_url}/v1",
                )
        return self._client

    def get_advice(
        self,
        state: GameState,
        deck_text: str = "",
        card_effects: list[str] | None = None,
        hand_analysis: str = "",
        history: str = "",
    ) -> dict | None:
        """Get AI advice for current game state."""
        user_prompt = build_user_prompt(state, deck_text, card_effects, hand_analysis, history)
        client = self._get_client()

        # Debug: log prompt to file for inspection
        try:
            debug_path = Path(__file__).parent.parent.parent / "data" / "debug" / "last_prompt.txt"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(
                f"=== SYSTEM PROMPT ===\n{self._system_prompt}\n\n=== USER PROMPT ===\n{user_prompt}",
                encoding="utf-8",
            )
            logger.debug(f"Prompt saved to {debug_path} ({len(user_prompt)} chars)")
        except Exception:
            pass

        if self.config.llm.provider == "deepseek":
            model = self.config.llm.deepseek.model
            max_tokens = self.config.llm.deepseek.max_tokens
            temperature = self.config.llm.deepseek.temperature
        else:
            model = self.config.llm.ollama.model
            max_tokens = 500
            temperature = 0.3

        content = ""
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {content}")
            return {
                "priority_action": content,
                "action_steps": [],
                "warnings": ["AI 回應格式異常"],
                "win_assessment": "無法判斷",
            }
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    def get_advice_stream(
        self,
        state: GameState,
        deck_text: str = "",
        card_effects: list[str] | None = None,
        hand_analysis: str = "",
        history: str = "",
    ):
        """Stream AI advice (yields partial text)."""
        user_prompt = build_user_prompt(state, deck_text, card_effects, history)
        client = self._get_client()

        if self.config.llm.provider == "deepseek":
            model = self.config.llm.deepseek.model
            max_tokens = self.config.llm.deepseek.max_tokens
            temperature = self.config.llm.deepseek.temperature
        else:
            model = self.config.llm.ollama.model
            max_tokens = 500
            temperature = 0.3

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            full_text = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_text += text
                    yield text
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield f"[Error: {e}]"
