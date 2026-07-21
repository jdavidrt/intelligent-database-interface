"""Join graph — deterministic FK-path resolution over DBProfile.relationship_edges.

The FK edge list is the closed vocabulary of legal joins: every edge is a
("table.col", "table.col") pair introspected from the schema's FOREIGN KEYs.
This module turns that flat list into something the pipeline can *reason* with:

- SQLGenerator injects `join_tree(...)` output into the prompt, so a small model
  never has to derive a multi-hop chain (artists -> track_artists -> tracks ->
  play_events) by itself — deriving those chains is exactly what 3B models are
  worst at, and the classic EC-08 hallucination (`play_events.artist_id`) is the
  shortcut they invent instead.
- VerificationAgent's semantic layer uses `has_edge(...)` to enforce prompt rule
  4b (every JOIN ... ON equality must be a real FK edge) and `path(...)` to tell
  the regeneration loop the exact legal chain to use instead of the invented key.

Join legality is *transitive*: `track_artists.track_id = play_events.track_id`
is not a literal FK edge, but both columns are FKs to the same
`tracks.track_id`, so the equality is exactly as sound as the two FK edges it
short-cuts (and it is the chain the EC-08 profile itself recommends for "most
played artists"). Columns are therefore grouped into equivalence classes
(union-find over the FK pairs); two columns are join-compatible iff they share
a class, and every same-class column pair becomes a derived graph edge.

Path selection: shortest first, and among equally short paths the one routed
through *junction tables* (tables holding >= 2 outgoing FKs, e.g. track_artists)
wins. Rationale: when two same-length chains connect artists to play_events —
via the track_artists bridge or via albums — only the bridge route carries the
real relationship semantics (albums drops standalone singles [EC-03] and
featured credits). The junction preference encodes EC-08's "anchor" rule
deterministically. Lexicographic order breaks any remaining tie, so output is
stable across runs.

Pure stdlib, no LLM, no I/O — safe to call on every request.
"""

from __future__ import annotations

from collections import deque


def split_qualified(qualified: str) -> tuple[str, str]:
    """'play_events.track_id' -> ('play_events', 'track_id') (lowered)."""
    table, _, col = qualified.rpartition(".")
    return table.strip().lower(), col.strip().lower()


class JoinGraph:
    """Undirected graph of tables; edges labeled with their ON-clause equality."""

    def __init__(self, edges: list[tuple[str, str]]) -> None:
        # table -> [(neighbor_table, "src.col = tgt.col"), ...]
        self._adj: dict[str, list[tuple[str, str]]] = {}
        self._edge_keys: set[frozenset[str]] = set()
        # Originals only; _edge_keys additionally gains the derived edges below.
        # Kept apart so _edge_label can prefer a real FK over a derived shortcut
        # when both connect the same table pair.
        self._fk_edge_keys: set[frozenset[str]] = set()
        # Every column participating in any FK, either side. "Is this a key
        # column?" is asked by the verifier when deciding whether an ON-clause
        # equality is a join key or a filter predicate — it must be answered
        # from the same object that answers "is this edge legal".
        self._key_columns: set[str] = set()
        self._class_of: dict[str, str] = {}  # union-find parent, qualified col -> root
        fk_out: dict[str, int] = {}
        for src, tgt in edges:
            s_table, _ = split_qualified(src)
            t_table, _ = split_qualified(tgt)
            if not s_table or not t_table:
                continue
            label = f"{src} = {tgt}"
            self._adj.setdefault(s_table, []).append((t_table, label))
            self._adj.setdefault(t_table, []).append((s_table, label))
            self._edge_keys.add(frozenset((src.lower(), tgt.lower())))
            self._fk_edge_keys.add(frozenset((src.lower(), tgt.lower())))
            self._key_columns.add(src.lower())
            self._key_columns.add(tgt.lower())
            # A self-referencing FK (users.referred_by_user_id -> users.user_id)
            # is a *role* edge, not an identity: merging the two columns into one
            # class would make every user-FK column in the schema join-legal
            # against the referrer column, and _add_derived_edges would
            # materialise that as a real join path — which is how
            # join_tree({"playlists","tracks"}) came to route through
            # playlists.forked_from_id instead of playlists.playlist_id.
            # The direct edge above stays legal; only the transitive closure is denied.
            if s_table != t_table:
                self._union(src.lower(), tgt.lower())
            fk_out[s_table] = fk_out.get(s_table, 0) + 1
        # Junction/bridge tables hold >= 2 outgoing FKs (track_artists,
        # playlist_tracks, user_follows_artists, ... and play_events itself).
        self._junction: set[str] = {t for t, n in fk_out.items() if n >= 2}
        self._add_derived_edges()

    # -- union-find over qualified columns (join-key equivalence classes) ---------------

    def _find(self, col: str) -> str:
        root = col
        while self._class_of.get(root, root) != root:
            root = self._class_of[root]
        while self._class_of.get(col, col) != root:  # path compression
            self._class_of[col], col = root, self._class_of[col]
        return root

    def _union(self, a: str, b: str) -> None:
        ra, rb = self._find(a), self._find(b)
        self._class_of.setdefault(a, a)
        self._class_of.setdefault(b, b)
        if ra != rb:
            self._class_of[ra] = rb

    def _add_derived_edges(self) -> None:
        """Every same-class column pair on different tables is a legal join —
        `track_artists.track_id = play_events.track_id` short-cuts through
        tracks.track_id with identical semantics. Adding these as graph edges
        lets path()/join_tree() propose the minimal chain the EC-08 profile
        itself recommends, instead of forcing the hop through tracks."""
        classes: dict[str, list[str]] = {}
        for col in list(self._class_of):
            classes.setdefault(self._find(col), []).append(col)
        for members in classes.values():
            for i, a in enumerate(sorted(members)):
                for b in sorted(members)[i + 1 :]:
                    if frozenset((a, b)) in self._edge_keys:
                        continue  # the original FK edge already exists
                    a_table, _ = split_qualified(a)
                    b_table, _ = split_qualified(b)
                    if a_table == b_table:
                        continue
                    label = f"{a} = {b}"
                    self._adj.setdefault(a_table, []).append((b_table, label))
                    self._adj.setdefault(b_table, []).append((a_table, label))
                    self._edge_keys.add(frozenset((a, b)))

    def has_edge(self, col_a: str, col_b: str) -> bool:
        """True when `col_a = col_b` is a legal join equality: a real FK edge or
        a transitive one (both columns FK-chain to the same key — same
        equivalence class). Args are qualified names, e.g. 'play_events.track_id'."""
        a, b = col_a.lower(), col_b.lower()
        if frozenset((a, b)) in self._edge_keys:
            return True
        return a in self._class_of and b in self._class_of and self._find(a) == self._find(b)

    def is_key_column(self, qualified: str) -> bool:
        """True when this column participates in any FK edge in the schema.

        Lets the verifier tell a join key from a filter predicate inside the
        same ON clause: `ON al.artist_id = a.artist_id AND al.label = a.label`
        carries one relationship and one filter, and only the first is rule
        4b's business (`albums.label`/`artists.label` are not key columns)."""
        return qualified.lower() in self._key_columns

    def is_fk_edge(self, col_a: str, col_b: str) -> bool:
        """True only for a *literal* FK edge — no transitive shortcuts. Used to
        decide whether a planned edge needs the "shortcut through a shared key"
        annotation in the prompt (the prompt renders raw FKs verbatim)."""
        return frozenset((col_a.lower(), col_b.lower())) in self._fk_edge_keys

    # -- path selection ---------------------------------------------------------------

    def _score(self, node_path: list[str]) -> tuple[int, list[str]]:
        """Sort key for equal-length paths: more junction intermediates first
        (negated for min()), then lexicographic node order for determinism."""
        intermediates = node_path[1:-1]
        return (-sum(1 for t in intermediates if t in self._junction), node_path)

    def _best_node_path(self, src: str, dst: str) -> list[str] | None:
        """Best shortest node path src..dst (junction-preferred, deterministic).

        When several routes tie, `_score`'s lexicographic tiebreak decides —
        arbitrary but stable. `ambiguous_bridges()` exposes exactly those ties
        so the verifier can say so instead of the choice being invisible.
        """
        if src == dst:
            return [src]
        paths = self._all_shortest_node_paths(src, dst)
        return min(paths, key=self._score) if paths else None

    def _edge_label(self, table_a: str, table_b: str) -> str | None:
        """Label of the direct edge between two adjacent tables.

        Real FK first, then lexicographic (stable). A pure lexicographic pick
        chose `payments.user_id = users.referred_by_user_id` over the real
        `payments.user_id = users.user_id` — the derived label happened to sort
        first. 0a removes that particular derived edge, but the preference is
        cheap insurance for any schema where a derived edge and a real FK
        connect the same table pair.
        """
        labels = [lbl for nxt, lbl in self._adj.get(table_a, []) if nxt == table_b]
        if not labels:
            return None

        def rank(label: str) -> tuple[int, str]:
            a, b = (s.strip().lower() for s in label.split("=", 1))
            return (0 if frozenset((a, b)) in self._fk_edge_keys else 1, label)

        return min(labels, key=rank)

    def _all_shortest_node_paths(self, src: str, dst: str) -> list[list[str]]:
        """Every shortest node path src..dst (schema graphs are tiny)."""
        if src == dst or src not in self._adj or dst not in self._adj:
            return []
        dist = {src: 0}
        parents: dict[str, set[str]] = {}
        queue = deque([src])
        while queue:
            cur = queue.popleft()
            for nxt, _ in self._adj.get(cur, []):
                if nxt not in dist:
                    dist[nxt] = dist[cur] + 1
                    parents.setdefault(nxt, set()).add(cur)
                    queue.append(nxt)
                elif dist[nxt] == dist[cur] + 1:
                    parents.setdefault(nxt, set()).add(cur)
        if dst not in dist:
            return []
        paths: list[list[str]] = []

        def walk(node: str, acc: list[str]) -> None:
            if node == src:
                paths.append([src] + list(reversed(acc)))
                return
            for p in sorted(parents.get(node, ())):
                walk(p, acc + [node])

        walk(dst, [])
        return paths

    def ambiguous_bridges(self, src_table: str, dst_table: str) -> list[tuple[str, ...]]:
        """Intermediate-table routes that tie for *best* between two tables.

        `_score` breaks such ties lexicographically, which is deterministic but
        arbitrary: playlists->tracks ties between `playlist_tracks` ("tracks IN
        the playlist"), `play_events` ("tracks PLAYED FROM it") and
        `user_liked_tracks`. Those answer different questions and the FK graph
        holds no opinion about which the user meant — so rather than pretend,
        this surfaces the alternatives and the verifier reports them as a
        caveat.

        Returns [] when the route is unambiguous (one best option, or none).
        """
        paths = self._all_shortest_node_paths(src_table.lower(), dst_table.lower())
        if not paths:
            return []
        best = max(sum(1 for t in path[1:-1] if t in self._junction) for path in paths)
        routes = {
            tuple(path[1:-1])
            for path in paths
            if sum(1 for t in path[1:-1] if t in self._junction) == best
        }
        routes.discard(())
        return sorted(routes) if len(routes) > 1 else []

    def path(self, src_table: str, dst_table: str) -> list[str] | None:
        """Chain of ON-clause equalities connecting two tables: shortest,
        junction-preferred (see module docstring). [] when src == dst,
        None when no FK path exists at all."""
        nodes = self._best_node_path(src_table.lower(), dst_table.lower())
        if nodes is None:
            return None
        chain: list[str] = []
        for a, b in zip(nodes, nodes[1:]):
            label = self._edge_label(a, b)
            if label is None:  # pragma: no cover — adjacency and labels are built together
                return None
            chain.append(label)
        return chain

    def join_tree(self, tables: set[str]) -> tuple[list[str], set[str]] | None:
        """Minimal set of ON-clause equalities connecting all of `tables`
        (greedy Steiner approximation: repeatedly attach the closest
        still-unconnected required table via the best `path`).

        Returns (edge labels in attach order, every table involved — including
        intermediates the FK graph forces in, e.g. `tracks` between
        `track_artists` and `play_events`). None when some required table is
        unreachable from the rest.
        """
        wanted = sorted({t.lower() for t in tables if t})
        if not wanted:
            return None
        connected: set[str] = {wanted[0]}
        edges: list[str] = []
        remaining = set(wanted[1:])
        while remaining:
            best: tuple[int, tuple[int, list[str]], list[str], str] | None = None
            for target in sorted(remaining):
                for anchor in sorted(connected):
                    nodes = self._best_node_path(anchor, target)
                    if nodes is None:
                        continue
                    key = (len(nodes), self._score(nodes), nodes, target)
                    if best is None or key < best:
                        best = key
            if best is None:
                return None
            _, _, nodes, target = best
            for a, b in zip(nodes, nodes[1:]):
                label = self._edge_label(a, b)
                if label is not None and label not in edges:
                    edges.append(label)
                connected.add(b)
            connected.add(target)
            remaining -= connected
        return edges, connected
