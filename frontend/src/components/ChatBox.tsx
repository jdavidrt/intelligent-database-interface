import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { AgentProgress } from './AgentProgress';
import { GeneratingIndicator } from './GeneratingIndicator';
import { AgentEvent } from '../utils/queryClient';

export interface Metrics {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    timeMs: number;
}

export interface Message {
    id: string;
    role: 'user' | 'bot';
    /** For user: plain text. For bot: rendered HTML string. */
    content: string;
    metrics?: Metrics;
}

interface ChatBoxProps {
    messages: Message[];
    /** True while a /query stream is in flight. */
    isWaiting: boolean;
    /** Live agent events for the current stream; empty when idle. */
    progressEvents: AgentEvent[];
}

export function ChatBox({ messages, isWaiting, progressEvents }: ChatBoxProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom whenever messages or progress changes
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isWaiting, progressEvents]);

    return (
        <div className="chat-box">
            {messages.map(msg => (
                <MessageBubble key={msg.id} role={msg.role} content={msg.content} metrics={msg.metrics} />
            ))}

            {progressEvents.length > 0 && <AgentProgress events={progressEvents} />}

            {isWaiting && progressEvents.length === 0 && <GeneratingIndicator />}

            <div ref={bottomRef} />
        </div>
    );
}
