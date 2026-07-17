type Page = 'chat' | 'benchmarks';

export type DrawerKind = 'sessions' | 'profile';

interface HeaderProps {
    themeName: string;
    onThemeCycle: () => void;
    page: Page;
    onPageChange: (page: Page) => void;
    drawer: DrawerKind | null;
    onDrawerToggle: (drawer: DrawerKind) => void;
    onNewChat: () => void;
}

export function Header({
    themeName,
    onThemeCycle,
    page,
    onPageChange,
    drawer,
    onDrawerToggle,
    onNewChat,
}: HeaderProps) {
    return (
        <div className="header">
            <h1>IDI (Intelligent Database Interface)</h1>

            <nav className="header-nav">
                <button
                    className="nav-tab nav-tab-icon"
                    aria-label="New chat"
                    title="New chat"
                    onClick={onNewChat}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
                        <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-4-1L3 20l1-5.5a8.5 8.5 0 1 1 17-3Z" />
                        <line x1="12" y1="8" x2="12" y2="14" />
                        <line x1="9" y1="11" x2="15" y2="11" />
                    </svg>
                </button>
                <button
                    className={`nav-tab ${page === 'chat' ? 'nav-tab-active' : ''}`}
                    onClick={() => onPageChange('chat')}
                >
                    💬 Chat
                </button>
                <button
                    className={`nav-tab ${page === 'benchmarks' ? 'nav-tab-active' : ''}`}
                    onClick={() => onPageChange('benchmarks')}
                >
                    📊 Benchmarks
                </button>
                <button
                    className={`nav-tab ${drawer === 'sessions' ? 'nav-tab-active' : ''}`}
                    onClick={() => onDrawerToggle('sessions')}
                >
                    🗂 Sessions
                </button>
                <button
                    className={`nav-tab ${drawer === 'profile' ? 'nav-tab-active' : ''}`}
                    onClick={() => onDrawerToggle('profile')}
                >
                    🗺 DB Profile
                </button>
            </nav>

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
