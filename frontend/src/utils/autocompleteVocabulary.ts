import { DBProfile } from '../services/api';

/**
 * Hand-curated colloquial terms the schema alone doesn't carry — this is what
 * makes "songs" suggestible even though the real table is `tracks`. Extend as
 * new edge cases surface.
 */
export const STATIC_SYNONYMS: string[] = [
    'songs',
    'tracks',
    'artists',
    'albums',
    'playlists',
    'plays',
    'listens',
    'streams',
    'genres',
    'singles',
    'subscribers',
    'users',
    'payments',
    'duration',
    'listened',
    'popular',
    'top',
    'count',
    'average',
    'longest',
    'newest',
    'release',
];

const MIN_WORD_LEN = 3;

/**
 * Merge the static synonym list with the live schema vocabulary mined from the
 * DBProfile: table names, column names (plus their snake_case sub-tokens), and
 * glossary abbreviations/meaning words. Lowercased and deduped. Synonyms keep
 * their curated order and rank ahead of schema terms, so e.g. a lone "s" still
 * surfaces "songs" first.
 */
export function mergeVocabulary(profile: DBProfile | null): string[] {
    const synonyms = STATIC_SYNONYMS.map(w => w.toLowerCase());
    const seen = new Set<string>(synonyms);
    const schemaWords = new Set<string>();

    if (profile) {
        const add = (word: string) => {
            if (!seen.has(word)) schemaWords.add(word);
        };
        for (const table of profile.tables) {
            add(table.name.toLowerCase());
            for (const col of table.columns) {
                const name = col.name.toLowerCase();
                add(name);
                for (const part of name.split('_')) {
                    if (part.length >= MIN_WORD_LEN) add(part);
                }
            }
        }
        for (const [abbrev, meaning] of Object.entries(profile.glossary)) {
            add(abbrev.toLowerCase());
            for (const part of meaning.toLowerCase().split(/[^a-z0-9]+/)) {
                if (part.length >= MIN_WORD_LEN) add(part);
            }
        }
    }

    return [...synonyms, ...[...schemaWords].sort()];
}

/**
 * Case-insensitive prefix match of the input's last (in-progress) token against
 * the vocabulary, preserving vocabulary order (synonyms first). Returns up to
 * `limit` matches; empty when there is no in-progress token or it is already an
 * exact vocabulary word.
 */
export function suggest(vocab: string[], value: string, limit = 5): string[] {
    const tokens = value.split(/\s+/);
    const token = tokens[tokens.length - 1]?.toLowerCase() ?? '';
    if (token.length < 1) return [];

    const matches = vocab.filter(w => w.startsWith(token) && w !== token);
    return matches.slice(0, limit);
}
