import dwani
import os
dwani.api_key = 'your_api_key'
dwani.api_base = 'your_dwani_url'
def main():
    print("hello")
    result = dwani.Documents.run_extract(file_path = "dwani-workshop.pdf", page_number=1, src_lang="english",tgt_lang="hindi" )
    print(result)

if __name__ == "__main__":
    main()