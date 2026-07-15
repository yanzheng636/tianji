import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import type { BookDetail, BookSummary } from '../types';

const classics: BookSummary[] = [
  { slug: 'yijing', char: '易', name: '周易', meta: '群经之首 · 观变之书', passageCount: 64 },
  { slug: 'liaofan', char: '善', name: '了凡四训', meta: '立命 · 改过 · 积善 · 谦德', passageCount: 32 },
  { slug: 'meihua', char: '梅', name: '梅花易数', meta: '象数心易 · 观物取象', passageCount: 28 },
  { slug: 'zengguang', char: '世', name: '增广贤文', meta: '世事洞明 · 人情练达', passageCount: 46 },
  { slug: 'ganying', char: '德', name: '太上感应篇', meta: '劝善修身 · 省察日用', passageCount: 30 },
  { slug: 'bushi-zhengzong', char: '卜', name: '卜筮正宗', meta: '六爻筮法 · 古本校证', passageCount: 72 },
];

export function Library() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [query, setQuery] = useState('');
  useEffect(() => { void api.books().then(setBooks).catch(() => undefined); }, []);
  const source = books.length ? books : classics;
  const shown = source.filter((book) => `${book.name}${book.meta}`.includes(query.trim()));
  return (
    <div className="inner-page library-page">
      <header className="premium-library-hero">
        <img src="/images/library-chamber-premium.webp" alt="木构藏经阁中，一本书在阅读灯下展开" />
        <div className="premium-library-shade" />
        <div className="premium-library-copy"><p className="museum-label"><span>天机寺藏本</span><i />SCRIPTURE ARCHIVE</p><h1>藏经阁</h1><p>古籍不是答案，<br />是走过长路的人留下的灯。</p></div>
        <div className="premium-library-search"><small>检索馆藏</small><div><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入书名、章节或主题" /><span>⌕</span></div></div>
        <div className="premium-library-meta"><span>馆藏 {source.length} 部</span><span>原文与释义分栏呈现</span><span>引用可追溯</span></div>
      </header>
      <div className="content-wrap">
        <section className="premium-featured-book"><div className="premium-book-spine"><small>古籍新读</small><span>了<br />凡<br />四<br />训</span><i>天机寺校读</i></div><div><p className="museum-label dark"><span>今日推荐</span><i />CURATOR'S NOTE</p><h2>命由我作，<br />福自己求。</h2><p>《了凡四训》不是许愿得偿的故事，而是一个人如何从“相信命定”，走向“为自己的选择负责”。</p><Link to="/library/liaofan">展开今日一卷 <span>→</span></Link></div><blockquote>从前种种，譬如昨日死；<br />从后种种，譬如今日生。<small>—《了凡四训》</small></blockquote></section>
        <section className="book-section"><div className="section-row"><div><p className="aside-label">馆藏索引</p><h2 className="section-title">择一卷而读</h2></div><small>原文与现代释义分栏呈现 · 引用可追溯</small></div><div className="books-grid">{shown.map((book, index) => <Link to={`/library/${book.slug}`} className="book-item" key={book.slug}><div className={`book-cover color-${index % 4}`}><small>天机寺藏</small><span>{book.char}</span><i>{book.name}</i></div><div><b>{book.name}</b><p>{book.meta}</p><small>{book.passageCount} 则可读段落</small></div></Link>)}</div></section>
      </div>
    </div>
  );
}

export function Book() {
  const { slug = '' } = useParams();
  const [book, setBook] = useState<BookDetail | null>(null);
  useEffect(() => { void api.book(slug).then(setBook).catch(() => undefined); }, [slug]);
  const fallback = classics.find((item) => item.slug === slug) ?? classics[0];
  return (
    <div className="inner-page reading-page">
      <aside className="reading-index"><Link to="/library">←　返回藏经阁</Link><p className="aside-label">章节目录</p>{(book?.passages ?? []).slice(0, 12).map((passage, index) => <a key={passage.id} href={`#passage-${passage.id}`}><span>{String(index + 1).padStart(2, '0')}</span>{passage.chapter}</a>)}</aside>
      <article className="reading-sheet"><header><p className="eyebrow dark">天机寺藏本 · 古籍新读</p><h1>{book?.name ?? fallback.name}</h1><p>{book?.meta ?? fallback.meta}</p></header>{book?.passages?.length ? book.passages.map((passage) => <section key={passage.id} id={`passage-${passage.id}`}><small>{passage.chapter}</small><h2>{passage.text}</h2>{passage.plain ? <p>{passage.plain}</p> : null}</section>) : <section><small>卷一 · 立命之学</small><h2>务要日日知非，日日改过；一日不知非，即一日安于自是。</h2><p>真正的改变从察觉开始。看见自己惯常的反应，才有机会做出不同的选择。古书所说的“改命”，在这里更接近持续修正自己的行为。</p></section>}<div className="reading-end">卷终 · 合卷静思</div></article>
      <aside className="reading-tools"><span>原</span><span>译</span><Link to="/chat">问</Link></aside>
    </div>
  );
}
