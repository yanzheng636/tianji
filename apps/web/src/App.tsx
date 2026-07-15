import { useEffect } from 'react';
import { useApp, type Screen } from './store/app';
import { IOSDevice } from './components/IOSDevice';
import { TabBar, Toast } from './components/ui';
import { LoginSheet } from './components/LoginSheet';
import { Home } from './screens/Home';
import { Hall } from './screens/Hall';
import { Qian } from './screens/Qian';
import { Incense } from './screens/Incense';
import { Wish } from './screens/Wish';
import { Library } from './screens/Library';
import { Domain } from './screens/Domain';
import { Concept } from './screens/Concept';
import { Book } from './screens/Book';
import { Chat } from './screens/Chat';
import { Profile } from './screens/Profile';
import { Vip } from './screens/Vip';
import { Palm } from './screens/Palm';

const SCREENS: Record<Screen, () => JSX.Element> = {
  home: Home,
  hall: Hall,
  qian: Qian,
  incense: Incense,
  wish: Wish,
  library: Library,
  domain: Domain,
  concept: Concept,
  book: Book,
  chat: Chat,
  profile: Profile,
  vip: Vip,
  palm: Palm,
};

// 显示底部 Tab 的页面
const TAB_SCREENS: Screen[] = ['home', 'wish', 'chat', 'profile'];

export default function App() {
  const { ready, nav, init, loginOpen, closeLogin } = useApp();

  useEffect(() => {
    init();
  }, [init]);

  const Current = SCREENS[nav.screen] ?? Home;
  const showTabs = TAB_SCREENS.includes(nav.screen);

  return (
    <IOSDevice>
      <div className="tj-app">
        {ready ? (
          // key 让切换页面时组件重挂载，避免脏状态串页
          <Current key={nav.screen + (nav.hallKey ?? '') + (nav.bookSlug ?? '') + (nav.domainSlug ?? '') + (nav.conceptId ?? '')} />
        ) : (
          <div style={{ flex: 1, display: 'grid', placeItems: 'center' }}>
            <div className="tj-spin" />
          </div>
        )}
        {showTabs && <TabBar />}
        <Toast />
        {loginOpen && <LoginSheet onClose={closeLogin} />}
      </div>
    </IOSDevice>
  );
}
