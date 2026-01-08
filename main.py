import os
from google import genai
from google.genai import types
import wave
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv('API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client()

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

model_name = "gemini-2.5-flash-preview-tts"  # Отличный голос для сказок, быстрый

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Hello! Send me English fairy tale text, and I'll narrate it with expressive Gemini 2.5 voice! ✨\n"
                        "Example: Once upon a time there lived a little girl...")

@dp.message_handler()
async def tts_handler(message: types.Message):
    text = message.text.strip()
    if len(text) > 1500:  # Лимит для стабильности (TTS лучше работает с короткими текстами)
        await message.reply("Text too long! Split into parts (max ~1500 symbols).")
        return

    await message.reply("Generating enchanting narration... 🎙️")

    try:
        # Генерация аудио
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"  # Красивый женский голос, можно попробовать Puck, Fenrir, Aoede, Charon
                        )
                    )
                )
            )
        )

        # Аудио в PCM формате (raw)
        pcm_data = response.candidates[0].content.parts[0].inline_data.data

        # Сохраняем в WAV (Telegram любит WAV/OGG, но voice принимает WAV)
        output_path = "/tmp/output.wav"
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(24000)  # Стандарт для Gemini TTS
            wf.writeframes(pcm_data)

        with open(output_path, "rb") as audio_file:
            await message.answer_voice(audio_file, caption="Your fairy tale narrated by Gemini 2.5! 📖🔊")

        os.remove(output_path)
    except Exception as e:
        await message.reply(f"Error: {str(e)}\nTry shorter text or another voice.")

async def on_startup(_):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{API_TOKEN}"
    await bot.set_webhook(webhook_url)
    print("Webhook set")

async def on_shutdown(_):
    await bot.delete_webhook()

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
