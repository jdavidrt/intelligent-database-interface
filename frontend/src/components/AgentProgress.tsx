import { AgentEvent, AgentName } from '../utils/queryClient';

const AGENT_LABELS: Record<AgentName, string> = {
    context_manager: 'Context Manager',
    query_understanding: 'Query Understanding',
    clarification: 'Clarification',
    sql_generator: 'SQL Generator',
    verification: 'Verification',
    visualization: 'Visualization',
    session_manager: 'Session Manager',
    orchestrator: 'Orchestrator',
};

const STATUS_ICON: Record<AgentEvent['status'], string> = {
    started: '◌',
    progress: '◍',
    done: '✓',
    error: '✗',
};

interface Step {
    agent: AgentName;
    status: AgentEvent['status'];
    message: string;
}

/** Collapse the event stream to the latest status + message per agent, in first-seen order. */
function collapse(events: AgentEvent[]): Step[] {
    const order: AgentName[] = [];
    const byAgent = new Map<AgentName, Step>();
    for (const ev of events) {
        if (!byAgent.has(ev.agent)) order.push(ev.agent);
        byAgent.set(ev.agent, { agent: ev.agent, status: ev.status, message: ev.message });
    }
    return order.map(a => byAgent.get(a)!);
}

export function AgentProgress({ events }: { events: AgentEvent[] }) {
    const steps = collapse(events);

    return (
        <div className="message bot-message agent-progress">
            <div className="agent-progress-title">Working through the pipeline…</div>
            <ul className="agent-progress-list">
                {steps.map(step => (
                    <li
                        key={step.agent}
                        className={`agent-step agent-step-${step.status}`}
                    >
                        <span className="agent-step-icon">{STATUS_ICON[step.status]}</span>
                        <span className="agent-step-label">{AGENT_LABELS[step.agent]}</span>
                        <span className="agent-step-msg">{step.message}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
