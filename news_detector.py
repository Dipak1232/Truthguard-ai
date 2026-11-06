from __future__ import annotations

import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "news_model.joblib"
VECTORIZER_PATH = MODEL_DIR / "news_vectorizer.joblib"
SUSPICIOUS_TERMS = {
    "shocking", "secret", "miracle", "guaranteed", "urgent", "exposed", "they don't want",
    "you won't believe", "100%", "everyone is saying", "breaking", "conspiracy", "unbelievable",
    "must see", "banned", "cure all", "overnight", "click here", "wake up",
}

_model: Any = None
_vectorizer: Any = None
_model_available = False


def _demo_training_data() -> tuple[list[str], list[int]]:
    reliable_style = [
        "The city council published meeting minutes and a budget summary.",
        "Researchers reported preliminary findings and described the study limitations.",
        "The agency released a statement with dates, sources, and methodology.",
        "Local officials said the road will close for repairs next month.",
        "The report cited public records and included links to supporting documents.",
        "A university team announced results that are awaiting peer review.",
        "The company filed its quarterly financial report with regulators.",
        "Meteorologists forecast rain based on regional weather observations.",
        "The article attributes the claim to named experts and official documents.",
        "A public health notice explains symptoms and recommends speaking with a clinician.",
        "The committee voted after a public hearing and published the final decision.",
        "The story distinguishes confirmed facts from statements that could not be verified.",
    ]
    misleading_style = [
        "SHOCKING secret cure guarantees instant results overnight!!!",
        "They do not want you to know this unbelievable truth.",
        "Everyone is saying this miracle discovery changes everything forever.",
        "URGENT: click here before this banned report disappears.",
        "A conspiracy exposed by an anonymous insider proves it all.",
        "You will not believe what happened next, share this immediately.",
        "This one weird trick is guaranteed to solve every problem.",
        "BREAKING: the secret plan will affect everyone tomorrow.",
        "Wake up! Experts hate this simple miracle solution.",
        "100% proof that the unbelievable claim is true with no sources.",
        "The media is hiding this shocking information from you.",
        "Must see footage proves a sensational claim beyond any doubt.",
    ]
    return reliable_style + misleading_style, [1] * len(reliable_style) + [0] * len(misleading_style)


def initialize_model() -> bool:
    global _model, _vectorizer, _model_available
    if _model_available:
        return True
    try:
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        MODEL_DIR.mkdir(exist_ok=True)
        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            _model = joblib.load(MODEL_PATH)
            _vectorizer = joblib.load(VECTORIZER_PATH)
        else:
            samples, labels = _demo_training_data()
            _vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True, max_features=900)
            features = _vectorizer.fit_transform(samples)
            _model = LogisticRegression(max_iter=450, class_weight="balanced", random_state=42)
            _model.fit(features, labels)
            joblib.dump(_model, MODEL_PATH)
            joblib.dump(_vectorizer, VECTORIZER_PATH)
        _model_available = True
        return True
    except Exception:
        _model_available = False
        return False


def _statistics(text: str) -> dict[str, int]:
    words = re.findall(r"\b[\w'-]+\b", text)
    sentences = [sentence for sentence in re.split(r"[.!?]+", text) if sentence.strip()]
    normalized = text.lower()
    suspicious_count = sum(normalized.count(term) for term in SUSPICIOUS_TERMS)
    return {
        "word_count": len(words),
        "character_count": len(text),
        "sentence_count": len(sentences),
        "suspicious_keyword_count": suspicious_count,
    }


def _signal_score(text: str, statistics: dict[str, int]) -> tuple[float, list[str]]:
    text_lower = text.lower()
    terms = [term for term in SUSPICIOUS_TERMS if term in text_lower]
    exclamation_ratio = min(text.count("!") / 6, 1.0)
    alpha_characters = [char for char in text if char.isalpha()]
    uppercase_ratio = sum(char.isupper() for char in alpha_characters) / max(len(alpha_characters), 1)
    short_text_signal = 0.18 if statistics["word_count"] < 12 else 0.0
    score = min(
        1.0,
        0.12 * min(statistics["suspicious_keyword_count"], 5)
        + 0.18 * exclamation_ratio
        + 0.34 * max(uppercase_ratio - 0.24, 0)
        + short_text_signal,
    )
    return score, terms


def analyze_news(headline: str, article: str) -> dict[str, Any]:
    text = f"{headline}\n{article}".strip()
    statistics = _statistics(text)
    signal_score, matched_terms = _signal_score(text, statistics)
    model_ready = initialize_model()
    model_misleading_score = 0.5

    if model_ready and _model is not None and _vectorizer is not None:
        try:
            probabilities = _model.predict_proba(_vectorizer.transform([text]))[0]
            model_misleading_score = float(probabilities[0])
        except Exception:
            model_ready = False

    misleading_score = min(0.92, max(0.08, (0.58 * model_misleading_score) + (0.42 * signal_score)))
    is_misleading = misleading_score >= 0.52
    confidence = round(min(94.0, 52.0 + abs(misleading_score - 0.5) * 82), 1)

    if is_misleading:
        risk = "High" if misleading_score >= 0.70 else "Medium"
        evidence = ", ".join(f'“{term}”' for term in matched_terms[:3]) or "a combination of attention-grabbing style signals"
        explanation = (
            f"This text contains {evidence} and has a style pattern that the local baseline model associates "
            "with potentially misleading or sensational framing. Verify key claims through independent, accountable sources."
        )
        label = "Potentially Misleading"
    else:
        risk = "Low" if misleading_score < 0.34 else "Medium"
        explanation = (
            "This text has relatively few sensational-style signals in this local baseline assessment. "
            "That does not independently verify its claims, sources, or context."
        )
        label = "Likely Reliable"

    return {
        "label": label,
        "risk": risk,
        "confidence": confidence,
        "explanation": explanation,
        "statistics": statistics,
        "model": "TF-IDF + Logistic Regression demo model" if model_ready else "Rule-based style fallback",
        "disclaimer": "This is an AI-assisted probabilistic analysis and should not be treated as definitive proof.",
    }
