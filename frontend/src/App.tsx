import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { ChatBox, Message } from './components/ChatBox';
import { InputArea } from './components/InputArea';
import { BenchmarksPage } from './components/BenchmarksPage';
import { streamQuery, buildResultHTML, AgentEvent, QueryResult } from './utils/queryClient';

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

const INITIAL_MESSAGE: Message = {
    id: 'init',
    role: 'bot',
    content: '<p>Hello! How can I help you today?</p>',
};

export default function App() {
    const [page, setPage] = useState<Page>('chat');
    const [themeIndex, setThemeIndex] = useState<number>(loadThemeIndex);
    const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
    const [isWaiting, setIsWaiting] = useState(false);
    const [progressEvents, setProgressEvents] = useState<AgentEvent[]>([]);
    const abortControllerRef = useRef<AbortController | null>(null);
    // Reused across turns so the pipeline gets multi-turn history + clarification replies.
    const sessionIdRef = useRef<string | null>(null);

    useEffect(() => { applyTheme(themeIndex); }, [themeIndex]);

    const cycleTheme = useCallback(() => {
        setThemeIndex(prev => (prev + 1) % THEMES.length);
    }, []);

    const pushBot = (content: string) =>
        setMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'bot', content }]);

    const sendMessage = useCallback(async (userText: string) => {
        setMessages(prev => [
            ...prev,
            { id: crypto.randomUUID(), role: 'user', content: userText },
        ]);

        setIsWaiting(true);
        setProgressEvents([]);
        abortControllerRef.current = new AbortController();

        try {
            let finalResult: QueryResult | null = null;
            for await (const item of streamQuery(
                userText, sessionIdRef.current, abortControllerRef.current.signal,
            )) {
                if (item.type === 'event') {
                    setProgressEvents(prev => [...prev, item]);
                } else {
                    finalResult = item;
                }
            }

            if (finalResult) {
                sessionIdRef.current = finalResult.session_id;
                pushBot(buildResultHTML(finalResult));
            } else {
                pushBot('<p>⚠️ The pipeline returned no result.</p>');
            }
        } catch (err: unknown) {
            if (err instanceof Error && err.name === 'AbortError') {
                pushBot('<p>⚠️ Request cancelled.</p>');
            } else {
                pushBot('<p>⚠️ Could not connect to the backend. Is it running on port 5000?</p>');
            }
        } finally {
            setIsWaiting(false);
            setProgressEvents([]);
            abortControllerRef.current = null;
        }
    }, []);

    const handleStop = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    return (
        <div className="container">
            <Header
                themeName={THEMES[themeIndex].name}
                onThemeCycle={cycleTheme}
                page={page}
                onPageChange={setPage}
            />

            {page === 'chat' ? (
                <>
                    <ChatBox
                        messages={messages}
                        isWaiting={isWaiting}
                        progressEvents={progressEvents}
                    />
                    <InputArea
                        isWaiting={isWaiting}
                        onSend={sendMessage}
                        onStop={handleStop}
                    />
                </>
            ) : (
                <BenchmarksPage />
            )}
        </div>
    );
}
