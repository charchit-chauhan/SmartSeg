import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from groq import Groq
import mysql.connector
from mysql.connector import Error
import warnings
import os
warnings.filterwarnings('ignore')
from pathlib import Path

# ====================== PAGE CONFIG (must be first Streamlit call) ======================
st.set_page_config(page_title="SmartSeg", layout="wide", page_icon="🛍️")

# Resolved path to local CSV file (relative to this script)
DATA_PATH = Path(__file__).resolve().parent / "data" / "shopping_trends.csv"


def is_valid_groq_key(key):
    return isinstance(key, str) and key.startswith("gsk_") and len(key) >= 30

# MySQL connection details (kept in one place so reconnects use the same config)
DB_CONFIG = {
    "host": "centerbeam.proxy.rlwy.net",
    "port": 32321,
    "user": "root",
    "password": "AgCcmzSFAvWAJhdqZaMTSDhNYylBWhwU",
    "database": "railway",
}

def run_sql(query):
    """Open a short-lived MySQL connection, run one query, and close it.

    A persistent connection stored across reruns kept going stale between
    tab switches (Railway's proxy closes idle sockets, and the gap between
    your clicks is often enough to trigger that). Opening fresh per query
    avoids relying on any socket surviving idle time — the cost is a
    fraction of a second per query, which is unnoticeable.
    """
    conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=10)
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# ====================== GLOBAL STYLE ======================
st.markdown("""
<style>
    /* Overall font + background */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    .block-container {
        padding-top: 1.5rem;
    }

    /* Pill-style horizontal nav (built on st.radio) */
    div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        border-bottom: 1px solid rgba(120,120,120,0.2);
        padding-bottom: 0.75rem;
        margin-bottom: 1.25rem;
    }
    div[role="radiogroup"] label {
        border: 1px solid rgba(120,120,120,0.25);
        border-radius: 999px;
        padding: 0.35rem 0.9rem;
        cursor: pointer;
        transition: all 0.15s ease;
        background: transparent;
    }
    div[role="radiogroup"] label:hover {
        border-color: #6C5CE7;
    }
    div[role="radiogroup"] input:checked + div {
        color: #6C5CE7;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: rgba(120,120,120,0.06);
        border: 1px solid rgba(120,120,120,0.15);
        border-radius: 10px;
        padding: 0.9rem 1rem;
    }

    /* Headings */
    h1, h2, h3 {
        font-weight: 600;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid rgba(120,120,120,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ====================== CACHING FOR SPEED ======================
@st.cache_data
def load_data():
    try:
        return pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at {DATA_PATH}. Ensure 'data/shopping_trends.csv' is present.")

def perform_segmentation(df):
    # Find available numeric columns for clustering
    possible_features = ['Age', 'Purchase Amount (USD)', 'Previous Purchases',
                          'Review Rating', 'Purchase Amount', 'Amount']
    features = [col for col in possible_features if col in df.columns]

    if len(features) < 2:
        features = df.select_dtypes(include=['number']).columns[:3].tolist()

    X = df[features]
    scaler = StandardScaler()
    scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df['Segment'] = kmeans.fit_predict(scaled)

    segment_map = {0: "At Risk", 1: "VIP Customers", 2: "New Customers",
                   3: "Loyal Customers", 4: "Hibernating"}
    df['Segment_Name'] = df['Segment'].map(segment_map)

    return df

# ====================== INITIALIZE SESSION STATE ======================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'groq_key' not in st.session_state:
    st.session_state.groq_key = ""
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'mysql_configured' not in st.session_state:
    st.session_state.mysql_configured = False
if 'mysql_error' not in st.session_state:
    st.session_state.mysql_error = None

# ====================== LOGIN ======================
def login_page():
    st.title("🔐 Login to SmartSeg")
    st.markdown("**Customer Segmentation & Personalized Offer System**")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", placeholder="admin123", type="password")
        if st.button("Login", use_container_width=True):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.success("✅ Login Successful!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

if not st.session_state.logged_in:
    login_page()
else:
    st.title("🛍️ SmartSeg — Customer Segmentation & Personalized Offer System")
    st.caption("Major Internship Project · Shopping Trends Dataset (MySQL)")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ====================== GROQ API KEY ======================
    st.sidebar.header("🤖 Groq AI Settings")
    groq_key = st.sidebar.text_input("Enter Groq API Key", type="password", value=st.session_state.groq_key)

    if groq_key and groq_key != st.session_state.groq_key:
        st.session_state.groq_key = groq_key
        st.sidebar.success("✅ Groq AI Connected!")

    # ====================== RAILWAY MySQL CONNECTION ======================
    st.sidebar.header("🌐 Railway MySQL Database")

    if st.sidebar.button("🔗 Connect to Railway MySQL"):
        try:
            test_conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=10)
            test_conn.close()  # only testing reachability; each query opens its own connection
            st.session_state.mysql_configured = True
            st.session_state.mysql_error = None
            st.session_state.pop('processed_df', None)  # force one-time reprocessing with new data
            st.sidebar.success("✅ Connected to Railway MySQL!")
        except Exception as e:
            st.session_state.mysql_configured = False
            st.session_state.mysql_error = f"{type(e).__name__}: {e}"
            st.sidebar.error(f"❌ Connection Failed: {e}")

    # ====================== LOAD + PROCESS DATA (once per session, not per rerun) ======================
    # Previously this whole block (MySQL query + KMeans clustering) ran again on every
    # single interaction — every click, keystroke, or chat message — since Streamlit
    # reruns the whole script top-to-bottom on any widget change. That meant a network
    # round-trip to the DB and a fresh KMeans fit every time, which is what made the
    # app feel slow. Now it only runs once and the result is reused from session_state.
    def normalize_column_names(raw_df):
        raw_df = raw_df.rename(columns=lambda c: c.strip())
        rename_map = {
            'Purchase_Amount_USD': 'Purchase Amount (USD)',
            'Previous_Purchases': 'Previous Purchases',
            'Review_Rating': 'Review Rating',
            'Customer_ID': 'Customer ID',
            'Preferred_Payment_Method': 'Preferred Payment Method',
            'Subscription_Status': 'Subscription Status',
            'Promo_Code_Used': 'Promo Code Used',
            'Shipping_Type': 'Shipping Type'
        }
        rename_map = {k: v for k, v in rename_map.items() if k in raw_df.columns}
        return raw_df.rename(columns=rename_map)

    def get_tier(points):
        if points >= 500:
            return "Gold"
        elif points >= 350:
            return "Silver"
        elif points >= 200:
            return "Bronze"
        else:
            return "Starter"

    if 'processed_df' not in st.session_state:
        with st.spinner("Loading and processing data..."):
            raw_df = None
            st.session_state.mysql_error = None
            if st.session_state.mysql_configured:
                try:
                    raw_df = run_sql("SELECT * FROM shopping_trends")
                    st.session_state.data_source_label = f"Data loaded from MySQL: {len(raw_df)} records"
                except Exception as e:
                    st.session_state.mysql_error = f"{type(e).__name__}: {e}"
                    st.session_state.mysql_configured = False
                    raw_df = None

            if raw_df is None:
                try:
                    raw_df = load_data()
                    st.session_state.data_source_label = "Using local CSV (connect to MySQL for live data)"
                except FileNotFoundError as e:
                    st.error(str(e))
                    st.stop()

            raw_df = normalize_column_names(raw_df)
            raw_df = perform_segmentation(raw_df)
            raw_df['Loyalty_Points'] = (raw_df['Purchase Amount (USD)'] * 6).astype(int)
            raw_df['Tier'] = raw_df['Loyalty_Points'].apply(get_tier)
            st.session_state.processed_df = raw_df

    df = st.session_state.processed_df

    # Persistent, hard-to-miss status banner — shows on every tab, every rerun,
    # instead of a one-off message that only appeared during the original load.
    if st.session_state.get('mysql_error'):
        st.error(f"⚠️ Currently using local CSV data. MySQL connection failed: {st.session_state.mysql_error}")
    st.sidebar.info(st.session_state.data_source_label)

    st.sidebar.subheader("📊 Tier Distribution")
    st.sidebar.write(df['Tier'].value_counts())

    if st.sidebar.button("🔄 Refresh Data"):
        st.session_state.pop('processed_df', None)
        st.rerun()

    # ====================== OFFERS ======================
    def get_personalized_offer(segment):
        offers = {
            "VIP Customers": [
                "🎉 25% OFF on entire bill + Free Home Delivery",
                "👑 Exclusive Early Access to New Arrivals",
                "💎 Buy 1 Get 1 Free on Premium Brands",
                "🏆 VIP Lounge Access + Priority Billing",
                "🌟 Double Loyalty Points on every purchase",
                "🎁 Free Gift Voucher worth ₹500 on next visit"
            ],
            "Loyal Customers": [
                "❤️ 20% OFF + Extra 100 Loyalty Points",
                "🔄 Buy 2 Get 1 Free on Selected Categories",
                "🎂 Birthday Special: Flat 30% OFF",
                "📦 Free Shipping on orders above ₹1000",
                "⭐ Monthly Loyalty Bonus Offer",
                "🛍️ Special Preview Sale Access"
            ],
            "New Customers": [
                "🌟 Welcome Offer: 30% OFF on First Purchase",
                "🎁 Free Gift with First Order",
                "🚚 Free Delivery on First 3 Orders",
                "💰 ₹300 OFF on minimum purchase of ₹999",
                "📲 Sign-up Bonus: 150 Loyalty Points"
            ],
            "At Risk": [
                "🔥 Win-Back Special: 35% OFF + Buy 1 Get 1",
                "❤️ We Miss You Offer: Flat 40% OFF",
                "⏰ Limited Time: Extra 20% OFF this week",
                "🎟️ Reactivation Coupon: ₹500 OFF on ₹1500",
                "💌 Special Comeback Gift"
            ],
            "Hibernating": [
                "📨 Reactivation Bomb: 40% OFF + Free Delivery",
                "🔄 Restart Offer: Double Points + 25% OFF",
                "🎯 Special Re-engagement Discount",
                "🏷️ Dormant Customer Special: Buy 1 Get 2",
                "💝 Welcome Back Gift Hamper"
            ]
        }
        return offers.get(segment, ["Special Offer Available!"])

    # ====================== GROQ AI FUNCTION ======================
    def ai_analytics_chat(query):
        if not st.session_state.groq_key:
            return "⚠️ Please enter your Groq API Key in the sidebar."

        if not is_valid_groq_key(st.session_state.groq_key):
            return "❌ Groq Error: The entered Groq API key does not look valid. Please enter a key starting with 'gsk_'."

        try:
            client = Groq(api_key=st.session_state.groq_key)

            context = f"""
            You are a data analyst. Answer ONLY using the current dataset.
            Total rows: {len(df)}
            Columns: {list(df.columns)}
            Segment distribution: {df['Segment_Name'].value_counts().to_dict()}
            """

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=700
            )
            return response.choices[0].message.content

        except Exception as e:
            error_text = str(e)
            if "invalid_api_key" in error_text.lower() or "401" in error_text:
                return "❌ Groq Error: Invalid API key. Please update the key in the sidebar or set GROQ_API_KEY."
            return f"❌ Groq Error: {error_text}"

    # ====================== PERSISTENT NAVIGATION ======================
    # This replaces st.tabs(), which resets to the first tab on every rerun
    # (any button click, chat input, SQL query, etc. triggers a rerun).
    # st.radio with a `key` keeps its selected value in session_state across
    # reruns unless the user actively changes it, so navigation stays put.
    nav_options = [
        "📊 Overview", "🔍 Segmentation", "🎁 Offer Engine",
        "📈 Insights", "💡 Strategies", "🤖 AI Chat", "🏆 Loyalty Program"
    ]
    active_tab = st.radio(
        "Navigation", nav_options, horizontal=True,
        label_visibility="collapsed", key="active_nav"
    )

    # ---------------------- OVERVIEW ----------------------
    if active_tab == "📊 Overview":
        st.header("Dataset Overview & Key Business Trends")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Customers", f"{len(df):,}")
        c2.metric("Total Revenue", f"${df['Purchase Amount (USD)'].sum():,.0f}")
        c3.metric("Avg Purchase", f"${df['Purchase Amount (USD)'].mean():.2f}")
        c4.metric("Avg Rating", f"{df['Review Rating'].mean():.2f}")

        st.subheader("Business Insights & Trends")
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(px.histogram(df, x='Purchase Amount (USD)', nbins=30,
                                          title="Purchase Amount Distribution"),
                             use_container_width=True)
            st.plotly_chart(px.box(df, x='Segment_Name', y='Purchase Amount (USD)',
                                    title="Spending by Segment"),
                             use_container_width=True)
            st.plotly_chart(px.histogram(df, x='Season', title="Sales by Season",
                                          color='Season'),
                             use_container_width=True)

        with col2:
            st.plotly_chart(px.scatter(df, x='Age', y='Purchase Amount (USD)',
                                        color='Segment_Name',
                                        title="Age vs Spending by Segment"),
                             use_container_width=True)
            st.plotly_chart(px.histogram(df, x='Category', color='Segment_Name',
                                          title="Category-wise Purchases"),
                             use_container_width=True)
            st.plotly_chart(px.pie(df, names='Segment_Name',
                                    title="Customer Distribution by Segment"),
                             use_container_width=True)

        st.subheader("More Business Trends")
        col3, col4 = st.columns(2)

        with col3:
            revenue_by_cat = df.groupby('Category')['Purchase Amount (USD)'].sum().reset_index()
            st.plotly_chart(px.bar(revenue_by_cat, x='Category', y='Purchase Amount (USD)',
                                    title="Revenue by Category"),
                             use_container_width=True)

        with col4:
            st.plotly_chart(px.histogram(df, x='Gender', title="Gender-wise Purchases",
                                          color='Gender'),
                             use_container_width=True)

        st.subheader("Segment Performance Summary")
        summary = df.groupby('Segment_Name').agg({
            'Customer ID': 'count',
            'Purchase Amount (USD)': ['sum', 'mean']
        }).round(2)
        summary.columns = ['Customer Count', 'Total Revenue', 'Avg Spending']
        st.dataframe(summary, use_container_width=True)

    # ---------------------- SEGMENTATION ----------------------
    elif active_tab == "🔍 Segmentation":
        st.header("Customer Segmentation & Dataset Explorer")

        subtab = st.radio(
            "View", ["📋 Full Dataset", "🔎 Search Dataset", "🗄️ SQL Query Explorer"],
            horizontal=True, label_visibility="collapsed", key="segmentation_subnav"
        )

        if subtab == "📋 Full Dataset":
            st.subheader("Complete Dataset")
            st.caption(f"Total Records: {len(df):,} | Showing first 1000 rows")
            st.dataframe(df.head(1000), use_container_width=True)

        elif subtab == "🔎 Search Dataset":
            st.subheader("Search in Dataset")
            search_term = st.text_input("Search by Customer ID, Name, Category, Season, Gender, etc.", "")

            if search_term:
                filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
                st.write(f"**Results for:** `{search_term}`  |  Found: {len(filtered_df)} records")
                st.dataframe(filtered_df.head(500), use_container_width=True)
            else:
                st.info("Enter a search term above to filter the dataset.")

        else:
            st.subheader("SQL Query Explorer")
            st.caption("Run custom SQL queries (works best when connected to MySQL)")

            default_query = """SELECT Category, COUNT(*) as Total_Customers,
                              SUM(Purchase_Amount_USD) as Total_Revenue,
                              ROUND(AVG(Purchase_Amount_USD), 2) as Avg_Spending
                              FROM shopping_trends
                              GROUP BY Category
                              ORDER BY Total_Revenue DESC
                              LIMIT 10"""

            sql_query = st.text_area("Write your SQL Query here:", default_query, height=130)

            if st.button("🚀 Run SQL Query"):
                if st.session_state.mysql_configured:
                    try:
                        result = run_sql(sql_query)
                        st.success("✅ Query Executed Successfully!")
                        st.dataframe(result, use_container_width=True)
                    except Exception as e:
                        st.error(f"Query Error: {e}")
                else:
                    st.warning("Please connect to MySQL first!")

    # ---------------------- OFFER ENGINE ----------------------
    elif active_tab == "🎁 Offer Engine":
        st.header("Personalized Offer Engine")

        cust_id_input = st.text_input("Enter Customer ID", placeholder="1")

        if cust_id_input:
            try:
                cust_id = int(cust_id_input.strip())
                customer_data = df[df['Customer ID'] == cust_id]

                if not customer_data.empty:
                    cust = customer_data.iloc[0]
                    st.success(f"✅ Customer Found! | **ID:** {cust['Customer ID']}")
                    st.markdown(f"**Segment:** `{cust['Segment_Name']}`")
                    st.markdown(f"**Tier:** `{cust['Tier']}`")

                    st.markdown("### Recommended Personalized Offers")
                    offers_list = get_personalized_offer(cust['Segment_Name'])
                    for i, offer in enumerate(offers_list, 1):
                        st.markdown(f"**{i}.** {offer}")

                    st.write("**Customer Details:**")
                    st.write(f"Age: {cust['Age']} | Gender: {cust['Gender']} | Category: {cust['Category']}")
                    st.write(f"Purchase Amount: ${cust['Purchase Amount (USD)']}")
                else:
                    st.error(f"❌ Customer ID **{cust_id}** not found in dataset.")
                    st.info("Tip: Try Customer IDs from 1 to " + str(len(df)))

            except ValueError:
                st.error("Please enter a valid numeric Customer ID.")
            except Exception as e:
                st.error(f"Error: {e}")

    # ---------------------- INSIGHTS ----------------------
    elif active_tab == "📈 Insights":
        st.header("Business Insights (Powered by MySQL)")

        st.subheader("Interactive Filters")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            selected_segments = st.multiselect("Filter by Segment",
                                                options=df['Segment_Name'].unique(),
                                                default=df['Segment_Name'].unique(),
                                                key="tab4_segment")
        with col_f2:
            selected_categories = st.multiselect("Filter by Category",
                                                  options=df['Category'].unique(),
                                                  default=df['Category'].unique(),
                                                  key="tab4_category")
        with col_f3:
            selected_seasons = st.multiselect("Filter by Season",
                                               options=df['Season'].unique(),
                                               default=df['Season'].unique(),
                                               key="tab4_season")

        filtered_df = df[
            (df['Segment_Name'].isin(selected_segments)) &
            (df['Category'].isin(selected_categories)) &
            (df['Season'].isin(selected_seasons))
        ]

        st.caption(f"Showing insights for **{len(filtered_df)}** filtered records")

        if st.session_state.mysql_configured:
            st.subheader("1. Top 10 Best Selling Categories")
            query1 = f"""
            SELECT Category, COUNT(*) as Total_Sold,
                   SUM(Purchase_Amount_USD) as Total_Revenue,
                   ROUND(AVG(Purchase_Amount_USD), 2) as Avg_Purchase
            FROM shopping_trends
            WHERE Category IN ({','.join([f"'{c}'" for c in selected_categories])})
              AND Season IN ({','.join([f"'{s}'" for s in selected_seasons])})
            GROUP BY Category
            ORDER BY Total_Revenue DESC
            LIMIT 10
            """
            try:
                result1 = run_sql(query1)
                st.dataframe(result1, use_container_width=True)

                st.subheader("2. Sales by Season")
                query2 = f"""
                SELECT Season, COUNT(*) as Total_Transactions,
                       SUM(Purchase_Amount_USD) as Revenue,
                       ROUND(AVG(Purchase_Amount_USD), 2) as Avg_Order_Value
                FROM shopping_trends
                WHERE Category IN ({','.join([f"'{c}'" for c in selected_categories])})
                  AND Season IN ({','.join([f"'{s}'" for s in selected_seasons])})
                GROUP BY Season
                ORDER BY Revenue DESC
                """
                result2 = run_sql(query2)
                st.dataframe(result2, use_container_width=True)
            except Exception as e:
                st.error(f"MySQL query failed: {e}")

            st.subheader("3. Revenue by Customer Segment")
            segment_summary = filtered_df.groupby('Segment_Name').agg({
                'Customer ID': 'count',
                'Purchase Amount (USD)': ['sum', 'mean']
            }).round(2)
            segment_summary.columns = ['Customer Count', 'Total Revenue', 'Avg Spending']
            st.dataframe(segment_summary, use_container_width=True)
        else:
            st.warning("Connect to MySQL to see detailed insights")

        st.caption("Filters apply across all insights. Segment filter runs in Python since Segment_Name is computed, not stored.")

    # ---------------------- STRATEGIES ----------------------
    elif active_tab == "💡 Strategies":
        st.header("Sales & Retention Strategies")
        st.markdown("""
        **Inspired by leading retail & delivery platforms (Zomato, Swiggy, Jio, Tata, DMart, Vishal Mega Mart & big malls)**

        ### 1. Win-Back & Reactivation
        - "We Miss You" 30–40% OFF coupons for lapsed customers
        - Bonus loyalty points on return purchase
        - Buy 1 Get 1 + free delivery bundles for dormant customers

        ### 2. Loyalty & Rewards
        - Tiered program (Bronze / Silver / Gold) with increasing benefits
        - Refer & earn — both referrer and new customer get points
        - Birthday and anniversary rewards
        - Points redeemable for vouchers or products

        ### 3. Personalization & Targeted Offers
        - VIP customers get early access and exclusive deals
        - Category-based recommendations from past purchases
        - Location-based offers for nearby high-selling categories

        ### 4. Seasonal & Festive Campaigns
        - Major seasonal sales during Diwali, Holi, Eid, Christmas
        - Flash sales and limited-time offers to create urgency
        - Bundle pricing on high-selling items

        ### 5. Engagement & Retention
        - Loyalty points for product reviews
        - Exclusive community for top customers
        - Personalized "your favorite brand is on sale" alerts
        - Light gamification — spin the wheel, scratch cards, challenges

        ### 6. Long-Term Growth
        - Prioritize customer lifetime value over one-off sales
        - Cross-sell and up-sell complementary products at checkout
        - Brand partnership offers
        """)

    # ---------------------- AI CHAT ----------------------
    elif active_tab == "🤖 AI Chat":
        st.header("Groq AI Chat Assistant")
        st.caption("Ask anything about your dataset (Clothing, Footwear, Age groups, Revenue, etc.)")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask any question about the data..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing dataset..."):
                    response = ai_analytics_chat(prompt)
                    st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response})

    # ---------------------- LOYALTY PROGRAM ----------------------
    elif active_tab == "🏆 Loyalty Program":
        st.header("Loyalty & Rewards Program")

        st.subheader("Tier Distribution")
        tier_dist = df['Tier'].value_counts()
        st.bar_chart(tier_dist)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🥇 Gold", len(df[df['Tier'] == 'Gold']))
        col2.metric("🥈 Silver", len(df[df['Tier'] == 'Silver']))
        col3.metric("🥉 Bronze", len(df[df['Tier'] == 'Bronze']))
        col4.metric("Starter", len(df[df['Tier'] == 'Starter']))

        st.divider()

        cust_id = st.text_input("Enter Customer ID", placeholder="1", key="loyalty")
        if cust_id:
            try:
                cust_id = int(cust_id.strip())
                cust = df[df['Customer ID'] == cust_id].iloc[0]
                st.success(f"**Tier:** {cust['Tier']}")
                st.progress(min(cust['Loyalty_Points'] / 400, 1.0))
                st.write(f"**Loyalty Points:** {cust['Loyalty_Points']}")
                st.write(f"**Total Spent:** ${cust['Purchase Amount (USD)']}")
            except Exception:
                st.error("Customer not found!")

    st.sidebar.info("SmartSeg — Major Internship Project")