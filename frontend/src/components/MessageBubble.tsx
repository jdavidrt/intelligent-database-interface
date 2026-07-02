import { Metrics } from './ChatBox';

interface MessageBubbleProps {
    role: 'user' | 'bot';
    /** For user messages: plain text. For bot messages: rendered HTML string. */
    content: string;
    metrics?: Metrics;
}

export function MessageBubble({ role, content, metrics }: MessageBubbleProps) {
    if (role === 'user') {
        return (
            <div className="message user-message">
                {content}
            </div>
        );
    }

    return (
        <div className="message bot-message">
            <div dangerouslySetInnerHTML={{ __html: content }} />
            {metrics && (
                <div className="message-metrics">
                    Time: {(metrics.timeMs / 1000).toFixed(2)}s |
                    Tokens: {metrics.promptTokens} prompt + {metrics.completionTokens} completion = {metrics.totalTokens} total
                    ({(metrics.completionTokens / (metrics.timeMs / 1000)).toFixed(1)} t/s)
                </div>
            )}
        </div>
    );
}
