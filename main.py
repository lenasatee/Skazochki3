import os
from google import genai
from google.genai import types
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv('API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client()

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher()  # Без аргументов в aiogram 3.x

model_name = "gemini-2.5-flash-preview-tts"  # Актуальная TTS-модель (быстрая и качественная)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Hello! Send me English fairy tale text, and I'll narrate it with Gemini 2.5 magic voice! ✨\nExample: Once upon a time...")

@dp.message_handler()
async def tts_handler(message: types.Message):
    text = message.text
    if len(text) > 2000:
        await message.reply("Text too long! Split into parts (max ~2000 chars).")
        return

    await message.reply("Generating fairy tale narration... 🎙️")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )
        )

        # Аудио в response (обычно в parts как binary data)
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        with open("/tmp/output.wav", "wb") as f:
            f.write(audio_data)

        with open("/tmp/output.wav", "rb") as audio_file:
            await message.answer_voice(audio_file, caption="Your English fairy tale narrated by Gemini 2.5! 📖🔊")

        os.remove("/tmp/output.wav")
    except Exception as e:
        await message.reply(f"Oops, error: {str(e)}\nMaybe try shorter text or check logs.")

async def on_startup(_):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{API_TOKEN}"
    await bot.set_webhook(webhook_url)

async def on_shutdown(_):
    await bot.delete_webhook()

@app.post("/webhook/{API_TOKEN}")
async def webhook(request: Request):
    update = types.Update.parse_raw(await request.json())
    await dp.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Fairy tale bot is alive and ready to narrate! ✨"}

if __name__ == "__main__":
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=f"/webhook/{API_TOKEN}",
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )
