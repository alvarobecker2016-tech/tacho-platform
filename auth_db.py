import streamlit as st
from supabase import create_client, Client
import hashlib

# Bezpieczne łączenie z chmurą Supabase
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    supabase = None
    print("Błąd połączenia z Supabase:", e)

def init_db():
    # Nie musimy tu już nic robić, bo zbudowałeś bazę w SQL w panelu Supabase!
    pass

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, full_name, company_name):
    if not supabase:
        return False
        
    hashed_pw = hash_password(password)
    
    try:
        # Rejestracja kierowcy w chmurze - domyślnie dostaje 3 Kredyty na start!
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
        # Błąd wyrzuci, np. gdy taki adres email(username) już istnieje
        print("Błąd rejestracji:", e)
        return False

def verify_login(username, password):
    if not supabase:
        return None
        
    hashed_pw = hash_password(password)
    
    try:
        # Pobieranie profilu kierowcy z chmury
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
        print("Błąd logowania:", e)
        return None