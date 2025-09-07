"""
Simple checks that your environment is set correctly.
"""
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

def main():
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY missing in .env")
        return
    try:
        _ = OpenAIEmbeddings(api_key=key)
        print("OpenAI key looks configured. 👍")
    except Exception as e:
        print("OpenAI configuration error:", e)

if __name__ == "__main__":
    main()
