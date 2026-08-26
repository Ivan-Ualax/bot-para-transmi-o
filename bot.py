import os

import discord
import aiohttp

from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

BASE_URL = "https://bot-para-transmi-o.vercel.app"


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
    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:

            async with session.post(
                f"{BASE_URL}/criar-sala"
            ) as resposta:

                if resposta.status != 200:
                    await interaction.followup.send(
                        "Não foi possível criar a sala."
                    )
                    return

                dados = await resposta.json()

                codigo = dados["codigo"]

                link = (
                    f"{BASE_URL}/sala/{codigo}"
                )

                mensagem = (
                    "🎥 **Sala criada!**\n\n"
                    f"**Código:** `{codigo}`\n"
                    f"**Entrar na sala:**\n{link}\n\n"
                    "Qualquer pessoa com o link "
                    "pode entrar, assistir ou transmitir."
                )

                await interaction.followup.send(
                    mensagem
                )

    except Exception as erro:

        print(
            "Erro ao criar sala:",
            erro
        )

        await interaction.followup.send(
            "Ocorreu um erro ao conectar "
            "com o Screen Share."
        )


if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN não encontrado no arquivo .env"
    )


bot.run(TOKEN)