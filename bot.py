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

# TROQUE pela URL do seu Render
BASE_URL = "https://SEU-PROJETO.onrender.com"


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

    # Responde ao Discord imediatamente
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
                        f"❌ Não foi possível criar a sala.\n"
                        f"Status: {resposta.status}"
                    )

                    return


                # ======================================
                # JSON
                # ======================================

                try:

                    dados = await resposta.json()

                except Exception as erro:

                    print(
                        "Erro lendo JSON:",
                        repr(erro)
                    )

                    await interaction.followup.send(
                        "❌ O servidor respondeu, "
                        "mas a resposta não veio em JSON."
                    )

                    return


                # ======================================
                # CÓDIGO DA SALA
                # ======================================

                codigo = dados.get(
                    "codigo"
                )

                if not codigo:

                    await interaction.followup.send(
                        "❌ A sala não retornou "
                        "um código válido."
                    )

                    return


                # ======================================
                # LINK
                # ======================================

                link = (
                    f"{BASE_URL}/sala/{codigo}"
                )


                # ======================================
                # MENSAGEM DISCORD
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
    # ERRO HTTP
    # ==================================================

    except aiohttp.ClientError as erro:

        print(
            "ERRO HTTP:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Não consegui conectar "
            "ao servidor do Screen Share."
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
            "❌ O servidor demorou demais "
            "para responder."
        )


    # ==================================================
    # OUTRO ERRO
    # ==================================================

    except Exception as erro:

        print(
            "ERRO CRIAR SALA:",
            repr(erro)
        )

        await interaction.followup.send(
            "❌ Ocorreu um erro ao criar a sala."
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