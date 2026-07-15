import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useApp } from '../store/app';
import { TopBar, Loading } from '../components/ui';
import { C, mono } from '../theme/tokens';
import type { WikiDomainDetail } from '../shared';

export function Domain() {
  const { nav, go } = useApp();
  const [detail, setDetail] = useState<WikiDomainDetail | null>(null);

  useEffect(() => {
    if (nav.domainSlug) api.wikiDomain(nav.domainSlug).then(setDetail).catch(() => {});
  }, [nav.domainSlug]);

  if (!detail) {
    return (
      <div className="tj-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <TopBar title="知识领域" onBack={() => go('library')} />
        <Loading />
      </div>
    );
  }

  return (
    <div className="tj-body" style={{ paddingBottom: 24 }}>
      <TopBar
        title={detail.name}
        code={`${detail.conceptCount} 概念 · ${detail.passageCount} 段`}
        onBack={() => go('library')}
      />
      <div style={{ padding: '0 20px' }}>
        <div style={{ marginTop: 12, fontSize: 13, color: C.sub, lineHeight: 1.9 }}>
          {detail.description}
        </div>

        <div style={{ marginTop: 18, marginBottom: 8, fontSize: 11, color: C.faint, letterSpacing: 2, fontFamily: mono }}>
          核心概念 · {detail.concepts.length}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {detail.concepts.map((c) => (
            <div
              key={c.id}
              className="tj-clickable"
              onClick={() => go('concept', { conceptId: c.id })}
              style={{ background: C.card, border: `1px solid ${C.line}`, borderRadius: 14, padding: '13px 15px' }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontWeight: 900, fontSize: 16 }}>{c.name}</span>
                <span style={{ fontSize: 10, color: C.faint }}>{c.evidenceCount} 段原文</span>
                <span style={{ marginLeft: 'auto', color: C.accent }}>→</span>
              </div>
              <div style={{ marginTop: 5, fontSize: 12.5, color: C.sub, lineHeight: 1.75, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {c.definition}
              </div>
              {c.intents.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {c.intents.map((it) => (
                    <span key={it} style={{ fontSize: 11, background: C.paper, border: `1px solid ${C.lineSoft}`, color: C.muted, padding: '2px 9px', borderRadius: 20 }}>{it}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 来源书籍：弱化的溯源线索，原文正文已在各概念的「原文证据」内可达 */}
        {detail.books.length > 0 && (
          <div style={{ marginTop: 22 }}>
            <div style={{ marginBottom: 8, fontSize: 11, color: C.faint, letterSpacing: 2, fontFamily: mono }}>来源书籍</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {detail.books.map((b) => (
                <div key={b.slug} style={{ background: C.cardWarm, border: '1px solid #D9CBA6', borderRadius: 10, padding: '8px 12px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: C.inkSoft }}>{b.name}</div>
                  <div style={{ fontSize: 10, color: C.muted, marginTop: 2 }}>{b.meta}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
