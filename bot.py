import os

import aiohttp
import discord

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
            repr(erro)
        )


@bot.tree.command(
    name="criar-sala",
    description="Cria uma sala de compartilhamento de tela"
)
async def criar_sala(
    interaction: discord.Interaction
):
    # Responde ao Discord imediatamente
    await interaction.response.defer()

    try:
        timeout = aiohttp.ClientTimeout(
            total=15
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            url = f"{BASE_URL}/criar-sala"

            print(
                "Chamando:",
                url
            )

            async with session.post(
                url
            ) as resposta:

                print(
                    "STATUS VERCEL:",
                    resposta.status
                )

                texto = await resposta.text()

                print(
                    "RESPOSTA VERCEL:",
                    texto
                )

                if resposta.status != 200:

                    await interaction.followup.send(
                        f"❌ Não foi possível criar a sala. "
                        f"Status: {resposta.status}"
                    )

                    return

                try:
                    dados = await resposta.json()

                except Exception:
                    await interaction.followup.send(
                        "❌ A Vercel respondeu, "
                        "mas a resposta não veio em JSON."
                    )

                    return

                codigo = dados.get(
                    "codigo"
                )

                if not codigo:

                    await interaction.followup.send(
                        "❌ A sala não retornou um código válido."
                    )

                    return

                link = (
                    f"{BASE_URL}/sala/{codigo}"
                )

                mensagem = (
                    "🎥 **Sala criada!**\n\n"
                    f"**Código:** `{codigo}`\n\n"
                    f"**Entrar na sala:**\n"
                    f"{link}\n\n"
                    "Qualquer pessoa com o link "
                    "pode entrar, assistir ou transmitir."
                )

                await interaction.followup.send(
                    mensagem
                )


    except aiohttp.ClientError as erro:

        print(
            "ERRO HTTP:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Não consegui conectar "
            "ao Screen Share."
        )


    except Exception as erro:

        print(
            "ERRO CRIAR SALA:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Ocorreu um erro ao criar a sala."
        )


if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN não encontrado no arquivo .env"
    )


bot.run(TOKEN)