import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Finance App", layout="wide")

# Load data
def load_data():
    try:
        return pd.read_csv("data.csv")
    except:
        return pd.DataFrame(columns=["type", "amount", "reason", "category", "where", "date", "time"])

data = load_data()

st.title("💰 Personal Finance Tracker")

# Sidebar navigation
page = st.sidebar.selectbox("Menu", ["Home", "Add Transaction", "History"])

# Home page
if page == "Home":
    st.header("Dashboard")
    
    income = data[data["type"] == "Income"]["amount"].sum()
    expenses = data[data["type"] == "Expense"]["amount"].sum()
    balance = income - expenses

    st.metric("Total Income", income)
    st.metric("Total Expenses", expenses)
    st.metric("Balance", balance)

    if not data.empty:
        st.subheader("Recent Transactions")
        st.dataframe(data.tail(5))

# Add transaction
if page == "Add Transaction":
    st.header("Add New Entry")

    with st.form("entry_form"):
        t = st.selectbox("Type", ["Income", "Expense"])
        amount = st.number_input("Amount", min_value=1.0)
        reason = st.text_input("Reason")
        category = st.text_input("Category")
        where = st.text_input("Where From / Where To")
        date = st.date_input("Date")
        time = st.time_input("Time")
        submitted = st.form_submit_button("Save")

        if submitted:
            new = pd.DataFrame([[t, amount, reason, category, where, date, time]],
                               columns=data.columns)
            updated = pd.concat([data, new], ignore_index=True)
            updated.to_csv("data.csv", index=False)
            st.success("Saved!")

# History page
if page == "History":
    st.header("Transaction History")
    if data.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(data)
