import { AgentEvent, AgentName } from '../services/api';
import { ProgressStep } from '../stores/progressStore';

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

export function AgentProgress({ steps }: { steps: ProgressStep[] }) {
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
                        {step.adapter !== undefined && (
                            <span className="agent-step-adapter">
                                profile: {step.adapter ?? 'base'}
                            </span>
                        )}
                        <span className="agent-step-msg">{step.message}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
