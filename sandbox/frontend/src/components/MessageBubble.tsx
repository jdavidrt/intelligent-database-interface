interface MessageBubbleProps {
    role: 'user' | 'bot';
    /** For user messages: plain text. For bot messages: rendered HTML string. */
    content: string;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
    if (role === 'user') {
        return (
            <div className="message user-message">
                {content}
            </div>
        );
    }

    return (
        <div
            className="message bot-message"
            dangerouslySetInnerHTML={{ __html: content }}
        />
    );
}
