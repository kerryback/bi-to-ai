"""Chinook chart app — ask questions and get charts, not just tables."""

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
from openai import OpenAI

matplotlib.use("Agg")

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

DB_PATH = os.path.join(os.path.dirname(__file__), "chinook.db")
LOG_PATH = os.path.join(os.path.dirname(__file__), "llm_log.jsonl")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)

st.title("Chinook Charts")
st.caption(
    "Ask a question about the Chinook music database — get back a chart or table."
)

question = st.text_input("Your question")

if question:
    with st.spinner("Generating Python code…"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=messages,
        )
        code = response.choices[0].message.content.strip()

        # Strip markdown fences if the LLM includes them anyway
        if code.startswith("```"):
            code = code.split("\n", 1)[1]
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]

        with open(LOG_PATH, "a") as f:
            json.dump(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "model": response.model,
                    "messages": messages,
                    "response": code,
                },
                f,
            )
            f.write("\n")

    st.subheader("Generated Python")
    st.code(code, language="python")

    try:
        conn = sqlite3.connect(DB_PATH)
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

        # Display the DataFrame if one was created and no chart was shown
        if "df" in namespace and isinstance(namespace["df"], pd.DataFrame):
            st.subheader("Results")
            st.dataframe(namespace["df"], use_container_width=True)
    except Exception as e:
        st.error(f"Execution error: {e}")
