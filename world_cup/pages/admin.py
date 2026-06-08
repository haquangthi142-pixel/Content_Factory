import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from world_cup import db
from world_cup import admin as admin_panel

st.set_page_config(
    page_title="Admin Panel — World Cup 2026",
    page_icon="🔒",
    layout="wide",
)

db.init_db()
admin_panel.render_admin()
