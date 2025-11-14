import chainlit as cl
from groq import Groq
import json
import os
from datetime import datetime, timedelta
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List
import pandas as pd
from collections import Counter
from dotenv import load_dotenv
from contextlib import contextmanager
import re

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("API_KEY_GROQ_API_KEY")
if not api_key:
    print("⚠️  WARNING: GROQ_API_KEY not found in environment variables!")
    print("Please set your Groq API key:")
    print("  1. Create a .env file in your project root")
    print("  2. Add: GROQ_API_KEY=your_api_key_here")
    print("  3. Or run: export GROQ_API_KEY=your_api_key_here")
else:
    print(f"✅ Groq API key loaded: {api_key[:10]}...")

client = Groq(api_key=api_key) if api_key else None

# Database connection parameters
DB_CONFIG = {
    "host": "hackathon-db.ceqjfmi6jhdd.ap-southeast-1.rds.amazonaws.com",
    "port": 5432,
    "database": "hackathon_db",
    "user": "hackathon_user",
    "password": "Hackathon2025!",
    "connect_timeout": 10  # Added timeout to prevent hanging
}

@contextmanager
def get_db_connection():
    """Create a database connection with automatic cleanup"""
    conn = None
    try:
        conn = psycopg2.connect(DB_CONFIG)
        yield conn
    except Exception as e:
        print(f"[ERROR] Database connection error: {e}")
        yield None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass  # Ignore errors during cleanup

def query_claims_data(destination: Optional[str] = None, limit: int = 1000) -> List[Dict]:
    """Query historical claims data from the database"""
    with get_db_connection() as conn:
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if destination:
                    query = """
                        SELECT * FROM hackathon.claims 
                        WHERE LOWER(destination) LIKE LOWER(%s)
                        ORDER BY accident_date DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (f"%{destination}%", limit))
                else:
                    query = """
                        SELECT * FROM hackathon.claims 
                        ORDER BY accident_date DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (limit,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"[ERROR] Query error: {e}")
            return []

def analyze_destination_risk(destination: str) -> Dict:
    """Analyze risk for a specific destination using real claims data"""
    claims = query_claims_data(destination=destination)
    
    if not claims:
        return {
            "risk_level": "Unknown",
            "total_claims": 0,
            "message": "No historical data available for this destination"
        }
    
    total_claims = len(claims)
    claim_types = Counter([c['claim_type'] for c in claims if c.get('claim_type')])
    causes = Counter([c['cause_of_loss'] for c in claims if c.get('cause_of_loss')])
    
    avg_gross_incurred = sum([float(c['gross_incurred'] or 0) for c in claims]) / total_claims if total_claims > 0 else 0
    avg_net_paid = sum([float(c['net_paid'] or 0) for c in claims]) / total_claims if total_claims > 0 else 0
    
    if avg_gross_incurred > 5000 or total_claims > 100:
        risk_level = "High"
    elif avg_gross_incurred > 2000 or total_claims > 50:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    
    months = Counter([c['accident_date'].month for c in claims if c.get('accident_date')])
    peak_months = months.most_common(3)
    
    return {
        "destination": destination,
        "risk_level": risk_level,
        "total_claims": total_claims,
        "most_common_claims": [{"type": k, "count": v} for k, v in claim_types.most_common(5)],
        "common_causes": [{"cause": k, "count": v} for k, v in causes.most_common(5)],
        "avg_claim_amount": round(avg_gross_incurred, 2),
        "avg_payout": round(avg_net_paid, 2),
        "peak_months": [{"month": datetime(2000, m, 1).strftime("%B"), "claims": c} for m, c in peak_months],
        "recommendation": f"Based on {total_claims} historical claims, we recommend {'Premium or Luxury' if risk_level == 'High' else 'Premium' if risk_level == 'Medium' else 'Basic'} coverage"
    }

def predict_claim_likelihood(destination: str, duration_days: int, activities: List[str]) -> Dict:
    """Predict claim likelihood based on historical data"""
    claims = query_claims_data(destination=destination)
    
    if not claims:
        return {
            "likelihood": "Unknown",
            "confidence": 0,
            "message": "Insufficient data for prediction"
        }
    
    total_claims = len(claims)
    
    if activities is None:
        activities = []
    elif isinstance(activities, tuple):
        activities = list(activities)
    elif not isinstance(activities, list):
        activities = [activities]
    
    activities = [str(act) if not isinstance(act, str) else act for act in activities]
    
    risk_multiplier = 1.0
    high_risk_activities = ['skiing', 'diving', 'climbing', 'surfing', 'hiking', 'adventure']
    for activity in activities:
        if any(risk_act in activity.lower() for risk_act in high_risk_activities):
            risk_multiplier += 0.3
    
    if duration_days > 14:
        risk_multiplier += 0.2
    elif duration_days > 7:
        risk_multiplier += 0.1
    
    base_rate = min(total_claims / 1000 * 100, 50)
    adjusted_likelihood = min(base_rate * risk_multiplier, 75)
    
    if adjusted_likelihood > 30:
        category = "High"
    elif adjusted_likelihood > 15:
        category = "Medium"
    else:
        category = "Low"
    
    claim_types = Counter([c['claim_type'] for c in claims if c.get('claim_type')])
    most_likely = claim_types.most_common(1) if claim_types else [("Medical", 0)]
    
    return {
        "likelihood_percentage": round(adjusted_likelihood, 1),
        "likelihood_category": category,
        "confidence": min(total_claims / 10, 100),
        "most_likely_claim_type": most_likely[0][0],
        "prevention_tips": [
            "Purchase insurance within 14 days of initial deposit for maximum coverage",
            "Keep digital copies of all travel documents and receipts",
            "Register with your embassy when traveling abroad",
            f"Be extra cautious with {most_likely[0][0].lower()} related activities"
        ]
    }