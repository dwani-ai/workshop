import dwani
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set dwani credentials from environment variables
dwani.api_key = os.getenv("DWANI_API_KEY")
dwani.api_base = os.getenv("DWANI_API_BASE")

def main():
    print("hello")
    result = dwani.Documents.run_extract(
        file_path="dwani-workshop.pdf",
        page_number=1,
        src_lang="english",
        tgt_lang="hindi"
    )
    print(result)

if __name__ == "__main__":
    main()
