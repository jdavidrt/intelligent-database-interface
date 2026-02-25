interface HeaderProps {
    themeName: string;
    onThemeCycle: () => void;
}

export function Header({ themeName, onThemeCycle }: HeaderProps) {
    return (
        <div className="header">
            <h1>IDI (Intelligent Database Interface)</h1>
            <button className="theme-btn" aria-label="Switch theme" onClick={onThemeCycle}>
                <span className="theme-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                        <path d="M12 2a10 10 0 1 0 3.16 19.49 1 1 0 0 0 .28-1.57A5 5 0 0 1 14 16a4 4 0 0 1 4-4 5 5 0 0 1 3.07 1.06 1 1 0 0 0 1.57-.28A9.94 9.94 0 0 0 22 9.5 10 10 0 0 0 12 2Zm-5 9a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm2-5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm6 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm3 5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z" />
                    </svg>
                </span>
                <span className="theme-label">{themeName}</span>
            </button>
        </div>
    );
}
