import os

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print("==============================")
    print(f"BOT ONLINE: {bot.user}")
    print("==============================")

    try:
        comandos = await bot.tree.sync()

        print(
            f"{len(comandos)} comando(s) sincronizado(s)."
        )

    except Exception as erro:
        print(
            "Erro ao sincronizar comandos:",
            erro
        )


@bot.tree.command(
    name="criar-sala",
    description="Cria uma sala de compartilhamento de tela"
)
async def criar_sala(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        "🚀 Comando funcionando! "
        "Agora vamos conectar ao Screen Share."
    )


if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN não encontrado no arquivo .env"
    )


bot.run(TOKEN)