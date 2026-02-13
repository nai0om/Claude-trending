"""Thai sentiment analysis — WangchanBERTa / PyThaiNLP based."""

import logging

logger = logging.getLogger(__name__)


def analyze_texts(texts: list[str]) -> dict:
    """Analyze sentiment of Thai texts.

    Uses PyThaiNLP for tokenization and basic sentiment.
    WangchanBERTa can be enabled for more accurate results.

    Args:
        texts: List of Thai text strings to analyze.

    Returns:
        Dict with score (-1 to +1), label, confidence.
    """
    if not texts:
        return {"score": 0.0, "label": "neutral", "confidence": "Low", "top_keywords": []}

    scores = []
    for text in texts:
        score = _analyze_single(text)
        scores.append(score)

    avg_score = sum(scores) / len(scores)
    label = "positive" if avg_score > 0.1 else "negative" if avg_score < -0.1 else "neutral"

    confidence = "High" if len(texts) >= 10 else "Medium" if len(texts) >= 3 else "Low"
    keywords = extract_keywords(texts)

    return {
        "score": round(avg_score, 4),
        "label": label,
        "confidence": confidence,
        "sample_size": len(texts),
        "top_keywords": keywords[:10],
    }


def _analyze_single(text: str) -> float:
    """Analyze sentiment of a single Thai text.

    Returns score from -1 (negative) to +1 (positive).
    """
    # Basic keyword-based sentiment (fallback before ML models)
    positive_words = ["ขึ้น", "กำไร", "ดี", "เติบโต", "แนะนำซื้อ", "เป้าหมาย", "บวก", "สูง", "แข็งแกร่ง"]
    negative_words = ["ลง", "ขาดทุน", "แย่", "ลด", "ขาย", "ลบ", "ต่ำ", "อ่อนแอ", "เสี่ยง", "หนี้"]

    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    total = pos_count + neg_count
    if total == 0:
        return 0.0

    return (pos_count - neg_count) / total


def extract_keywords(texts: list[str], top_n: int = 10) -> list[str]:
    """Extract most frequent meaningful keywords from texts.

    Uses basic word frequency. Can be upgraded to TF-IDF or Thai word segmentation.
    """
    try:
        from pythainlp.tokenize import word_tokenize
        from pythainlp.corpus import thai_stopwords

        stopwords = thai_stopwords()
        word_freq: dict[str, int] = {}

        for text in texts:
            words = word_tokenize(text, engine="newmm")
            for word in words:
                word = word.strip()
                if len(word) > 1 and word not in stopwords:
                    word_freq[word] = word_freq.get(word, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:top_n]]

    except ImportError:
        logger.warning("PyThaiNLP not available, skipping keyword extraction")
        return []
