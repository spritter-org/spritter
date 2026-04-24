from __future__ import annotations

import base64
import difflib
import logging
import re
from io import BytesIO
from typing import NamedTuple, Iterator

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class FuelTypeKeyword(NamedTuple):
    keyword: str
    confidence: float


class OcrCorrector:
    """Dynamically corrects OCR artifacts in fuel labels using fuzzy matching."""
    
    FUEL_TYPE_COMPONENTS = {
        "diesel", "super", "premium", "euro", "plus", "eco", "regular", "unleaded",
        "95", "98", "100", "motion", "x", "ultimate", "evolution", "advanced",
        "optimal", "max", "maxx", "v", "evo",
    }

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def extract_keywords(self, text: str) -> list[FuelTypeKeyword]:
        keywords: dict[str, float] = {}
        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", text) if 2 <= len(t) <= 20]
        
        for token in tokens:
            lower_token = token.lower()
            for component in self.FUEL_TYPE_COMPONENTS:
                if component in lower_token:
                    weight = 2.0 if lower_token == component else 1.0
                    keywords[token] = keywords.get(token, 0) + weight
                    break

        max_conf = max(keywords.values()) if keywords else 1.0
        return [
            FuelTypeKeyword(keyword=k, confidence=min(1.0, v / max_conf))
            for k, v in sorted(keywords.items(), key=lambda x: -x[1])
        ]

    def build_vocabulary(self, text: str) -> set[str]:
        keywords = self.extract_keywords(text)
        vocabulary: set[str] = {kw.keyword for kw in keywords}
        
        # Build n-grams from the actual text order to capture multi-word labels natively
        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", text) if len(t) >= 2]
        for i in range(len(tokens)):
            for j in range(i + 1, min(i + 4, len(tokens) + 1)):
                ngram = " ".join(tokens[i:j])
                ngram_lower = ngram.lower()
                if any(kw.keyword.lower() in ngram_lower for kw in keywords if kw.confidence >= 0.4):
                    vocabulary.add(ngram)
                    
        return vocabulary

    def has_artifacts(self, label: str) -> bool:
        if not label or not any(c.isalpha() for c in label):
            return False
            
        if any(d in label and l.lower() in label.lower() for d, l in [('1', 'I'), ('0', 'O'), ('5', 'S')]):
            return True
            
        transitions = sum(1 for i in range(1, len(label)) 
                         if label[i].isupper() != label[i-1].isupper() and label[i].isalpha() and label[i-1].isalpha())
        return transitions > 2

    def correct_map(self, price_map: dict[str, float], ocr_text: str) -> dict[str, float]:
        if not price_map:
            return price_map
            
        vocabulary = self.build_vocabulary(ocr_text)
        search_pool = vocabulary or self.FUEL_TYPE_COMPONENTS
        corrected_map = {}
        
        for label, price in price_map.items():
            label_norm = label.strip()
            best_match, best_ratio = label_norm, 0.0
            
            if self.has_artifacts(label_norm) and label_norm not in vocabulary:
                for candidate in search_pool:
                    ratio = difflib.SequenceMatcher(None, label_norm.lower(), candidate.lower()).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = candidate if ratio >= self.threshold else label_norm
            
            corrected_map[best_match] = price
            
        return corrected_map


class OcrService:
    """Handles OCR extraction and intelligent parsing of price maps."""
    
    PRICE_PATTERN = re.compile(r"(?P<price>\d[.,]\d{2,3})")
    HEADER_PATTERN = re.compile(r"(?i)(?:datum|zeit|date|time)[^\d]*\d{4}[-./]\d{2}[-./]\d{2}(?:\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?)?")
    CURRENCY_TOKENS = {"eur", "euro", "€", "lei", "ron", "huf", "ft"}
    STOP_TOKENS = {"datum", "zeit", "datum/zeit", "date", "time", "preis", "price", "eur", "euro"}

    def __init__(self, corrector: OcrCorrector | None = None, max_label_tokens: int = 4):
        self.corrector = corrector or OcrCorrector()
        self.max_label_tokens = max_label_tokens

    def extract_from_base64_url(self, price_url: str) -> dict[str, float]:
        image_bytes = self._decode_image(price_url)
        image = self._prepare_image(image_bytes)
        
        # Use PSM 6 (Assume a single uniform block of text) to maintain row structure consistently
        text = pytesseract.image_to_string(image, config="--psm 6")
        
        prices = self._parse_prices(text)
        return self.corrector.correct_map(prices, text)

    def _decode_image(self, price_url: str) -> bytes:
        encoded = price_url.strip()
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        return base64.b64decode(encoded, validate=True)

    def _prepare_image(self, image_bytes: bytes) -> Image.Image:
        image = Image.open(BytesIO(image_bytes)).convert("RGBA")
        white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
        merged = Image.alpha_composite(white_bg, image).convert("RGB")
        
        # Upscale by 2x to significantly improve OCR precision on small/thin numbers across OS libs
        return merged.resize((merged.width * 2, merged.height * 2), getattr(Image, 'Resampling', Image).LANCZOS)

    def _parse_prices(self, text: str) -> dict[str, float]:
        text = self.HEADER_PATTERN.sub(" ", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        prices = {}
        
        # Try line-by-line matching first
        if len(lines) > 1:
            for line in lines:
                last_end = 0
                for match in self.PRICE_PATTERN.finditer(line):
                    # Only parse tokens between the previous price and the current price
                    chunk = line[last_end:match.start()]
                    label = self._extract_label_before(chunk, len(chunk))
                    if label:
                        prices[label] = float(match.group("price").replace(",", "."))
                    last_end = match.end()
                        
        if prices:
            return prices
            
        # Fallback to flat line parsing if OCR collapsed the layout completely
        flat_text = " ".join(lines)
        return self._parse_flat_line(flat_text)

    def _parse_flat_line(self, line: str) -> dict[str, float]:
        matches = list(self.PRICE_PATTERN.finditer(line))
        if not matches:
            return {}
            
        tokens = self._get_label_tokens(line[:matches[0].start()])
        if not tokens:
            return {}

        best_partition = None
        best_score = -float('inf')

        for partition in self._generate_partitions(tokens, len(matches), self.max_label_tokens):
            score = self._score_partition(partition)
            if score > best_score:
                best_score = score
                best_partition = partition

        if not best_partition:
            return {}

        return {
            " ".join(chunk): float(match.group("price").replace(",", "."))
            for chunk, match in zip(best_partition, matches)
        }

    def _generate_partitions(self, tokens: list[str], groups: int, max_len: int) -> Iterator[list[list[str]]]:
        """Generates all valid combinations of token chunks."""
        if groups == 1:
            if 1 <= len(tokens) <= max_len:
                yield [tokens]
            return
            
        for i in range(1, min(max_len, len(tokens) - groups + 1) + 1):
            for tail in self._generate_partitions(tokens[i:], groups - 1, max_len):
                yield [tokens[:i]] + tail

    def _score_partition(self, partition: list[list[str]]) -> float:
        return sum(self._score_chunk(chunk) for chunk in partition)

    def _score_chunk(self, chunk: list[str]) -> float:
        if not chunk:
            return -1000.0

        score = 0.0
        has_fuel_keyword = False
        
        for token in chunk:
            if token.isdigit():
                score += 0.5
            elif token.isupper() and token.isalpha():
                score += 1.5
            elif token[:1].isupper():
                score += 1.2
            else:
                score += 0.8

            if any(ch.isalpha() for ch in token) and any(ch.isdigit() for ch in token):
                score += 0.4
                
            lower_token = token.lower()
            if any(comp in lower_token for comp in self.corrector.FUEL_TYPE_COMPONENTS):
                has_fuel_keyword = True
                score += 2.0

        if not has_fuel_keyword:
            score -= 10.0

        # Bonus for starting with a known component
        first_lower = chunk[0].lower()
        if any(first_lower.startswith(comp) for comp in self.corrector.FUEL_TYPE_COMPONENTS):
            score += 5.0

        # Semantic boundary heuristics
        # Bonus for ending with a number-like token (e.g., "Super 95", "Super 100plus")
        if chunk[-1][0].isdigit():
            score += 3.0
            
        # Penalty for starting with a number-like token in a multi-word label
        if chunk[0][0].isdigit() and len(chunk) > 1:
            score -= 5.0

        for i in range(1, len(chunk)):
            # Penalty for number immediately followed by a string (indicates crossed boundary)
            if chunk[i-1][0].isdigit() and chunk[i][0].isalpha():
                score -= 4.0

        # Non-linear penalty for length to prevent mathematical ties across grouped partitions
        score -= (len(chunk) - 1) ** 1.5

        return score

    def _get_label_tokens(self, text: str) -> list[str]:
        raw_tokens = text.split()
        tokens = []
        for t in raw_tokens:
            clean = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", t)
            if not clean:
                continue
                
            lower_clean = clean.casefold()
            if lower_clean in self.STOP_TOKENS or "datum" in lower_clean or "zeit" in lower_clean:
                continue
                
            if re.fullmatch(r"\d{4}[-./]\d{2}[-./]\d{2}|\d{1,2}[:.]\d{2}(?:[:.]\d{2})?", clean):
                continue
                
            tokens.append(clean)
        return tokens

    def _extract_label_before(self, text: str, pos: int) -> str | None:
        tokens = self._get_label_tokens(text[:pos])
        if not tokens:
            return None
            
        while tokens and tokens[-1].casefold() in self.CURRENCY_TOKENS:
            tokens.pop()
            
        label = " ".join(tokens[-self.max_label_tokens:])
        return label if label else None