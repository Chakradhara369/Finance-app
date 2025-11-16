import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import calendar
try:
    from streamlit_calendar import calendar
    CALENDAR_AVAILABLE = True
except ImportError:
    st.warning("Install streamlit-calendar for full calendar view: pip install streamlit-calendar")
    CALENDAR_AVAILABLE = False
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

# Initialize session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = "Home"

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

# Cashflow calculation helper
def calculate_cashflow(group):
    income = group[group['type'] == 'Income']['amount'].sum() if not group.empty else 0
    expense = group[group['type'] == 'Expense']['amount'].sum() if not group.empty else 0
    return income - expense

# Sidebar navigation
st.sidebar.title("💰 Finance App")
pages = ["Home", "Add Transaction", "Daily Analysis", "Weekly Analysis", 
         "Monthly Analysis", "Income Summary", "Expense Summary", 
         "History", "Calendar View", "Category Breakdown"]
selected = st.sidebar.selectbox("Menu", pages, index=pages.index(st.session_state.page))
st.session_state.page = selected

# Home Page shortcut in sidebar
if st.session_state.page == "Home":
    if st.sidebar.button("➕ Add Transaction"):
        st.session_state.page = "Add Transaction"
        st.rerun()

# Home Page
if st.session_state.page == "Home":
    st.title("🏠 Dashboard")
    df = get_transactions()
    
    if df.empty:
        st.info("No transactions yet. Add some to see insights!")
    else:
        today = date.today()
        this_month_start = today.replace(day=1)
        this_month_end = date(today.year, today.month % 12 + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year + 1, 1, 1) - timedelta(days=1)
        this_month = df[(df['date'].dt.date >= this_month_start) & (df['date'].dt.date <= this_month_end)]
        
        total_income = this_month[this_month['type'] == 'Income']['amount'].sum()
        total_expenses = this_month[this_month['type'] == 'Expense']['amount'].sum()
        balance = total_income - total_expenses
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Income", f"₹{total_income:,.0f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Expenses", f"₹{total_expenses:,.0f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            delta_color = "positive" if balance >= 0 else "negative"
            st.markdown(f'<style>.stMetric.delta-text-only {{"color": "#2ca02c" if balance >= 0 else "#d62728"}}</style>', unsafe_allow_html=True)
            st.metric("Balance", f"₹{balance:,.0f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Last 7 days cashflow
        last_7_days = df[df['date'].dt.date >= today - timedelta(days=7)]
        daily_cashflow = last_7_days.groupby(last_7_days['date'].dt.date).apply(calculate_cashflow).reindex(
            pd.date_range(today - timedelta(days=6), today).date, fill_value=0
        )
        
        fig_line = px.line(x=list(daily_cashflow.index), y=daily_cashflow.values, title="Last 7 Days Cashflow")
        fig_line.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Pie chart for categories (expenses only)
        expenses = this_month[this_month['type'] == 'Expense']
        if not expenses.empty:
            cat_breakdown = expenses.groupby('category')['amount'].sum().reset_index()
            fig_pie = px.pie(cat_breakdown, values='amount', names='category', title="Expense Categories")
            fig_pie.update_traces(marker=dict(colors=px.colors.qualitative.Set3))
            st.plotly_chart(fig_pie, use_container_width=True)

# Add Transaction Page
elif st.session_state.page == "Add Transaction":
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
elif st.session_state.page == "Daily Analysis":
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
                st.metric("Cashflow", f"₹{cashflow:,.0f}")
            
            # Pie chart
            exp_day = day_data[day_data['type'] == 'Expense']
            if not exp_day.empty:
                cat_sum = exp_day.groupby('category')['amount'].sum().reset_index()
                fig = px.pie(cat_sum, values='amount', names='category', title="Category Breakdown")
                fig.update_traces(marker=dict(colors=px.colors.qualitative.Set3))
                st.plotly_chart(fig, use_container_width=True)
            
            # Table with currency
            display_df = day_data[['type', 'amount', 'reason', 'category', 'where_from', 'time']].copy()
            display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:.2f}")
            st.subheader("Transactions")
            st.dataframe(display_df)

# Weekly Analysis
elif st.session_state.page == "Weekly Analysis":
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
            daily_totals = week_data.groupby(week_data['date'].dt.date).apply(calculate_cashflow).reset_index(name='amount')
            
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

# Monthly Analysis
elif st.session_state.page == "Monthly Analysis":
    st.title("📈 Monthly Analysis")
    df = get_transactions()
    if df.empty:
        st.info("No data available.")
    else:
        today = date.today()
        month_start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        month_end = today.replace(day=last_day)
        
        month_data = df[(df['date'].dt.date >= month_start) & (df['date'].dt.date <= month_end)]
        if month_data.empty:
            st.info("No transactions this month.")
        else:
            # Line chart: daily totals
            daily_month = month_data.groupby(month_data['date'].dt.date).apply(calculate_cashflow).reset_index(name='amount')
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
                highest_amount = spend_days.max()
                st.metric("Highest Spend Day", highest_day.strftime("%Y-%m-%d"), f"₹{highest_amount:.0f}")
            
            # Most expensive category
            cat_month = month_data[month_data['type'] == 'Expense'].groupby('category')['amount'].sum()
            if not cat_month.empty:
                most_exp_cat = cat_month.idxmax()
                cat_amount = cat_month.max()
                st.metric("Most Expensive Category", most_exp_cat, f"₹{cat_amount:.0f}")

# Income Summary
elif st.session_state.page == "Income Summary":
    st.title("💹 Income Summary")
    df = get_transactions()
    income_df = df[df['type'] == 'Income']
    if income_df.empty:
        st.info("No income data.")
    else:
        display_df = income_df[['date', 'amount', 'reason', 'category', 'where_from']].copy()
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:.2f}")
        st.dataframe(display_df)
        total_income_all = income_df['amount'].sum()
        st.metric("Total Income (All Time)", f"₹{total_income_all:,.0f}")

# Expense Summary
elif st.session_state.page == "Expense Summary":
    st.title("📉 Expense Summary")
    df = get_transactions()
    expense_df = df[df['type'] == 'Expense']
    if expense_df.empty:
        st.info("No expense data.")
    else:
        display_df = expense_df[['date', 'amount', 'reason', 'category', 'where_from']].copy()
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:.2f}")
        st.dataframe(display_df)
        total_expenses_all = expense_df['amount'].sum()
        st.metric("Total Expenses (All Time)", f"₹{total_expenses_all:,.0f}")

# History Page
elif st.session_state.page == "History":
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
            date_range = st.date_input("Date Range", value=(df['date'].min().date() if not df.empty else date.today(), df['date'].max().date() if not df.empty else date.today()))
        
        filtered_df = df.copy()
        if search:
            filtered_df = filtered_df[filtered_df['reason'].str.contains(search, case=False, na=False)]
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
        
        display_df = filtered_df[['date', 'type', 'amount', 'reason', 'category', 'where_from']].copy()
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:.2f}")
        st.dataframe(display_df)
        
        # Download CSV
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "transactions.csv", "text/csv")

# Category Breakdown (Pie Charts)
elif st.session_state.page == "Category Breakdown":
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

# Calendar View
elif st.session_state.page == "Calendar View":
    st.title("🗓️ Calendar View")
    df = get_transactions()
    if df.empty:
        st.info("No data for calendar.")
    elif not CALENDAR_AVAILABLE:
        st.info("Calendar component not available. Install via pip.")
    else:
        # Prepare events for calendar
        events = []
        for _, row in df.iterrows():
            net_amount = row['amount'] if row['type'] == 'Income' else -row['amount']
            color = 'green' if net_amount > 0 else 'red' if net_amount < -50 else 'yellow'  # Threshold for heavy expense
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
            "events": events,
            "dateClick": "function(info) { return info.dateStr; }"
        }
        
        selected_date = calendar(events=events, options=calendar_options, key="finance_calendar")
        if selected_date:
            day_data = df[df['date'].dt.date == pd.to_datetime(selected_date).date()]
            if not day_data.empty:
                st.subheader(f"Details for {selected_date}:")
                display_df = day_data[['type', 'amount', 'reason', 'category', 'where_from', 'time']].copy()
                display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:.2f}")
                st.dataframe(display_df)
