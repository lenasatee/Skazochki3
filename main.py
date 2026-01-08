import os
import google.generativeai as genai
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentType

API_TOKEN = os.getenv('API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Актуальная модель TTS (flash — быстрее, pro — качественнее)
model_name = "gemini-2.5-flash-preview-tts"  # Или "gemini-2.5-pro-preview-tts"

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Hi! Send me English fairy tale text, and I'll narrate it with Gemini 2.5 TTS! ✨")

@dp.message_handler(content_types=ContentType.TEXT)
async def tts_handler(message: types.Message):
    text = message.text
    if len(text) > 3000:
        await message.reply("Text too long! Split into parts.")
        return

    await message.reply("Generating magical narration... 🎙️")

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            text,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="audio/wav"  # Или "audio/pcm" если нужно
            )
        )

        audio_data = response.parts[0].inline_data.data

        with open("output.wav", "wb") as f:
            f.write(audio_data)

        with open("output.wav", "rb") as audio_file:
            await message.answer_voice(audio_file, caption="Your fairy tale narrated by Gemini 2.5! 📖🔊")

        os.remove("output.wav")
    except Exception as e:
        await message.reply(f"Oops: {str(e)}")

@app.on_event("startup")
async def on_startup():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{API_TOKEN}"
    await bot.set_webhook(webhook_url)

@app.post(f"/webhook/{{API_TOKEN}}")
async def webhook(request: Request, API_TOKEN: str):
    update = types.Update.parse_raw(await request.json())
    await dp.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Fairy tale bot is alive!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
