import os
import time
import streamlit as st
from dotenv import load_dotenv

from world_cup import db

load_dotenv()

ADMIN_PIN = os.getenv("ADMIN_PIN", "0000")

try:
    ADMIN_PIN = st.secrets.get("ADMIN_PIN", ADMIN_PIN)
except Exception:
    pass

MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = 60

ADMIN_CSS = """
<style>
/* ── Admin panel: minimal overrides, default Streamlit colors ── */
.admin-root {
    font-family: 'Chakra Petch', sans-serif;
}
.admin-root h2, .admin-root h3, .admin-root h4 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 0.05em;
}

/* Buttons */
.admin-root .stButton button {
    background: #0a0a0a !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 6px !important;
    font-weight: 600;
}
.admin-root .stButton button:hover {
    background: #1a1a1a !important;
    border-color: rgba(255,255,255,0.45) !important;
}
.admin-root .stButton button:disabled {
    opacity: 0.30;
}

/* Delete buttons — red tint */
.admin-root .admin-delete-btn button {
    background: rgba(231,76,60,0.12) !important;
    border-color: rgba(231,76,60,0.40) !important;
    color: #e74c3c !important;
}
.admin-root .admin-delete-btn button:hover {
    background: rgba(231,76,60,0.22) !important;
}

/* Credit Coins button — green tint */
.admin-root .admin-credit-btn button {
    background: rgba(46,204,113,0.12) !important;
    border-color: rgba(46,204,113,0.40) !important;
    color: #2ecc71 !important;
}
.admin-root .admin-credit-btn button:hover {
    background: rgba(46,204,113,0.22) !important;
}

/* Dataframes / tables */
.admin-root [data-testid="stTable"] {
    background: transparent;
}

.admin-root hr {
    border-color: rgba(255,255,255,0.08) !important;
}

/* ── Admin match select cards ── */
.admin-match-card {
    background: var(--bg-card, #111820);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    transition: all 0.2s ease;
    cursor: pointer;
}
.admin-match-card:hover {
    border-color: rgba(255,255,255,0.15);
    background: var(--bg-card-hover, #161e2a);
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
    color: var(--text-primary, #e8e4dc);
}
.admin-team-a, .admin-team-b {
    flex: 1;
}
.admin-team-b {
    text-align: right;
}
.admin-vs {
    color: var(--text-muted, #8b8d92);
    font-size: 0.7rem;
    text-transform: uppercase;
}
.admin-match-meta {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-family: 'Chakra Petch', sans-serif;
    font-size: 0.7rem;
    color: var(--text-muted, #8b8d92);
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

/* ── Admin handicap editor panel ── */
.admin-editor-card {
    background: rgba(17, 24, 32, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(212, 168, 67, 0.3);
    border-radius: 12px;
    padding: 1.25rem;
}
.admin-editor-header {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.3rem;
    letter-spacing: 0.06em;
    color: var(--gold-bright, #f0c75e);
    margin-bottom: 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 0.5rem;
}
.admin-editor-placeholder {
    font-family: 'Chakra Petch', sans-serif;
    color: var(--text-muted, #8b8d92);
    font-size: 0.85rem;
    text-align: center;
    padding: 3rem 1rem;
}
.admin-editor-match-header {
    font-family: 'Chakra Petch', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: var(--text-primary, #e8e4dc);
    margin-bottom: 1rem;
    text-align: center;
}
.admin-editor-team {
    font-size: 1.05rem;
}
.admin-editor-vs {
    color: var(--text-muted, #8b8d92);
    font-size: 0.7rem;
    margin: 0 0.35rem;
}
.admin-editor-time {
    font-size: 0.72rem;
    color: var(--text-muted, #8b8d92);
}
.admin-editor-label {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    color: var(--gold, #d4a843);
    margin: 0.75rem 0 0.25rem 0;
    text-transform: uppercase;
}
</style>
"""


def _pin_gate():
    if "admin_attempts" not in st.session_state:
        st.session_state.admin_attempts = 0
    if "admin_lockout_until" not in st.session_state:
        st.session_state.admin_lockout_until = 0.0

    if st.session_state.get("admin_authenticated"):
        return True

    st.markdown(ADMIN_CSS, unsafe_allow_html=True)
    st.markdown('<div class="admin-root">', unsafe_allow_html=True)
    st.title("Admin Panel")
    st.markdown("---")

    now = time.time()
    lockout_remaining = int(st.session_state.admin_lockout_until - now)

    if lockout_remaining > 0:
        mins = lockout_remaining // 60
        secs = lockout_remaining % 60
        if mins:
            st.error(f"Too many failed attempts. Try again in {mins}m {secs}s.")
        else:
            st.error(f"Too many failed attempts. Try again in {secs}s.")
        st.markdown('</div>', unsafe_allow_html=True)
        return False

    attempts = st.session_state.admin_attempts
    remaining = MAX_ATTEMPTS - attempts

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.subheader("Enter Admin PIN")
        pin = st.text_input("PIN", type="password", key="admin_pin_input", label_visibility="collapsed")
        st.caption(f"{remaining} attempt{'s' if remaining > 1 else ''} remaining")
        if st.button("Unlock", use_container_width=True):
            if pin == ADMIN_PIN:
                st.session_state.admin_authenticated = True
                st.session_state.admin_attempts = 0
                st.session_state.admin_lockout_until = 0.0
                st.rerun()
            else:
                st.session_state.admin_attempts += 1
                if st.session_state.admin_attempts >= MAX_ATTEMPTS:
                    st.session_state.admin_lockout_until = time.time() + LOCKOUT_SECONDS
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    return False


def _render_users():
    users = db.admin_get_all_users()

    # -- Add User --
    with st.expander("➕ Add User", expanded=False):
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            phone = c1.text_input("Phone", key="add_user_phone")
            name = c2.text_input("Full Name", key="add_user_name")
            c3, c4 = st.columns(2)
            password = c3.text_input("Password", type="password", value="123123", key="add_user_password")
            coins = c4.number_input("Starting Coins", min_value=0, value=10, step=10, key="add_user_coins")
            if st.form_submit_button("Create User"):
                if phone.strip() and name.strip():
                    existing = db.get_user_by_phone(phone.strip())
                    if existing:
                        st.error(f"Phone {phone.strip()} already registered to **{existing['full_name']}**.")
                    else:
                        db.register_user(phone.strip(), name.strip(), password.strip())
                        st.success(f"Created user: {name}")
                        st.rerun()
                else:
                    st.warning("Phone and name are required.")

    if not users:
        st.info("No users yet.")
        return

    st.caption(f"{len(users)} user(s)")

    # -- User list table --
    st.dataframe(
        [{k: u[k] for k in ["id", "phone", "full_name", "current_coins", "created_at"]} for u in users],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")

    # -- Edit / Delete User --
    st.subheader("Edit User")
    user_opts = [f"[{u['id']}] {u['phone']} — {u['full_name']}" for u in users]
    id_to_user = {f"[{u['id']}] {u['phone']} — {u['full_name']}": u for u in users}

    edit_sel = st.selectbox("Search & select user", user_opts, key="edit_user_select")
    user = id_to_user[edit_sel]

    if user:
        c1, c2, c3 = st.columns(3)
        new_phone = c1.text_input("Phone", value=user["phone"], key="edit_user_phone")
        new_name = c2.text_input("Full Name", value=user["full_name"], key="edit_user_name")
        new_coins = c3.number_input("Coins", value=user["current_coins"], step=10, key="edit_user_coins")

        col_save, col_del = st.columns([1, 1])
        with col_save:
            if st.button("Save Changes", key="save_user"):
                db.admin_update_user(user["id"], new_phone, new_name, new_coins)
                st.success("User updated.")
                st.rerun()
        with col_del:
            st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
            confirm = st.checkbox("I understand this deletes all user data", key=f"del_user_{user['id']}")
            if st.button("Delete User", key="del_user_btn", disabled=not confirm):
                db.admin_delete_user(user["id"])
                st.success(f"Deleted user #{user['id']}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # -- Pending Purchase Requests --
    st.markdown("---")
    st.subheader("Pending Purchase Requests")

    pending_reqs = db.admin_get_purchase_requests("pending")
    if pending_reqs:
        for req in pending_reqs:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f"**#{req['req_id']}** — {req['user_name']} ({req['phone']}) "
                    f"requests **{req['coin_amount']} coins** ({req['vnd_amount']:,} VND) — "
                    f"{req['created_at'][:16]}"
                )
            with col_btn:
                c_approve, c_reject = st.columns(2)
                with c_approve:
                    if st.button(f"Approve", key=f"approve_{req['req_id']}"):
                        db.admin_approve_purchase_request(req["req_id"])
                        st.success(f"Approved #{req['req_id']}")
                        st.rerun()
                with c_reject:
                    if st.button(f"Reject", key=f"reject_{req['req_id']}"):
                        db.admin_reject_purchase_request(req["req_id"])
                        st.warning(f"Rejected #{req['req_id']}")
                        st.rerun()
            st.markdown("---")
    else:
        st.info("No pending requests.")

    # -- Manual Buy Coins --
    st.subheader("Manual Credit")

    # Clear form after purchase
    if st.session_state.get("_clear_buy_form"):
        for k in ["_clear_buy_form", "buy_coins_done", "buy_coins_result", "buy_coins_confirm"]:
            st.session_state.pop(k, None)
        st.rerun()

    # Phone search — text input avoids BaseWeb select styling issues
    search_phone = st.text_input(
        "Search player by phone",
        placeholder="Type phone number...",
        key="buy_coins_search",
    )

    # Filter users by phone match
    matches = [u for u in users if search_phone.strip() in u["phone"]] if search_phone.strip() else users[:5]

    if not matches:
        if search_phone.strip():
            st.warning("No player found with that phone number.")
        return

    # Show matching players
    match_opts = [f"{u['phone']} — {u['full_name']} [{u['current_coins']} coins]" for u in matches]
    match_ids = [u["id"] for u in matches]

    if len(match_opts) == 1:
        buy_user_id = match_ids[0]
        st.success(f"Selected: {match_opts[0]}")
    else:
        buy_sel = st.radio("Select player", match_opts, key="buy_coins_radio")
        idx = match_opts.index(buy_sel)
        buy_user_id = match_ids[idx]

    c1, c2 = st.columns(2)
    with c1:
        buy_vnd = st.number_input(
            "VND Amount",
            min_value=100000, value=100000, step=100000,
            key="buy_vnd",
            help="1,000 VND = 1 coin. Min 100,000 VND.",
        )
        buy_coins = buy_vnd // 1000
        st.caption(f"Credits: **{buy_coins} coins** ({buy_vnd:,} VND)")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="admin-credit-btn">', unsafe_allow_html=True)
        confirmed = st.checkbox("Confirm purchase", key="buy_coins_confirm")

        if "buy_coins_done" not in st.session_state:
            st.session_state.buy_coins_done = False

        if st.button("Credit Coins", key="buy_coins_btn", disabled=not confirmed, use_container_width=True):
            try:
                credited = db.purchase_coins(buy_user_id, buy_vnd)
                st.session_state.buy_coins_done = True
                st.session_state.buy_coins_result = (buy_user_id, credited, buy_vnd)
            except ValueError as e:
                st.error(str(e))
        st.markdown('</div>', unsafe_allow_html=True)

    # Show status after purchase
    if st.session_state.get("buy_coins_done"):
        uid, credited, vnd = st.session_state.buy_coins_result
        updated_user = db.get_user(uid)
        st.success(f"Done! +{credited} coins → **{updated_user['full_name']}** ({updated_user['phone']}). New balance: **{updated_user['current_coins']:,} coins**")
        st.session_state._clear_buy_form = True
        st.rerun()


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
            # Convert to DB values
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

    st.markdown("---")
    st.subheader("Edit Match (Full)")

    match_opts = [f"[{m['match_id']}] {m['team_a']} vs {m['team_b']} ({m['status']})" for m in matches]
    id_to_match = {f"[{m['match_id']}] {m['team_a']} vs {m['team_b']} ({m['status']})": m for m in matches}

    edit_sel = st.selectbox("Search & select match", match_opts, key="edit_match_select")
    match = id_to_match[edit_sel]

    if match:
        c1, c2 = st.columns(2)
        new_team_a = c1.text_input("Team A", value=match["team_a"], key="edit_match_team_a")
        new_team_b = c2.text_input("Team B", value=match["team_b"], key="edit_match_team_b")
        new_time = st.text_input("Match Time", value=match["match_time"], key="edit_match_time")

        c3, c4 = st.columns(2)
        status_opts = ["Not Started", "Live", "Finished"]
        new_status = c3.selectbox("Status", status_opts,
            index=status_opts.index(match["status"]) if match["status"] in status_opts else 0,
            key="edit_match_status")
        result_opts = ["None", "A_win", "B_win", "Draw"]
        cur_result = match.get("result") or "None"
        new_result = c4.selectbox("Result", result_opts,
            index=result_opts.index(cur_result) if cur_result in result_opts else 0,
            key="edit_match_result")

        es1, es2 = st.columns(2)
        new_score_a = es1.number_input("Score A", min_value=0, step=1, key="edit_score_a",
                                       value=match.get("score_a") or 0)
        new_score_b = es2.number_input("Score B", min_value=0, step=1, key="edit_score_b",
                                       value=match.get("score_b") or 0)

        st.caption("Handicap")
        cur_h_line = match.get("handicap_line")
        cur_h_fav = match.get("handicap_favorite")
        ehc1, ehc2 = st.columns(2)
        eh_line = ehc1.number_input("Team A gives (goals)", min_value=0.0, max_value=10.0, step=0.5,
            value=float(cur_h_line) if cur_h_line is not None else 0.0, key="edit_h_line")
        eh_fav = ehc2.selectbox("Favorite",
            ["None", "Team A", "Team B"],
            index=0 if cur_h_fav is None else (1 if cur_h_fav == "A" else 2),
            key="edit_h_fav")
        eh_fee = st.number_input("Fee %", min_value=0, max_value=20,
            value=match.get("handicap_fee") or 5, key="edit_h_fee")
        # Convert to DB values
        if eh_fav == "None" or eh_line == 0.0:
            eh_line, eh_fav = None, None
        else:
            eh_fav = "A" if eh_fav == "Team A" else "B"

        col_save, col_settle, col_del = st.columns([1, 1, 1])
        with col_save:
            if st.button("Save Changes", key="save_match"):
                final_result = None if new_result == "None" else new_result
                db.admin_update_match(
                    match["match_id"], new_team_a, new_team_b, new_time, new_status,
                    final_result,
                    score_a=new_score_a, score_b=new_score_b,
                    handicap_line=eh_line, handicap_favorite=eh_fav, handicap_fee=eh_fee,
                )
                if new_status == "Finished" and final_result:
                    db.settle_match_bets(match["match_id"], final_result)
                    st.success(f"Updated & bets settled: {final_result}")
                else:
                    st.success("Match updated.")
                st.rerun()
        with col_settle:
            cur_result_val = match.get("result")
            can_settle = cur_result_val and cur_result_val != "None"
            if st.button("Settle Bets", key="settle_match", disabled=not can_settle,
                         help="Settle pending bets on this match"):
                if cur_result_val:
                    db.settle_match_bets(match["match_id"], cur_result_val)
                    st.success(f"Bets settled: {cur_result_val}")
                    st.rerun()
        with col_del:
            st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
            confirm = st.checkbox("Deletes all bets on this match", key=f"del_match_{match['match_id']}")
            if st.button("Delete Match", key="del_match_btn", disabled=not confirm):
                db.admin_delete_match(match["match_id"])
                st.success(f"Deleted match #{match['match_id']}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def _render_match_select_card(match):
    """Render a single clickable match card for the admin match list."""
    selected_id = st.session_state.get("selected_match_id")
    is_selected = selected_id == match["match_id"]

    # Build the handicap badge text
    h_line = match.get("handicap_line")
    h_fav = match.get("handicap_favorite")
    if h_line is not None and h_fav is not None:
        fav_team = match["team_a"] if h_fav == "A" else match["team_b"]
        badge = f"{fav_team} &#x2212;{h_line} &middot; {match.get('handicap_fee', 5)}%"
        badge_color = "rgba(46,204,113,0.18)"
        badge_text = "#2ecc71"
    else:
        badge = "&mdash; no handicap"
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
        from datetime import datetime as _dt
        dt = _dt.strptime(match_time[:19], "%Y-%m-%dT%H:%M:%S")
        time_display = dt.strftime("%a %d %b &middot; %H:%M")
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
                <span>&middot;</span>
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


def _render_handicap_editor(matches):
    """Render the handicap editor panel for the selected match."""
    selected_id = st.session_state.get("selected_match_id")

    # Look up the selected match (needed for both empty state and header)
    match = None
    if selected_id is not None:
        for m in matches:
            if m["match_id"] == selected_id:
                match = m
                break

    # Editor card wrapper
    st.markdown("""
    <div class="admin-editor-card">
        <div class="admin-editor-header">HANDICAP EDITOR</div>
    """, unsafe_allow_html=True)

    if selected_id is None:
        st.markdown("""
        <div class="admin-editor-placeholder">
            &#x2190; Select a match to edit handicap
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if match is None:
        st.markdown(f"""
        <div class="admin-editor-placeholder">
            Match #{selected_id} not found &mdash; it may have been deleted.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
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

    # Current handicap state from DB
    cur_line = match.get("handicap_line")
    cur_fav = match.get("handicap_favorite")
    cur_fee = match.get("handicap_fee") or 5

    # Handicap Line
    st.markdown('<p class="admin-editor-label">Handicap Line</p>', unsafe_allow_html=True)
    quick_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    qcols = st.columns(len(quick_vals) + 1)
    line_key = f"edit_h_line_{selected_id}"
    if line_key not in st.session_state:
        st.session_state[line_key] = float(cur_line) if cur_line is not None else 0.0
    for i, val in enumerate(quick_vals):
        with qcols[i]:
            is_active = abs(st.session_state[line_key] - val) < 0.01
            btn_label = f"**{val}**" if is_active else str(val)
            if st.button(btn_label, key=f"qh_{val}_{selected_id}", use_container_width=True):
                st.session_state[line_key] = val
                st.rerun()
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
    if fav_choice != "None" and st.session_state[line_key] > 0.0:
        payout_mult = float(db.HANDICAP_PAYOUT) if hasattr(db, 'HANDICAP_PAYOUT') else 2.0
        st.info(
            f"**{fav_choice}** gives **{st.session_state[line_key]}** goals &middot; "
            f"Fee: **{new_fee}%**  \n"
            f"Payout multiplier: **{payout_mult:.1f}&times;** "
            f"(stake minus fee, doubled on win)"
        )
    elif st.session_state[line_key] > 0.0:
        st.caption("⚠️ Select a favorite to activate the handicap.")

    # Save & Clear
    col_save, col_clear = st.columns([2, 1])
    with col_save:
        if st.button("\U0001f4be Save Handicap", key=f"save_h_{selected_id}", use_container_width=True):
            # Build final values
            if fav_choice == "None" or st.session_state[line_key] == 0.0:
                final_line, final_fav = None, None
            else:
                final_line = float(st.session_state[line_key])
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
                for k in [line_key, fav_key, fee_key]:
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

    with col_clear:
        if cur_line is not None or cur_fav is not None:
            if st.button("\U0001f5d1 Clear", key=f"clear_h_{selected_id}", use_container_width=True):
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

    st.markdown("</div>", unsafe_allow_html=True)


def _render_bets():
    bets = db.admin_get_all_bets()

    if not bets:
        st.info("No bets yet.")
        return

    st.caption(f"{len(bets)} bet(s)")
    display_cols = ["bet_id", "user_name", "team_a", "team_b", "bet_choice", "bet_amount", "status", "created_at"]
    st.dataframe(
        [{k: b.get(k) for k in display_cols} for b in bets],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.subheader("Edit Bet")
    bet_opts = [f"#{b['bet_id']} — {b['user_name']} | {b['team_a']} vs {b['team_b']} | {b['status']}" for b in bets]
    id_to_bet = {f"#{b['bet_id']} — {b['user_name']} | {b['team_a']} vs {b['team_b']} | {b['status']}": b for b in bets}

    edit_sel = st.selectbox("Search & select bet", bet_opts, key="edit_bet_select")
    bet = id_to_bet[edit_sel]

    if bet:
        c1, c2, c3 = st.columns(3)
        new_choice = c1.selectbox("Choice", ["A", "B", "DRAW"],
            index=["A", "B", "DRAW"].index(bet["bet_choice"]) if bet["bet_choice"] in ["A", "B", "DRAW"] else 0,
            key="edit_bet_choice")
        new_amount = c2.number_input("Amount", value=bet["bet_amount"], step=10, min_value=10, key="edit_bet_amount")
        status_opts = ["Pending", "Won", "Lost", "Refunded"]
        new_status = c3.selectbox("Status", status_opts,
            index=status_opts.index(bet["status"]) if bet["status"] in status_opts else 0,
            key="edit_bet_status")

        col_save, col_del = st.columns([1, 1])
        with col_save:
            if st.button("Save Changes", key="save_bet"):
                db.admin_update_bet(bet["bet_id"], new_choice, new_amount, new_status)
                st.success("Bet updated.")
                st.rerun()
        with col_del:
            st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
            confirm = st.checkbox("Confirm delete", key=f"del_bet_{bet['bet_id']}")
            if st.button("Delete Bet", key="del_bet_btn", disabled=not confirm):
                db.admin_delete_bet(bet["bet_id"])
                st.success(f"Deleted bet #{bet['bet_id']}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def _render_transactions():
    txs = db.admin_get_all_transactions()

    if not txs:
        st.info("No transactions yet.")
        return

    st.caption(f"{len(txs)} transaction(s)")
    display_cols = ["tx_id", "user_name", "amount", "type", "description", "created_at"]
    st.dataframe(
        [{k: t.get(k) for k in display_cols} for t in txs],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.subheader("Delete Transaction")
    tx_opts = [f"#{t['tx_id']} — {t['user_name']} | {t['type']} | {t['amount']} coins" for t in txs]
    id_to_tx = {f"#{t['tx_id']} — {t['user_name']} | {t['type']} | {t['amount']} coins": t for t in txs}

    edit_sel = st.selectbox("Search & select transaction", tx_opts, key="edit_tx_select")
    tx = id_to_tx[edit_sel]

    st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
    confirm = st.checkbox("Confirm delete", key=f"del_tx_{tx['tx_id']}")
    if st.button("Delete Transaction", key="del_tx_btn", disabled=not confirm):
        db.admin_delete_transaction(tx["tx_id"])
        st.success(f"Deleted transaction #{tx['tx_id']}")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_missions():
    missions = db.admin_get_all_missions()

    if not missions:
        st.info("No mission logs yet.")
        return

    st.caption(f"{len(missions)} entr{'y' if len(missions) == 1 else 'ies'}")
    display_cols = ["log_id", "user_name", "mission_type", "reward_coins", "completed_at"]
    st.dataframe(
        [{k: m.get(k) for k in display_cols} for m in missions],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.subheader("Delete Mission Log")
    log_opts = [f"#{m['log_id']} — {m['user_name']} | {m['mission_type']} | +{m['reward_coins']}" for m in missions]
    id_to_log = {f"#{m['log_id']} — {m['user_name']} | {m['mission_type']} | +{m['reward_coins']}": m for m in missions}

    edit_sel = st.selectbox("Search & select log", log_opts, key="edit_mission_select")
    log = id_to_log[edit_sel]

    st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
    confirm = st.checkbox("Confirm delete", key=f"del_mission_{log['log_id']}")
    if st.button("Delete Log", key="del_mission_btn", disabled=not confirm):
        db.admin_delete_mission(log["log_id"])
        st.success(f"Deleted mission log #{log['log_id']}")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_purchases():
    # -- Completed purchase transactions --
    purchases = db.admin_get_purchases()
    st.subheader("Completed Transactions")
    if purchases:
        st.caption(f"{len(purchases)} purchase(s)")
        display_cols = ["tx_id", "user_name", "amount", "description", "created_at"]
        st.dataframe(
            [{k: p[k] for k in display_cols} for p in purchases],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No completed purchases yet.")

    # -- All purchase requests --
    st.markdown("---")
    st.subheader("Request History")
    all_reqs = db.admin_get_purchase_requests()
    if all_reqs:
        st.caption(f"{len(all_reqs)} request(s)")
        display_cols = ["req_id", "user_name", "phone", "vnd_amount", "coin_amount", "status", "created_at"]
        st.dataframe(
            [{k: r.get(k) for k in display_cols} for r in all_reqs],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No purchase requests yet.")


def render_admin():
    if not _pin_gate():
        return

    st.markdown(ADMIN_CSS, unsafe_allow_html=True)
    st.markdown('<div class="admin-root">', unsafe_allow_html=True)

    st.title("Admin Panel")
    st.caption(f"DB: {db.DB_PATH}")

    tabs = st.tabs(["Users", "Matches", "Bets", "Transactions", "Purchases", "Missions"])

    with tabs[0]:
        _render_users()
    with tabs[1]:
        _render_matches()
    with tabs[2]:
        _render_bets()
    with tabs[3]:
        _render_transactions()
    with tabs[4]:
        _render_purchases()
    with tabs[5]:
        _render_missions()

    st.markdown('</div>', unsafe_allow_html=True)
