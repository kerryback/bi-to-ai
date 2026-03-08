"""Chinook chart app — ask questions and get charts, not just tables."""

# --- Import libraries --------------------------------------------------------
# json: read/write structured data    os: access environment variables & paths
# sqlite3: connect to the SQLite database file
# datetime: timestamp each query for the log
# matplotlib (plt): creates static charts (bar, line, scatter, etc.)
# pandas (pd): tabular data manipulation
# plotly (px, go): creates interactive charts with hover/zoom
# streamlit (st): builds the web interface from this single script
# anthropic: official Python client for the Anthropic API (Claude)

import json
import os
import sqlite3
from datetime import datetime, timezone

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from anthropic import Anthropic

matplotlib.use("Agg")  # use a non-interactive backend (no pop-up windows)

# --- Schema description -------------------------------------------------------
# This text tells Claude what tables and columns exist in the database.
# The LLM never sees the actual data — only these table/column names.
# Arrows (→) show foreign-key relationships between tables.

SCHEMA = """
The Chinook database has these tables:

artists(ArtistId, Name)
albums(AlbumId, Title, ArtistId) → artists
tracks(TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice) → albums, genres, media_types
genres(GenreId, Name)
media_types(MediaTypeId, Name)
playlists(PlaylistId, Name)
playlist_track(PlaylistId, TrackId) → playlists, tracks
employees(EmployeeId, LastName, FirstName, Title, ReportsTo, BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email) → employees (self-ref)
customers(CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId) → employees
invoices(InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState, BillingCountry, BillingPostalCode, Total) → customers
invoice_items(InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity) → invoices, tracks

Revenue = SUM(invoice_items.UnitPrice * invoice_items.Quantity).
"""

# --- System prompt ------------------------------------------------------------
# Unlike the query app (which asks for SQL), this prompt asks Claude to return
# a complete Python script that queries the database AND produces a chart.
# The rules tell Claude which libraries are already loaded and how to display
# results inside Streamlit.

SYSTEM_PROMPT = (
    "You are a Python code assistant for the Chinook music database. "
    "Given the schema below and a user question, return ONLY a Python script. "
    "No explanation, no markdown fences, no comments outside the code.\n\n"
    "Rules for the Python script:\n"
    "- Use sqlite3 to query the database. The connection is already available as `conn`.\n"
    "- Use pandas for data manipulation.\n"
    "- If the question asks for a chart or visualization, use matplotlib (via `plt`). "
    "Call `st.pyplot(fig)` to display it.\n"
    "- If the question asks for an interactive chart, use plotly and call `st.plotly_chart(fig)`.\n"
    "- Always store query results in a DataFrame called `df`.\n"
    "- If the result is tabular (no chart requested), just create the `df`. "
    "The app will display it automatically.\n"
    "- Do NOT call plt.show(). Use st.pyplot(fig) instead.\n"
    "- Do NOT call conn.close().\n"
    "- Do NOT import sqlite3, pandas, matplotlib, plotly, or streamlit — they are already available.\n\n"
    "Available variables: conn (sqlite3 connection), pd, plt, px, go, st\n\n"
    + SCHEMA
)

# --- File paths ---------------------------------------------------------------
# DB_PATH:  location of the Chinook SQLite database (same folder as this script)
# LOG_PATH: every question/answer pair is appended here for auditing

DB_PATH = os.path.join(os.path.dirname(__file__), "chinook.db")
LOG_PATH = os.path.join(os.path.dirname(__file__), "llm_log.jsonl")

# --- Anthropic client ---------------------------------------------------------
# Reads the ANTHROPIC_API_KEY environment variable automatically.

client = Anthropic()

# --- Build the web page -------------------------------------------------------
# Streamlit turns these function calls into HTML elements in the browser.

st.title("Chinook Charts")
st.caption(
    "Ask a question about the Chinook music database — get back a chart or table."
)

question = st.text_input("Your question")

# --- When the user submits a question ----------------------------------------

if question:
    # 1. Send the question to Claude and get back a Python script
    with st.spinner("Generating Python code…"):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,                           # schema + instructions
            messages=[{"role": "user", "content": question}],  # the user's question
        )
        code = response.content[0].text.strip()  # extract the Python code

        # Strip markdown fences if the LLM includes them anyway
        if code.startswith("```"):
            code = code.split("\n", 1)[1]
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]

        # Save the question and response to a log file
        with open(LOG_PATH, "a") as f:
            json.dump(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "model": response.model,
                    "question": question,
                    "response": code,
                },
                f,
            )
            f.write("\n")

    # 2. Show the generated code so the user can inspect it
    st.subheader("Generated Python")
    st.code(code, language="python")

    # 3. Execute the generated Python against the local database
    try:
        conn = sqlite3.connect(DB_PATH)

        # Build a namespace with the libraries the generated code expects.
        # exec() runs the code string as if it were typed into this script,
        # giving it access to the database connection and all the libraries.
        namespace = {
            "conn": conn,
            "pd": pd,
            "plt": plt,
            "px": px,
            "go": go,
            "st": st,
            "sqlite3": sqlite3,
        }
        exec(code, namespace)  # noqa: S102
        conn.close()

        # If the code created a DataFrame but no chart, display the table
        if "df" in namespace and isinstance(namespace["df"], pd.DataFrame):
            st.subheader("Results")
            st.dataframe(namespace["df"], use_container_width=True)
    except Exception as e:
        st.error(f"Execution error: {e}")
