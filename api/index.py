import os
import uuid
import random
import string

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

from upstash_redis import Redis


# =========================================================
# APLICAÇÃO
# =========================================================

app = FastAPI()


# =========================================================
# REDIS
# =========================================================

REDIS_URL = os.getenv("gQAAAAAAArbjAAIgcDJmNjQyNDE0NTA3NmE0Nzk0ODY2N2FlYTg2MDgzNzUzYg")
REDIS_TOKEN = os.getenv("KV_REST_API_TOKEN")


if not REDIS_URL or not REDIS_TOKEN:
    print(
        "AVISO: KV_REST_API_URL ou "
        "KV_REST_API_TOKEN não encontrados."
    )

    redis = None

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
# usuário é considerado ativo por até 2 minutos


# =========================================================
# SOCKETS LOCAIS
# =========================================================
#
# IMPORTANTE:
#
# O WebSocket não pode ser salvo no Redis.
#
# Aqui ficam somente os WebSockets conectados
# à instância atual.
#
# Estrutura:
#
# sockets_locais[codigo][usuario_id] = websocket
#
# =========================================================

sockets_locais = {}


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def gerar_codigo_sala(tamanho=6):

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


def chave_sala(codigo):

    return f"sala:{codigo}"


def chave_usuarios(codigo):

    return f"sala:{codigo}:usuarios"


def chave_transmissoes(codigo):

    return f"sala:{codigo}:transmissoes"


def chave_usuario_ativo(
    codigo,
    usuario_id,
):

    return (
        f"sala:{codigo}:ativo:"
        f"{usuario_id}"
    )


def redis_disponivel():

    return redis is not None


def sala_existe(codigo):

    if not redis_disponivel():
        return False

    return bool(
        redis.exists(
            chave_sala(codigo)
        )
    )


def renovar_sala(codigo):

    if not redis_disponivel():
        return

    redis.expire(
        chave_sala(codigo),
        TEMPO_SALA,
    )

    redis.expire(
        chave_usuarios(codigo),
        TEMPO_SALA,
    )

    redis.expire(
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
                    "Redis não configurado."
            },
            status_code=500,
        )

    codigo = gerar_codigo_sala()

    while sala_existe(codigo):

        codigo = gerar_codigo_sala()

    redis.set(
        chave_sala(codigo),
        "1",
        ex=TEMPO_SALA,
    )

    print(
        f"Sala criada no Redis: {codigo}"
    )

    return JSONResponse(
        {
            "codigo": codigo,
            "url": f"/sala/{codigo}",
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
                    "Redis não configurado."
            },
            status_code=500,
        )

    if not sala_existe(codigo):

        print(
            f"Tentativa de abrir sala "
            f"inexistente: {codigo}"
        )

        # Se você ainda não criou
        # sala_inexistente.html,
        # usamos o index por enquanto.

        return FileResponse(
            "static/index.html",
            status_code=404,
        )

    renovar_sala(codigo)

    return FileResponse(
        "static/sala.html"
    )


# =========================================================
# OBTER USUÁRIOS
# =========================================================

def obter_usuarios(codigo):

    if not redis_disponivel():
        return {}

    usuarios = (
        redis.hgetall(
            chave_usuarios(codigo)
        )
        or {}
    )

    usuarios_validos = {}

    for usuario_id, nome in usuarios.items():

        ativo = redis.exists(
            chave_usuario_ativo(
                codigo,
                usuario_id,
            )
        )

        if ativo:

            usuarios_validos[
                usuario_id
            ] = nome

        else:

            # Remove usuário fantasma

            redis.hdel(
                chave_usuarios(codigo),
                usuario_id,
            )

            redis.hdel(
                chave_transmissoes(
                    codigo
                ),
                usuario_id,
            )

    return usuarios_validos


# =========================================================
# OBTER TRANSMISSÕES
# =========================================================

def obter_transmissoes(codigo):

    if not redis_disponivel():
        return {}

    return (
        redis.hgetall(
            chave_transmissoes(codigo)
        )
        or {}
    )


# =========================================================
# MONTAR ESTADO
# =========================================================

def montar_estado(codigo):

    usuarios = obter_usuarios(
        codigo
    )

    transmissoes = obter_transmissoes(
        codigo
    )

    lista_usuarios = []

    for usuario_id, nome in usuarios.items():

        lista_usuarios.append(
            {
                "id": usuario_id,
                "nome": nome,
            }
        )

    lista_transmissoes = []

    for usuario_id in transmissoes:

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
        "usuarios": lista_usuarios,
        "transmissoes":
            lista_transmissoes,
    }


# =========================================================
# ENVIAR ESTADO
# =========================================================

async def enviar_estado_sala(
    codigo
):

    estado = montar_estado(
        codigo
    )

    conexoes = (
        sockets_locais.get(
            codigo,
            {}
        )
    )

    sockets_mortos = []

    for usuario_id, websocket in list(
        conexoes.items()
    ):

        try:

            await websocket.send_json(
                estado
            )

        except Exception as erro:

            print(
                "Erro ao enviar estado "
                f"para {usuario_id}:",
                repr(erro),
            )

            sockets_mortos.append(
                usuario_id
            )

    for usuario_id in sockets_mortos:

        conexoes.pop(
            usuario_id,
            None,
        )


# =========================================================
# ENVIAR PARA USUÁRIO LOCAL
# =========================================================

async def enviar_para_usuario(
    codigo,
    usuario_id,
    mensagem,
):

    websocket = (
        sockets_locais
        .get(codigo, {})
        .get(usuario_id)
    )

    if websocket is None:

        print(
            "Usuário não está nesta "
            "instância:",
            usuario_id,
        )

        return False

    try:

        await websocket.send_json(
            mensagem
        )

        return True

    except Exception as erro:

        print(
            "Erro ao enviar mensagem:",
            repr(erro),
        )

        return False


# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket("/ws/{codigo}")
async def websocket_sala(
    websocket: WebSocket,
    codigo: str,
):

    codigo = codigo.upper()

    # -----------------------------------------------------
    # VALIDA SALA
    # -----------------------------------------------------

    if not redis_disponivel():

        await websocket.close(
            code=1011
        )

        return

    if not sala_existe(codigo):

        await websocket.close(
            code=1008
        )

        return

    # -----------------------------------------------------
    # ACEITA CONEXÃO
    # -----------------------------------------------------

    await websocket.accept()

    usuario_id = str(
        uuid.uuid4()
    )

    nome = "Usuário"

    # -----------------------------------------------------
    # REGISTRA SOCKET LOCAL
    # -----------------------------------------------------

    if codigo not in sockets_locais:

        sockets_locais[codigo] = {}

    sockets_locais[codigo][
        usuario_id
    ] = websocket

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
        # SALVA USUÁRIO NO REDIS
        # =================================================

        redis.hset(
            chave_usuarios(codigo),
            values={
                usuario_id: nome
            },
        )

        # Marca usuário como ativo

        redis.set(
            chave_usuario_ativo(
                codigo,
                usuario_id,
            ),
            "1",
            ex=TEMPO_USUARIO,
        )

        renovar_sala(codigo)

        # =================================================
        # ENVIA ID
        # =================================================

        await websocket.send_json(
            {
                "tipo": "meu_id",
                "id": usuario_id,
            }
        )

        print(
            f"{nome} entrou "
            f"na sala {codigo}"
        )

        usuarios = obter_usuarios(
            codigo
        )

        print(
            "Usuários no Redis:",
            len(usuarios),
        )

        await enviar_estado_sala(
            codigo
        )

        # =================================================
        # LOOP
        # =================================================

        while True:

            mensagem = (
                await websocket.receive_json()
            )

            # Renova presença do usuário

            redis.set(
                chave_usuario_ativo(
                    codigo,
                    usuario_id,
                ),
                "1",
                ex=TEMPO_USUARIO,
            )

            renovar_sala(codigo)

            tipo = mensagem.get(
                "tipo"
            )

            print(
                f"{nome} enviou evento: "
                f"{tipo}"
            )

            # =================================================
            # HEARTBEAT
            # =================================================

            if tipo == "ping":

                await websocket.send_json(
                    {
                        "tipo": "pong"
                    }
                )

            # =================================================
            # INICIAR TRANSMISSÃO
            # =================================================

            elif tipo == (
                "iniciar_transmissao"
            ):

                redis.hset(
                    chave_transmissoes(
                        codigo
                    ),
                    values={
                        usuario_id: "1"
                    },
                )

                renovar_sala(codigo)

                print(
                    f"{nome} iniciou "
                    "transmissão"
                )

                await enviar_estado_sala(
                    codigo
                )

            # =================================================
            # PARAR TRANSMISSÃO
            # =================================================

            elif tipo == (
                "parar_transmissao"
            ):

                redis.hdel(
                    chave_transmissoes(
                        codigo
                    ),
                    usuario_id,
                )

                print(
                    f"{nome} encerrou "
                    "transmissão"
                )

                await enviar_estado_sala(
                    codigo
                )

            # =================================================
            # ASSISTIR
            # =================================================

            elif tipo == "assistir":

                transmissor_id = (
                    mensagem.get(
                        "transmissor_id"
                    )
                )

                print(
                    f"{nome} quer assistir "
                    f"{transmissor_id}"
                )

                usuarios = obter_usuarios(
                    codigo
                )

                if (
                    transmissor_id
                    not in usuarios
                ):

                    print(
                        "Transmissor não "
                        "encontrado no Redis."
                    )

                    await websocket.send_json(
                        {
                            "tipo": "erro",
                            "mensagem":
                                "Transmissor "
                                "não encontrado.",
                        }
                    )

                    continue

                enviado = (
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
                )

                if enviado:

                    print(
                        "Pedido enviado "
                        "ao transmissor."
                    )

                else:

                    print(
                        "Transmissor existe "
                        "no Redis, mas está "
                        "em outra instância."
                    )

            # =================================================
            # WEBRTC
            #
            # OFFER / ANSWER / ICE
            # =================================================

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
                    f"{nome} enviou "
                    f"{tipo} para "
                    f"{destino}"
                )

                enviado = (
                    await enviar_para_usuario(
                        codigo,
                        destino,
                        mensagem,
                    )
                )

                if enviado:

                    print(
                        f"{tipo} "
                        "encaminhado."
                    )

                else:

                    print(
                        f"{tipo}: usuário "
                        "está possivelmente "
                        "em outra instância."
                    )

            # =================================================
            # EVENTO DESCONHECIDO
            # =================================================

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
            f"{nome} desconectou "
            f"da sala {codigo}"
        )

    except Exception as erro:

        print(
            "ERRO NO WEBSOCKET:",
            repr(erro),
        )

    # =====================================================
    # LIMPEZA
    # =====================================================

    finally:

        # Remove socket local

        if codigo in sockets_locais:

            sockets_locais[
                codigo
            ].pop(
                usuario_id,
                None,
            )

            if not sockets_locais[
                codigo
            ]:

                sockets_locais.pop(
                    codigo,
                    None,
                )

        # Remove usuário do Redis

        if redis_disponivel():

            try:

                redis.hdel(
                    chave_usuarios(
                        codigo
                    ),
                    usuario_id,
                )

                redis.hdel(
                    chave_transmissoes(
                        codigo
                    ),
                    usuario_id,
                )

                redis.delete(
                    chave_usuario_ativo(
                        codigo,
                        usuario_id,
                    )
                )

            except Exception as erro:

                print(
                    "Erro ao limpar Redis:",
                    repr(erro),
                )

        print(
            f"{nome} removido "
            f"da sala {codigo}"
        )

        try:

            await enviar_estado_sala(
                codigo
            )

        except Exception as erro:

            print(
                "Erro ao atualizar "
                "estado final:",
                repr(erro),
            )


# =========================================================
# ARQUIVOS ESTÁTICOS
# =========================================================

app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static",
)