import { createContext, lazy, Suspense, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { api } from './api';
import { AppShell } from './components/AppShell';
import { Home } from './pages/Home';
import type { MetaConfig, User } from './types';

const Chat = lazy(() => import('./pages/Chat').then((m) => ({ default: m.Chat })));
const Qian = lazy(() => import('./pages/Qian').then((m) => ({ default: m.Qian })));
const Incense = lazy(() => import('./pages/Incense').then((m) => ({ default: m.Incense })));
const Wishes = lazy(() => import('./pages/Wishes').then((m) => ({ default: m.Wishes })));
const Library = lazy(() => import('./pages/Library').then((m) => ({ default: m.Library })));
const LibraryDomain = lazy(() => import('./pages/Library').then((m) => ({ default: m.LibraryDomain })));
const LibraryConcept = lazy(() => import('./pages/Library').then((m) => ({ default: m.LibraryConcept })));
const Book = lazy(() => import('./pages/Library').then((m) => ({ default: m.Book })));
const Profile = lazy(() => import('./pages/Profile').then((m) => ({ default: m.Profile })));
const Lamp = lazy(() => import('./pages/Lamp').then((m) => ({ default: m.Lamp })));
const Palm = lazy(() => import('./pages/Palm').then((m) => ({ default: m.Palm })));

interface AppContextValue {
  user: User | null;
  config: MetaConfig | null;
  sessionReady: boolean;
  refreshUser: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);
export const useTianji = () => {
  const value = useContext(AppContext);
  if (!value) throw new Error('useTianji must be used within App');
  return value;
};

function PageLoader() {
  return <div className="page-loader" role="status"><span className="seal-spinner">山</span><p>正在入山…</p></div>;
}

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<MetaConfig | null>(null);
  const [sessionReady, setSessionReady] = useState(false);

  const refreshUser = async () => setUser(await api.me());

  useEffect(() => {
    let active = true;
    void Promise.allSettled([api.ensureGuest(), api.config()]).then(([guest, meta]) => {
      if (!active) return;
      if (guest.status === 'fulfilled') setUser(guest.value.user);
      if (meta.status === 'fulfilled') setConfig(meta.value);
      setSessionReady(true);
    });
    return () => { active = false; };
  }, []);

  const context = useMemo(() => ({ user, config, sessionReady, refreshUser }), [user, config, sessionReady]);

  return (
    <AppContext.Provider value={context}>
      <AppShell>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/temple" element={<Home />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/qian" element={<Qian />} />
            <Route path="/incense" element={<Incense />} />
            <Route path="/wishes" element={<Wishes />} />
            <Route path="/library" element={<Library />} />
            <Route path="/library/domain/:slug" element={<LibraryDomain />} />
            <Route path="/library/concept/:conceptId" element={<LibraryConcept />} />
            <Route path="/library/:slug" element={<Book />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/profile/chart" element={<Profile />} />
            <Route path="/lamp" element={<Lamp />} />
            <Route path="/palm" element={<Palm />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </AppShell>
    </AppContext.Provider>
  );
}
