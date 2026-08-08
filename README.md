🛍️ SmartSeg
Intelligent Customer Segmentation & Personalized Offer System
Major Internship Project | Retail Analytics Dashboard

🌟 Project Overview
SmartSeg is a smart retail analytics platform designed to help mall owners and businesses understand their customers better and boost sales through data-driven decisions.

Using Machine Learning, the system automatically segments customers based on their purchase behavior and delivers personalized marketing strategies, loyalty rewards, and actionable business insights — all in one interactive dashboard.

✨ Key Features
Feature	Description
Customer Segmentation	K-Means Clustering creating 5 meaningful segments (VIP, Loyal, New, At Risk, Hibernating)
Personalized Offer Engine	Multiple smart offers tailored to each customer segment
Gamified Loyalty Program	Points system with Starter, Bronze, Silver & Gold tiers
Interactive Business Insights	Dynamic filters + real-time charts for deeper analysis
Groq AI Chat Assistant	Ask natural language questions about your sales data
Dataset Explorer	Search, filter, and run custom SQL queries
Dual Database Support	Works with Local CSV + MySQL (Railway Cloud)
Modern UI	Clean dark-themed Streamlit interface
🛠️ Tech Stack
Frontend: Streamlit
Data Processing: Pandas, NumPy
Machine Learning: Scikit-learn (K-Means Clustering)
Visualization: Plotly Express
AI Assistant: Groq (llama-3.3-70b-versatile)
Database: MySQL (Local + Railway Cloud)
Deployment: Railway
🚀 How to Run Locally
1. Clone the Repository
git clone https://github.com/charchit-chauhan/SmartSeg.git
cd SmartSeg/Final

# Windows
python -m venv smartseg_env
smartseg_env\Scripts\activate

# macOS/Linux
python3 -m venv smartseg_env
source smartseg_env/bin/activate

pip install -r requirements.txt

streamlit run app.py

🌐 Live Deployment
The project is deployed on Railway and connected to a Railway MySQL database for cloud access.


📊 Dataset

Name: Customer Shopping Latest Trends Dataset
Source: Kaggle
Records: ~3,900+ customers
Key Columns: Age, Gender, Category, Purchase Amount, Season, Review Rating, Previous Purchases, etc.

🏆 Highlights

Secure Login System
Real-time Interactive Charts
SQL Query Explorer
Multi-offer Personalized Recommendations
Tier-based Loyalty System
AI-powered Business Assistant
Fully Responsive Dashboard

👤 Author
Charchit Chauhan
Major Internship Project – SURE Trust
