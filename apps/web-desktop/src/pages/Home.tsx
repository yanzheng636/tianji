import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { TodayFortune } from '../types';

const practices = [
  { to: '/qian', index: '壹', title: '求一支签', body: '把犹疑放在案前，借一句古语看清真正所问。' },
  { to: '/chat', index: '贰', title: '问一件事', body: '从可追溯的古籍原文中，寻找另一种观看方法。' },
  { to: '/incense', index: '叁', title: '燃一炷香', body: '把半个时辰留给自己，不急着向外寻找答案。' },
  { to: '/wishes', index: '肆', title: '写一个愿', body: '说清楚真正珍惜的事，也确认愿意为它做什么。' },
] as const;

export function Home() {
  const [today, setToday] = useState<TodayFortune | null>(null);
  useEffect(() => { void api.today().then(setToday).catch(() => undefined); }, []);

  return (
    <div className="premium-home">
      <section className="premium-hero" aria-labelledby="premium-home-title">
        <img className="premium-hero-image" src="/images/temple-hero-premium.webp" alt="暮色中的山间寺院，石阶通向亮着灯的主殿" fetchPriority="high" />
        <div className="premium-hero-shade" />
        <div className="premium-hero-grain" />

        <div className="premium-hero-copy">
          <p className="museum-label"><span>东方数字寺院</span><i />丙午年</p>
          <h1 id="premium-home-title"><span>入山</span><em>·</em><span>问心</span></h1>
          <p>在古籍与当下之间，<br />给困惑一处安放之所。</p>
          <div className="premium-hero-actions">
            <Link to="/chat" className="action-solid">开始一问</Link>
            <Link to="/qian" className="action-quiet">今日求签 <span>↗</span></Link>
          </div>
        </div>

        <div className="temple-map" aria-label="寺院场景入口">
          <Link to="/library" className="map-marker marker-library"><i /><span><small>古籍可考</small>藏经阁</span></Link>
          <Link to="/chat" className="map-marker marker-chat"><i /><span><small>有惑可问</small>问天殿</span></Link>
          <Link to="/incense" className="map-marker marker-incense"><i /><span><small>一炷清香</small>香火殿</span></Link>
        </div>

        <aside className="premium-temple-note">
          <span>今日寺语</span>
          <blockquote>静不是没有声音，<br />是终于听见自己。</blockquote>
          <small>{today ? `${today.ganzhi} · 宜 ${today.yi.slice(0, 2).join('、')}` : '清风入山 · 灯火初上'}</small>
        </aside>

        <div className="premium-hero-foot">
          <span>TIANJI TEMPLE · 传统文化娱乐与心理疗愈</span>
          <a href="#today-practice">向下游寺 <i>↓</i></a>
          <span>{today?.date ?? '七月十五'} · 山门已开</span>
        </div>
      </section>

      <section className="practice-section" id="today-practice">
        <header>
          <p className="museum-label dark"><span>今日可做</span><i />FOUR PRACTICES</p>
          <h2>先安顿一念，<br />再决定往哪里去。</h2>
          <p>这里不替你预测未来。每一种仪式，都是一次认真看见自己的机会。</p>
        </header>
        <div className="practice-list">
          {practices.map((item) => (
            <Link to={item.to} key={item.to}>
              <small>{item.index}</small>
              <div><h3>{item.title}</h3><p>{item.body}</p></div>
              <span>↗</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="source-section">
        <div className="source-visual"><span>典</span><p>古籍原文<br />可追溯引用</p></div>
        <div className="source-copy"><p className="museum-label dark"><span>不是答案，是照见</span><i />TEXTUAL EVIDENCE</p><h2>借古人的文字，<br />看清此刻的心。</h2><p>天机寺收录真实古籍文本。每次解读都尽可能回到原文，让你知道一句话从哪里来，也保留自己判断的空间。</p><Link to="/library">走进藏经阁 <span>→</span></Link></div>
      </section>
    </div>
  );
}
