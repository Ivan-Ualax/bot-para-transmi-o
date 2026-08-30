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
# URL DO RENDER
# ======================================================
#
# TROQUE A LINHA ABAIXO PELA URL REAL DO SEU SERVIÇO.
#
# Exemplo:
# BASE_URL = "https://screen-share-abc123.onrender.com"
#

BASE_URL = "https://bot-para-transmi-o.vercel.app/"


# ======================================================
# BOT
# ======================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ======================================================
# QUANDO O BOT FICAR ONLINE
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

    await interaction.response.defer()

    try:

        timeout = aiohttp.ClientTimeout(
            total=30
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            url = f"{BASE_URL}/criar-sala"

            print(
                "Chamando:",
                url
            )


            # ==========================================
            # CRIAR SALA NO BACKEND
            # ==========================================

            async with session.post(
                url
            ) as resposta:

                print(
                    "STATUS RENDER:",
                    resposta.status
                )

                texto = await resposta.text()

                print(
                    "RESPOSTA RENDER:",
                    texto
                )


                # ======================================
                # ERRO HTTP
                # ======================================

                if resposta.status != 200:

                    await interaction.followup.send(
                        "❌ Não foi possível criar a sala.\n"
                        f"Status: {resposta.status}\n"
                        f"URL: {url}"
                    )

                    return


                # ======================================
                # LER JSON
                # ======================================

                try:

                    dados = await resposta.json()

                except Exception as erro:

                    print(
                        "ERRO JSON:",
                        repr(erro)
                    )

                    await interaction.followup.send(
                        "❌ O servidor respondeu, "
                        "mas não retornou JSON válido."
                    )

                    return


                # ======================================
                # PEGAR CÓDIGO
                # ======================================

                codigo = dados.get(
                    "codigo"
                )

                if not codigo:

                    print(
                        "Resposta recebida sem código:",
                        dados
                    )

                    await interaction.followup.send(
                        "❌ O servidor não retornou "
                        "o código da sala."
                    )

                    return


                # ======================================
                # CRIAR LINK DA SALA
                # ======================================

                link = (
                    f"{BASE_URL}/sala/{codigo}"
                )


                # ======================================
                # MENSAGEM
                # ======================================

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


    # ==================================================
    # ERROS HTTP
    # ==================================================

    except aiohttp.ClientConnectorError as erro:

        print(
            "ERRO DE CONEXÃO:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Não foi possível conectar "
            "ao servidor do Render."
        )


    except aiohttp.ClientResponseError as erro:

        print(
            "ERRO DE RESPOSTA:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ O Render retornou um erro."
        )


    except aiohttp.ClientError as erro:

        print(
            "ERRO HTTP:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Erro de comunicação "
            "com o servidor."
        )


    # ==================================================
    # TIMEOUT
    # ==================================================

    except TimeoutError as erro:

        print(
            "TIMEOUT:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ O servidor demorou "
            "demais para responder."
        )


    # ==================================================
    # ERRO GERAL
    # ==================================================

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
# VALIDAR TOKEN
# ======================================================

if not TOKEN:

    raise ValueError(
        "DISCORD_TOKEN não encontrado no arquivo .env"
    )


# ======================================================
# INICIAR BOT
# ======================================================

bot.run(TOKEN)