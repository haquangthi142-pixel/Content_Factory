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

RED_BUTTON = """
<style>
.admin-delete-btn button {
    background: linear-gradient(135deg, rgba(231,76,60,0.25) 0%, rgba(231,76,60,0.08) 100%) !important;
    border-color: rgba(231,76,60,0.5) !important;
    color: #e74c3c !important;
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

    return False


def _render_users():
    st.subheader("Users")
    users = db.admin_get_all_users()

    with st.expander("Add User", expanded=False):
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            phone = c1.text_input("Phone")
            name = c2.text_input("Full Name")
            coins = st.number_input("Starting Coins", min_value=0, value=1000, step=100)
            if st.form_submit_button("Create User"):
                if phone.strip() and name.strip():
                    db.register_user(phone.strip(), name.strip())
                    st.success(f"Created user: {name}")
                    st.rerun()
                else:
                    st.warning("Phone and name are required.")

    if not users:
        st.info("No users yet.")
        return

    st.caption(f"{len(users)} users")
    st.dataframe(users, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Edit / Delete User")
    user_ids = [u["id"] for u in users]
    selected_id = st.selectbox("Select user by ID", user_ids, key="edit_user_select")
    user = next((u for u in users if u["id"] == selected_id), None)

    if user:
        c1, c2, c3 = st.columns(3)
        new_phone = c1.text_input("Phone", value=user["phone"], key="edit_user_phone")
        new_name = c2.text_input("Full Name", value=user["full_name"], key="edit_user_name")
        new_coins = c3.number_input("Coins", value=user["current_coins"], step=10, key="edit_user_coins")

        col_save, col_del = st.columns([1, 1])
        with col_save:
            if st.button("Save Changes", key="save_user"):
                db.admin_update_user(selected_id, new_phone, new_name, new_coins)
                st.success("User updated.")
                st.rerun()
        with col_del:
            st.markdown(RED_BUTTON, unsafe_allow_html=True)
            st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
            confirm = st.checkbox("I understand this deletes all user data (bets, transactions, missions)", key=f"del_user_{selected_id}")
            if st.button("Delete User", key="del_user_btn", disabled=not confirm):
                db.admin_delete_user(selected_id)
                st.success(f"Deleted user #{selected_id}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def _render_matches():
    st.subheader("Matches")
    matches = db.admin_get_all_matches()

    with st.expander("Add Match", expanded=False):
        with st.form("add_match"):
            c1, c2 = st.columns(2)
            match_id = c1.number_input("Match ID", min_value=1, step=1, key="add_match_id")
            team_a = c1.text_input("Team A", key="add_team_a")
            team_b = c2.text_input("Team B", key="add_team_b")
            match_time = st.text_input("Match Time (ISO format)", placeholder="2026-06-11T20:00:00Z", key="add_match_time")
            c3, c4 = st.columns(2)
            status = c3.selectbox("Status", ["Not Started", "Live", "Finished"], key="add_match_status")
            result = c4.selectbox("Result", ["None", "A_win", "B_win", "Draw"], key="add_match_result")
            if st.form_submit_button("Add Match"):
                if team_a.strip() and team_b.strip() and match_time.strip():
                    db.admin_insert_match(
                        match_id, team_a, team_b, match_time, status,
                        None if result == "None" else result,
                    )
                    st.success(f"Added match #{match_id}")
                    st.rerun()
                else:
                    st.warning("Team A, Team B, and Match Time are required.")

    if not matches:
        st.info("No matches yet.")
        return

    st.caption(f"{len(matches)} matches")
    st.dataframe(matches, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Edit / Delete Match")
    match_ids = [m["match_id"] for m in matches]
    selected_id = st.selectbox("Select match by ID", match_ids, key="edit_match_select")
    match = next((m for m in matches if m["match_id"] == selected_id), None)

    if match:
        c1, c2 = st.columns(2)
        new_team_a = c1.text_input("Team A", value=match["team_a"], key="edit_match_team_a")
        new_team_b = c2.text_input("Team B", value=match["team_b"], key="edit_match_team_b")
        new_time = st.text_input("Match Time", value=match["match_time"], key="edit_match_time")
        c3, c4 = st.columns(2)
        status_opts = ["Not Started", "Live", "Finished"]
        new_status = c3.selectbox(
            "Status", status_opts,
            index=status_opts.index(match["status"]) if match["status"] in status_opts else 0,
            key="edit_match_status",
        )
        result_opts = ["None", "A_win", "B_win", "Draw"]
        cur_result = match.get("result") or "None"
        new_result = c4.selectbox(
            "Result", result_opts,
            index=result_opts.index(cur_result) if cur_result in result_opts else 0,
            key="edit_match_result",
        )

        col_save, col_settle, col_del = st.columns([1, 1, 1])
        with col_save:
            if st.button("Save Changes", key="save_match"):
                final_result = None if new_result == "None" else new_result
                db.admin_update_match(
                    selected_id, new_team_a, new_team_b, new_time, new_status,
                    final_result,
                )
                # Auto-settle bets if match is set to Finished with a result
                if new_status == "Finished" and final_result:
                    db.settle_match_bets(selected_id, final_result)
                    st.success(f"Match updated & bets settled: {final_result}")
                else:
                    st.success("Match updated.")
                st.rerun()
        with col_settle:
            # Standalone settle button for matches that already have a result
            cur_result_val = match.get("result")
            can_settle = cur_result_val and cur_result_val != "None"
            if st.button("⚡ Settle Bets", key="settle_match", disabled=not can_settle,
                         help="Settle all pending bets on this match"):
                if cur_result_val:
                    db.settle_match_bets(selected_id, cur_result_val)
                    st.success(f"Bets settled: {cur_result_val}")
                    st.rerun()
        with col_del:
            st.markdown(RED_BUTTON, unsafe_allow_html=True)
            st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
            confirm = st.checkbox("I understand this deletes all bets on this match", key=f"del_match_{selected_id}")
            if st.button("Delete Match", key="del_match_btn", disabled=not confirm):
                db.admin_delete_match(selected_id)
                st.success(f"Deleted match #{selected_id}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def _render_bets():
    st.subheader("Bets")
    bets = db.admin_get_all_bets()

    if not bets:
        st.info("No bets yet.")
        return

    st.caption(f"{len(bets)} bets")
    display_cols = ["bet_id", "user_name", "team_a", "team_b", "bet_choice", "bet_amount", "status", "created_at"]
    st.dataframe(
        [{k: b.get(k) for k in display_cols} for b in bets],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.markdown("#### Edit / Delete Bet")
    bet_ids = [b["bet_id"] for b in bets]
    selected_id = st.selectbox("Select bet by ID", bet_ids, key="edit_bet_select")
    bet = next((b for b in bets if b["bet_id"] == selected_id), None)

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
                db.admin_update_bet(selected_id, new_choice, new_amount, new_status)
                st.success("Bet updated.")
                st.rerun()
        with col_del:
            st.markdown(RED_BUTTON, unsafe_allow_html=True)
            st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
            confirm = st.checkbox("Confirm delete", key=f"del_bet_{selected_id}")
            if st.button("Delete Bet", key="del_bet_btn", disabled=not confirm):
                db.admin_delete_bet(selected_id)
                st.success(f"Deleted bet #{selected_id}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def _render_transactions():
    st.subheader("Coin Transactions")
    txs = db.admin_get_all_transactions()

    if not txs:
        st.info("No transactions yet.")
        return

    st.caption(f"{len(txs)} transactions")
    display_cols = ["tx_id", "user_name", "amount", "type", "description", "created_at"]
    st.dataframe(
        [{k: t.get(k) for k in display_cols} for t in txs],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.markdown("#### Delete Transaction")
    tx_ids = [t["tx_id"] for t in txs]
    selected_id = st.selectbox("Select transaction by ID", tx_ids, key="edit_tx_select")

    st.markdown(RED_BUTTON, unsafe_allow_html=True)
    st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
    confirm = st.checkbox("Confirm delete", key=f"del_tx_{selected_id}")
    if st.button("Delete Transaction", key="del_tx_btn", disabled=not confirm):
        db.admin_delete_transaction(selected_id)
        st.success(f"Deleted transaction #{selected_id}")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_missions():
    st.subheader("Mission Logs")
    missions = db.admin_get_all_missions()

    if not missions:
        st.info("No mission logs yet.")
        return

    st.caption(f"{len(missions)} entries")
    display_cols = ["log_id", "user_name", "mission_type", "reward_coins", "completed_at"]
    st.dataframe(
        [{k: m.get(k) for k in display_cols} for m in missions],
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.markdown("#### Delete Mission Log")
    log_ids = [m["log_id"] for m in missions]
    selected_id = st.selectbox("Select log by ID", log_ids, key="edit_mission_select")

    st.markdown(RED_BUTTON, unsafe_allow_html=True)
    st.markdown('<div class="admin-delete-btn">', unsafe_allow_html=True)
    confirm = st.checkbox("Confirm delete", key=f"del_mission_{selected_id}")
    if st.button("Delete Log", key="del_mission_btn", disabled=not confirm):
        db.admin_delete_mission(selected_id)
        st.success(f"Deleted mission log #{selected_id}")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_admin():
    if not _pin_gate():
        return

    st.title("Admin Panel")
    st.caption(f"Authenticated — {db.DB_PATH}")

    tabs = st.tabs(["Users", "Matches", "Bets", "Transactions", "Missions"])

    with tabs[0]:
        _render_users()
    with tabs[1]:
        _render_matches()
    with tabs[2]:
        _render_bets()
    with tabs[3]:
        _render_transactions()
    with tabs[4]:
        _render_missions()
