"""Chinook natural-language query app — ask questions in plain English."""

import json
import os
import sqlite3
from datetime import datetime, timezone

import streamlit as st
from openai import OpenAI

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

SYSTEM_PROMPT = (
    "You are a SQL assistant. Given the schema below and a user question, "
    "return ONLY a single SQLite SELECT statement. No explanation, no markdown "
    "fences, no comments — just the SQL.\n\n" + SCHEMA
)

DB_PATH = os.path.join(os.path.dirname(__file__), "chinook.db")
LOG_PATH = os.path.join(os.path.dirname(__file__), "llm_log.jsonl")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)

st.title("Chinook Query")
st.caption("Ask a plain-English question about the Chinook music database.")

question = st.text_input("Your question")

if question:
    with st.spinner("Generating SQL…"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=messages,
        )
        sql = response.choices[0].message.content.strip()

        with open(LOG_PATH, "a") as f:
            json.dump(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "model": response.model,
                    "messages": messages,
                    "response": sql,
                },
                f,
            )
            f.write("\n")

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    try:
        conn = sqlite3.connect(DB_PATH)
        import pandas as pd

        df = pd.read_sql_query(sql, conn)
        conn.close()
        st.subheader("Results")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Query error: {e}")
