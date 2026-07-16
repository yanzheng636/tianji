import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, FormEvent } from 'react';
import { api, ApiError } from '../api';
import type { Wish, WishPool } from '../types';

const EMPTY_WISHES: Wish[] = [];
const DATE_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
});

type WishStarStyle = CSSProperties & {
  '--wish-star-x': string;
  '--wish-star-y': string;
  '--wish-star-size': string;
  '--wish-star-delay': string;
};

type WishDetailStyle = CSSProperties & {
  '--wish-detail-x': string;
  '--wish-detail-y': string;
};

interface WishStarPoint {
  wish: Wish;
  x: number;
  y: number;
  style: WishStarStyle;
}

function hashWishId(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function getWishStarPoint(wish: Wish, index: number): WishStarPoint {
  const seed = hashWishId(`${wish.id}-${index}`);
  const x = 10 + (seed % 8200) / 100;
  const y = 8 + ((seed >>> 8) % 5700) / 100;
  return {
    wish,
    x,
    y,
    style: {
      '--wish-star-x': `${x}%`,
      '--wish-star-y': `${y}%`,
      '--wish-star-size': `${12 + ((seed >>> 16) % 7)}px`,
      '--wish-star-delay': `${-((seed >>> 20) % 50) / 10}s`,
    },
  };
}

function wishDate(value: string) {
  return DATE_FORMAT.format(new Date(value));
}

export function Wishes() {
  const [pool, setPool] = useState<WishPool | null>(null);
  const [loadError, setLoadError] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [hoveredWishId, setHoveredWishId] = useState<string | null>(null);
  const [focusedWishId, setFocusedWishId] = useState<string | null>(null);
  const pointerFocusRef = useRef(false);
  const [newWishId, setNewWishId] = useState<string | null>(null);
  const [fulfillingId, setFulfillingId] = useState<string | null>(null);
  const [fulfillError, setFulfillError] = useState<{ id: string; message: string } | null>(null);

  const loadPool = useCallback(async () => {
    setLoadError('');
    try {
      const nextPool = await api.wishPool();
      setPool(nextPool);
    } catch (error) {
      setLoadError(error instanceof ApiError ? error.message : '愿星暂未显现，请稍后再看');
    }
  }, []);

  useEffect(() => { void loadPool(); }, [loadPool]);

  const mine = pool?.mine ?? EMPTY_WISHES;
  const { activeWishes, fulfilledCount } = useMemo(() => {
    const active: Wish[] = [];
    let fulfilled = 0;
    for (const wish of mine) {
      if (wish.status === 'active') active.push(wish);
      else fulfilled += 1;
    }
    return { activeWishes: active, fulfilledCount: fulfilled };
  }, [mine]);
  const { stars, connections } = useMemo(() => {
    const positioned = mine.map(getWishStarPoint);
    const chronological = [...positioned].reverse();
    return {
      stars: positioned,
      connections: chronological.slice(1).map((to, index) => {
        const from = chronological[index];
        return {
          id: `${from.wish.id}-${to.wish.id}`,
          from,
          to,
          fulfilled: from.wish.status === 'fulfilled' && to.wish.status === 'fulfilled',
        };
      }),
    };
  }, [mine]);
  const previewWishId = hoveredWishId ?? focusedWishId;
  const previewStar = stars.find(({ wish }) => wish.id === previewWishId) ?? null;

  const openEditor = (returnToHero = false) => {
    setEditorOpen(true);
    setNotice('');
    if (returnToHero) {
      window.requestAnimationFrame(() => {
        document.querySelector('.wish-observatory-hero')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setNotice('');
    try {
      const wish = await api.createWish(trimmed);
      setPool((current) => current
        ? { ...current, total: current.total + 1, mine: [wish, ...current.mine] }
        : { total: 1, floating: [], mine: [wish] });
      setNewWishId(wish.id);
      setText('');
      setEditorOpen(false);
      setNotice('愿望已记下，愿你记得为何出发');
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : '愿望暂未记下，请稍后再试');
    } finally {
      setBusy(false);
    }
  };

  const fulfill = async (wishId: string) => {
    if (fulfillingId) return;
    setFulfillingId(wishId);
    setFulfillError(null);
    try {
      const fulfilled = await api.fulfillWish(wishId);
      setPool((current) => current
        ? { ...current, mine: current.mine.map((wish) => wish.id === wishId ? fulfilled : wish) }
        : current);
      setNotice('愿已还，走过的路仍会留下一点微光');
    } catch (error) {
      setFulfillError({
        id: wishId,
        message: error instanceof ApiError ? error.message : '暂时未能还愿，请稍后再试',
      });
    } finally {
      setFulfillingId(null);
    }
  };

  return (
    <div className="wish-observatory-page">
      <section className={editorOpen ? 'wish-observatory-hero is-writing' : 'wish-observatory-hero'}>
        <div className="wish-observatory-grain" aria-hidden="true" />

        <div className="wish-observatory-copy">
          <p className="museum-label"><span>愿池</span><i />只属于你的星图</p>
          <h1>念有所向，<br />微光自来。</h1>
          <p>写下此刻真正想守住的事。愿望不会替你走路，却会在回望时提醒你为何出发。</p>
          <div className="wish-observatory-stats" aria-label="个人愿望统计">
            <strong>{pool?.total ?? '—'}</strong>
            <span>颗个人愿星</span>
            <i />
            <span>{activeWishes.length} 件仍在路上<br />{fulfilledCount} 件已经还愿</span>
          </div>
          <button className="wish-open-composer" type="button" onClick={() => openEditor()}>
            写下一颗愿星 <span>＋</span>
          </button>
          {notice ? <p className="wish-observatory-notice" role="status">{notice}</p> : null}
        </div>

        <div className="wish-private-note"><i />这片星图仅自己可见</div>

        <section className="wish-star-map" aria-label="我的愿星图">
          <svg className="wish-star-connections" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {connections.map((connection) => (
              <line
                key={connection.id}
                className={`${connection.fulfilled ? 'is-fulfilled' : 'is-active'}${connection.to.wish.id === newWishId ? ' is-new' : ''}`}
                x1={connection.from.x}
                y1={connection.from.y}
                x2={connection.to.x}
                y2={connection.to.y}
              />
            ))}
          </svg>
          {stars.map(({ wish, style }) => (
            <button
              key={wish.id}
              type="button"
              className={`wish-star ${wish.status === 'fulfilled' ? 'is-fulfilled' : 'is-active'}${wish.id === previewStar?.wish.id ? ' is-previewed' : ''}${wish.id === newWishId ? ' is-new' : ''}`}
              style={style}
              aria-label={`${wish.status === 'fulfilled' ? '已还愿' : '进行中'}：${wish.text}`}
              aria-describedby={wish.id === previewStar?.wish.id ? `wish-star-detail-${wish.id}` : undefined}
              onMouseEnter={() => setHoveredWishId(wish.id)}
              onMouseLeave={() => setHoveredWishId(null)}
              onPointerDown={(event) => {
                pointerFocusRef.current = true;
                setFocusedWishId(event.pointerType === 'touch' ? wish.id : null);
              }}
              onPointerUp={() => { pointerFocusRef.current = false; }}
              onFocus={() => {
                if (pointerFocusRef.current) {
                  pointerFocusRef.current = false;
                  return;
                }
                setFocusedWishId(wish.id);
              }}
              onBlur={() => {
                pointerFocusRef.current = false;
                setFocusedWishId(null);
              }}
            />
          ))}

          {pool === null && !loadError ? (
            <div className="wish-star-loading" role="status"><i />愿星正在显现</div>
          ) : null}
          {loadError ? (
            <div className="wish-star-empty">
              <span>隐</span><p>{loadError}</p><button type="button" onClick={() => void loadPool()}>重新查看</button>
            </div>
          ) : null}
          {pool && mine.length === 0 ? (
            <div className="wish-star-empty"><span>愿</span><p>星图尚空，写下第一件想守住的事。</p></div>
          ) : null}

          {previewStar ? (
            <article
              key={previewStar.wish.id}
              id={`wish-star-detail-${previewStar.wish.id}`}
              className={`wish-star-detail ${previewStar.x > 52 ? 'is-left' : 'is-right'} ${previewStar.y < 22 ? 'is-top' : previewStar.y > 52 ? 'is-bottom' : 'is-middle'}`}
              style={{ '--wish-detail-x': `${previewStar.x}%`, '--wish-detail-y': `${previewStar.y}%` } as WishDetailStyle}
              role="tooltip"
            >
              <header>
                <span><i />{previewStar.wish.status === 'fulfilled' ? '已还愿 · 化为余光' : '愿望进行中'}</span>
                <small>愿星心愿</small>
              </header>
              <blockquote>{previewStar.wish.text}</blockquote>
              <footer><time>{wishDate(previewStar.wish.createdAt)}</time><span>移开即收起</span></footer>
            </article>
          ) : null}
          <div className="wish-star-legend" aria-hidden="true"><span><i />仍在路上</span><span><i />已经还愿</span></div>
        </section>

        {editorOpen ? (
          <form className="wish-composer" onSubmit={submit}>
            <header><span>写下此刻最想守住的一件事</span><button type="button" onClick={() => setEditorOpen(false)}>收起 ×</button></header>
            <div className="wish-composer-entry">
              <div><textarea autoFocus maxLength={200} rows={3} value={text} onChange={(event) => setText(event.target.value)} placeholder="愿我……" /><span>{text.length} / 200</span></div>
              <button type="submit" disabled={busy || !text.trim()}>{busy ? '正在点亮…' : '点亮愿星'}<i>→</i></button>
            </div>
            <small>愿望只保存在你的个人星图中。</small>
          </form>
        ) : null}
      </section>

      <section className="wish-unfulfilled-section">
        <header>
          <div><span>MY UNFULFILLED WISHES</span><h2>尚未还愿</h2></div>
          <p><strong>{activeWishes.length}</strong> 件仍在路上</p>
        </header>

        {activeWishes.length ? (
          <div className="wish-unfulfilled-list">
            {activeWishes.map((wish) => (
              <article key={wish.id}>
                <span className="wish-row-mark">愿</span>
                <div><h3>{wish.text}</h3><time>写于 {wishDate(wish.createdAt)}</time></div>
                <span className="wish-row-status">愿望进行中</span>
                <button type="button" disabled={fulfillingId === wish.id} onClick={() => void fulfill(wish.id)}>
                  {fulfillingId === wish.id ? '正在还愿…' : '已经实现，去还愿'}
                </button>
                {fulfillError?.id === wish.id ? <p className="wish-row-error" role="alert">{fulfillError.message}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="wish-unfulfilled-empty"><span>愿</span><h3>此刻没有尚未还的愿</h3><p>写下一颗新的愿星，让想走的路更清晰一些。</p><button type="button" onClick={() => openEditor(true)}>写下愿望</button></div>
        )}
        <p className="wish-history-note">还愿后会从这里移除，但对应的星星会留在上方，成为一束柔和余光。</p>
      </section>
    </div>
  );
}
