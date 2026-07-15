import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { useApp } from '../store/app';
import { TopBar, Loading, QualityTag } from '../components/ui';
import { C, mono } from '../theme/tokens';
import type { WikiDomainSummary, WikiSearchResult } from '../shared';

export function Library() {
  const { go } = useApp();
  const [domains, setDomains] = useState<WikiDomainSummary[] | null>(null);
  const [q, setQ] = useState('');
  const [results, setResults] = useState<WikiSearchResult | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    api.wikiDomains().then(setDomains).catch(() => setDomains([]));
  }, []);

  const total = useMemo(
    () => domains?.reduce((n, d) => n + d.passageCount, 0) ?? 0,
    [domains],
  );

  const runSearch = () => {
    const query = q.trim();
    if (!query) {
      setResults(null);
      return;
    }
    setSearching(true);
    api.wikiSearch(query)
      .then(setResults)
      .catch(() => setResults({ concepts: [], passages: [] }))
      .finally(() => setSearching(false));
  };

  const clearSearch = () => {
    setQ('');
    setResults(null);
  };

  return (
    <div className="tj-body" style={{ paddingBottom: 24 }}>
      <TopBar title="藏经阁" code={`RAG · ${total} 段可溯源`} onBack={() => go('home')} />
      <div style={{ padding: '0 20px' }}>
        <div style={{ marginTop: 12, fontSize: 13, color: C.sub, lineHeight: 1.8 }}>
          大师引用的每一句，都能在这里翻到出处。不玄乎，可溯源。
        </div>

        {/* 搜索：概念词条为主，原文段落为辅，与问卦同一套检索 */}
        <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
          <input
            className="tj-reset"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') runSearch(); }}
            placeholder="试试「印堂」「用神」「文昌」"
            style={{ flex: 1, background: C.card, border: `1px solid ${C.line}`, borderRadius: 12, padding: '10px 14px', fontSize: 14, color: C.ink }}
          />
          <button
            className="tj-reset tj-clickable"
            onClick={runSearch}
            style={{ background: C.dark, color: C.gold, borderRadius: 12, padding: '0 16px', fontWeight: 700, fontSize: 14 }}
          >搜</button>
        </div>

        {searching && <div style={{ marginTop: 20 }}><Loading /></div>}

        {results && !searching && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: C.muted }}>
                命中 {results.concepts.length} 词条 · {results.passages.length} 原文
              </div>
              <button className="tj-reset tj-clickable" onClick={clearSearch} style={{ fontSize: 12, color: C.accent }}>清除 ✕</button>
            </div>

            {results.concepts.length === 0 && results.passages.length === 0 && (
              <div style={{ marginTop: 16, fontSize: 13, color: C.muted, textAlign: 'center' }}>没找到相关词条，换个词试试。</div>
            )}

            {/* 概念词条命中（可点进词条页） */}
            {results.concepts.length > 0 && (
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {results.concepts.map((c) => (
                  <div
                    key={c.id}
                    className="tj-clickable"
                    onClick={() => go('concept', { conceptId: c.id })}
                    style={{ background: C.card, border: `1px solid ${C.line}`, borderRadius: 12, padding: '12px 14px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <span style={{ fontWeight: 900, fontSize: 15 }}>{c.name}</span>
                      <span style={{ fontSize: 10, color: C.faint }}>{c.domainName} · {c.evidenceCount} 段</span>
                      <span style={{ marginLeft: 'auto', color: C.accent }}>→</span>
                    </div>
                    <div style={{ marginTop: 4, fontSize: 12, color: C.sub, lineHeight: 1.7, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{c.definition}</div>
                  </div>
                ))}
              </div>
            )}

            {/* 原文段落命中（只读证据） */}
            {results.passages.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 11, color: C.faint, letterSpacing: 1, marginBottom: 6 }}>原文段落</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {results.passages.map((p, i) => (
                    <div key={p.sourceId ?? i} style={{ background: C.paper, border: `1px solid ${C.lineSoft}`, borderRadius: 10, padding: '10px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
                        <span style={{ fontSize: 11, color: C.accentDeep }}>《{p.book} · {p.chapter}》</span>
                        <span style={{ marginLeft: 'auto' }}><QualityTag quality={p.quality} /></span>
                      </div>
                      <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.8, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{p.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 五大道入口 */}
        {!results && (
          !domains ? (
            <Loading />
          ) : (
            <>
              <div style={{ marginTop: 18, marginBottom: 8, fontSize: 11, color: C.faint, letterSpacing: 2, fontFamily: mono }}>五大道</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {domains.map((d) => (
                  <div
                    key={d.slug}
                    className="tj-clickable"
                    onClick={() => go('domain', { domainSlug: d.slug })}
                    style={{ background: C.card, border: `1px solid ${C.line}`, borderRadius: 14, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}
                  >
                    <div style={{ width: 44, height: 56, background: C.dark, borderRadius: '4px 8px 8px 4px', borderLeft: `4px solid ${C.accent}`, display: 'grid', placeItems: 'center', color: C.gold, fontWeight: 900, fontSize: 20, flexShrink: 0 }}>{d.char}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 900, fontSize: 15 }}>{d.name}</div>
                      <div style={{ fontSize: 12, color: C.sub, marginTop: 3, lineHeight: 1.6, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{d.description}</div>
                      <div style={{ fontSize: 10, color: C.muted, marginTop: 4 }}>{d.conceptCount} 概念 · {d.passageCount} 段原文</div>
                    </div>
                    <div style={{ color: C.accent }}>→</div>
                  </div>
                ))}
              </div>
            </>
          )
        )}
      </div>
    </div>
  );
}
