# Admin Matches Tab — Handicap Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Matches tab edit section with a split-panel layout: clickable match cards on the left, handicap editor on the right.

**Architecture:** Single-function refactor of `_render_matches()` in `admin.py`. Two-column Streamlit layout — left column renders match cards with click handlers via `st.session_state`, right column renders a handicap editor form pre-populated from the selected match. All DB calls go through existing `db.py` functions.

**Tech Stack:** Streamlit (st.columns, st.button, st.number_input, st.radio, st.session_state), existing SQLite via db.py, existing CSS in admin.py + components.py

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `world_cup/admin.py:301-431` | Replace `_render_matches()` | Split-panel match list + handicap editor |
| `world_cup/admin.py:20-76` | Modify `ADMIN_CSS` | Add new CSS for match cards, selected state, editor glassmorphism |

No new files. No DB changes. No new dependencies.

---

### Task 1: Replace match list with clickable match cards

**Files:**
- Modify: `world_cup/admin.py:301-346` (top half of `_render_matches`)

- [ ] **Step 1: Replace the dataframe + selectbox pattern with a two-column layout**

Replace lines 301–356 of `_render_matches()` (from `def _render_matches():` through the selectbox) with:

```python
def _render_matches():
    matches = db.admin_get_all_matches()

    # -- Add Match --
    with st.expander("➕ Add Match", expanded=False):
        with st.form("add_match"):
            c1, c2 = st.columns(2)
            match_id = c1.number_input("Match ID", min_value=1, step=1, key="add_match_id")
            team_a = c1.text_input("Team A", key="add_team_a")
            team_b = c2.text_input("Team B", key="add_team_b")
            match_time = st.text_input("Match Time (ISO)", placeholder="2026-06-11T20:00:00Z", key="add_match_time")
            c3, c4 = st.columns(2)
            status = c3.selectbox("Status", ["Not Started", "Live", "Finished"], key="add_match_status")
            result = c4.selectbox("Result", ["None", "A_win", "B_win", "Draw"], key="add_match_result")
            cs1, cs2 = st.columns(2)
            add_score_a = cs1.number_input("Score A", min_value=0, step=1, key="add_score_a", value=None)
            add_score_b = cs2.number_input("Score B", min_value=0, step=1, key="add_score_b", value=None)
            st.caption("Handicap (optional)")
            hc1, hc2 = st.columns(2)
            h_line = hc1.number_input("Team A gives (goals)", min_value=0.0, max_value=10.0, step=0.5, value=0.0, key="add_h_line")
            h_fav = hc2.selectbox("Favorite", ["None", "Team A", "Team B"], key="add_h_fav")
            h_fee = st.number_input("Fee %", min_value=0, max_value=20, value=5, key="add_h_fee")
            if h_fav == "None" or h_line == 0.0:
                h_line, h_fav = None, None
            else:
                h_fav = "A" if h_fav == "Team A" else "B"
            if st.form_submit_button("Add Match"):
                if team_a.strip() and team_b.strip() and match_time.strip():
                    db.admin_insert_match(
                        match_id, team_a, team_b, match_time, status,
                        None if result == "None" else result,
                        score_a=add_score_a, score_b=add_score_b,
                        handicap_line=h_line, handicap_favorite=h_fav, handicap_fee=h_fee,
                    )
                    st.success(f"Added match #{match_id}")
                    st.rerun()
                else:
                    st.warning("Team A, Team B, and Match Time required.")

    if not matches:
        st.info("No matches yet.")
        return

    # -- Filter --
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "Not Started", "Live", "Finished"],
        key="match_filter",
    )
    filtered = matches if status_filter == "All" else [m for m in matches if m["status"] == status_filter]
    st.caption(f"{len(filtered)} match(es)")

    left, right = st.columns([1, 1])

    with left:
        for m in filtered:
            _render_match_select_card(m)

    with right:
        _render_handicap_editor(matches)
```

- [ ] **Step 2: Verify the layout renders**

Run: `streamlit run premier_league_dashboard.py` (navigate to Admin → Matches)
Expected: Two-column layout appears with match list on left. Right panel shows placeholder.

- [ ] **Step 3: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: split-panel layout for admin matches tab"
```

---

### Task 2: Build the clickable match card helper

**Files:**
- Create: helper function `_render_match_select_card(match)` in `world_cup/admin.py`

- [ ] **Step 1: Add `_render_match_select_card()` after `_render_matches()`**

```python
def _render_match_select_card(match):
    """Render a single clickable match card for the admin match list."""
    selected_id = st.session_state.get("selected_match_id")
    is_selected = selected_id == match["match_id"]

    # Build the handicap badge text
    h_line = match.get("handicap_line")
    h_fav = match.get("handicap_favorite")
    if h_line is not None and h_fav is not None:
        fav_team = match["team_a"] if h_fav == "A" else match["team_b"]
        badge = f"{fav_team} −{h_line} · {match.get('handicap_fee', 5)}%"
        badge_color = "rgba(46,204,113,0.18)"
        badge_text = "#2ecc71"
    else:
        badge = "— no handicap"
        badge_color = "rgba(255,255,255,0.06)"
        badge_text = "var(--text-muted)"

    # Status dot
    status_color = {
        "Not Started": "#5a6a7a",
        "Live": "#e67e22",
        "Finished": "#27ae60",
    }.get(match["status"], "#5a6a7a")

    # Time display
    match_time = match.get("match_time", "")
    try:
        from datetime import datetime
        dt = datetime.strptime(match_time[:19], "%Y-%m-%dT%H:%M:%S")
        time_display = dt.strftime("%a %d %b · %H:%M")
    except (ValueError, TypeError):
        time_display = match_time[:16] if match_time else ""

    border_style = (
        "border-left: 3px solid var(--gold-bright);"
        "background: var(--bg-card-hover);"
        if is_selected else
        "border-left: 1px solid var(--border-subtle);"
    )

    st.markdown(f"""
    <div class="admin-match-card" style="{border_style}">
        <div class="admin-match-card-inner">
            <div class="admin-match-teams">
                <span class="admin-team-a">{match['team_a']}</span>
                <span class="admin-vs">vs</span>
                <span class="admin-team-b">{match['team_b']}</span>
            </div>
            <div class="admin-match-meta">
                <span class="admin-status-dot" style="background:{status_color}"></span>
                <span>{match['status']}</span>
                <span>·</span>
                <span>{time_display}</span>
            </div>
            <span class="admin-handicap-badge" style="background:{badge_color};color:{badge_text}">
                {badge}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Click handler
    label = "✕ Deselect" if is_selected else "Select"
    if st.button(label, key=f"sel_match_{match['match_id']}"):
        if is_selected:
            st.session_state.pop("selected_match_id", None)
        else:
            st.session_state["selected_match_id"] = match["match_id"]
        st.rerun()
```

- [ ] **Step 2: Verify cards render and are clickable**

Run: `streamlit run premier_league_dashboard.py` → Admin → Matches
Expected: Each match renders as a card with team names, status dot, time, handicap badge. Clicking "Select" highlights the card (gold border). Clicking "Deselect" removes highlight.

- [ ] **Step 3: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: clickable match select cards in admin matches tab"
```

---

### Task 3: Build the handicap editor panel

**Files:**
- Create: helper function `_render_handicap_editor(matches)` in `world_cup/admin.py`

- [ ] **Step 1: Add `_render_handicap_editor()` after `_render_match_select_card()`**

```python
def _render_handicap_editor(matches):
    """Render the handicap editor panel for the selected match."""
    selected_id = st.session_state.get("selected_match_id")

    # Wrapper card
    st.markdown("""
    <div class="admin-editor-card">
        <div class="admin-editor-header">HANDICAP EDITOR</div>
    </div>
    """, unsafe_allow_html=True)

    if selected_id is None:
        st.markdown("""
        <div class="admin-editor-placeholder">
            ← Select a match to edit handicap
        </div>
        """, unsafe_allow_html=True)
        return

    # Look up the selected match
    match = None
    for m in matches:
        if m["match_id"] == selected_id:
            match = m
            break

    if match is None:
        st.warning(f"Match #{selected_id} not found — it may have been deleted.")
        return

    # Header: teams + time
    st.markdown(f"""
    <div class="admin-editor-match-header">
        <span class="admin-editor-team">{match['team_a']}</span>
        <span class="admin-editor-vs">vs</span>
        <span class="admin-editor-team">{match['team_b']}</span>
        <br>
        <span class="admin-editor-time">{match.get('match_time', '')[:16]}</span>
    </div>
    """, unsafe_allow_html=True)

    # Current handicap state
    cur_line = match.get("handicap_line")
    cur_fav = match.get("handicap_favorite")
    cur_fee = match.get("handicap_fee") or 5

    # Handicap Line
    st.markdown('<p class="admin-editor-label">Handicap Line</p>', unsafe_allow_html=True)
    quick_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    qcols = st.columns(len(quick_vals) + 1)
    for i, val in enumerate(quick_vals):
        with qcols[i]:
            if st.button(f"{val}", key=f"qh_{val}_{selected_id}", use_container_width=True):
                st.session_state[f"edit_h_line_{selected_id}"] = val
                st.rerun()

    line_key = f"edit_h_line_{selected_id}"
    if line_key not in st.session_state:
        st.session_state[line_key] = float(cur_line) if cur_line is not None else 0.0

    with qcols[-1]:
        new_line = st.number_input(
            "Custom", min_value=0.0, max_value=10.0, step=0.5,
            key=line_key, label_visibility="collapsed",
        )

    # Favorite
    st.markdown('<p class="admin-editor-label">Favorite</p>', unsafe_allow_html=True)
    fav_key = f"edit_h_fav_{selected_id}"
    if fav_key not in st.session_state:
        default_fav = 0
        if cur_fav == "A":
            default_fav = 1
        elif cur_fav == "B":
            default_fav = 2
        st.session_state[fav_key] = default_fav

    fav_choice = st.radio(
        "Favorite",
        ["None", match["team_a"], match["team_b"]],
        key=fav_key,
        horizontal=True,
        label_visibility="collapsed",
    )

    # Fee
    st.markdown('<p class="admin-editor-label">Fee %</p>', unsafe_allow_html=True)
    fee_key = f"edit_h_fee_{selected_id}"
    if fee_key not in st.session_state:
        st.session_state[fee_key] = cur_fee
    new_fee = st.number_input(
        "Fee", min_value=0, max_value=20, step=1,
        key=fee_key, label_visibility="collapsed",
    )

    # Live preview
    st.markdown("---")
    if fav_choice != "None" and new_line > 0.0:
        preview = (
            f"**{fav_choice}** gives **{new_line}** goals · Fee: **{new_fee}%**  \n"
            f"Payout multiplier: **{2.0:.1f}×** (stake minus fee, doubled on win)"
        )
        st.info(preview)
    elif new_line > 0.0:
        st.caption("⚠️ Select a favorite to activate the handicap.")

    # Save & Clear buttons
    col_save, col_clear = st.columns([2, 1])
    with col_save:
        if st.button("💾 Save Handicap", key=f"save_h_{selected_id}", use_container_width=True):
            # Build final values
            if fav_choice == "None" or new_line == 0.0:
                final_line, final_fav = None, None
            else:
                final_line = float(new_line)
                final_fav = "A" if fav_choice == match["team_a"] else "B"

            try:
                db.admin_update_match(
                    selected_id,
                    match["team_a"], match["team_b"], match["match_time"],
                    match["status"], match.get("result"),
                    score_a=match.get("score_a"), score_b=match.get("score_b"),
                    handicap_line=final_line, handicap_favorite=final_fav, handicap_fee=new_fee,
                )
                st.toast(f"✅ Handicap saved for {match['team_a']} vs {match['team_b']}")
                # Clear cached widget state so re-render picks up fresh DB values
                for k in [line_key, fav_key, fee_key]:
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

    with col_clear:
        if cur_line is not None or cur_fav is not None:
            if st.button("🗑 Clear", key=f"clear_h_{selected_id}", use_container_width=True):
                try:
                    db.admin_update_match(
                        selected_id,
                        match["team_a"], match["team_b"], match["match_time"],
                        match["status"], match.get("result"),
                        score_a=match.get("score_a"), score_b=match.get("score_b"),
                        handicap_line=None, handicap_favorite=None, handicap_fee=new_fee,
                    )
                    st.toast("Handicap cleared")
                    for k in [line_key, fav_key, fee_key]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Clear failed: {e}")
```

- [ ] **Step 2: Verify the editor works end-to-end**

Run: `streamlit run premier_league_dashboard.py` → Admin → Matches
Manual test:
1. Click "Select" on a match → right panel shows handicap editor with match header
2. Click quick-set "1.5" → line input updates
3. Select favorite → radio toggles
4. Adjust fee → number changes
5. Live preview updates
6. Click "Save Handicap" → toast appears, DB updated
7. Click "Clear" → handicap cleared, line/fav become None
8. Refresh page → values persist (loaded from DB)

- [ ] **Step 3: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: handicap editor panel in admin matches tab"
```

---

### Task 4: Add CSS for new components

**Files:**
- Modify: `world_cup/admin.py:20-76` (`ADMIN_CSS`)

- [ ] **Step 1: Append new CSS rules to `ADMIN_CSS`**

Add these rules before the closing `</style>` tag in `ADMIN_CSS`:

```python
# Find the closing </style> tag in ADMIN_CSS (around line 75 in admin.py)
# and insert the following rules BEFORE it (after the last existing rule):

# Append to ADMIN_CSS before </style>:
"""
/* ── Match select cards ── */
.admin-match-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    transition: all 0.2s ease;
    cursor: pointer;
}
.admin-match-card:hover {
    border-color: rgba(255,255,255,0.15);
    background: var(--bg-card-hover);
}
.admin-match-card-inner {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}
.admin-match-teams {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: 'Chakra Petch', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text-primary);
}
.admin-team-a, .admin-team-b {
    flex: 1;
}
.admin-team-b {
    text-align: right;
}
.admin-vs {
    color: var(--text-muted);
    font-size: 0.7rem;
    text-transform: uppercase;
}
.admin-match-meta {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-family: 'Chakra Petch', sans-serif;
    font-size: 0.7rem;
    color: var(--text-muted);
}
.admin-status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
}
.admin-handicap-badge {
    display: inline-block;
    font-family: 'Chakra Petch', sans-serif;
    font-size: 0.68rem;
    font-weight: 500;
    padding: 2px 10px;
    border-radius: 10px;
    letter-spacing: 0.02em;
    align-self: flex-start;
}

/* ── Handicap editor panel ── */
.admin-editor-card {
    background: rgba(17, 24, 32, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-gold);
    border-radius: 12px;
    padding: 1.25rem;
}
.admin-editor-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    letter-spacing: 0.06em;
    color: var(--gold-bright);
    margin-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 0.5rem;
}
.admin-editor-placeholder {
    font-family: 'Chakra Petch', sans-serif;
    color: var(--text-muted);
    font-size: 0.85rem;
    text-align: center;
    padding: 3rem 1rem;
}
.admin-editor-match-header {
    font-family: 'Chakra Petch', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: var(--text-primary);
    margin-bottom: 1rem;
    text-align: center;
}
.admin-editor-team {
    font-size: 1.05rem;
}
.admin-editor-vs {
    color: var(--text-muted);
    font-size: 0.7rem;
    margin: 0 0.35rem;
}
.admin-editor-time {
    font-size: 0.72rem;
    color: var(--text-muted);
}
.admin-editor-label {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    color: var(--gold);
    margin: 0.75rem 0 0.25rem 0;
    text-transform: uppercase;
}
</style>
"""
```

Note: The actual edit must preserve ALL existing CSS rules. Only append the new rules.

- [ ] **Step 2: Verify the styles apply**

Run: `streamlit run premier_league_dashboard.py` → Admin → Matches
Expected: Match cards have proper spacing, hover effects, badge colors. Editor panel has gold-bordered glassmorphism card, Bebas Neue headers.

- [ ] **Step 3: Commit**

```bash
git add world_cup/admin.py
git commit -m "style: add CSS for match select cards and handicap editor"
```

---

### Task 5: Preserve existing Edit/Delete match section

**Files:**
- Modify: `world_cup/admin.py` — append the existing full-edit section below the split panel

- [ ] **Step 1: Add the existing full-edit form below the split panel in `_render_matches()`**

After the `left, right` columns block, add:

```python
    st.markdown("---")
    st.subheader("Edit Match (Full)")

    match_opts = [f"[{m['match_id']}] {m['team_a']} vs {m['team_b']} ({m['status']})" for m in matches]
    id_to_match = {f"[{m['match_id']}] {m['team_a']} vs {m['team_b']} ({m['status']})": m for m in matches}

    edit_sel = st.selectbox("Search & select match", match_opts, key="edit_match_select")
    match = id_to_match[edit_sel]

    if match:
        # (existing edit form code from lines 358-431 of current admin.py)
        c1, c2 = st.columns(2)
        new_team_a = c1.text_input("Team A", value=match["team_a"], key="edit_match_team_a")
        # ... (rest of existing full-edit form)
```

Note: This is copy-paste of the existing edit form from lines 358-431. No changes.

- [ ] **Step 2: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: preserve existing full-edit match section below split panel"
```

---

### Task 6: Manual verification checklist

- [ ] **Step 1: Run the app and verify all flows**

```bash
streamlit run premier_league_dashboard.py
```

Checklist:
1. Navigate to Admin → Matches
2. Filter dropdown works (All / Not Started / Live / Finished)
3. Click "Select" on a match → card highlights gold, editor populates
4. Change handicap line via quick-set buttons → input updates
5. Change favorite → radio toggles
6. Change fee → number updates
7. Live preview shows correct handicap language
8. "Save Handicap" → toast, DB updated, values persist on refresh
9. "Clear" button appears only when handicap is set → clears it
10. Click "Deselect" → editor shows placeholder
11. "Add Match" expander still works
12. Full edit section below split panel still works
13. Delete match still works

- [ ] **Step 2: Run existing tests to ensure no regressions**

```bash
python -m pytest world_cup/tests/ -v
```

Expected: All existing tests pass (no game logic or DB schema changes).

- [ ] **Step 3: Final commit if any fixes made**

```bash
git add world_cup/admin.py
git commit -m "fix: address manual verification findings"
```
