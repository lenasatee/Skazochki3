import os
import wave
from google import genai
from google.genai import types
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types

API_TOKEN = os.getenv('API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client()

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher()  # В aiogram 3 бот привязывается автоматически при обработке

model_name = "gemini-2.5-flash-preview-tts"  # Топовый быстрый TTS

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Hello! Send me English fairy tale text, and I'll narrate it with expressive Gemini 2.5 voice! ✨\n"
                        "Try: Once upon a time there was a beautiful princess...")

@dp.message_handler()
async def tts_handler(message: types.Message):
    text = message.text.strip()
    if len(text) > 1500:
        await message.reply("Text too long! Keep it under ~1500 characters for best quality.")
        return

    await message.reply("Brewing magical narration... 🎙️")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"  # Мягкий женский голос для сказок (Aoede, Leda, Puck тоже крутые)
                        )
                    )
                )
            )
        )

        # Аудио в PCM (raw data)
        pcm_data = response.candidates[0].content.parts[0].inline_data.data

        # Конвертируем в WAV
        output_path = "/tmp/output.wav"
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)          # Моно
            wf.setsampwidth(2)          # 16-bit
            wf.setframerate(24000)      # Стандарт для Gemini TTS
            wf.writeframes(pcm_data)

        with open(output_path, "rb") as audio_file:
            await message.answer_voice(audio_file, caption="Your fairy tale narrated by Gemini 2.5! 📖🔊")

        os.remove(output_path)
    except Exception as e:
        await message.reply(f"Oops: {str(e)}. Try shorter text or check if TTS preview is available.")

async def on_startup():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{API_TOKEN}"
    await bot.set_webhook(webhook_url)
    print("Webhook set!")

async def on_shutdown():
    await bot.delete_webhook()
    print("Webhook deleted.")

@app.on_event("startup")
async def startup_event():
    await on_startup()

@app.on_event("shutdown")
async def shutdown_event():
    await on_shutdown()

@app.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    if token != API_TOKEN:
        return {"ok": False}
    update = types.Update.parse_raw(await request.json())
    await dp.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "English Fairy Tales Bot is alive and ready to tell stories! ✨"}
