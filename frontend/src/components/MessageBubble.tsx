import { Message } from '../stores/queryStore';
import { AnswerPanel } from './AnswerPanel';

export function MessageBubble({ message }: { message: Message }) {
    if (message.role === 'user') {
        return (
            <div className="message user-message">
                {message.content}
            </div>
        );
    }

    const { result, restored, content, metrics } = message;

    return (
        <div className="message bot-message">
            {result ? (
                <AnswerPanel result={result} restored={restored ?? false} />
            ) : (
                <div dangerouslySetInnerHTML={{ __html: content }} />
            )}
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
