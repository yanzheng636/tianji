import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useApp } from '../store/app';
import { TopBar, Loading, QualityTag } from '../components/ui';
import { C, mono, serif } from '../theme/tokens';
import type { WikiConceptDetail } from '../shared';

export function Concept() {
  const { nav, go } = useApp();
  const [detail, setDetail] = useState<WikiConceptDetail | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (nav.conceptId) api.wikiConcept(nav.conceptId).then(setDetail).catch(() => {});
  }, [nav.conceptId]);

  const toggle = (i: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  if (!detail) {
    return (
      <div className="tj-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <TopBar title="词条" onBack={() => go('library')} />
        <Loading />
      </div>
    );
  }

  const back = () =>
    detail.domain ? go('domain', { domainSlug: detail.domain }) : go('library');

  return (
    <div className="tj-body" style={{ paddingBottom: 24 }}>
      <TopBar title={detail.name} code={detail.domainName} onBack={back} />
      <div style={{ padding: '0 20px' }}>
        {/* 面包屑 */}
        <div style={{ marginTop: 10, fontSize: 11, color: C.faint, fontFamily: mono }}>
          {detail.domainName} › {detail.name}
        </div>

        {/* 标题 + 状态 */}
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 28, fontWeight: 900, letterSpacing: 2, fontFamily: serif }}>{detail.name}</span>
          <span style={{ fontSize: 11, color: C.accentDeep, background: C.cream, border: `1px solid ${C.line}`, padding: '2px 9px', borderRadius: 20 }}>
            {detail.domainName}{detail.status === 'verified' ? ' · verified' : ''}
          </span>
        </div>
        {detail.aliases.length > 0 && (
          <div style={{ marginTop: 4, fontSize: 11, color: C.muted }}>又称：{detail.aliases.join(' · ')}</div>
        )}

        {/* 白话释义 */}
        <div style={{ margin: '14px 0 4px', paddingLeft: 12, borderLeft: `3px solid ${C.gold}`, color: C.inkSoft, fontSize: 15, lineHeight: 1.9, fontFamily: serif }}>
          {detail.definition}
        </div>

        {/* 用于（意图） */}
        {detail.intents.length > 0 && (
          <>
            <div style={{ margin: '16px 0 6px', fontSize: 11, color: C.muted, letterSpacing: 1 }}>用于</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {detail.intents.map((it) => (
                <span key={it} style={{ fontSize: 12, background: C.paper, border: `1px solid ${C.line}`, color: C.sub, padding: '3px 10px', borderRadius: 20 }}>{it}</span>
              ))}
            </div>
          </>
        )}

        {/* 相关概念（可跳转） */}
        {detail.related.length > 0 && (
          <>
            <div style={{ margin: '16px 0 6px', fontSize: 11, color: C.muted, letterSpacing: 1 }}>相关概念 · 可跳转</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {detail.related.map((r) => (
                <button
                  key={r.id}
                  className="tj-reset tj-clickable"
                  onClick={() => go('concept', { conceptId: r.id })}
                  style={{ fontSize: 13, background: C.cream, border: `1px solid ${C.line}`, color: C.ink, padding: '4px 11px', borderRadius: 20 }}
                >
                  {r.name} <span style={{ color: C.faint, fontSize: 10 }}>{r.relation}</span> →
                </button>
              ))}
            </div>
          </>
        )}

        {/* 原文证据 */}
        <div style={{ margin: '22px 0 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, fontWeight: 900 }}>原文证据</span>
          <span style={{ fontSize: 11, color: C.faint, fontFamily: mono }}>
            {detail.evidence.length}／{detail.evidenceTotal} 段 · 溯源
          </span>
        </div>

        {detail.evidence.length === 0 ? (
          <div style={{ fontSize: 12, color: C.muted }}>暂无可展示的原文证据。</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {detail.evidence.map((e, i) => {
              const open = expanded.has(i);
              return (
                <div key={e.sourceId ?? i} style={{ background: C.paper, border: `1px solid ${C.lineSoft}`, borderRadius: 10, padding: '11px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: C.accentDeep }}>《{e.book} · {e.chapter}》</span>
                    <span style={{ marginLeft: 'auto' }}><QualityTag quality={e.quality} /></span>
                  </div>
                  <div
                    style={{
                      fontSize: 12.5, color: C.sub, lineHeight: 1.85,
                      ...(open ? {} : { display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }),
                    }}
                  >
                    {e.text}
                  </div>
                  <button
                    className="tj-reset tj-clickable"
                    onClick={() => toggle(i)}
                    style={{ marginTop: 6, fontSize: 11, color: C.accent }}
                  >
                    {open ? '收起 ⌃' : '展开全文 ⌄'}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* 带着这个概念去问卦 */}
        <button
          className="tj-reset tj-clickable"
          onClick={() => go('chat', { chatPreset: `帮我讲讲「${detail.name}」` })}
          style={{ marginTop: 16, width: '100%', background: C.accent, color: C.creamText, textAlign: 'center', padding: 14, borderRadius: 14, fontWeight: 700, letterSpacing: 2 }}
        >带着这个概念去问卦</button>

        <div style={{ marginTop: 14, fontSize: 10, color: C.faint, lineHeight: 1.7, fontFamily: mono }}>
          按历史文献知识保存，不等同于现代医学、法律或确定性现实结论。
        </div>
      </div>
    </div>
  );
}
