import dwani
import os
dwani.api_key = 'your_api_key'
dwani.api_base = 'your_dwani_url'
def main():
    print("hello")
    resp = dwani.Chat.create(prompt="Hello!", src_lang="english", tgt_lang="kannada")
    print(resp)
    
if __name__ == "__main__":
    main()