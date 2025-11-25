import re
import math
from collections import Counter, defaultdict
from typing import List, Tuple, Optional

try:
    import jieba  # type: ignore
    _HAS_JIEBA = True
except Exception:
    _HAS_JIEBA = False


# -----------------------------
# Basic utilities
# -----------------------------

_ZH_PUNCTS = "。！？；…!?.;，,、：:；;（()）[]【】<>《》\"'“”‘’—-"
_EN_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_HTML_TAG = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"\s+")

_STOPWORDS_ZH = set(
    [
        "的", "了", "和", "是", "在", "也", "就", "都", "而", "及", "与", "着", "或", "一个",
        "没有", "我们", "你们", "他们", "因此", "但是", "并且", "由于", "如果", "对于", "以及",
        "这种", "这些", "那些", "可以", "可能", "已经", "因为", "所以", "通过", "需要",
    ]
)

_STOPWORDS_EN = set(
    [
        "the", "a", "an", "and", "or", "but", "if", "then", "so", "because", "as",
        "is", "are", "was", "were", "be", "been", "being",
        "of", "for", "to", "in", "on", "at", "by", "with", "from", "that", "this",
        "it", "its", "we", "you", "they", "he", "she", "them", "our", "your", "their",
    ]
)


def _strip_html(text: str) -> str:
    text = _HTML_TAG.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


def _detect_lang(text: str) -> str:
    # Heuristic: ratio of CJK characters
    if not text:
        return "zh"
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ratio = cjk / max(1, len(text))
    return "zh" if ratio > 0.15 else "en"


def _split_sentences(text: str, lang: str) -> List[str]:
    if lang == "zh":
        # Split by Chinese sentence-ending punctuations while preserving boundaries
        sents: List[str] = []
        buff = []
        for ch in text:
            buff.append(ch)
            if ch in "。！？!?;；\n":
                s = "".join(buff).strip()
                if s:
                    sents.append(s)
                buff = []
        if buff:
            s = "".join(buff).strip()
            if s:
                sents.append(s)
        return sents
    # English-like
    # Normalize whitespace
    text = _MULTI_SPACE.sub(" ", text.strip())
    parts = _EN_SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def _tokenize(sent: str, lang: str) -> List[str]:
    if lang == "zh":
        if _HAS_JIEBA:
            toks = [w.strip() for w in jieba.cut(sent) if w.strip()]
        else:
            # Fallback: split by punctuation and spaces (coarse)
            toks = re.split(rf"[{re.escape(_ZH_PUNCTS)}\s]+", sent)
            toks = [t for t in toks if t]
        return [t for t in toks if t not in _STOPWORDS_ZH and t not in _ZH_PUNCTS]
    # English
    toks = re.split(r"[^A-Za-z0-9_]+", sent.lower())
    toks = [t for t in toks if t and t not in _STOPWORDS_EN]
    return toks


def _build_tfidf(sent_tokens: List[List[str]]) -> Tuple[List[dict], dict]:
    # Compute IDF over sentences
    df = Counter()
    for toks in sent_tokens:
        for term in set(toks):
            df[term] += 1
    n = max(1, len(sent_tokens))
    idf = {term: math.log((n + 1) / (df_v + 1)) + 1.0 for term, df_v in df.items()}

    vectors: List[dict] = []
    for toks in sent_tokens:
        tf = Counter(toks)
        vec = {}
        if not tf:
            vectors.append(vec)
            continue
        max_tf = max(tf.values())
        for term, freq in tf.items():
            vec[term] = (0.5 + 0.5 * freq / max_tf) * idf.get(term, 1.0)
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        for k in list(vec.keys()):
            vec[k] /= norm
        vectors.append(vec)
    return vectors, idf


def _cosine_sim(v1: dict, v2: dict) -> float:
    if not v1 or not v2:
        return 0.0
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    s = 0.0
    for k, w in v1.items():
        w2 = v2.get(k)
        if w2 is not None:
            s += w * w2
    return float(s)


def _pagerank(weights: List[List[float]], d: float = 0.85, tol: float = 1e-6, max_iter: int = 100) -> List[float]:
    n = len(weights)
    if n == 0:
        return []
    pr = [1.0 / n] * n
    for _ in range(max_iter):
        new_pr = [0.0] * n
        for i in range(n):
            out_sum = sum(weights[i])
            if out_sum == 0:
                # Distribute uniformly if no outgoing weight
                share = pr[i] / n
                for j in range(n):
                    new_pr[j] += share
            else:
                for j in range(n):
                    if weights[i][j] > 0:
                        new_pr[j] += pr[i] * weights[i][j] / out_sum
        new_pr = [d * v + (1 - d) / n for v in new_pr]
        diff = sum(abs(new_pr[i] - pr[i]) for i in range(n))
        pr = new_pr
        if diff < tol:
            break
    return pr


def _smart_truncate(text: str, max_chars: int, lang: str) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Try cut on sentence boundary or word boundary
    if lang == "zh":
        for p in "。！？；，、;,.":
            idx = cut.rfind(p)
            if idx >= max_chars * 0.6:
                return cut[: idx + 1]
        return cut + ("…" if not cut.endswith("…") else "")
    else:
        idx = cut.rfind(" ")
        if idx >= int(max_chars * 0.6):
            return cut[:idx] + "…"
        return cut + "…"


def _title_boost(scores: List[float], sentences: List[str], title: Optional[str], lang: str) -> List[float]:
    if not title:
        return scores
    title_toks = set(_tokenize(title, lang))
    if not title_toks:
        return scores
    boosted = []
    for s, sc in zip(sentences, scores):
        stoks = set(_tokenize(s, lang))
        overlap = len(title_toks & stoks)
        boosted.append(sc * (1.0 + 0.15 * overlap))
    return boosted


def extractive_summary(
    text: str,
    max_sentences: int = 3,
    lang: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Extract top-k sentences using a lightweight TextRank-like algorithm.

    - Works offline; optional jieba for zh improves quality.
    - Compatible with zh/en via simple language detection.
    """
    text = _strip_html(text)
    lang = lang or _detect_lang(text)
    sentences = _split_sentences(text, lang)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 4]

    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    tokens = [_tokenize(s, lang) for s in sentences]
    vectors, _ = _build_tfidf(tokens)

    n = len(sentences)
    # Similarity graph
    W: List[List[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim = _cosine_sim(vectors[i], vectors[j])
            if sim <= 0:
                continue
            W[i][j] = sim
            W[j][i] = sim

    scores = _pagerank(W)
    scores = _title_boost(scores, sentences, title, lang)

    idx = list(range(n))
    idx.sort(key=lambda k: scores[k], reverse=True)
    top_idx = sorted(idx[:max_sentences])  # keep original order
    if lang == "zh":
        glue = ""
    else:
        glue = " "
    summary = glue.join([sentences[i] for i in top_idx]).strip()
    return summary


def compress_summary(text: str, max_chars: int = 120, lang: Optional[str] = None) -> str:
    """Lightweight compression without external models.

    This is a placeholder for a local LM-based compressor. For now, it
    applies simple cleanup and smart truncation to keep within max_chars.
    """
    if not text:
        return ""
    lang = lang or _detect_lang(text)
    # Remove bracketed asides and duplicate spaces
    text = re.sub(r"\s*([\(（][^\)）]{0,80}[\)）])\s*", " ", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return _smart_truncate(text, max_chars, lang)


def summarize_text(
    text: str,
    max_chars: int = 120,
    lang: Optional[str] = None,
    title: Optional[str] = None,
    max_sentences: int = 3,
) -> str:
    """Hybrid pipeline (extract -> lightweight compress) fully offline.

    Parameters:
      - text: raw article content (plain text or HTML)
      - max_chars: target character limit for final summary
      - lang: 'zh' or 'en'; auto-detected if None
      - title: optional title for boosting relevance
      - max_sentences: number of sentences to extract before compress
    """
    if not text:
        return ""
    lang = lang or _detect_lang(text)
    extracted = extractive_summary(text, max_sentences=max_sentences, lang=lang, title=title)
    return compress_summary(extracted, max_chars=max_chars, lang=lang)


__all__ = [
    "summarize_text",
    "extractive_summary",
    "compress_summary",
]

