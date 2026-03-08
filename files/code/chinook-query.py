"""Chinook natural-language query app — ask questions in plain English."""

# --- Import libraries --------------------------------------------------------
# json: read/write structured data    os: access environment variables & paths
# sqlite3: connect to the SQLite database file
# datetime: timestamp each query for the log
# streamlit (st): builds the web interface from this single script
# anthropic: official Python client for the Anthropic API (Claude)

import json
import os
import sqlite3
from datetime import datetime, timezone

import streamlit as st
from anthropic import Anthropic

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
# Instructions sent to Claude with every request.  They tell the model to
# return raw SQL only — no explanations, no markdown formatting.

SYSTEM_PROMPT = (
    "You are a SQL assistant. Given the schema below and a user question, "
    "return ONLY a single SQLite SELECT statement. No explanation, no markdown "
    "fences, no comments — just the SQL.\n\n" + SCHEMA
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

st.title("Chinook Query")
st.caption("Ask a plain-English question about the Chinook music database.")

question = st.text_input("Your question")

# --- When the user submits a question ----------------------------------------

if question:
    # 1. Send the question to Claude and get back a SQL query
    with st.spinner("Generating SQL…"):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            system=SYSTEM_PROMPT,                           # schema + instructions
            messages=[{"role": "user", "content": question}],  # the user's question
        )
        sql = response.content[0].text.strip()  # extract the SQL string

        # Save the question and response to a log file
        with open(LOG_PATH, "a") as f:
            json.dump(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "model": response.model,
                    "question": question,
                    "response": sql,
                },
                f,
            )
            f.write("\n")

    # 2. Show the generated SQL so the user can verify it
    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    # 3. Run the SQL against the local database and display results
    try:
        conn = sqlite3.connect(DB_PATH)
        import pandas as pd

        df = pd.read_sql_query(sql, conn)  # execute the query, get a table
        conn.close()
        st.subheader("Results")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Query error: {e}")
