"""确定性知识图谱检索：用户问题 -> 意图 -> 概念 -> 一跳关系 -> 原典证据。

该模块只读取构建产物 ``knowledge_wiki/graph.json``，不调用 LLM、embedding
服务或数据库。生产问卦可在图谱缺失时继续使用旧的数据库关键词检索。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.knowledge.graph_catalog import CONCEPTS, INTENTS

_GRAPH_RELATIONS = {
    "is_a",
    "part_of",
    "generates",
    "restrains",
    "depends_on",
    "used_by",
    "contrasts_with",
    "differs_from",
    "contradicts",
}


@dataclass(frozen=True)
class GraphHit:
    source_id: str
    book: str
    chapter: str
    text: str
    quality: str
    concepts: tuple[str, ...]
    intents: tuple[str, ...]
    path: str
    score: float
    relation_hops: tuple[str, ...] = ()
    structure: dict[str, Any] | None = None


def _default_graph_path() -> Path:
    configured = os.getenv("KNOWLEDGE_GRAPH_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[4] / "knowledge_wiki" / "graph.json"


def _bigrams(value: str) -> set[str]:
    compact = "".join(char for char in value if char.strip())
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[index : index + 2] for index in range(len(compact) - 1)}


def _intent_scores(query: str, topic: str | None) -> dict[str, float]:
    scores: dict[str, float] = {}
    if topic:
        scores[topic] = 5.0
    for intent in INTENTS:
        score = sum(query.count(keyword) for keyword in intent.keywords)
        if score:
            scores[intent.slug] = scores.get(intent.slug, 0.0) + float(score * 2)
    if not scores:
        scores["general"] = 1.0
    return scores


class GraphIndex:
    def __init__(self, payload: dict[str, Any], graph_path: Path):
        self.graph_path = graph_path
        self.schema_version = int(payload.get("schema_version", 1))
        self.nodes: dict[str, dict[str, Any]] = {
            str(node["id"]): node
            for node in payload.get("nodes", [])
            if isinstance(node, dict) and node.get("id")
        }
        self.edges: list[dict[str, Any]] = [
            edge for edge in payload.get("edges", []) if isinstance(edge, dict)
        ]
        self.book_names = {
            node_id.removeprefix("book:"): str(node.get("name") or "古籍")
            for node_id, node in self.nodes.items()
            if node.get("type") == "book"
        }
        self.intent_domains = {
            intent.slug: set(intent.preferred_domains)
            for intent in INTENTS
        }
        self.concept_specs = {spec.node_id: spec for spec in CONCEPTS}
        self.concept_neighbors: dict[str, set[str]] = {}
        for edge in self.edges:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            relation = str(edge.get("relation") or "")
            if relation not in _GRAPH_RELATIONS:
                continue
            if source.startswith("concept:") and target.startswith("concept:"):
                self.concept_neighbors.setdefault(source, set()).add(target)
                self.concept_neighbors.setdefault(target, set()).add(source)

    def _match_concepts(self, query: str, topic: str | None = None) -> dict[str, float]:
        matches: dict[str, float] = {}
        for node_id, node in self.nodes.items():
            if node.get("type") != "concept":
                continue
            intents = {str(item) for item in node.get("intents", []) if item}
            if topic and topic != "general" and intents and topic not in intents:
                continue
            metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
            spec = self.concept_specs.get(node_id)
            terms = {
                str(node.get("name") or ""),
                *(str(item) for item in node.get("aliases", []) if item),
                *(str(item) for item in metadata.get("keywords", []) if item),
            }
            if spec:
                terms.update(spec.keywords)
                terms.update(spec.aliases)
            direct = [term for term in terms if len(term) >= 2 and term in query]
            if direct:
                matches[node_id] = 6.0 + max(len(term) for term in direct) * 0.3
        return matches

    def retrieve(
        self,
        query: str,
        *,
        topic: str | None = None,
        k: int = 3,
        allow_review: bool = False,
    ) -> list[GraphHit]:
        query = query.strip()
        if not query or k <= 0:
            return []

        intent_scores = _intent_scores(query, topic)
        concept_scores = self._match_concepts(query, topic)
        relation_hops: dict[str, set[str]] = {}
        evidence_scores: dict[str, float] = {}
        direct_evidence: set[str] = set()

        for concept_id, score in concept_scores.items():
            concept_node = self.nodes.get(concept_id, {})
            for source_id in concept_node.get("evidence", []):
                source_key = str(source_id)
                direct_evidence.add(source_key)
                evidence_scores[source_key] = evidence_scores.get(source_key, 0.0) + score
                relation_hops.setdefault(source_key, set()).add(concept_id)
            for neighbor in self.concept_neighbors.get(concept_id, set()):
                neighbor_node = self.nodes.get(neighbor, {})
                for source_id in neighbor_node.get("evidence", []):
                    evidence_scores[str(source_id)] = evidence_scores.get(str(source_id), 0.0) + 1.5
                    relation_hops.setdefault(str(source_id), set()).add(f"{concept_id}->{neighbor}")

        query_bigrams = _bigrams(query)
        hits: list[GraphHit] = []
        for node_id, node in self.nodes.items():
            if node.get("type") != "source":
                continue
            quality = str(node.get("status") or "review-needed")
            if quality == "unusable" or (quality != "verified" and not allow_review):
                continue
            domain = str(node.get("domain") or "")
            preferred_domains = self.intent_domains.get(topic or "", set())
            if preferred_domains and domain and domain not in preferred_domains:
                continue

            metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
            text = str(metadata.get("text") or node.get("description") or "").strip()
            chapter = str(metadata.get("chapter") or "正文")
            intents = tuple(str(item) for item in node.get("intents", []) if item)
            if topic and topic != "general" and intents and topic not in intents:
                continue
            evidence_score = evidence_scores.get(node_id, 0.0)
            score = evidence_score
            overlap = 0
            if query_bigrams:
                overlap = len(query_bigrams & (_bigrams(text) | _bigrams(chapter)))
                score += min(overlap, 8) * 0.65
            # 一跳关系只能扩展候选，不能用一个宽泛的邻居概念替代用户实际
            # 询问的概念；非直接证据仍须至少两个二元词与原文重叠。
            if node_id not in direct_evidence and overlap < 2:
                continue
            for intent, intent_score in intent_scores.items():
                if intent in intents:
                    score += intent_score

            book_id = str(metadata.get("book_id") or "")
            if not book_id and node_id.startswith("source:"):
                book_id = node_id.split(":", 2)[1]
            concept_ids = tuple(
                sorted(
                    {
                        str(item)
                        for item in metadata.get("concepts", [])
                        if item
                    }
                    | {
                        hop.split("->", 1)[0]
                        for hop in relation_hops.get(node_id, set())
                    }
                )
            )
            concept_names = tuple(
                str(self.nodes.get(concept_id, {}).get("name") or concept_id)
                for concept_id in concept_ids
            )
            hits.append(
                GraphHit(
                    source_id=node_id,
                    book=str(metadata.get("book_name") or self.book_names.get(book_id) or "古籍"),
                    chapter=chapter,
                    text=text,
                    quality=quality,
                    concepts=concept_names,
                    intents=intents,
                    path=str(node.get("path") or ""),
                    score=score,
                    relation_hops=tuple(sorted(relation_hops.get(node_id, set()))),
                    structure=(metadata.get("structure") if isinstance(metadata.get("structure"), dict) else None),
                )
            )

        hits.sort(key=lambda item: (-item.score, item.source_id))
        selected: list[GraphHit] = []
        seen_text: set[str] = set()
        for hit in hits:
            fingerprint = re.sub(r"\s+", "", hit.text)[:80]
            if not fingerprint or fingerprint in seen_text:
                continue
            seen_text.add(fingerprint)
            selected.append(hit)
            if len(selected) >= k:
                break
        return selected


@lru_cache(maxsize=4)
def _load_index(path_value: str, mtime_ns: int) -> GraphIndex:
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("知识图谱根节点必须是对象")
    return GraphIndex(payload, path)


def get_graph_index(path: Path | None = None) -> GraphIndex | None:
    graph_path = (path or _default_graph_path()).resolve()
    try:
        stat = graph_path.stat()
        return _load_index(str(graph_path), stat.st_mtime_ns)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def retrieve_graph(
    query: str,
    *,
    topic: str | None = None,
    k: int = 3,
    allow_review: bool = False,
    path: Path | None = None,
) -> list[GraphHit]:
    index = get_graph_index(path)
    if index is None:
        return []
    return index.retrieve(query, topic=topic, k=k, allow_review=allow_review)
