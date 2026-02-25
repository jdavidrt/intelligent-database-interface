import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { ChatBox, Message } from './components/ChatBox';
import { InputArea } from './components/InputArea';
import { buildBotMessageHTML } from './utils/markdownRenderer';

const BACKEND_URL = 'http://localhost:5000/chat';

const THEMES = [
    { name: 'Mystic Dusk',    key: 'mystic-dusk' },
    { name: 'Desert Bloom',   key: 'desert-bloom' },
    { name: 'Abyss',          key: 'abyss' },
    { name: 'Neon Burst',     key: 'neon-burst' },
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
    const [themeIndex, setThemeIndex] = useState<number>(loadThemeIndex);
    const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
    const [isWaiting, setIsWaiting] = useState(false);
    const [typingText, setTypingText] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    useEffect(() => { applyTheme(themeIndex); }, [themeIndex]);

    const cycleTheme = useCallback(() => {
        setThemeIndex(prev => (prev + 1) % THEMES.length);
    }, []);

    const handleTypingDone = useCallback((html: string) => {
        setTypingText(null);
        if (html) {
            setMessages(prev => [
                ...prev,
                { id: crypto.randomUUID(), role: 'bot', content: html },
            ]);
        }
    }, []);

    const sendMessage = useCallback(async (userText: string) => {
        setMessages(prev => [
            ...prev,
            { id: crypto.randomUUID(), role: 'user', content: userText },
        ]);

        setIsWaiting(true);
        abortControllerRef.current = new AbortController();

        try {
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userText }),
                signal: abortControllerRef.current.signal,
            });
            const data = await response.json();
            setIsWaiting(false);

            if (data.response) {
                setTypingText(data.response);
            } else {
                const errText = `⚠️ Error: ${data.error || 'Unknown error'}`;
                setMessages(prev => [
                    ...prev,
                    { id: crypto.randomUUID(), role: 'bot', content: buildBotMessageHTML(errText) },
                ]);
            }
        } catch (err: unknown) {
            setIsWaiting(false);
            let errMsg: string;
            if (err instanceof Error && err.name === 'AbortError') {
                errMsg = '⚠️ Request cancelled.';
            } else {
                errMsg = '⚠️ Could not connect to the backend. Is it running on port 5000?';
            }
            setMessages(prev => [
                ...prev,
                { id: crypto.randomUUID(), role: 'bot', content: `<p>${errMsg}</p>` },
            ]);
        } finally {
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
            <Header themeName={THEMES[themeIndex].name} onThemeCycle={cycleTheme} />
            <ChatBox
                messages={messages}
                isWaiting={isWaiting}
                typingText={typingText}
                onTypingDone={handleTypingDone}
            />
            <InputArea
                isWaiting={isWaiting}
                onSend={sendMessage}
                onStop={handleStop}
            />
        </div>
    );
}
