import dwani
import os
dwani.api_key = 'your_api_key'
dwani.api_base = 'your_dwani_url'
def main():
    print("hello")
    result = dwani.Vision.caption(
    file_path="image.png",
    query="Describe this logo",
    src_lang="english",
    tgt_lang="kannada"
)
    print(result)
if __name__ == "__main__":
    main()