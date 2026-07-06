import { useMemo, useRef, useState } from 'react';
import { useDbProfileStore } from '../stores/dbProfileStore';
import { mergeVocabulary, suggest } from '../utils/autocompleteVocabulary';
import styles from './InputArea.module.css';

interface InputAreaProps {
    isWaiting: boolean;
    onSend: (message: string) => void;
    onStop: () => void;
}

export function InputArea({ isWaiting, onSend, onStop }: InputAreaProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [value, setValue] = useState('');
    const [suggestions, setSuggestions] = useState<string[]>([]);
    // Dropdown dismissed via Backspace/Delete/Escape; cleared by the next printable key.
    const [suppressed, setSuppressed] = useState(false);

    const profile = useDbProfileStore(s => s.profile);
    const vocab = useMemo(() => mergeVocabulary(profile), [profile]);

    const dropdownOpen = suggestions.length > 0 && !suppressed;

    const handleChange = (next: string) => {
        // Text grew (typed or pasted) → a new partial word may start matching.
        if (next.length > value.length) setSuppressed(false);
        setValue(next);
        setSuggestions(suggest(vocab, next));
    };

    /** Replace the in-progress last word with `word`, keeping the rest of the sentence. */
    const accept = (word: string) => {
        const parts = value.split(/(\s+)/);
        parts[parts.length - 1] = word;
        setValue(parts.join('') + ' ');
        setSuggestions([]);
        inputRef.current?.focus();
    };

    const handleSend = () => {
        const text = value.trim();
        if (!text) return;
        setValue('');
        setSuggestions([]);
        onSend(text);
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Tab' && dropdownOpen) {
            // Tab is the only key that accepts a suggestion.
            e.preventDefault();
            accept(suggestions[0]);
        } else if (e.key === 'Enter') {
            handleSend();
        } else if (
            (e.key === 'Backspace' || e.key === 'Delete' || e.key === 'Escape') &&
            dropdownOpen
        ) {
            // Close the dropdown; Backspace/Delete still perform their edit.
            setSuppressed(true);
        } else if (e.key.length === 1 && suppressed) {
            // A new partial word may start matching again.
            setSuppressed(false);
        }
    };

    return (
        <div className="input-area">
            <div className={styles.wrapper}>
                {dropdownOpen && (
                    <div className={styles.dropdown}>
                        {suggestions.map((word, i) => (
                            <button
                                key={word}
                                type="button"
                                className={i === 0 ? `${styles.item} ${styles.itemTop}` : styles.item}
                                // onMouseDown so the input keeps focus (no blur-close race).
                                onMouseDown={e => {
                                    e.preventDefault();
                                    accept(word);
                                }}
                            >
                                {word}
                                {i === 0 && <span className={styles.hint}>Tab ⇥ accepts</span>}
                            </button>
                        ))}
                    </div>
                )}
                <input
                    ref={inputRef}
                    className="chat-input"
                    type="text"
                    placeholder="Type your message here..."
                    autoComplete="off"
                    disabled={isWaiting}
                    value={value}
                    onChange={e => handleChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={() => setSuppressed(true)}
                />
            </div>
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
