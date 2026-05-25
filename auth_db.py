import streamlit as st
from supabase import create_client, Client
import hashlib

# Funkcja diagnostyczna: Łączenie z chmurą przy każdym kliknięciu
def get_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"🚨 PROBLEM Z KLUCZAMI (Secrets): {e}")
        return None

def init_db():
    pass

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, full_name, company_name):
    supabase = get_supabase()
    if not supabase:
        return False
        
    hashed_pw = hash_password(password)
    
    try:
        # Próba wysłania danych do chmury
        response = supabase.table("users").insert({
            "username": username,
            "password": hashed_pw,
            "full_name": full_name,
            "company_name": company_name,
            "credits": 3,
            "is_premium": False
        }).execute()
        return True
    except Exception as e:
        # ZAMIAST MILCZEĆ, APLIKACJA WYŚWIETLI PRAWDZIWY BŁĄD:
        st.error(f"🚨 CHMURA ODRZUCIŁA DANE. POWÓD: {str(e)}")
        return False

def verify_login(username, password):
    supabase = get_supabase()
    if not supabase:
        return None
        
    hashed_pw = hash_password(password)
    
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", hashed_pw).execute()
        data = response.data
        
        if data and len(data) > 0:
            user = data[0]
            return {
                "username": user["username"],
                "full_name": user["full_name"],
                "company_name": user["company_name"],
                "credits": user["credits"],
                "is_premium": user["is_premium"]
            }
        return None
    except Exception as e:
        st.error(f"🚨 BŁĄD ODCZYTU PRZY LOGOWANIU: {str(e)}")
        return None