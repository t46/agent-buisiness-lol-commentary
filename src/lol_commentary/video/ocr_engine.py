from __future__ import annotations
import logging
import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR engine specialized for LoL spectator mode HUD elements."""

    @staticmethod
    def preprocess(image: np.ndarray, invert: bool = True) -> np.ndarray:
        """Standard preprocessing: grayscale -> resize -> binarize -> denoise."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Upscale for better OCR accuracy
        h, w = gray.shape[:2]
        if h < 50:
            scale = 50 / h
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Binarize
        if invert:
            gray = cv2.bitwise_not(gray)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Denoise
        binary = cv2.medianBlur(binary, 3)

        return binary

    def read_timer(self, image: np.ndarray) -> str | None:
        """Read game timer from HUD region.

        Expected format: MM:SS or M:SS
        """
        processed = self.preprocess(image)
        pil_image = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_image,
            config="--psm 7 -c tessedit_char_whitelist=0123456789:",
        ).strip()

        # Validate timer format
        if re.match(r'^\d{1,2}:\d{2}$', text):
            return text
        return None

    def read_player_name(self, image: np.ndarray) -> str | None:
        """Read a player name from HUD region."""
        processed = self.preprocess(image)
        pil_image = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_image,
            config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_ ",
        ).strip()

        if len(text) >= 2:
            return text
        return None

    def read_score(self, image: np.ndarray) -> int | None:
        """Read a numeric score (kills count, etc.)."""
        processed = self.preprocess(image)
        pil_image = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_image,
            config="--psm 7 -c tessedit_char_whitelist=0123456789",
        ).strip()

        try:
            return int(text)
        except ValueError:
            return None

    def read_kda(self, image: np.ndarray) -> tuple[int, int, int] | None:
        """Read KDA from HUD (format: K/D/A)."""
        processed = self.preprocess(image)
        pil_image = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_image,
            config="--psm 7 -c tessedit_char_whitelist=0123456789/",
        ).strip()

        match = re.match(r'(\d+)/(\d+)/(\d+)', text)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return None

    def extract_all_player_names(
        self,
        blue_name_images: list[np.ndarray],
        red_name_images: list[np.ndarray],
    ) -> dict[str, list[str]]:
        """Extract all player names from scoreboard regions."""
        blue_names = []
        for img in blue_name_images:
            name = self.read_player_name(img)
            if name:
                blue_names.append(name)

        red_names = []
        for img in red_name_images:
            name = self.read_player_name(img)
            if name:
                red_names.append(name)

        return {"blue": blue_names, "red": red_names}
