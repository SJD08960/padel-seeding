def compute_seeding(
    rankings: dict,
    tournaments: list,
    display_names: dict,
    signups: list,
    console=None,
) -> list[tuple[str, str]]:
    """
    Compute seeding for tournament n+1.

    Phase 1: Players from most recent tournament n, in rank order.
    Phase 2: For each older tournament k = n-1, n-2, ..., insert new signed-up
             players one by one using violation minimization with tie-breaking.
    Phase 3: Players with no history appended at end in sign-up order.
    """
    signup_lower = [s.lower() for s in signups]

    # Build display name lookup: prefer signup casing, fall back to CSV
    name_display = {}
    for s in signups:
        name_display[s.lower()] = s
    for k, v in display_names.items():
        if k not in name_display:
            name_display[k] = v

    def log(msg):
        if console:
            console.print(msg)

    seeding = []    # list of (player_lower, reason_str)
    placed = set()

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    n = tournaments[-1]
    n_players = sorted(
        (p for p in signup_lower if p in rankings[n]),
        key=lambda p: rankings[n][p],
    )
    log(
        f"  [cyan]Phase 1[/cyan] [dim]({n}, most recent):[/dim] "
        f"[bold]{len(n_players)}[/bold] player(s) seeded directly"
    )
    for player in n_players:
        rank = rankings[n][player]
        seeding.append((player, f"Ranked #{rank} in {n} (most recent tournament)"))
        placed.add(player)

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    for t_idx in range(len(tournaments) - 2, -1, -1):
        t = tournaments[t_idx]
        new_players = sorted(
            (p for p in signup_lower if p not in placed and p in rankings[t]),
            key=lambda p: rankings[t][p],
        )
        if not new_players:
            log(
                f"  [cyan]Phase 2[/cyan] [dim]({t}):[/dim] "
                f"[dim]no new signed-up players, skipping[/dim]"
            )
            continue
        log(
            f"  [cyan]Phase 2[/cyan] [dim]({t}):[/dim] "
            f"inserting [bold]{len(new_players)}[/bold] player(s)"
        )
        for player in new_players:
            seeding = _insert_player(
                player, seeding, rankings, tournaments, t_idx, name_display
            )
            placed.add(player)

    # ── Phase 3 ───────────────────────────────────────────────────────────────
    never_appeared = [p for p in signup_lower if p not in placed]
    if never_appeared:
        log(
            f"  [cyan]Phase 3:[/cyan] [bold]{len(never_appeared)}[/bold] "
            f"player(s) with no history, placed at end"
        )
    for player in never_appeared:
        seeding.append((player, "No previous tournament history"))

    return [(name_display.get(p, p), reason) for p, reason in seeding]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_violations(slot: int, player_rank: int, anchors: dict, t_rankings: dict) -> int:
    """
    Count ordering violations if player (with player_rank in tournament t)
    is inserted at position `slot` in the current seeding.

    anchors: {player_lower: current_seeding_index}
    t_rankings: {player_lower: rank_in_t}

    Violations:
      - player inserted above an anchor that beat player in t  (anchor_rank < player_rank)
      - player inserted below an anchor that player beat in t  (anchor_rank > player_rank)
    """
    count = 0
    for anchor, pos in anchors.items():
        rank_a = t_rankings[anchor]
        if rank_a < player_rank:    # anchor beat player → player should be after anchor
            if slot <= pos:          # player inserted before anchor → violation
                count += 1
        elif rank_a > player_rank:  # player beat anchor → player should be before anchor
            if slot > pos:           # player inserted after anchor → violation
                count += 1
    return count


def _insert_player(
    player: str,
    seeding: list,
    rankings: dict,
    tournaments: list,
    source_t_idx: int,
    name_display: dict,
) -> list:
    """
    Insert player into seeding using violation minimization.

    1. Score all slots by violation count using source tournament k.
    2. If tied, repeat within tied slots using k-1, k-2, ... until resolved.
    3. Final tie resolved pessimistically:
       - Consecutive tied slots → bottom of range.
       - Non-consecutive → ceiling of midpoint between extremes.
    """
    candidate_slots = list(range(len(seeding) + 1))
    source_t = tournaments[source_t_idx]
    tie_break_used = None

    for t_idx in range(source_t_idx, -1, -1):
        if len(candidate_slots) <= 1:
            break

        t = tournaments[t_idx]

        # Need player's rank in this tournament to score
        if player not in rankings[t]:
            continue

        player_rank = rankings[t][player]
        anchors = {p: i for i, (p, _) in enumerate(seeding) if p in rankings[t]}
        if not anchors:
            continue

        violations = {
            s: _count_violations(s, player_rank, anchors, rankings[t])
            for s in candidate_slots
        }
        min_v = min(violations.values())
        new_cands = [s for s in candidate_slots if violations[s] == min_v]

        if len(new_cands) < len(candidate_slots):
            candidate_slots = new_cands
            if t_idx < source_t_idx:
                tie_break_used = t

    # Resolve any remaining tie pessimistically
    if len(candidate_slots) == 1:
        insert_pos = candidate_slots[0]
    else:
        lo, hi = min(candidate_slots), max(candidate_slots)
        if hi - lo == len(candidate_slots) - 1:   # consecutive
            insert_pos = hi                         # bottom of range (pessimistic)
        else:                                       # non-consecutive
            insert_pos = (lo + hi + 1) // 2        # ceiling midpoint (pessimistic)

    # Build reason string
    player_rank_in_source = rankings[source_t][player]
    anchors_in_source = {p: i for i, (p, _) in enumerate(seeding) if p in rankings[source_t]}

    reason_parts = [f"Ranked #{player_rank_in_source} in {source_t}"]
    if anchors_in_source:
        min_v_final = _count_violations(
            insert_pos, player_rank_in_source, anchors_in_source, rankings[source_t]
        )
        reason_parts.append(
            f"{min_v_final} violation(s) among {len(anchors_in_source)} anchor(s)"
        )
    if tie_break_used:
        reason_parts.append(f"tie-broken using {tie_break_used}")

    if insert_pos == 0:
        reason_parts.append("placed at top")
    elif insert_pos == len(seeding):
        reason_parts.append("placed at bottom")
    else:
        above = name_display.get(seeding[insert_pos - 1][0], seeding[insert_pos - 1][0])
        below = name_display.get(seeding[insert_pos][0], seeding[insert_pos][0])
        reason_parts.append(f"placed between {above} and {below}")

    seeding.insert(insert_pos, (player, "; ".join(reason_parts)))
    return seeding
