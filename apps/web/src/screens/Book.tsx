import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useApp } from '../store/app';
import { TopBar, Loading } from '../components/ui';
import { C } from '../theme/tokens';
import type { BookDetail } from '../shared';

export function Book() {
  const { nav, go } = useApp();
  const [book, setBook] = useState<BookDetail | null>(null);

  useEffect(() => {
    if (nav.bookSlug) api.book(nav.bookSlug).then(setBook).catch(() => {});
  }, [nav.bookSlug]);

  if (!book) {
    return (
      <div className="tj-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <TopBar title="经卷" onBack={() => go('library')} />
        <Loading />
      </div>
    );
  }

  return (
    <div className="tj-body" style={{ paddingBottom: 24 }}>
      <TopBar title={book.name} code={book.meta} onBack={() => go('library')} />
      <div style={{ padding: '14px 20px 0', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {book.passages.map((p) => (
          <div key={p.id} style={{ background: C.cardWarm, border: '1px solid #D9CBA6', borderRadius: 14, padding: 16, position: 'relative' }}>
            <div style={{ position: 'absolute', top: -1, right: 16, background: C.ink, color: C.gold, fontSize: 11, padding: '3px 10px', borderRadius: '0 0 8px 8px', letterSpacing: 2 }}>{p.chapter}</div>
            <div style={{ fontSize: 16, lineHeight: 2.1, fontWeight: 600, color: C.inkSoft, marginTop: 6 }}>{p.text}</div>
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px dashed #D9CBA6', fontSize: 12, color: C.sub, lineHeight: 1.8 }}>
              <span style={{ color: C.accent, fontWeight: 700 }}>白话：</span>{p.plain}
            </div>
          </div>
        ))}
        <button
          className="tj-reset tj-clickable"
          onClick={() => go('chat', { chatPreset: `帮我讲讲《${book.name}》` })}
          style={{ marginTop: 4, background: C.accent, color: C.creamText, textAlign: 'center', padding: 14, borderRadius: 14, fontWeight: 700, letterSpacing: 2 }}
        >带着这卷去问卦</button>
      </div>
    </div>
  );
}
