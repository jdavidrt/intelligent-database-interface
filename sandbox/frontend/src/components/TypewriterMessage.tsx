import { useEffect, useRef, useState } from 'react';
import { buildBotMessageHTML, insideCodeFence } from '../utils/markdownRenderer';

interface TypewriterMessageProps {
    rawText: string;
    speedMs?: number;
    onDone: (html: string) => void;
}

const RENDER_EVERY = 6;

export function TypewriterMessage({ rawText, speedMs = 44, onDone }: TypewriterMessageProps) {
    const [buffer, setBuffer] = useState('');
    const [done, setDone] = useState(false);
    const indexRef = useRef(0);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const doneRef = useRef(false);

    // For error messages starting with ⚠️, skip animation
    const isError = rawText.startsWith('⚠️');

    const flush = () => {
        if (doneRef.current) return;
        doneRef.current = true;
        if (timerRef.current) clearTimeout(timerRef.current);
        setBuffer(rawText);
        setDone(true);
        onDone(isError ? '' : buildBotMessageHTML(rawText));
    };

    useEffect(() => {
        if (isError) {
            flush();
            return;
        }

        const chars = [...rawText]; // unicode-safe split
        const total = chars.length;

        const tick = () => {
            if (doneRef.current) return;
            const batchEnd = Math.min(indexRef.current + RENDER_EVERY, total);
            const newChars = chars.slice(indexRef.current, batchEnd).join('');
            indexRef.current = batchEnd;

            setBuffer(prev => {
                const next = prev + newChars;
                return next;
            });

            if (indexRef.current >= total) {
                flush();
                return;
            }
            timerRef.current = setTimeout(tick, speedMs);
        };

        timerRef.current = setTimeout(tick, speedMs);

        return () => {
            if (timerRef.current) clearTimeout(timerRef.current);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (done) return null; // parent renders the completed message

    if (isError) {
        return (
            <div className="message bot-message">
                {rawText}
            </div>
        );
    }

    // While typing: if we're inside an unclosed code fence, temporarily close it so the
    // partial SQL is rendered incrementally rather than appearing all at once at the end.
    const htmlToShow = insideCodeFence(buffer)
        ? buildBotMessageHTML(buffer + '\n```')
        : buildBotMessageHTML(buffer);

    const withCursor = htmlToShow + '<span class="typewriter-cursor"></span>';

    return (
        <div
            className="message bot-message typing-live"
            dangerouslySetInnerHTML={{ __html: withCursor }}
            onClick={flush}
        />
    );
}
