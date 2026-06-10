# Admin Matches Tab — Handicap Editor Redesign

**Date:** 2026-06-10
**Status:** Approved

## Overview

Redesign the "Matches" tab in the Admin panel with a split-panel layout: a scrollable match list on the left and a fixed handicap editor on the right. Clicking a match loads its handicap data into the editor for quick adjustment.

## Motivation

The current Matches tab uses a `st.selectbox` dropdown to pick a match, then shows all edit fields (teams, time, status, result, scores, handicap) in a single form. This is functional but slow for the admin's primary workflow: rapidly setting and adjusting handicaps across many matches.

## Design: "Pitchside Analyst"

Aesthetic: Extends the existing dark World Cup theme — deep navy/charcoal backgrounds, gold accents, Bebas Neue headers, glassmorphism cards.

### Layout

Split panel using `st.columns([1, 1])`:

- **Left column**: Scrollable list of match cards with filter, plus "Add Match" expander at top
- **Right column**: Fixed handicap editor panel (glassmorphism card)

### Left Panel — Match Cards

Each match card shows:
- Team crests + names
- Match date & time
- Current handicap badge (green pill if set, grey "—" if not set)
- Status dot: orange (Live), green (Finished), muted (Upcoming)
- **Selected state**: gold left-border glow, subtle background lift

Filter dropdown at top: "All", "Upcoming", "Live", "Finished"
"Add Match" expander stays at top, collapsed by default.

### Right Panel — Handicap Editor

When a match is selected:
- Header: team crests + names + date (read-only, for context)
- Three controls in vertical stack:
  - **Handicap Line**: number input with quick-set buttons (0, 0.5, 1.0, 1.5, 2.0)
  - **Favorite**: pill toggle — "Team A" / "Team B"
  - **Fee %**: compact number input (0–20)
- **Live preview**: handicap in plain language + calculated payout multiplier
- **Save button**: gold, full-width
- **Clear button**: removes handicap entirely (sets line=None, fav=None)

When no match is selected: placeholder "← Select a match to edit handicap"

### Visual Details

- Editor card uses glassmorphism (`backdrop-filter: blur()` on semi-transparent dark bg)
- Selected match card has subtle pulsing gold border animation
- Handicap preview updates as values change (no extra rerun needed — pure Python)
- Smooth visual feedback: save confirmation via `st.toast()`

## Data Flow

```
Match card clicked
  → st.session_state["selected_match_id"] = match_id
  → st.rerun()
  → Right panel: db.get_match(selected_match_id)
  → Form fields pre-populate from match row
  → User edits handicap values
  → "Save Handicap" clicked
  → db.admin_update_match(match_id, ..., handicap_line=..., handicap_favorite=..., handicap_fee=...)
  → st.toast("Handicap updated ✓")
  → st.rerun()
```

Only `handicap_line`, `handicap_favorite`, and `handicap_fee` are editable via the right panel. All other match fields (teams, status, result, scores) remain editable in the existing "Edit Match" section below the split panel.

## Error Handling

| Scenario | Behavior |
|---|---|
| Stale match_id (deleted by another admin) | Right panel shows "Match not found" placeholder |
| Handicap line set but no favorite | Soft warning: "Select a favorite to activate the handicap" |
| DB write error | `st.error()` with message |
| Empty state (no matches) | "No matches yet" info message |

## Scope

### In scope
- Split-panel layout for Matches tab
- Click-to-select match cards (left panel)
- Handicap editor form (right panel)
- Handicap clear/reset
- Status filter dropdown
- Live handicap preview text

### Out of scope
- Bulk handicap editing
- Drag-and-drop reordering
- Match card redesign beyond the handicap badge addition
- Changes to other admin tabs

## Implementation Notes

- **File**: `world_cup/admin.py` — modify `_render_matches()` only
- **No DB changes**: handicap columns already exist in `matches` table
- **No new dependencies**: Streamlit-only implementation
- **Existing CSS**: extends `ADMIN_CSS` in `admin.py`, aligns with `GLOBAL_CSS` in `components.py`
- **Estimated**: ~80 lines of Streamlit code replacing the current edit section

## Testing

- Manual: select a match → edit handicap → save → verify DB
- Manual: clear handicap → verify line/fav become NULL
- Manual: filter by status → verify only matching statuses shown
- Manual: delete match via existing Delete button → verify editor clears
- Existing tests in `world_cup/tests/test_game.py` should continue to pass (no game logic changes)
