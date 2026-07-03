import { useCallback, useEffect, useState } from 'react';
import { Header, DrawerKind } from './components/Header';
import { ChatBox } from './components/ChatBox';
import { InputArea } from './components/InputArea';
import { BenchmarksPage } from './components/BenchmarksPage';
import { Drawer } from './components/Drawer';
import { SessionLibrary } from './components/SessionLibrary';
import { DBProfileForm } from './components/DBProfileForm';
import { useQueryStore } from './stores/queryStore';
import { useDbProfileStore } from './stores/dbProfileStore';

type Page = 'chat' | 'benchmarks';

const THEMES = [
    { name: 'Mystic Dusk', key: 'mystic-dusk' },
    { name: 'Desert Bloom', key: 'desert-bloom' },
    { name: 'Abyss', key: 'abyss' },
    { name: 'Neon Burst', key: 'neon-burst' },
    { name: 'Lavender Dream', key: 'lavender-dream' },
] as const;

function loadThemeIndex(): number {
    const saved = localStorage.getItem('idi-theme');
    if (saved !== null) {
        const idx = parseInt(saved, 10);
        if (!isNaN(idx) && idx >= 0 && idx < THEMES.length) return idx;
    }
    return 0;
}

function applyTheme(index: number) {
    const theme = THEMES[index];
    if (theme.key === 'mystic-dusk') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', theme.key);
    }
    localStorage.setItem('idi-theme', String(index));
}

export default function App() {
    const [page, setPage] = useState<Page>('chat');
    const [themeIndex, setThemeIndex] = useState<number>(loadThemeIndex);
    const [drawer, setDrawer] = useState<DrawerKind | null>(null);

    const isWaiting = useQueryStore(s => s.isWaiting);
    const send = useQueryStore(s => s.send);
    const stop = useQueryStore(s => s.stop);

    useEffect(() => { applyTheme(themeIndex); }, [themeIndex]);

    // Try the profile once on mount (404 is fine until the first query runs) —
    // autocomplete and the DB Profile card both feed off it.
    useEffect(() => {
        void useDbProfileStore.getState().loadProfile();
    }, []);

    const cycleTheme = useCallback(() => {
        setThemeIndex(prev => (prev + 1) % THEMES.length);
    }, []);

    const toggleDrawer = useCallback((kind: DrawerKind) => {
        setDrawer(prev => (prev === kind ? null : kind));
    }, []);

    return (
        <div className="container">
            <Header
                themeName={THEMES[themeIndex].name}
                onThemeCycle={cycleTheme}
                page={page}
                onPageChange={setPage}
                drawer={drawer}
                onDrawerToggle={toggleDrawer}
            />

            {page === 'chat' ? (
                <>
                    <ChatBox />
                    <InputArea
                        isWaiting={isWaiting}
                        onSend={text => void send(text)}
                        onStop={stop}
                    />
                </>
            ) : (
                <BenchmarksPage />
            )}

            {drawer === 'sessions' && (
                <Drawer title="Session Library" onClose={() => setDrawer(null)}>
                    <SessionLibrary onClose={() => setDrawer(null)} />
                </Drawer>
            )}

            {drawer === 'profile' && (
                <Drawer title="Database Map" onClose={() => setDrawer(null)}>
                    <DBProfileForm />
                </Drawer>
            )}
        </div>
    );
}
