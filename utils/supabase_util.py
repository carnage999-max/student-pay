from supabase import create_client, Client
from decouple import config


url = config("SUPABASE_URL")
key = config("SUPABASE_KEY")
supabase: Client = create_client(url, key)
