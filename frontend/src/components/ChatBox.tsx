import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { AgentProgress } from './AgentProgress';
import { GeneratingIndicator } from './GeneratingIndicator';
import { useQueryStore } from '../stores/queryStore';
import { useProgressStore } from '../stores/progressStore';

export function ChatBox() {
    const messages = useQueryStore(s => s.messages);
    const isWaiting = useQueryStore(s => s.isWaiting);
    const steps = useProgressStore(s => s.steps);

    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom whenever messages or progress changes
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isWaiting, steps]);

    return (
        <div className="chat-box">
            {messages.map(msg => (
                <MessageBubble key={msg.id} message={msg} />
            ))}

            {steps.length > 0 && <AgentProgress steps={steps} />}

            {isWaiting && steps.length === 0 && <GeneratingIndicator />}

            <div ref={bottomRef} />
        </div>
    );
}
