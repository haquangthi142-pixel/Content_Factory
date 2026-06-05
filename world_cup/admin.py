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
/* ── Admin panel: black bg, white text ── */
.admin-root, .admin-root * {
    color: #ffffff !important;
    font-family: 'Chakra Petch', sans-serif;
}
.admin-root h2, .admin-root h3, .admin-root h4 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 0.05em;
    color: #ffffff !important;
}

/* Select boxes */
.admin-root [data-baseweb="select"],
.admin-root .stSelectbox [data-baseweb="select"] {
    background: #0a0a0a !important;
    border-color: rgba(255,255,255,0.20) !important;
    border-radius: 6px !important;
}
.admin-root [data-baseweb="select"] *,
.admin-root [data-baseweb="select"] span,
.admin-root [data-baseweb="select"] div {
    color: #ffffff !important;
}

/* Dropdown popover */
.admin-root [data-baseweb="popover"] {
    background: #0a0a0a !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
}
.admin-root [data-baseweb="popover"] li {
    color: #ffffff !important;
}
.admin-root [data-baseweb="popover"] li:hover {
    background: #1a1a1a !important;
}
.admin-root [data-baseweb="popover"] input {
    color: #ffffff !important;
    background: #000000 !important;
}

/* Text inputs & number inputs */
.admin-root input[type="text"],
.admin-root input[type="password"],
.admin-root input[type="number"],
.admin-root .stTextInput input,
.admin-root .stNumberInput input {
    background: #0a0a0a !important;
    color: #ffffff !important;
    border-color: rgba(255,255,255,0.20) !important;
    border-radius: 6px !important;
}
.admin-root input::placeholder {
    color: rgba(255,255,255,0.35) !important;
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
.admin-root .stDataFrame {
    background: #0a0a0a !important;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 6px;
}
.admin-root .stDataFrame * {
    color: #ffffff !important;
}

/* Expanders */
.admin-root .stExpander {
    background: #0a0a0a !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 6px !important;
}
.admin-root .stExpander * {
    color: #ffffff !important;
}

/* Checkboxes */
.admin-root .stCheckbox {
    color: #ffffff !important;
}

/* Info / Success / Error boxes keep defaults */

/* Captions */
.admin-root .stCaption {
    color: rgba(255,255,255,0.55) !important;
}

/* HR */
.admin-root hr {
    border-color: rgba(255,255,255,0.08) !important;
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
            coins = st.number_input("Starting Coins", min_value=0, value=10, step=10, key="add_user_coins")
            if st.form_submit_button("Create User"):
                if phone.strip() and name.strip():
                    existing = db.get_user_by_phone(phone.strip())
                    if existing:
                        st.error(f"Phone {phone.strip()} already registered to **{existing['full_name']}**.")
                    else:
                        db.register_user(phone.strip(), name.strip())
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

    # -- Buy Coins --
    st.markdown("---")
    st.subheader("Buy Coins")

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
            ch1, ch2, ch3 = st.columns(3)
            h_line = ch1.selectbox("Line", [None, 0.5, 1.5, 2.5, 3.5], key="add_h_line")
            h_fav = ch2.selectbox("Favorite", [None, "A", "B"], key="add_h_fav")
            h_fee = ch3.number_input("Fee %", min_value=0, max_value=20, value=5, key="add_h_fee")
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

    st.caption(f"{len(matches)} match(es)")
    st.dataframe(matches, use_container_width=True, hide_index=True)

    st.markdown("---")

    # -- Edit / Delete Match --
    st.subheader("Edit Match")
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
        eh1, eh2, eh3 = st.columns(3)
        h_line_opts = [None, 0.5, 1.5, 2.5, 3.5]
        cur_h_line = match.get("handicap_line")
        eh_line = eh1.selectbox("Line", h_line_opts,
            index=h_line_opts.index(cur_h_line) if cur_h_line in h_line_opts else 0,
            key="edit_h_line")
        h_fav_opts = [None, "A", "B"]
        cur_h_fav = match.get("handicap_favorite")
        eh_fav = eh2.selectbox("Favorite", h_fav_opts,
            index=h_fav_opts.index(cur_h_fav) if cur_h_fav in h_fav_opts else 0,
            key="edit_h_fav")
        eh_fee = eh3.number_input("Fee %", min_value=0, max_value=20,
            value=match.get("handicap_fee") or 5, key="edit_h_fee")

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
    purchases = db.admin_get_purchases()

    if not purchases:
        st.info("No purchases yet.")
        return

    st.caption(f"{len(purchases)} purchase(s)")
    display_cols = ["tx_id", "user_name", "amount", "description", "created_at"]
    st.dataframe(
        [{k: p[k] for k in display_cols} for p in purchases],
        use_container_width=True, hide_index=True,
    )


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
