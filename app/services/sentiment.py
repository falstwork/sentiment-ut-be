import re
from typing import List, Tuple, Optional
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory


class SentimentAnalyzer:
    def __init__(self):
        self.stemmer = StemmerFactory().create_stemmer()
        self.stopword_remover = StopWordRemoverFactory().create_stop_word_remover()

        # Indonesian sentiment lexicon (expanded)
        # Positive words with scores
        self.positive_words = {
            # General positive
            "bagus": 0.5, "baik": 0.5, "baiklah": 0.3, "mantap": 0.8, "mantap": 0.8,
            "luar biasa": 0.9, "hebat": 0.7, "keren": 0.6, "wow": 0.7, "ajaib": 0.7,
            "indah": 0.6, "cantik": 0.5, "elegan": 0.5, "spesial": 0.6,

            # Education related
            "mudah": 0.5, "gampang": 0.4, "simpel": 0.3, "praktis": 0.4,
            "fleksibel": 0.6, "flexible": 0.6, "modern": 0.5, "innovatif": 0.5,
            "cerdas": 0.5, "cerdas": 0.5, "pintar": 0.5, "cerdas": 0.5,
            "besar": 0.3, "luas": 0.4, "lengkap": 0.5,

            # Achievement
            "sukses": 0.7, "berhasil": 0.6, "lulus": 0.5, "tamat": 0.4,
            "memenangkan": 0.7, "menang": 0.6, "juara": 0.7,

            # Satisfaction
            "puas": 0.6, "senang": 0.6, "gembira": 0.7, "bahagia": 0.7,
            "terima kasih": 0.5, "thanks": 0.4, "tq": 0.4,
            "suka": 0.4, "sukacita": 0.6, "gembira": 0.6,

            # Helpful
            "membantu": 0.6, "bermanfaat": 0.6, "berguna": 0.5, "berfaedah": 0.5,
            "efektif": 0.5, "produktif": 0.5,

            # Recommendation
            "rekomendasi": 0.5, "saran": 0.3, "anjuran": 0.4,

            # Affirmation
            "setuju": 0.3, "ok": 0.2, "oke": 0.2, "betul": 0.3, "benar": 0.3,
            "pasti": 0.3, "yakin": 0.3,

            # Convenience
            "cepat": 0.4, "landing": 0.3, "tidak ribet": 0.5, "tidak rumit": 0.5,
            "simplifikasi": 0.4, "praktis": 0.4, "efisien": 0.5,
        }

        # Negative words with scores
        self.negative_words = {
            # General negative
            "buruk": -0.6, "jelek": -0.5, "hancur": -0.7, "parah": -0.7,
            "terrible": -0.8, "horrible": -0.8, "awful": -0.8,
            "gagal": -0.6, "defect": -0.6, "rusak": -0.5,

            # Education problems
            "sulit": -0.5, "rumit": -0.5, "susah": -0.5, "berat": -0.4,
            "banyak masalah": -0.6, "problem": -0.5, "masalah": -0.5,
            "kendala": -0.4, "hambatan": -0.4, "rintangan": -0.4,

            # Technical issues
            "error": -0.6, "bug": -0.5, "crash": -0.7, "down": -0.5,
            "lemot": -0.5, "lambat": -0.4, "delay": -0.4, "telat": -0.3,
            "loading": -0.3, "hang": -0.5, "freeze": -0.5,
            "buffering": -0.4, "patah": -0.4, "putus": -0.4,

            # Cost issues
            "mahal": -0.5, "biaya": -0.3, "mahalnya": -0.5,
            "uang": -0.2, "rugi": -0.5, "bayar": -0.2,

            # Dissatisfaction
            "kecewa": -0.7, "kecewa": -0.7, "frustrasi": -0.7, "kesal": -0.6,
            "marah": -0.6, "benci": -0.7, "bosan": -0.4, "jenuh": -0.4,
            "komplain": -0.6, "protes": -0.6, "keluh": -0.4,

            # Online/digital issues
            "downloading": -0.3, "upload": -0.2, "server": -0.3,
            "website": -0.2, "aplikasi": -0.2, "sistem": -0.2,

            # Rejection
            "tolak": -0.4, "tidak setuju": -0.4, "bukan": -0.2,
            "salah": -0.3, "keliru": -0.4, " blunder": -0.5,

            # Regret
            "penyesalan": -0.5, "menyesal": -0.5, "sesal": -0.5,
            "minta maaf": -0.3, " apologize": -0.3,
        }

        # Negation words
        self.negation_words = {
            "tidak", "bukan", "nggak", "ga", "gak", "tidak", "ndak",
            "jangan", "sekali", "sangat", "terlalu"
        }

    def preprocess(self, text: str) -> str:
        """Clean and preprocess text"""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)

        # Remove mentions and hashtags
        text = re.sub(r'@\w+|#\w+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def stem_text(self, text: str) -> str:
        """Stem text using Sastrawi"""
        try:
            words = text.split()
            stemmed_words = [self.stemmer.stem(word) for word in words]
            return ' '.join(stemmed_words)
        except Exception:
            return text

    def remove_stopwords(self, text: str) -> str:
        """Remove Indonesian stopwords"""
        try:
            return self.stopword_remover.remove(text)
        except Exception:
            return text

    def calculate_sentiment(self, text: str) -> Tuple[float, str, float]:
        """
        Calculate sentiment score for text.
        Returns: (score, label, confidence)
        Score range: -1 (very negative) to 1 (very positive)
        """
        if not text or len(text.strip()) == 0:
            return 0.0, "neutral", 0.0

        # Preprocess
        clean_text = self.preprocess(text)

        # Calculate scores
        positive_score = 0.0
        negative_score = 0.0
        word_count = 0

        words = clean_text.split()
        negation_window = 0

        for i, word in enumerate(words):
            # Check for negation in previous word
            is_negated = (i > 0 and words[i - 1] in self.negation_words)

            # Check positive words
            if word in self.positive_words:
                score = self.positive_words[word]
                if is_negated:
                    score = -score * 0.8  # Negation reduces and inverts
                positive_score += score
                word_count += 1

            # Check negative words
            elif word in self.negative_words:
                score = self.negative_words[word]
                if is_negated:
                    score = -score * 0.8  # Double negative
                negative_score += abs(score)
                word_count += 1

        # Also check for multi-word phrases
        for phrase, score in self.positive_words.items():
            if len(phrase.split()) > 1 and phrase in clean_text:
                positive_score += score
                word_count += 1

        for phrase, score in self.negative_words.items():
            if len(phrase.split()) > 1 and phrase in clean_text:
                negative_score += abs(score)
                word_count += 1

        if word_count == 0:
            return 0.0, "neutral", 0.0

        # Normalize scores
        total_score = (positive_score - negative_score) / word_count

        # Clamp to -1, 1
        total_score = max(-1.0, min(1.0, total_score))

        # Determine label
        if total_score > 0.1:
            label = "positive"
        elif total_score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        # Confidence based on consistency of scores
        total_abs = positive_score + negative_score
        if word_count > 0:
            confidence = min(1.0, total_abs / word_count)
        else:
            confidence = 0.0

        return total_score, label, confidence

    def analyze(self, text: str) -> dict:
        """Full analysis of text"""
        score, label, confidence = self.calculate_sentiment(text)

        return {
            "sentiment_score": score,
            "sentiment_label": label,
            "sentiment_confidence": confidence
        }


# Singleton instance
sentiment_analyzer = SentimentAnalyzer()
