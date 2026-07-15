import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { BookDetail, BookSummary, WikiConceptDetail, WikiDomainDetail, WikiDomainSummary, WikiQuality, WikiSearchResult } from '../types';

const classics: BookSummary[] = [
  { slug: 'yijing', char: '易', name: '周易', meta: '群经之首 · 观变之书', passageCount: 64 },
  { slug: 'liaofan', char: '善', name: '了凡四训', meta: '立命 · 改过 · 积善 · 谦德', passageCount: 32 },
  { slug: 'meihua', char: '梅', name: '梅花易数', meta: '象数心易 · 观物取象', passageCount: 28 },
  { slug: 'zengguang', char: '世', name: '增广贤文', meta: '世事洞明 · 人情练达', passageCount: 46 },
  { slug: 'ganying', char: '德', name: '太上感应篇', meta: '劝善修身 · 省察日用', passageCount: 30 },
  { slug: 'bushi-zhengzong', char: '卜', name: '卜筮正宗', meta: '六爻筮法 · 古本校证', passageCount: 72 },
];

export function Library() {
  const [domains, setDomains] = useState<WikiDomainSummary[] | null>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<WikiSearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    void api.wikiDomains().then(setDomains).catch((reason) => setError(errorMessage(reason)));
  }, []);

  const totals = useMemo(() => (domains ?? []).reduce((sum, domain) => ({
    concepts: sum.concepts + domain.conceptCount,
    passages: sum.passages + domain.passageCount,
  }), { concepts: 0, passages: 0 }), [domains]);

  const search = async () => {
    const value = query.trim();
    if (!value) { setResults(null); return; }
    setSearching(true); setError('');
    try { setResults(await api.wikiSearch(value)); }
    catch (reason) { setError(errorMessage(reason)); setResults({ concepts: [], passages: [] }); }
    finally { setSearching(false); }
  };

  return (
    <div className="inner-page library-page wiki-library-page">
      <header className="premium-library-hero">
        <img src="/images/library-chamber-premium.webp" alt="木构书阁中，一本书在阅读灯下展开" />
        <div className="premium-library-shade" />
        <div className="premium-library-copy"><p className="museum-label"><span>山问知识谱</span><i />书阁</p><h1>书阁</h1><p>大师引用的每一句，<br />都能在这里翻到出处。</p></div>
        <form className="premium-library-search" onSubmit={(event) => { event.preventDefault(); void search(); }}>
          <small>检索概念与原典</small><div><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="试试「印堂」「用神」「文昌」" /><button type="submit" aria-label="搜索">⌕</button></div>
        </form>
        <div className="premium-library-meta"><span>{totals.concepts} 个概念</span><span>{totals.passages.toLocaleString('zh-CN')} 段原文</span><span>引用可追溯</span></div>
      </header>

      <div className="wiki-library-body">
        {error ? <div className="wiki-error" role="alert"><span>服务未连接</span><p>{error}</p></div> : null}
        {searching ? <WikiLoader label="正在查阅知识谱…" /> : null}
        {results && !searching ? <SearchResults results={results} query={query} onClear={() => { setQuery(''); setResults(null); }} /> : null}
        {!results && !searching ? <DomainIndex domains={domains} totals={totals} /> : null}
      </div>
    </div>
  );
}

function DomainIndex({ domains, totals }: { domains: WikiDomainSummary[] | null; totals: { concepts: number; passages: number } }) {
  if (!domains) return <WikiLoader label="正在展开知识谱…" />;
  return (
    <section className="wiki-domain-index">
      <header><div><p className="museum-label dark"><span>五大道</span><i />知识领域</p><h2>不是按书找答案，<br />而是沿着概念找到原文。</h2></div><p>从签、命、相、易、修五个领域进入。每一个概念都连接定义、相关词条与古籍证据。</p></header>
      <div className="wiki-domain-list">
        {domains.map((domain, index) => (
          <Link to={`/library/domain/${domain.slug}`} key={domain.slug}>
            <small>{String(index + 1).padStart(2, '0')}</small><span>{domain.char}</span>
            <div><h3>{domain.name}</h3><p>{domain.description}</p><em>{domain.conceptCount} 个概念 · {domain.passageCount.toLocaleString('zh-CN')} 段原文</em></div><i>进入领域 →</i>
          </Link>
        ))}
      </div>
      <footer><span>当前知识谱</span><strong>{totals.concepts}</strong><small>概念</small><strong>{totals.passages.toLocaleString('zh-CN')}</strong><small>段可溯源原文</small></footer>
    </section>
  );
}

function SearchResults({ results, query, onClear }: { results: WikiSearchResult; query: string; onClear: () => void }) {
  const empty = results.concepts.length === 0 && results.passages.length === 0;
  return (
    <section className="wiki-search-results">
      <header><div><p className="museum-label dark"><span>检索结果</span><i>{query}</i></p><h2>命中 {results.concepts.length} 个概念，{results.passages.length} 段原文</h2></div><button onClick={onClear}>清除检索 ×</button></header>
      {empty ? <div className="wiki-empty"><b>没有找到相关内容</b><p>换一个更具体的概念，或从五大道开始浏览。</p></div> : null}
      {results.concepts.length ? <div className="wiki-result-grid">{results.concepts.map((concept) => <Link to={`/library/concept/${encodeURIComponent(concept.id)}`} key={concept.id}><small>{concept.domainName} · {concept.evidenceCount} 段证据</small><h3>{concept.name}</h3><p>{concept.definition}</p><span>展开词条 →</span></Link>)}</div> : null}
      {results.passages.length ? <div className="wiki-passage-results"><h3>原文段落</h3>{results.passages.map((passage, index) => <article key={passage.sourceId ?? `${passage.book}-${index}`}><div><span>《{passage.book}》</span><small>{passage.chapter}</small><QualityBadge quality={passage.quality} /></div><blockquote>{passage.text}</blockquote></article>)}</div> : null}
    </section>
  );
}

export function LibraryDomain() {
  const { slug = '' } = useParams();
  const [detail, setDetail] = useState<WikiDomainDetail | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { void api.wikiDomain(slug).then(setDetail).catch((reason) => setError(errorMessage(reason))); }, [slug]);
  if (!detail) return <WikiPageState title="知识领域" error={error} />;

  return (
    <div className="wiki-detail-page">
      <header className="wiki-domain-hero"><div className="wiki-breadcrumb"><Link to="/library">书阁</Link><span>／</span><b>{detail.name}</b></div><span className="wiki-domain-char">{detail.char}</span><div><p className="museum-label"><span>知识领域</span><i />{detail.conceptCount} 个概念</p><h1>{detail.name}</h1><p>{detail.description}</p></div><aside><strong>{detail.passageCount.toLocaleString('zh-CN')}</strong><span>段原文证据</span><small>{detail.books.length} 部来源古籍</small></aside></header>
      <main className="wiki-domain-content">
        <section className="wiki-concept-ledger"><header><div><p>核心概念</p><h2>沿着词条，进入原典。</h2></div><span>{detail.concepts.length} ENTRIES</span></header>{detail.concepts.map((concept, index) => <Link to={`/library/concept/${encodeURIComponent(concept.id)}`} key={concept.id}><small>{String(index + 1).padStart(2, '0')}</small><div><h3>{concept.name}</h3><p>{concept.definition}</p><span>{concept.intents.join(' · ')}</span></div><aside><b>{concept.evidenceCount}</b><em>段证据</em><i>→</i></aside></Link>)}</section>
        <aside className="wiki-source-books"><p>来源书籍</p><h2>这组知识从哪里来</h2>{detail.books.map((book) => <article key={book.slug}><span>典</span><div><b>{book.name}</b><small>{book.meta || '知识谱来源文献'}</small></div></article>)}</aside>
      </main>
    </div>
  );
}

export function LibraryConcept() {
  const { conceptId = '' } = useParams();
  const [detail, setDetail] = useState<WikiConceptDetail | null>(null);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  useEffect(() => { void api.wikiConcept(conceptId).then(setDetail).catch((reason) => setError(errorMessage(reason))); }, [conceptId]);
  if (!detail) return <WikiPageState title="概念词条" error={error} />;

  const toggle = (id: string) => setExpanded((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  return (
    <div className="wiki-concept-page">
      <header className="wiki-concept-heading"><div className="wiki-breadcrumb"><Link to="/library">书阁</Link><span>／</span><Link to={`/library/domain/${detail.domain}`}>{detail.domainName}</Link><span>／</span><b>{detail.name}</b></div><div><p className="museum-label"><span>{detail.domainName}</span><i />概念词条</p><h1>{detail.name}</h1>{detail.aliases.length ? <small>又称：{detail.aliases.join(' · ')}</small> : null}</div><QualityBadge quality={detail.status} /></header>
      <main className="wiki-concept-layout">
        <article className="wiki-definition"><p>白话释义</p><blockquote>{detail.definition}</blockquote>{detail.intents.length ? <div><span>用于</span>{detail.intents.map((intent) => <i key={intent}>{intent}</i>)}</div> : null}{detail.related.length ? <section><p>相关概念</p>{detail.related.map((related) => <Link key={related.id} to={`/library/concept/${encodeURIComponent(related.id)}`}><b>{related.name}</b><small>{related.relation}</small><span>→</span></Link>)}</section> : null}<Link className="wiki-ask-link" to={`/chat?prompt=${encodeURIComponent(`帮我讲讲「${detail.name}」`)}`}>带着这个概念去问室 <span>→</span></Link></article>
        <section className="wiki-evidence"><header><div><p>原文证据</p><h2>每一句，都能回到出处。</h2></div><span>{detail.evidence.length} / {detail.evidenceTotal}</span></header>{detail.evidence.length ? detail.evidence.map((evidence, index) => { const open = expanded.has(evidence.sourceId); return <article key={evidence.sourceId}><div className="wiki-evidence-index"><span>{String(index + 1).padStart(2, '0')}</span><QualityBadge quality={evidence.quality} /></div><div><p>《{evidence.book}》<small>{evidence.chapter}</small></p><blockquote className={open ? 'is-open' : ''}>{evidence.text}</blockquote><button onClick={() => toggle(evidence.sourceId)}>{open ? '收起原文 ↑' : '展开原文 ↓'}</button></div></article>; }) : <div className="wiki-empty"><b>暂无可展示证据</b><p>该词条仍在整理中。</p></div>}<footer>按历史文献知识保存，不等同于现代医学、法律或确定性现实结论。</footer></section>
      </main>
    </div>
  );
}

function QualityBadge({ quality }: { quality: WikiQuality }) {
  const label = quality === 'verified' ? '已校验' : quality === 'review-needed' ? '待校验' : '不采用';
  return <span className={`wiki-quality ${quality}`}>{label}</span>;
}

function WikiLoader({ label }: { label: string }) { return <div className="wiki-loader" role="status"><span>谱</span><p>{label}</p></div>; }
function WikiPageState({ title, error }: { title: string; error: string }) { return <div className="wiki-page-state"><Link to="/library">← 返回书阁</Link><div>{error ? <><b>{title}暂未载入</b><p>{error}</p></> : <WikiLoader label={`正在展开${title}…`} />}</div></div>; }
function errorMessage(reason: unknown) { return reason instanceof ApiError ? reason.message : '内容暂未载入，请稍后再试'; }

export function Book() {
  const { slug = '' } = useParams();
  const [book, setBook] = useState<BookDetail | null>(null);
  useEffect(() => { void api.book(slug).then(setBook).catch(() => undefined); }, [slug]);
  const fallback = classics.find((item) => item.slug === slug) ?? classics[0];
  return (
    <div className="inner-page reading-page">
      <aside className="reading-index"><Link to="/library">←　返回书阁</Link><p className="aside-label">章节目录</p>{(book?.passages ?? []).slice(0, 12).map((passage, index) => <a key={passage.id} href={`#passage-${passage.id}`}><span>{String(index + 1).padStart(2, '0')}</span>{passage.chapter}</a>)}</aside>
      <article className="reading-sheet"><header><p className="eyebrow dark">山问藏本 · 古籍新读</p><h1>{book?.name ?? fallback.name}</h1><p>{book?.meta ?? fallback.meta}</p></header>{book?.passages?.length ? book.passages.map((passage) => <section key={passage.id} id={`passage-${passage.id}`}><small>{passage.chapter}</small><h2>{passage.text}</h2>{passage.plain ? <p>{passage.plain}</p> : null}</section>) : <section><small>卷一 · 立命之学</small><h2>务要日日知非，日日改过；一日不知非，即一日安于自是。</h2><p>真正的改变从察觉开始。看见自己惯常的反应，才有机会做出不同的选择。古书所说的“改命”，在这里更接近持续修正自己的行为。</p></section>}<div className="reading-end">卷终 · 合卷静思</div></article>
      <aside className="reading-tools"><span>原</span><span>译</span><Link to="/chat">问</Link></aside>
    </div>
  );
}
