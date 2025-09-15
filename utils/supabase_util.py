from supabase import create_client, Client
from decouple import config


url = config("SUPABASE_URL")
key = config("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def upload_to_supabase(bucket_name, file_path, file_data):
    """
    The function `upload_to_supabase` uploads a file to a Supabase storage bucket and returns the public
    URL of the uploaded file.
    
    :param bucket_name: Bucket name is the name of the storage bucket in Supabase where you want to
    upload the file.
    :param file_path: The `file_path` parameter in the `upload_to_supabase` function represents the path
    where the file will be stored in the Supabase storage bucket. 
    :param file_data: The `file_data` parameter in the `upload_to_supabase` function should be the
    actual data of the file that you want to upload to Supabase.
    :return: The function `upload_to_supabase` is returning the public URL of the uploaded file in the
    Supabase storage.
    """
    supabase.storage.from_(bucket_name).upload(
        path=file_path,
        file=file_data,
        file_options={"upsert": "true"},
    )
    public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
    return public_url
