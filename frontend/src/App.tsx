import { useCallback, useEffect, useState } from 'react';
import { Header, DrawerKind } from './components/Header';
import { ChatBox } from './components/ChatBox';
import { InputArea } from './components/InputArea';
import { BenchmarksPage } from './components/BenchmarksPage';
import { Drawer } from './components/Drawer';
import { SessionLibrary } from './components/SessionLibrary';
import { DBProfileForm } from './components/DBProfileForm';
import { DatabaseSelector } from './components/DatabaseSelector';
import { useQueryStore } from './stores/queryStore';
import { useDatabaseStore } from './stores/databaseStore';

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
    const activeDbName = useDatabaseStore(s => s.activeDbName);

    useEffect(() => { applyTheme(themeIndex); }, [themeIndex]);

    const cycleTheme = useCallback(() => {
        setThemeIndex(prev => (prev + 1) % THEMES.length);
    }, []);

    const toggleDrawer = useCallback((kind: DrawerKind) => {
        setDrawer(prev => (prev === kind ? null : kind));
    }, []);

    if (!activeDbName) {
        return (
            <div className="container">
                <DatabaseSelector />
            </div>
        );
    }

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
