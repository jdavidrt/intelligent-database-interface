import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypewriterMessage } from './TypewriterMessage';
import { GeneratingIndicator } from './GeneratingIndicator';

export interface Message {
    id: string;
    role: 'user' | 'bot';
    /** For user: plain text. For bot: rendered HTML string. */
    content: string;
}

interface ChatBoxProps {
    messages: Message[];
    isWaiting: boolean;
    /** Raw text being typed out. Present only while the typewriter is active. */
    typingText: string | null;
    onTypingDone: (html: string) => void;
}

export function ChatBox({ messages, isWaiting, typingText, onTypingDone }: ChatBoxProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom whenever messages or typing content changes
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isWaiting, typingText]);

    return (
        <div className="chat-box">
            {messages.map(msg => (
                <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
            ))}

            {typingText !== null && (
                <TypewriterMessage
                    rawText={typingText}
                    onDone={onTypingDone}
                />
            )}

            {isWaiting && <GeneratingIndicator />}

            <div ref={bottomRef} />
        </div>
    );
}
