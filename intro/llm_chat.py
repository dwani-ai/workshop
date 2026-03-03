import dwani
import os
dwani.api_key = 'your_api_key'
dwani.api_base = 'dwani api url'
def main():
    resp = dwani.Chat.create(prompt="Hello!", src_lang="english", tgt_lang="kannada", model="gemma3")


    print(resp)

    resp = dwani.Chat.direct(prompt="Hello! I am sachin")

    print(resp)

    
if __name__ == "__main__":
    main()