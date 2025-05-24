import uvicorn
from fastapi import FastAPI
import dwani
dwani.api_key = 'your_api_key'
dwani.api_base = 'your_base_url'
app = FastAPI(
    title="dwani.ai API",
    redirect_slashes=False,
)
@app.post("/v1/chat")
async def chat(
):
    resp = dwani.Chat.create(prompt="Hello!", src_lang="english", tgt_lang="kannada")
    return resp

if __name__ == "__main__":
    uvicorn.run(app)