"""RAG léger : base de fiches Markdown + recherche TF-IDF (sans dépendance réseau).

Pour une version "embeddings" il suffit de remplacer TfidfVectorizer par un modèle d'embeddings et
ChromaDB ; l'interface `retrieve(query, k)` reste la même.
"""
from pathlib import Path
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def load_docs(kb_dir=KB_DIR):
    docs = []
    for p in sorted(Path(kb_dir).glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        meta, body = {}, raw
        if m:
            for line in m.group(1).splitlines():
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
            body = m.group(2)
        docs.append({"id": meta.get("id", p.stem), "label": meta.get("label", "reference"),
                     "title": meta.get("title", p.stem), "text": body.strip()})
    return docs


class Retriever:
    def __init__(self, kb_dir=KB_DIR):
        self.docs = load_docs(kb_dir)
        self.vec = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vec.fit_transform([d["title"] + " " + d["text"] for d in self.docs])

    def retrieve(self, query, k=3):
        sims = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        order = sims.argsort()[::-1][:k]
        return [dict(self.docs[i], score=float(sims[i])) for i in order]
