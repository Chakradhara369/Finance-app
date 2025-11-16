import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from streamlit_calendar import calendar
import numpy as np

# Page configuration
st.set_page_config(page_title="Personal Finance App", page_icon="💰", layout="wide")

# Custom CSS for better colors and styling
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .stMetric > label {
        color: #333;
        font-weight: bold;
    }
    .stMetric > div > div {
        color: #1f77b4;
        font-size: 2rem;
    }
    .positive {
        color: #2ca02c;
    }
    .negative {
        color: #d62728;
    }
    .neutral {
        color: #ff7f0e;
    }
</style>
""", unsafe_allow_html=True)

# Database initialization
@st.cache_resource
def init_db():
    conn = sqlite3.connect('finance.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         type TEXT,
         amount REAL,
         reason TEXT,
         category TEXT,
         where_from TEXT,
         date TEXT,
         time TEXT,
         timestamp REAL)
    ''')
    conn.commit()
    return conn

# Categories
CATEGORIES = ["Food", "Travel", "Bills", "Entertainment", "Shopping", "Savings", "Health", "Other"]

# Initialize database
conn = init_db()

# Function to add transaction
def add_transaction(type_, amount, reason, category, where_from, date_, time_):
    timestamp = datetime.now().timestamp()
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (type, amount, reason, category, where_from, date, time, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (type_, amount, reason, category, where_from, date_.isoformat(), time_.isoformat(), timestamp))
    conn.commit()

# Function to get all transactions as DataFrame
def get_transactions():
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY timestamp DESC", conn)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    return df

# Sidebar navigation
st.sidebar.title("💰 Finance App")
page = st.sidebar.selectbox("Menu", [
    "Home", "Add Transaction", "Daily Analysis", "Weekly Analysis", 
    "Monthly Analysis", "Income Summary", "Expense Summary", 
    "History", "Calendar View", "Category Breakdown"
])

# Home Page
if page == "Home":
    st.title("🏠 Dashboard")
    df = get_transactions()
    
    if df.empty:
        st.info("No transactions yet. Add some to see insights!")
    else:
        today = date.today()
        this_month = df[df['date'].dt.month == today.month]
        
        total_income = this_month[this_month['type'] == 'Income']['amount'].sum()
        total_expenses = this_month[this_month['type'] == 'Expense']['amount'].sum()
        balance = total_income - total_expenses
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Income", f"₹{total_income:,.0f}", delta=None, label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Expenses", f"₹{total_expenses:,.0f}", delta=None, label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            color = "positive" if balance >= 0 else "negative"
            st.markdown(f'<div class="metric-container">', unsafe_allow_html=True)
            st.markdown(f'<div class="stMetric {color}">', unsafe_allow_html=True)
            st.metric("Balance", f"₹{balance:,.0f}", delta=None, label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Last 7 days cashflow
        last_7_days = df[df['date'] >= today - timedelta(days=7)]
        daily_cashflow = last_7_days.groupby(last_7_days['date'].dt.date)['amount'].apply(
            lambda x: x[this_month['type'] == 'Income'].sum() - x[this_month['type'] == 'Expense'].sum()
        ).reindex(pd.date_range(today - timedelta(days=6), today).date, fill_value=0)
        
        fig_line = px.line(x=daily_cashflow.index, y=daily_cashflow.values, title="Last 7 Days Cashflow")
        fig_line.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Pie chart for categories (expenses only)
        expenses = this_month[this_month['type'] == 'Expense']
        if not expenses.empty:
            cat_breakdown = expenses.groupby('category')['amount'].sum().reset_index()
            fig_pie = px.pie(cat_breakdown, values='amount', names='category', title="Expense Categories")
            fig_pie.update_traces(marker=dict(colors=px.colors.qualitative.Set3))
            st.plotly_chart(fig_pie, use_container_width=True)
    
    if st.sidebar.button("➕ Add Transaction"):
        st.switch_page("Add Transaction")  # Note: In multi-page, but since single file, we'll handle below

# Add Transaction Page
elif page == "Add Transaction":
    st.title("➕ Add New Transaction")
    
    with st.form("entry_form"):
        type_ = st.selectbox("Type", ["Income", "Expense"])
        amount = st.number_input("Amount", min_value=0.01, format="%.2f")
        reason = st.text_input("Reason / Description")
        category = st.selectbox("Category", CATEGORIES)
        where_from = st.text_input("Received From / Sent To")
        col1, col2 = st.columns(2)
        with col1:
            date_ = st.date_input("Date", value=date.today())
        with col2:
            time_ = st.time_input("Time", value=datetime.now().time())
        
        submitted = st.form_submit_button("💾 Save")
        
        if submitted:
            add_transaction(type_, amount, reason, category, where_from, date_, time_)
            st.success("Transaction added successfully!")
            st.rerun()

# Daily Analysis
elif page == "Daily Analysis":
    st.title("📅 Daily Analysis")
    df = get_transactions()
    if df.empty:
        st.info("No data available.")
    else:
        selected_date = st.date_input("Select Date", value=date.today())
        day_data = df[df['date'].dt.date == selected_date]
        
        if day_data.empty:
            st.info("No transactions for this day.")
        else:
            income = day_data[day_data['type'] == 'Income']['amount'].sum()
            expenses = day_data[day_data['type'] == 'Expense']['amount'].sum()
            cashflow = income - expenses
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Income", f"₹{income:,.0f}")
            with col2:
                st.metric("Expenses", f"₹{expenses:,.0f}")
            with col3:
                color = "positive" if cashflow >= 0 else "negative"
                st.metric("Cashflow", f"₹{cashflow:,.0f}", delta=None)
            
            # Pie chart
            exp_day = day_data[day_data['type'] == 'Expense']
            if not exp_day.empty:
                cat_sum = exp_day.groupby('category')['amount'].sum().reset_index()
                fig = px.pie(cat_sum, values='amount', names='category', title="Category Breakdown")
                fig.update_traces(marker=dict(colors=px.colors.qualitative.Set3))
                st.plotly_chart(fig, use_container_width=True)
            
            # Table
            st.subheader("Transactions")
            st.dataframe(day_data[['type', 'amount', 'reason', 'category', 'where_from', 'time']].style.format({'amount': '₹{:.2f}'}))
    
    [web:1][web:4]

# Weekly Analysis
elif page == "Weekly Analysis":
    st.title("📆 Weekly Analysis")
    df = get_transactions()
    if df.empty:
        st.info("No data available.")
    else:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        week_data = df[(df['date'].dt.date >= start_of_week) & (df['date'].dt.date <= end_of_week)]
        if week_data.empty:
            st.info("No transactions this week.")
        else:
            daily_totals = week_data.groupby(week_data['date'].dt.date).agg({
                'amount': lambda x: x[week_data['type'] == 'Income'].sum() - x[week_data['type'] == 'Expense'].sum()
            }).reset_index()
            
            fig_bar = px.bar(daily_totals, x='date', y='amount', title="Daily Totals (Income - Expenses)")
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            total_week_income = week_data[week_data['type'] == 'Income']['amount'].sum()
            total_week_expenses = week_data[week_data['type'] == 'Expense']['amount'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Weekly Income", f"₹{total_week_income:,.0f}")
            with col2:
                st.metric("Weekly Expenses", f"₹{total_week_expenses:,.0f}")
            
            # Category breakdown (expenses)
            exp_week = week_data[week_data['type'] == 'Expense']
            if not exp_week.empty:
                cat_week = exp_week.groupby('category')['amount'].sum().reset_index()
                fig_pie_week = px.pie(cat_week, values='amount', names='category', title="Weekly Expense Categories")
                fig_pie_week.update_traces(marker=dict(colors=px.colors.qualitative.Set3))
                st.plotly_chart(fig_pie_week, use_container_width=True)
    
    [web:1]

# Monthly Analysis
elif page == "Monthly Analysis":
    st.title("📈 Monthly Analysis")
    df = get_transactions()
    if df.empty:
        st.info("No data available.")
    else:
        today = date.today()
        month_start = today.replace(day=1)
        month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        month_data = df[(df['date'].dt.date >= month_start) & (df['date'].dt.date <= month_end)]
        if month_data.empty:
            st.info("No transactions this month.")
        else:
            # Line chart: daily totals
            daily_month = month_data.groupby(month_data['date'].dt.date).agg({
                'amount': lambda x: x[month_data['type'] == 'Income'].sum() - x[month_data['type'] == 'Expense'].sum()
            }).reset_index()
            fig_line_month = px.line(daily_month, x='date', y='amount', title="Daily Cashflow")
            fig_line_month.update_layout(height=400)
            st.plotly_chart(fig_line_month, use_container_width=True)
            
            total_month_income = month_data[month_data['type'] == 'Income']['amount'].sum()
            total_month_expenses = month_data[month_data['type'] == 'Expense']['amount'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Monthly Income", f"₹{total_month_income:,.0f}")
            with col2:
                st.metric("Monthly Expenses", f"₹{total_month_expenses:,.0f}")
            
            # Highest spend day
            spend_days = month_data[month_data['type'] == 'Expense'].groupby(month_data['date'].dt.date)['amount'].sum()
            if not spend_days.empty:
                highest_day = spend_days.idxmax()
                st.metric("Highest Spend Day", highest_day.strftime("%Y-%m-%d"), f"₹{spend_days.max():.0f}")
            
            # Most expensive category
            cat_month = month_data[month_data['type'] == 'Expense'].groupby('category')['amount'].sum()
            if not cat_month.empty:
                most_exp_cat = cat_month.idxmax()
                st.metric("Most Expensive Category", most_exp_cat, f"₹{cat_month.max():.0f}")
    
    [web:1]

# Income Summary
elif page == "Income Summary":
    st.title("💹 Income Summary")
    df = get_transactions()
    income_df = df[df['type'] == 'Income']
    if income_df.empty:
        st.info("No income data.")
    else:
        st.dataframe(income_df[['date', 'amount', 'reason', 'category', 'where_from']].style.format({'amount': '₹{:.2f}'}))
        total_income_all = income_df['amount'].sum()
        st.metric("Total Income (All Time)", f"₹{total_income_all:,.0f}")
    
    [web:1]

# Expense Summary
elif page == "Expense Summary":
    st.title("📉 Expense Summary")
    df = get_transactions()
    expense_df = df[df['type'] == 'Expense']
    if expense_df.empty:
        st.info("No expense data.")
    else:
        st.dataframe(expense_df[['date', 'amount', 'reason', 'category', 'where_from']].style.format({'amount': '₹{:.2f}'}))
        total_expenses_all = expense_df['amount'].sum()
        st.metric("Total Expenses (All Time)", f"₹{total_expenses_all:,.0f}")
    
    [web:1]

# History Page
elif page == "History":
    st.title("📜 Transaction History")
    df = get_transactions()
    if df.empty:
        st.info("No transactions yet.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            search = st.text_input("Search Reason")
        with col2:
            cat_filter = st.selectbox("Category", ["All"] + CATEGORIES)
        with col3:
            date_range = st.date_input("Date Range", value=(df['date'].min().date(), df['date'].max().date()))
        
        filtered_df = df.copy()
        if search:
            filtered_df = filtered_df[filtered_df['reason'].str.contains(search, case=False)]
        if cat_filter != "All":
            filtered_df = filtered_df[filtered_df['category'] == cat_filter]
        filtered_df = filtered_df[(filtered_df['date'].dt.date >= date_range[0]) & (filtered_df['date'].dt.date <= date_range[1])]
        
        # Sort
        sort_by = st.selectbox("Sort By", ["Date (Newest)", "Amount (High to Low)", "Amount (Low to High)"])
        if sort_by == "Amount (High to Low)":
            filtered_df = filtered_df.sort_values('amount', ascending=False)
        elif sort_by == "Amount (Low to High)":
            filtered_df = filtered_df.sort_values('amount', ascending=True)
        else:
            filtered_df = filtered_df.sort_values('date', ascending=False)
        
        st.dataframe(filtered_df[['date', 'type', 'amount', 'reason', 'category', 'where_from']].style.format({'amount': '₹{:.2f}'}))
        
        # Download CSV
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "transactions.csv", "text/csv")
    
    [web:1]

# Category Breakdown (Pie Charts)
elif page == "Category Breakdown":
    st.title("🍰 Category Breakdown")
    df = get_transactions()
    expense_df = df[df['type'] == 'Expense']
    if expense_df.empty:
        st.info("No expense data for breakdown.")
    else:
        cat_sum = expense_df.groupby('category')['amount'].sum().reset_index()
        fig = px.pie(cat_sum, values='amount', names='category', title="All Time Expense Categories")
        fig.update_traces(marker=dict(colors=px.colors.qualitative.Set3), textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        # Bar chart for comparison
        fig_bar_cat = px.bar(cat_sum, x='category', y='amount', title="Expense by Category", color='amount')
        fig_bar_cat.update_layout(height=500)
        st.plotly_chart(fig_bar_cat, use_container_width=True)
    
    [web:1]

# Calendar View
elif page == "Calendar View":
    st.title("🗓️ Calendar View")
    df = get_transactions()
    if df.empty:
        st.info("No data for calendar.")
    else:
        # Prepare events for calendar
        events = []
        for _, row in df.iterrows():
            net_amount = row['amount'] if row['type'] == 'Income' else -row['amount']
            color = 'green' if net_amount > 0 else 'red' if net_amount < 0 else 'yellow'
            event = {
                'title': f"{row['type']}: ₹{abs(row['amount']):.0f} - {row['reason'][:20]}",
                'start': row['date'].isoformat(),
                'backgroundColor': color,
                'borderColor': color
            }
            events.append(event)
        
        calendar_options = {
            "initialView": "dayGridMonth",
            "editable": False,
            "selectable": True,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek"
            },
            "events": events
        }
        
        cal_data = calendar(events=events, options=calendar_options, key="finance_calendar")
        if cal_data:
            st.write("Calendar Interaction:", cal_data)
    
    [web:1][web:2][web:4][web:5]

# Close connection on app end (handled by Streamlit)
