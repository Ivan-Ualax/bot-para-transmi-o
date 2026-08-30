import os

import aiohttp
import discord

from discord.ext import commands
from dotenv import load_dotenv


# ======================================================
# VARIÁVEIS DE AMBIENTE
# ======================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


# ======================================================
# BACKEND VERCEL
# ======================================================

BASE_URL = "https://bot-para-transmi-o.vercel.app"


# ======================================================
# BOT
# ======================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ======================================================
# BOT ONLINE
# ======================================================

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


# ======================================================
# COMANDO /criar-sala
# ======================================================

@bot.tree.command(
    name="criar-sala",
    description="Cria uma sala de compartilhamento de tela"
)
async def criar_sala(
    interaction: discord.Interaction
):

    # Responde imediatamente ao Discord
    await interaction.response.defer()

    try:

        timeout = aiohttp.ClientTimeout(
            total=30
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            url = f"{BASE_URL}/criar-sala"

            print("==============================")
            print("CRIANDO SALA")
            print("URL:", url)
            print("==============================")


            # ==================================================
            # CRIAR SALA
            # ==================================================

            async with session.post(
                url
            ) as resposta:

                texto = await resposta.text()

                print(
                    "STATUS VERCEL:",
                    resposta.status
                )

                print(
                    "RESPOSTA VERCEL:",
                    texto
                )


                # ==================================================
                # ERRO HTTP
                # ==================================================

                if resposta.status != 200:

                    await interaction.followup.send(
                        "❌ Não foi possível criar a sala.\n\n"
                        f"Status: `{resposta.status}`"
                    )

                    return


                # ==================================================
                # CONVERTER PARA JSON
                # ==================================================

                try:

                    dados = await resposta.json()

                except Exception as erro:

                    print(
                        "ERRO JSON:",
                        repr(erro)
                    )

                    print(
                        "RESPOSTA BRUTA:",
                        texto
                    )

                    await interaction.followup.send(
                        "❌ A Vercel respondeu, "
                        "mas não retornou um JSON válido."
                    )

                    return


                # ==================================================
                # PEGAR CÓDIGO
                # ==================================================

                codigo = dados.get(
                    "codigo"
                )


                if not codigo:

                    print(
                        "ERRO: código não encontrado."
                    )

                    print(
                        "JSON recebido:",
                        dados
                    )

                    await interaction.followup.send(
                        "❌ O servidor não retornou "
                        "um código de sala válido."
                    )

                    return


                print(
                    "CÓDIGO DA SALA:",
                    codigo
                )


                # ==================================================
                # CRIAR LINK
                # ==================================================

                link = (
                    f"{BASE_URL}/sala/{codigo}"
                )


                print(
                    "LINK:",
                    link
                )


                # ==================================================
                # MENSAGEM DISCORD
                # ==================================================

                mensagem = (
                    "🎥 **Sala criada!**\n\n"
                    f"**Código:** `{codigo}`\n\n"
                    "**Entrar na sala:**\n"
                    f"{link}\n\n"
                    "Qualquer pessoa com o link "
                    "pode entrar, assistir ou transmitir."
                )


                await interaction.followup.send(
                    mensagem
                )


                print(
                    "Sala enviada para o Discord."
                )


    # ======================================================
    # ERRO DE CONEXÃO
    # ======================================================

    except aiohttp.ClientConnectorError as erro:

        print(
            "ERRO DE CONEXÃO:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Não consegui conectar "
            "ao servidor da transmissão."
        )


    # ======================================================
    # TIMEOUT
    # ======================================================

    except TimeoutError as erro:

        print(
            "TIMEOUT:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ O servidor demorou demais "
            "para responder."
        )


    # ======================================================
    # ERRO AIOHTTP
    # ======================================================

    except aiohttp.ClientError as erro:

        print(
            "ERRO HTTP:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Ocorreu um erro de comunicação "
            "com a Vercel."
        )


    # ======================================================
    # ERRO GERAL
    # ======================================================

    except Exception as erro:

        print(
            "ERRO CRIAR SALA:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Ocorreu um erro inesperado "
            "ao criar a sala."
        )


# ======================================================
# VERIFICAR TOKEN
# ======================================================

if not TOKEN:

    raise ValueError(
        "DISCORD_TOKEN não encontrado no arquivo .env"
    )


# ======================================================
# INICIAR BOT
# ======================================================

bot.run(TOKEN)