import yake
from typing import List
from app.core.config import settings


class KeywordExtractor:
    def __init__(self):
        self.extractor = yake.KeywordExtractor(
            lan=settings.KEYWORD_LANGUAGE,
            n=2,  # max n-gram size
            dedupLim=0.7,
            top=settings.KEYWORD_MAX_KEYWORDS,
            features=None
        )

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        if not text or len(text.strip()) < 10:
            return []

        try:
            keywords = self.extractor.extract_keywords(text)
            return [kw[0] for kw in keywords if len(kw[0]) > 2]
        except Exception:
            return []

    def get_keyword_sentiment(self, keyword: str, text: str, sentiment_analyzer) -> str:
        """Determine sentiment of a keyword based on context"""
        # Simple approach: look at sentences containing the keyword
        sentences = text.split('.')
        scores = []

        for sentence in sentences:
            if keyword.lower() in sentence.lower():
                score, _, _ = sentiment_analyzer.calculate_sentiment(sentence)
                scores.append(score)

        if not scores:
            return "neutral"

        avg_score = sum(scores) / len(scores)
        if avg_score > 0.1:
            return "positive"
        elif avg_score < -0.1:
            return "negative"
        return "neutral"


# Singleton instance
keyword_extractor = KeywordExtractor()
