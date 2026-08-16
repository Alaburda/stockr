"""Shared UI helpers — tighter, denser styling than Streamlit's defaults."""
import streamlit as st

_CSS = """
<style>
  /* tighten the page margins */
  .block-container { padding-top: 2.2rem; padding-bottom: 1rem; max-width: 100%; }
  /* compact headings */
  h1 { font-size: 1.6rem; margin: 0.2rem 0 0.6rem; }
  h2, h3 { font-size: 1.05rem; margin: 0.6rem 0 0.2rem; }
  /* denser dataframes */
  [data-testid="stDataFrame"] { font-size: 0.78rem; }
  [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 1px 6px !important; }
  /* compact metrics */
  [data-testid="stMetricValue"] { font-size: 1.1rem; }
  [data-testid="stMetricLabel"] { font-size: 0.75rem; }
  /* slimmer sidebar */
  section[data-testid="stSidebar"] { width: 230px !important; }
  /* reduce gap between elements */
  [data-testid="stVerticalBlock"] { gap: 0.5rem; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
