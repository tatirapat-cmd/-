# db.py
import os
from supabase import create_client, Client

# ใส่ URL และ Anon Key ที่ก๊อปปี้มาจากขั้นตอนที่ 3
# (แนะนำให้เก็บเป็น Environment Variables บน Vercel ภายหลัง)
SUPABASE_URL = "ใส่_Project_URL_ตรงนี้"
SUPABASE_KEY = "ใส่_anon_public_Key_ตรงนี้"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ฟังก์ชันกลางสำหรับดึงและบันทึกข้อมูลแทนการใช้ไฟล์ JSON ---
def db_get(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        return response.data
    except Exception as e:
        print(f"Error fetching {table_name}: {e}")
        return []

def db_insert(table_name, data):
    try:
        response = supabase.table(table_name).insert(data).execute()
        return response.data
    except Exception as e:
        print(f"Error inserting into {table_name}: {e}")
        return None

def db_update(table_name, match_column, match_value, update_data):
    try:
        response = supabase.table(table_name).update(update_data).eq(match_column, match_value).execute()
        return response.data
    except Exception as e:
        print(f"Error updating {table_name}: {e}")
        return None

def db_delete(table_name, match_column, match_value):
    try:
        response = supabase.table(table_name).delete().eq(match_column, match_value).execute()
        return response.data
    except Exception as e:
        print(f"Error deleting from {table_name}: {e}")
        return None
