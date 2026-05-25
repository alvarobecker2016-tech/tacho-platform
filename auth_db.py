import streamlit as st
from supabase import create_client, Client
import hashlib

def get_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"🚨 PROBLEM Z KLUCZAMI: {e}")
        return None

def init_db():
    pass

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, full_name, company_name):
    supabase = get_supabase()
    if not supabase: return False
        
    hashed_pw = hash_password(password)
    
    try:
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
        st.error(f"🚨 CHMURA ODRZUCIŁA DANE. POWÓD: {str(e)}")
        return False

def verify_login(username, password):
    supabase = get_supabase()
    if not supabase: return None
        
    hashed_pw = hash_password(password)
    
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", hashed_pw).execute()
        data = response.data
        
        if data and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        st.error(f"🚨 BŁĄD ODCZYTU: {str(e)}")
        return None

# --- NOWOŚĆ: SYSTEM POBIERANIA ŻETONÓW ---
def use_credit(username):
    supabase = get_supabase()
    if not supabase: return None
    
    try:
        # Sprawdzamy stan konta
        response = supabase.table("users").select("credits, is_premium").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            user = response.data[0]
            
            # Jeśli ktoś kupił abonament (Premium), nie traci żetonów
            if user["is_premium"]:
                return True
                
            current_credits = user["credits"]
            
            # Jeśli ma żetony, zabieramy jeden
            if current_credits > 0:
                new_balance = current_credits - 1
                supabase.table("users").update({"credits": new_balance}).eq("username", username).execute()
                return new_balance
        return None
    except Exception as e:
        print("Błąd pobierania opłaty:", e)
        return None