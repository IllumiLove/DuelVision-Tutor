from __future__ import annotations

import re

import numpy as np
from loguru import logger

from src.parser.game_state import GameState, FieldCard
from src.parser.ocr_engine import OCREngine
from src.parser.regions import OCR_REGIONS, scale_regions


class StateParser:
    """Parse game screenshots into structured GameState."""

    def __init__(self, ocr_engine: OCREngine, card_matcher=None):
        self.ocr = ocr_engine
        self.card_matcher = card_matcher
        self._turn_count = 0

    def parse(self, frame: np.ndarray, window_size: tuple[int, int] | None = None) -> GameState:
        """Parse a full game screenshot into GameState."""
        h, w = frame.shape[:2]
        if window_size:
            actual_w, actual_h = window_size
        else:
            actual_w, actual_h = w, h

        regions = scale_regions(OCR_REGIONS, actual_w, actual_h)
        state = GameState()

        # Parse LP
        my_lp = self.ocr.recognize_number(frame, regions["my_lp"])
        if my_lp is not None:
            state.my_lp = my_lp
            logger.debug(f"OCR my_lp: {my_lp}")

        opp_lp = self.ocr.recognize_number(frame, regions["opp_lp"])
        if opp_lp is not None:
            state.opp_lp = opp_lp
            logger.debug(f"OCR opp_lp: {opp_lp}")

        # Parse phase
        if "phase" in regions:
            phase_texts = self.ocr.recognize_region(frame, regions["phase"], preprocess=False)
            phase_str = " ".join(t for t, c in phase_texts if c > 0.3)
            state.phase = self._parse_phase(phase_str)
            state.turn_count = self._parse_turn(phase_str)
            logger.debug(f"OCR phase raw: '{phase_str}' -> {state.phase}, turn {state.turn_count}")

        # Parse hand cards (raw image gives better results than preprocessed)
        hand_texts = self.ocr.recognize_region(frame, regions["my_hand"], preprocess=False)
        raw_hand = [t for t, c in hand_texts if c > 0.3]
        logger.debug(f"OCR hand raw: {raw_hand}")
        state.my_hand = self._match_card_names(raw_hand)

        # Parse field
        my_monster_texts = self.ocr.recognize_region(frame, regions["my_monsters"], preprocess=False)
        logger.debug(f"OCR my_monsters raw: {[(t, f'{c:.2f}') for t, c in my_monster_texts]}")
        state.my_field = self._parse_field_cards(my_monster_texts, "MONSTER")

        opp_monster_texts = self.ocr.recognize_region(frame, regions["opp_monsters"], preprocess=False)
        logger.debug(f"OCR opp_monsters raw: {[(t, f'{c:.2f}') for t, c in opp_monster_texts]}")
        state.opp_field = self._parse_field_cards(opp_monster_texts, "MONSTER")

        # Determine turn player based on phase visibility
        if state.phase != "UNKNOWN":
            state.turn_player = "self"

        logger.info(
            f"State: LP={state.my_lp}/{state.opp_lp}, phase={state.phase}, "
            f"turn={state.turn_count}, hand={len(state.my_hand)}, "
            f"field={len(state.my_field)}/{len(state.opp_field)}, "
            f"hand_cards={state.my_hand[:3]}{'...' if len(state.my_hand) > 3 else ''}"
        )
        return state

    def _match_card_names(self, raw_texts: list[str]) -> list[str]:
        """Match OCR texts to card database names."""
        if not self.card_matcher:
            return raw_texts
        matched = []
        for text in raw_texts:
            result = self.card_matcher(text)
            matched.append(result if result else text)
        return matched

    def _parse_field_cards(self, texts: list[tuple[str, float]], zone_type: str) -> list[FieldCard]:
        """Parse field card info from OCR results."""
        cards = []
        for i, (text, conf) in enumerate(texts):
            if conf < 0.4:
                continue
            card = FieldCard(name=text, zone=f"{zone_type}_{i + 1}")
            self._extract_stats(card, text)
            cards.append(card)
        return cards

    @staticmethod
    def _extract_stats(card: FieldCard, text: str):
        """Try to extract ATK/DEF values from OCR text."""
        atk_match = re.search(r"ATK[:\s]*(\d+)", text, re.IGNORECASE)
        if atk_match:
            card.atk = int(atk_match.group(1))
        def_match = re.search(r"DEF[:\s]*(\d+)", text, re.IGNORECASE)
        if def_match:
            card.def_ = int(def_match.group(1))

    @staticmethod
    def _parse_phase(text: str) -> str:
        """Parse phase from OCR text like 'Turn 1 Main1'."""
        text_lower = text.lower()
        if "main1" in text_lower or "main 1" in text_lower:
            return "MAIN1"
        if "main2" in text_lower or "main 2" in text_lower:
            return "MAIN2"
        if "battle" in text_lower:
            return "BATTLE"
        if "draw" in text_lower:
            return "DRAW"
        if "standby" in text_lower:
            return "STANDBY"
        if "end" in text_lower:
            return "END"
        if "main" in text_lower:
            return "MAIN1"
        return "UNKNOWN"

    @staticmethod
    def _parse_turn(text: str) -> int:
        """Extract turn number from OCR text."""
        match = re.search(r"turn\s*(\d+)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0

    def increment_turn(self):
        self._turn_count += 1
