from typing import Set


class SensitiveWordFilter:
    def __init__(self):
        self.words: Set[str] = set()
        self._built = False

    def add_words(self, words: list[str]):
        for word in words:
            word = word.strip().lower()
            if word:
                self.words.add(word)

    def contains(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(word in text_lower for word in self.words)

    def filter(self, text: str, replace: str = "***") -> str:
        if not text:
            return text
        result = text
        text_lower = text.lower()
        for word in self.words:
            idx = 0
            while True:
                pos = text_lower.find(word, idx)
                if pos == -1:
                    break
                result = result[:pos] + replace + result[pos + len(word):]
                text_lower = result.lower()
                idx = pos + len(replace)
        return result


sensitive_filter = SensitiveWordFilter()
