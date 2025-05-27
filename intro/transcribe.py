import dwani
import os
dwani.api_key = 'your_api_key'
dwani.api_base = 'your_dwani_url'
def main():
    print("hello")
    result = dwani.ASR.transcribe(file_path="kannada_sample.wav", language="kannada")
    print(result)

if __name__ == "__main__":
    main()