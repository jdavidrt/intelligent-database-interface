import { useRef } from 'react';

interface InputAreaProps {
    isWaiting: boolean;
    onSend: (message: string) => void;
    onStop: () => void;
}

export function InputArea({ isWaiting, onSend, onStop }: InputAreaProps) {
    const inputRef = useRef<HTMLInputElement>(null);

    const handleSend = () => {
        const value = inputRef.current?.value.trim() ?? '';
        if (!value) return;
        if (inputRef.current) inputRef.current.value = '';
        onSend(value);
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') handleSend();
    };

    return (
        <div className="input-area">
            <input
                ref={inputRef}
                className="chat-input"
                type="text"
                placeholder="Type your message here..."
                autoComplete="off"
                disabled={isWaiting}
                onKeyDown={handleKeyDown}
            />
            <button
                className="send-btn"
                disabled={isWaiting}
                onClick={handleSend}
            >
                Send
            </button>
            <button
                className="stop-btn"
                disabled={!isWaiting}
                onClick={onStop}
            >
                Stop
            </button>
        </div>
    );
}
