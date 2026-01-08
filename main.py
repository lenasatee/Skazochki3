import os
import wave
import logging
from aiohttp import web
from google import genai
from google.genai import types
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv('API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

model_name = "gemini-2.5-flash-preview-tts"  # Быстрый и экспрессивный TTS для сказок

@router.message(CommandStart())
async def start(message: Message):
    await message.reply("Hello! Send me English fairy tale text, and I'll narrate it with magical Gemini 2.5 voice! ✨\n"
                        "Example: Once upon a time in a kingdom far away...")

@router.message()
async def tts_handler(message: Message):
    text = message.text.strip()
    if len(text) > 1500:
        await message.reply("Text too long! Keep it under 1500 characters for best result.")
        return

    await message.reply("Weaving fairy tale magic into voice... 🎙️")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"  # Мягкий женский голос (попробуй Aoede, Leda, Puck для других)
                        )
                    )
                )
            )
        )

        pcm_data = response.candidates[0].content.parts[0].inline_data.data

        output_path = "/tmp/output.wav"
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)

        with open(output_path, "rb") as audio_file:
            await message.answer_voice(audio_file, caption="Your fairy tale narrated by Gemini 2.5! 📖🔊")

        os.remove(output_path)
    except Exception as e:
        await message.reply(f"Oops, something went wrong: {str(e)}")

dp.include_router(router)

async def on_startup(app: web.Application):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook set to {webhook_url}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()

app = web.Application()
app["bot"] = bot

setup_application(app, dp, bot=bot)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
