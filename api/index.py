import os
import uuid
import random
import string
import asyncio
from contextlib import suppress

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

from fastapi.staticfiles import StaticFiles

from fastapi.responses import (
    FileResponse,
    JSONResponse,
)

from upstash_redis.asyncio import Redis


# =========================================================
# APP
# =========================================================

app = FastAPI()


# =========================================================
# REDIS
# =========================================================

REDIS_URL = os.getenv(
    "KV_REST_API_URL"
)

REDIS_TOKEN = os.getenv(
    "KV_REST_API_TOKEN"
)


if not REDIS_URL or not REDIS_TOKEN:

    redis = None

    print(
        "ERRO: Redis não configurado."
    )

else:

    redis = Redis(
        url=REDIS_URL,
        token=REDIS_TOKEN,
    )


# =========================================================
# CONFIGURAÇÕES
# =========================================================

TEMPO_SALA = 21600
# 6 horas

TEMPO_USUARIO = 120
# 2 minutos

TEMPO_FILA = 300
# mensagens de sinalização:
# 5 minutos


# =========================================================
# CHAVES REDIS
# =========================================================

def chave_sala(codigo):

    return f"sala:{codigo}"


def chave_usuarios(codigo):

    return (
        f"sala:{codigo}:usuarios"
    )


def chave_transmissoes(codigo):

    return (
        f"sala:{codigo}:transmissoes"
    )


def chave_ativo(
    codigo,
    usuario_id,
):

    return (
        f"sala:{codigo}:ativo:"
        f"{usuario_id}"
    )


def chave_fila(
    codigo,
    usuario_id,
):

    return (
        f"sala:{codigo}:fila:"
        f"{usuario_id}"
    )


# =========================================================
# GERAR CÓDIGO
# =========================================================

def gerar_codigo_sala(
    tamanho=6
):

    caracteres = (
        string.ascii_uppercase
        + string.digits
    )

    return "".join(
        random.choices(
            caracteres,
            k=tamanho,
        )
    )


# =========================================================
# REDIS DISPONÍVEL
# =========================================================

def redis_disponivel():

    return redis is not None


# =========================================================
# SALA EXISTE
# =========================================================

async def sala_existe(codigo):

    if not redis_disponivel():

        return False

    resultado = await redis.exists(
        chave_sala(codigo)
    )

    return bool(resultado)


# =========================================================
# RENOVAR SALA
# =========================================================

async def renovar_sala(codigo):

    if not redis_disponivel():

        return

    await redis.expire(
        chave_sala(codigo),
        TEMPO_SALA,
    )

    await redis.expire(
        chave_usuarios(codigo),
        TEMPO_SALA,
    )

    await redis.expire(
        chave_transmissoes(codigo),
        TEMPO_SALA,
    )


# =========================================================
# HOME
# =========================================================

@app.get("/")
async def home():

    return FileResponse(
        "static/index.html"
    )


# =========================================================
# CRIAR SALA
# =========================================================

@app.post("/criar-sala")
async def criar_sala():

    if not redis_disponivel():

        return JSONResponse(
            {
                "erro":
                    "Redis indisponível"
            },
            status_code=500,
        )

    codigo = gerar_codigo_sala()

    while await sala_existe(
        codigo
    ):

        codigo = gerar_codigo_sala()

    await redis.set(
        chave_sala(codigo),
        "1",
        ex=TEMPO_SALA,
    )

    print(
        f"SALA CRIADA: {codigo}"
    )

    return JSONResponse(
        {
            "codigo": codigo,

            "url":
                f"/sala/{codigo}",
        }
    )


# =========================================================
# ABRIR SALA
# =========================================================

@app.get("/sala/{codigo}")
async def abrir_sala(
    codigo: str
):

    codigo = codigo.upper()

    if not redis_disponivel():

        return JSONResponse(
            {
                "erro":
                    "Redis indisponível"
            },
            status_code=500,
        )

    if not await sala_existe(
        codigo
    ):

        return FileResponse(
            "static/index.html",
            status_code=404,
        )

    await renovar_sala(
        codigo
    )

    return FileResponse(
        "static/sala.html"
    )


# =========================================================
# USUÁRIOS ATIVOS
# =========================================================

async def obter_usuarios(
    codigo
):

    usuarios = (
        await redis.hgetall(
            chave_usuarios(codigo)
        )
        or {}
    )

    ativos = {}

    for (
        usuario_id,
        nome
    ) in usuarios.items():

        existe = await redis.exists(
            chave_ativo(
                codigo,
                usuario_id,
            )
        )

        if existe:

            ativos[
                usuario_id
            ] = nome

        else:

            await redis.hdel(
                chave_usuarios(codigo),
                usuario_id,
            )

            await redis.hdel(
                chave_transmissoes(
                    codigo
                ),
                usuario_id,
            )

    return ativos


# =========================================================
# TRANSMISSÕES
# =========================================================

async def obter_transmissoes(
    codigo
):

    return (
        await redis.hgetall(
            chave_transmissoes(
                codigo
            )
        )
        or {}
    )


# =========================================================
# ESTADO DA SALA
# =========================================================

async def montar_estado(
    codigo
):

    usuarios = (
        await obter_usuarios(
            codigo
        )
    )

    transmissoes = (
        await obter_transmissoes(
            codigo
        )
    )

    lista_usuarios = []

    for (
        usuario_id,
        nome
    ) in usuarios.items():

        lista_usuarios.append(
            {
                "id": usuario_id,
                "nome": nome,
            }
        )

    lista_transmissoes = []

    for usuario_id in (
        transmissoes.keys()
    ):

        if usuario_id in usuarios:

            lista_transmissoes.append(
                {
                    "usuario_id":
                        usuario_id,

                    "nome":
                        usuarios[
                            usuario_id
                        ],
                }
            )

    return {
        "tipo": "estado",

        "usuarios":
            lista_usuarios,

        "transmissoes":
            lista_transmissoes,
    }


# =========================================================
# COLOCAR MENSAGEM NA FILA
# =========================================================

async def enviar_para_usuario(
    codigo,
    usuario_id,
    mensagem,
):

    import json

    fila = chave_fila(
        codigo,
        usuario_id,
    )

    await redis.rpush(
        fila,
        json.dumps(
            mensagem
        ),
    )

    await redis.expire(
        fila,
        TEMPO_FILA,
    )


# =========================================================
# BROADCAST
# =========================================================

async def broadcast_estado(
    codigo
):

    estado = await montar_estado(
        codigo
    )

    usuarios = (
        await obter_usuarios(
            codigo
        )
    )

    for usuario_id in (
        usuarios.keys()
    ):

        await enviar_para_usuario(
            codigo,
            usuario_id,
            estado,
        )


# =========================================================
# ENTREGADOR DE FILA
# =========================================================

async def entregar_fila(
    websocket,
    codigo,
    usuario_id,
):

    import json

    fila = chave_fila(
        codigo,
        usuario_id,
    )

    while True:

        try:

            mensagem = (
                await redis.lpop(
                    fila
                )
            )

            if mensagem:

                if isinstance(
                    mensagem,
                    bytes,
                ):

                    mensagem = (
                        mensagem.decode(
                            "utf-8"
                        )
                    )

                dados = json.loads(
                    mensagem
                )

                await websocket.send_json(
                    dados
                )

            else:

                # Pequeno polling para
                # atravessar instâncias
                # diferentes da Vercel.

                await asyncio.sleep(
                    0.35
                )

        except asyncio.CancelledError:

            raise

        except Exception as erro:

            print(
                "ERRO FILA:",
                repr(erro),
            )

            await asyncio.sleep(
                1
            )


# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket("/ws/{codigo}")
async def websocket_sala(
    websocket: WebSocket,
    codigo: str,
):

    codigo = codigo.upper()

    # =====================================================
    # VALIDAR
    # =====================================================

    if not redis_disponivel():

        await websocket.close(
            code=1011
        )

        return

    if not await sala_existe(
        codigo
    ):

        await websocket.close(
            code=1008
        )

        return


    # =====================================================
    # CONECTAR
    # =====================================================

    await websocket.accept()

    usuario_id = str(
        uuid.uuid4()
    )

    nome = "Usuário"

    tarefa_fila = None


    try:

        # =================================================
        # PRIMEIRA MENSAGEM
        # =================================================

        primeira_mensagem = (
            await websocket.receive_json()
        )

        nome = (
            primeira_mensagem
            .get("nome", "")
            .strip()
        )

        if not nome:

            await websocket.send_json(
                {
                    "tipo": "erro",

                    "mensagem":
                        "Nome obrigatório.",
                }
            )

            await websocket.close()

            return


        # =================================================
        # REGISTRAR USUÁRIO
        # =================================================

        await redis.hset(
            chave_usuarios(
                codigo
            ),
            values={
                usuario_id: nome
            },
        )

        await redis.set(
            chave_ativo(
                codigo,
                usuario_id,
            ),
            "1",
            ex=TEMPO_USUARIO,
        )

        await renovar_sala(
            codigo
        )


        # =================================================
        # ENVIA ID DIRETAMENTE
        # =================================================

        await websocket.send_json(
            {
                "tipo":
                    "meu_id",

                "id":
                    usuario_id,
            }
        )


        # =================================================
        # INICIAR ENTREGADOR
        # =================================================

        tarefa_fila = (
            asyncio.create_task(
                entregar_fila(
                    websocket,
                    codigo,
                    usuario_id,
                )
            )
        )


        print(
            f"{nome} entrou "
            f"na sala {codigo}"
        )


        # =================================================
        # ATUALIZA TODOS
        # =================================================

        await broadcast_estado(
            codigo
        )


        # =================================================
        # LOOP
        # =================================================

        while True:

            mensagem = (
                await websocket
                .receive_json()
            )

            # =============================================
            # RENOVAR PRESENÇA
            # =============================================

            await redis.set(
                chave_ativo(
                    codigo,
                    usuario_id,
                ),
                "1",
                ex=TEMPO_USUARIO,
            )

            await renovar_sala(
                codigo
            )

            tipo = mensagem.get(
                "tipo"
            )


            print(
                f"{nome}: {tipo}"
            )


            # =============================================
            # PING
            # =============================================

            if tipo == "ping":

                await enviar_para_usuario(
                    codigo,
                    usuario_id,
                    {
                        "tipo": "pong"
                    },
                )


            # =============================================
            # INICIAR TRANSMISSÃO
            # =============================================

            elif (
                tipo
                == "iniciar_transmissao"
            ):

                await redis.hset(
                    chave_transmissoes(
                        codigo
                    ),
                    values={
                        usuario_id:
                            "1"
                    },
                )

                print(
                    f"{nome} iniciou "
                    "transmissão"
                )

                await broadcast_estado(
                    codigo
                )


            # =============================================
            # PARAR TRANSMISSÃO
            # =============================================

            elif (
                tipo
                == "parar_transmissao"
            ):

                await redis.hdel(
                    chave_transmissoes(
                        codigo
                    ),
                    usuario_id,
                )

                await broadcast_estado(
                    codigo
                )


            # =============================================
            # ASSISTIR
            # =============================================

            elif tipo == "assistir":

                transmissor_id = (
                    mensagem.get(
                        "transmissor_id"
                    )
                )

                usuarios = (
                    await obter_usuarios(
                        codigo
                    )
                )

                if (
                    transmissor_id
                    not in usuarios
                ):

                    await enviar_para_usuario(
                        codigo,
                        usuario_id,
                        {
                            "tipo":
                                "erro",

                            "mensagem":
                                "Transmissor "
                                "não encontrado.",
                        },
                    )

                    continue


                print(
                    f"{nome} quer assistir "
                    f"{transmissor_id}"
                )


                # AQUI está a principal
                # diferença:
                #
                # não precisamos mais
                # que o transmissor esteja
                # nesta mesma Function.

                await enviar_para_usuario(
                    codigo,
                    transmissor_id,
                    {
                        "tipo":
                            "novo_espectador",

                        "espectador_id":
                            usuario_id,
                    },
                )


            # =============================================
            # OFFER / ANSWER / ICE
            # =============================================

            elif tipo in [
                "offer",
                "answer",
                "ice",
            ]:

                destino = (
                    mensagem.get(
                        "destino"
                    )
                )

                if not destino:

                    continue


                mensagem[
                    "origem"
                ] = usuario_id


                print(
                    f"{tipo}: "
                    f"{usuario_id} "
                    f"→ {destino}"
                )


                # Também atravessa
                # diferentes instâncias.

                await enviar_para_usuario(
                    codigo,
                    destino,
                    mensagem,
                )


            # =============================================
            # EVENTO DESCONHECIDO
            # =============================================

            else:

                print(
                    "Evento desconhecido:",
                    tipo,
                )


    # =====================================================
    # DESCONECTOU
    # =====================================================

    except WebSocketDisconnect:

        print(
            f"{nome} desconectou"
        )


    except Exception as erro:

        print(
            "ERRO WEBSOCKET:",
            repr(erro),
        )


    # =====================================================
    # FINALMENTE
    # =====================================================

    finally:

        # =================================================
        # CANCELAR ENTREGADOR
        # =================================================

        if tarefa_fila:

            tarefa_fila.cancel()

            with suppress(
                asyncio.CancelledError
            ):

                await tarefa_fila


        # =================================================
        # LIMPAR REDIS
        # =================================================

        if redis_disponivel():

            try:

                await redis.hdel(
                    chave_usuarios(
                        codigo
                    ),
                    usuario_id,
                )

                await redis.hdel(
                    chave_transmissoes(
                        codigo
                    ),
                    usuario_id,
                )

                await redis.delete(
                    chave_ativo(
                        codigo,
                        usuario_id,
                    )
                )

                await redis.delete(
                    chave_fila(
                        codigo,
                        usuario_id,
                    )
                )

                await broadcast_estado(
                    codigo
                )

            except Exception as erro:

                print(
                    "ERRO LIMPEZA:",
                    repr(erro),
                )


# =========================================================
# STATIC
# =========================================================

app.mount(
    "/static",

    StaticFiles(
        directory="static"
    ),

    name="static",
)