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

# ====================== INITIALIZE SESSION STATE ======================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'groq_key' not in st.session_state:
    st.session_state.groq_key = ""
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conn' not in st.session_state:
    st.session_state.conn = None

# ====================== LOGIN ======================
def login_page():
    st.title("🔐 Login to SmartSeg")
    st.markdown("**Customer Segmentation & Personalized Offer System**")
    col1, col2, col3 = st.columns([1,2,1])
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
    st.set_page_config(page_title="SmartSeg", layout="wide")
    st.title("🛍️ SmartSeg - Customer Segmentation & Personalized Offer System")
    st.markdown("**Major Internship Project** | Shopping Trends Dataset (MySQL)")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ====================== GROQ API KEY ======================
    st.sidebar.header("🤖 Groq AI Settings")
    groq_key = st.sidebar.text_input("Enter Groq API Key", type="password", value=st.session_state.groq_key)
    
    if groq_key and groq_key != st.session_state.groq_key:
        st.session_state.groq_key = groq_key
        st.sidebar.success("✅ Groq AI Connected!")

    # ====================== MySQL CONNECTION (Persistent) ======================
    st.sidebar.header("🗄️ MySQL Database")
    if st.sidebar.button("Connect to MySQL") or st.session_state.conn is not None:
        if st.session_state.conn is None:
            try:
                conn = mysql.connector.connect(
                    host=os.getenv("MYSQL_HOST", "localhost"),
                    user=os.getenv("MYSQL_USER", "root"),
                    password=os.getenv("MYSQL_PASSWORD", ""),           
                    database=os.getenv("MYSQL_DATABASE", "SmartSeg")
                )
                st.session_state.conn = conn
                st.sidebar.success("✅ Connected to MySQL!")
            except Error as e:
                st.sidebar.warning("⚠️ MySQL not available. Using CSV file instead.")
                st.session_state.conn = None

    # Load Data
    if st.session_state.conn:
        df = pd.read_sql("SELECT * FROM shopping_trends", st.session_state.conn)
        st.success(f"✅ Data Loaded from MySQL: {len(df)} records")
    else:
        csv_path = os.path.join(os.path.dirname(__file__), "data/shopping_trends.csv")
        df = pd.read_csv(csv_path)
        st.info("Using CSV file (Click 'Connect to MySQL' to use database)")

    # ====================== SEGMENTATION ======================
    @st.cache_resource
    def perform_segmentation(df):
        features = df[['Age', 'Purchase Amount (USD)', 'Previous Purchases', 'Review Rating']]
        scaler = StandardScaler()
        scaled = scaler.fit_transform(features)
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        df['Segment'] = kmeans.fit_predict(scaled)
        
        segment_map = {0: "At Risk", 1: "VIP Customers", 2: "New Customers", 
                       3: "Loyal Customers", 4: "Hibernating"}
        df['Segment_Name'] = df['Segment'].map(segment_map)
        return df

    df = perform_segmentation(df)

        # ====================== FINAL BALANCED LOYALTY SYSTEM ======================
    # Optimized for your dataset (lower thresholds)
    df['Loyalty_Points'] = (df['Purchase Amount (USD)'] * 6).astype(int)   # Higher multiplier

    def get_tier(points):
        if points >= 500:
            return "Gold"
        elif points >= 350:
            return "Silver"
        elif points >= 200:
            return "Bronze"
        else:
            return "Starter"

    df['Tier'] = df['Loyalty_Points'].apply(get_tier)

    # Show distribution in Sidebar
    st.sidebar.subheader("📊 Tier Distribution")
    st.sidebar.write(df['Tier'].value_counts())

       # ====================== OFFER ======================
       
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
            return f"❌ Error: {str(e)}"

    # ====================== TABS ======================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Overview", "🔍 Segmentation", "🎁 Offer Engine", "📈 Insights", 
        "💡 Strategies", "🤖 AI Chat", "🏆 Loyalty Program"
    ])

    with tab1:
        st.header("📊 Dataset Overview & Key Business Trends")

        # Key Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Customers", f"{len(df):,}")
        c2.metric("Total Revenue", f"${df['Purchase Amount (USD)'].sum():,.0f}")
        c3.metric("Avg Purchase", f"${df['Purchase Amount (USD)'].mean():.2f}")
        c4.metric("Avg Rating", f"{df['Review Rating'].mean():.2f}")

        # Charts Section
        st.subheader("📈 Business Insights & Trends")

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

        # Additional Charts Row
        st.subheader("More Business Trends")
        col3, col4 = st.columns(2)

        with col3:
            # Top Categories by Revenue
            revenue_by_cat = df.groupby('Category')['Purchase Amount (USD)'].sum().reset_index()
            st.plotly_chart(px.bar(revenue_by_cat, x='Category', y='Purchase Amount (USD)', 
                                  title="Revenue by Category"), 
                           use_container_width=True)

        with col4:
            # Gender Distribution
            st.plotly_chart(px.histogram(df, x='Gender', title="Gender-wise Purchases", 
                                        color='Gender'), 
                           use_container_width=True)

        # Summary Table
        st.subheader("Segment Performance Summary")
        summary = df.groupby('Segment_Name').agg({
            'Customer ID': 'count',
            'Purchase Amount (USD)': ['sum', 'mean']
        }).round(2)
        summary.columns = ['Customer Count', 'Total Revenue', 'Avg Spending']
        st.dataframe(summary, use_container_width=True)
    with tab2:
            
        st.header("🔍 Customer Segmentation & Dataset Explorer")

        # Tab inside Segmentation Tab
        subtab1, subtab2, subtab3 = st.tabs(["📋 Full Dataset", "🔎 Search Dataset", "🗄️ SQL Query Explorer"])

        with subtab1:
            st.subheader("📋 Complete Dataset")
            st.caption(f"Total Records: {len(df):,} | Showing first 1000 rows")
            st.dataframe(df.head(1000), use_container_width=True)

        with subtab2:
            st.subheader("🔎 Search in Dataset")
            search_term = st.text_input("Search by Customer ID, Name, Category, Season, Gender, etc.", "")
            
            if search_term:
                filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
                st.write(f"**Results for:** `{search_term}`  |  Found: {len(filtered_df)} records")
                st.dataframe(filtered_df.head(500), use_container_width=True)
            else:
                st.info("Enter a search term above to filter the dataset.")

        with subtab3:
            st.subheader("🗄️ SQL Query Explorer")
            st.caption("Run custom SQL queries (Works best when connected to MySQL)")
            
            default_query = """SELECT Category, COUNT(*) as Total_Customers, 
                              SUM(`Purchase Amount (USD)`) as Total_Revenue,
                              ROUND(AVG(`Purchase Amount (USD)`), 2) as Avg_Spending
                              FROM shopping_trends 
                              GROUP BY Category 
                              ORDER BY Total_Revenue DESC 
                              LIMIT 10"""
            
            sql_query = st.text_area("Write your SQL Query here:", default_query, height=130)
            
            if st.button("🚀 Run SQL Query"):
                if st.session_state.conn:
                    try:
                        result = pd.read_sql(sql_query, st.session_state.conn)
                        st.success("✅ Query Executed Successfully!")
                        st.dataframe(result, use_container_width=True)
                    except Exception as e:
                        st.error(f"Query Error: {e}")
                else:
                    st.warning("Please connect to MySQL first!")

        st.info("💡 You can now view the full dataset, search anything, or run SQL queries in this tab.")

    with tab3:
        st.header("🎁 Personalized Offer Engine")
        
        cust_id_input = st.text_input("Enter Customer ID", placeholder="1")
        
        if cust_id_input:
            try:
                # Convert to proper type and search safely
                cust_id = int(cust_id_input.strip())
                
                # Search in dataframe
                customer_data = df[df['Customer ID'] == cust_id]
                
                if not customer_data.empty:
                    cust = customer_data.iloc[0]
                    st.success(f"✅ Customer Found! | **ID:** {cust['Customer ID']}")
                    st.markdown(f"**Segment:** `{cust['Segment_Name']}`")
                    st.markdown(f"**Tier:** `{cust['Tier']}`")
                    
                    # Multiple Offers Display
                    st.markdown("### 🎁 Recommended Personalized Offers:")
                    offers_list = get_personalized_offer(cust['Segment_Name'])
                    
                    for i, offer in enumerate(offers_list, 1):
                        st.markdown(f"**{i}.** {offer}")
                    
                    # Bonus: Show customer details
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

    with tab4:
        st.header("📈 Business Insights (Powered by MySQL)")

        # ==================== INTERACTIVE FILTERS ====================
        st.subheader("🔍 Interactive Filters")
        
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

        # Apply Filter in Pandas (since Segment_Name is not in MySQL)
        filtered_df = df[
            (df['Segment_Name'].isin(selected_segments)) &
            (df['Category'].isin(selected_categories)) &
            (df['Season'].isin(selected_seasons))
        ]

        st.caption(f"Showing insights for **{len(filtered_df)}** filtered records")

        # ==================== MySQL QUERIES (Without Segment_Name filter) ====================
        if st.session_state.conn:
            st.subheader("1. Top 10 Best Selling Categories")
            query1 = f"""
            SELECT Category, COUNT(*) as Total_Sold, 
                   SUM(`Purchase Amount (USD)`) as Total_Revenue,
                   ROUND(AVG(`Purchase Amount (USD)`), 2) as Avg_Purchase
            FROM shopping_trends 
            WHERE Category IN ({','.join([f"'{c}'" for c in selected_categories])})
              AND Season IN ({','.join([f"'{s}'" for s in selected_seasons])})
            GROUP BY Category 
            ORDER BY Total_Revenue DESC 
            LIMIT 10
            """
            result1 = pd.read_sql(query1, st.session_state.conn)
            st.dataframe(result1, use_container_width=True)

            st.subheader("2. Sales by Season")
            query2 = f"""
            SELECT Season, COUNT(*) as Total_Transactions, 
                   SUM(`Purchase Amount (USD)`) as Revenue,
                   ROUND(AVG(`Purchase Amount (USD)`), 2) as Avg_Order_Value
            FROM shopping_trends 
            WHERE Category IN ({','.join([f"'{c}'" for c in selected_categories])})
              AND Season IN ({','.join([f"'{s}'" for s in selected_seasons])})
            GROUP BY Season 
            ORDER BY Revenue DESC
            """
            result2 = pd.read_sql(query2, st.session_state.conn)
            st.dataframe(result2, use_container_width=True)

            st.subheader("3. Revenue by Customer Segment (Python)")
            segment_summary = filtered_df.groupby('Segment_Name').agg({
                'Customer ID': 'count',
                'Purchase Amount (USD)': ['sum', 'mean']
            }).round(2)
            segment_summary.columns = ['Customer Count', 'Total Revenue', 'Avg Spending']
            st.dataframe(segment_summary, use_container_width=True)

        else:
            st.warning("Connect to MySQL to see detailed insights")

        st.info("💡 Filters are applied across all insights. Segment filter works via Python (since Segment_Name is calculated).")
    with tab5:
        st.header("💡 Sales & Retention Strategies")
        st.markdown("### 🎯 Proven Sales & Customer Retention Strategies")
        st.info("""
        **Inspired by Top Companies (Zomato, Swiggy, Jio, Tata, DMart, Vishal Mega Mart & Big Malls)**

        ### 1. Win-Back & Reactivation Strategies
        - **Lost Customer Offers** – Send "We Miss You" 30-40% OFF coupons (like Zomato & Swiggy)
        - **Reactivation Bonus** – Give extra loyalty points on return purchase (Jio & Swiggy style)
        - **Win-Back Bundles** – Buy 1 Get 1 + Free Delivery for dormant customers

        ### 2. Loyalty & Rewards Strategies
        - **Tiered Loyalty Program** – Bronze, Silver, Gold tiers with increasing benefits (like Jio Prime & DMart)
        - **Referral Program** – "Refer & Earn" – Both referrer and new customer get points (Zomato/Swiggy model)
        - **Birthday & Anniversary Rewards** – Special discounts + free gifts (common in Big Malls)
        - **Points Redemption System** – Allow customers to redeem points for vouchers or products

        ### 3. Personalization & Targeted Offers
        - **Segment-Specific Offers** – VIP customers get early access & exclusive deals
        - **Category-Based Recommendations** – Suggest products based on past purchases (like Amazon & DMart)
        - **Location-Based Offers** – Send offers for nearby high-selling categories

        ### 4. Seasonal & Festive Campaigns
        - **Mega Seasonal Sales** – Big discounts during Diwali, Holi, Eid, Christmas (Vishal Mega Mart style)
        - **Flash Sales & Limited Time Offers** – Create urgency (Zomato & Swiggy technique)
        - **Bundle Offers** – Combine high-selling items at discounted prices

        ### 5. Engagement & Retention Tactics
        - **Feedback & Review Rewards** – Give loyalty points for product reviews
        - **VIP Customer Community** – Create exclusive WhatsApp groups for top customers
        - **Personalized Notifications** – Send "Your favorite brand is on sale" alerts
        - **Gamification** – Spin the wheel, scratch cards, and challenges to earn points

        ### 6. Long-term Growth Strategies
        - **Customer Lifetime Value Focus** – Prioritize high-spending customers
        - **Cross-Selling & Up-Selling** – Suggest complementary products during checkout
        - **Partnership Offers** – Tie-ups with other brands (like Jio & Tata strategies)
        """)

    with tab6:
        st.header("🤖 Groq AI Chat Assistant")
        st.caption("Ask anything about sales, customers, segments, or strategies")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if prompt := st.chat_input("Ask any question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = ai_analytics_chat(prompt)
                    st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    with tab7:
        st.header("🏆 Loyalty & Rewards Program")
        
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
                st.progress(min(cust['Loyalty_Points']/400, 1.0))
                st.write(f"**Loyalty Points:** {cust['Loyalty_Points']}")
                st.write(f"**Total Spent:** ${cust['Purchase Amount (USD)']}")
            except:
                st.error("Customer not found!")

    st.sidebar.info("SmartSeg - Major Internship Project")