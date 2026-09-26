import os
import uuid
import random
import string
import json
import asyncio
import requests

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from upstash_redis.asyncio import Redis


app = FastAPI()


# ======================================================
# CONFIGURAÇÃO REDIS / UPSTASH
# ======================================================

REDIS_URL = os.environ.get("UPSTASH_KV_REST_API_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_KV_REST_API_TOKEN")

if not REDIS_URL or not REDIS_TOKEN:
    print("ERRO: variáveis do Upstash Redis não configuradas.")

redis = Redis(
    url=REDIS_URL,
    token=REDIS_TOKEN
)


# ======================================================
# CONFIGURAÇÕES
# ======================================================

# Sala vazia desaparece após 10 minutos.
TEMPO_EXPIRACAO_SALA = 10 * 60

# Presença de cada usuário.
# O navegador manda ping periodicamente.
TEMPO_PRESENCA_USUARIO = 90

# WebSockets continuam sendo objetos locais.
# O Redis faz a ponte entre instâncias.
sockets_locais = {}


# ======================================================
# CHAVES REDIS
# ======================================================

def chave_sala(codigo):
    return f"sala:{codigo}"


def chave_usuarios(codigo):
    return f"sala:{codigo}:usuarios"


def chave_transmissoes(codigo):
    return f"sala:{codigo}:transmissoes"


def chave_presenca(codigo, usuario_id):
    return f"sala:{codigo}:presenca:{usuario_id}"


def chave_fila(usuario_id):
    return f"ws:fila:{usuario_id}"


def chave_versao(codigo):
    return f"sala:{codigo}:versao"


# ======================================================
# CLOUDFLARE TURN
# ======================================================

@app.get("/api/turn-credentials")
async def turn_credentials():

    turn_key_id = os.environ.get(
        "CLOUDFLARE_TURN_KEY_ID"
    )

    turn_api_token = os.environ.get(
        "CLOUDFLARE_TURN_API_TOKEN"
    )

    if not turn_key_id or not turn_api_token:

        print(
            "ERRO: variáveis Cloudflare TURN "
            "não configuradas."
        )

        return JSONResponse(
            status_code=500,
            content={
                "erro":
                    "Credenciais Cloudflare TURN "
                    "não configuradas."
            }
        )

    url = (
        "https://rtc.live.cloudflare.com/"
        "v1/turn/keys/"
        f"{turn_key_id}/"
        "credentials/generate-ice-servers"
    )

    headers = {
        "Authorization":
            f"Bearer {turn_api_token}",

        "Content-Type":
            "application/json",

        "Accept":
            "application/json",

        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 "
                "Safari/537.36"
            )
    }

    payload = {
        "ttl": 86400
    }

    try:

        print(
            "Solicitando credenciais TURN "
            "à Cloudflare..."
        )

        resposta = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        print(
            "Cloudflare status:",
            resposta.status_code
        )

        if not resposta.ok:

            print(
                "Cloudflare TURN recusou:",
                resposta.text
            )

            return JSONResponse(
                status_code=502,
                content={
                    "erro":
                        "Cloudflare recusou "
                        "a geração TURN.",

                    "status":
                        resposta.status_code,

                    "detalhe":
                        resposta.text
                }
            )

        try:

            dados = resposta.json()

        except ValueError as erro:

            print(
                "Resposta Cloudflare não é JSON:",
                repr(erro)
            )

            return JSONResponse(
                status_code=502,
                content={
                    "erro":
                        "Resposta inválida "
                        "da Cloudflare TURN."
                }
            )

        ice_servers = dados.get(
            "iceServers"
        )

        if (
            not isinstance(ice_servers, list)
            or
            len(ice_servers) == 0
        ):

            print(
                "Cloudflare respondeu "
                "sem iceServers:",
                dados
            )

            return JSONResponse(
                status_code=502,
                content={
                    "erro":
                        "Cloudflare não retornou "
                        "iceServers válidos."
                }
            )

        print(
            "Cloudflare TURN OK."
        )

        return JSONResponse(
            content=dados
        )

    except requests.Timeout:

        return JSONResponse(
            status_code=504,
            content={
                "erro":
                    "Timeout ao acessar "
                    "Cloudflare TURN."
            }
        )

    except requests.ConnectionError as erro:

        print(
            "Erro de conexão Cloudflare:",
            repr(erro)
        )

        return JSONResponse(
            status_code=502,
            content={
                "erro":
                    "Falha de conexão com "
                    "Cloudflare TURN."
            }
        )

    except requests.RequestException as erro:

        print(
            "Erro HTTP Cloudflare:",
            repr(erro)
        )

        return JSONResponse(
            status_code=502,
            content={
                "erro":
                    "Erro ao solicitar "
                    "credenciais TURN."
            }
        )

    except Exception as erro:

        print(
            "Erro inesperado Cloudflare:",
            repr(erro)
        )

        return JSONResponse(
            status_code=500,
            content={
                "erro":
                    "Erro interno ao gerar "
                    "credenciais TURN."
            }
        )


# ======================================================
# GERAR CÓDIGO
# ======================================================

def gerar_codigo_sala(tamanho=6):

    caracteres = (
        string.ascii_uppercase +
        string.digits
    )

    return "".join(
        random.choices(
            caracteres,
            k=tamanho
        )
    )


# ======================================================
# VERIFICAR SE SALA EXISTE
# ======================================================

async def sala_existe(codigo):

    existe = await redis.exists(
        chave_sala(codigo)
    )

    return bool(existe)


# ======================================================
# LIMPAR USUÁRIOS MORTOS
# ======================================================

async def limpar_usuarios_mortos(codigo):

    usuarios = await redis.hgetall(
        chave_usuarios(codigo)
    )

    if not usuarios:
        return 0

    removidos = False

    for usuario_id in list(
        usuarios.keys()
    ):

        presente = await redis.exists(
            chave_presenca(
                codigo,
                usuario_id
            )
        )

        if not presente:

            await redis.hdel(
                chave_usuarios(codigo),
                usuario_id
            )

            await redis.srem(
                chave_transmissoes(codigo),
                usuario_id
            )

            await redis.delete(
                chave_fila(usuario_id)
            )

            removidos = True

    if removidos:

        await redis.incr(
            chave_versao(codigo)
        )

    usuarios = await redis.hgetall(
        chave_usuarios(codigo)
    )

    return len(
        usuarios or {}
    )


# ======================================================
# CONTROLAR EXPIRAÇÃO DA SALA
# ======================================================

async def atualizar_expiracao_sala(codigo):

    if not await sala_existe(codigo):
        return

    quantidade = await limpar_usuarios_mortos(
        codigo
    )

    if quantidade == 0:

        # Ninguém na sala.
        # Redis apaga automaticamente após 10 minutos.
        await redis.expire(
            chave_sala(codigo),
            TEMPO_EXPIRACAO_SALA
        )

        await redis.expire(
            chave_usuarios(codigo),
            TEMPO_EXPIRACAO_SALA
        )

        await redis.expire(
            chave_transmissoes(codigo),
            TEMPO_EXPIRACAO_SALA
        )

        await redis.expire(
            chave_versao(codigo),
            TEMPO_EXPIRACAO_SALA
        )

        print(
            f"Sala {codigo} vazia. "
            "Expira em 10 minutos."
        )

    else:

        # Tem alguém conectado.
        # Sala não pode expirar.
        await redis.persist(
            chave_sala(codigo)
        )

        await redis.persist(
            chave_usuarios(codigo)
        )

        await redis.persist(
            chave_transmissoes(codigo)
        )

        await redis.persist(
            chave_versao(codigo)
        )


# ======================================================
# HOME
# ======================================================

@app.get("/")
async def home():

    return FileResponse(
        "static/index.html"
    )


# ======================================================
# CRIAR SALA
# ======================================================

@app.post("/criar-sala")
async def criar_sala():

    while True:

        codigo = gerar_codigo_sala()

        # NX = somente cria se não existir.
        criada = await redis.set(
            chave_sala(codigo),
            "1",
            ex=TEMPO_EXPIRACAO_SALA,
            nx=True
        )

        if criada:
            break

    await redis.set(
        chave_versao(codigo),
        0,
        ex=TEMPO_EXPIRACAO_SALA
    )

    print(
        f"Sala criada no Redis: {codigo}"
    )

    return JSONResponse(
        content={
            "codigo": codigo,
            "url": f"/sala/{codigo}"
        }
    )


# ======================================================
# ABRIR SALA
# ======================================================

@app.get("/sala/{codigo}")
async def abrir_sala(
    codigo: str
):

    codigo = codigo.upper().strip()

    if not await sala_existe(
        codigo
    ):

        print(
            f"Sala inexistente: {codigo}"
        )

        return FileResponse(
            "static/sala_inexistente.html",
            status_code=404
        )

    await atualizar_expiracao_sala(
        codigo
    )

    # Pode ter expirado durante a limpeza.
    if not await sala_existe(
        codigo
    ):

        return FileResponse(
            "static/sala_inexistente.html",
            status_code=404
        )

    return FileResponse(
        "static/sala.html"
    )


# ======================================================
# GERAR ESTADO GLOBAL DA SALA
# ======================================================

async def obter_estado_sala(codigo):

    await limpar_usuarios_mortos(
        codigo
    )

    usuarios = await redis.hgetall(
        chave_usuarios(codigo)
    )

    transmissoes = await redis.smembers(
        chave_transmissoes(codigo)
    )

    usuarios = usuarios or {}
    transmissoes = transmissoes or []

    lista_usuarios = []

    for usuario_id, nome in usuarios.items():

        lista_usuarios.append({
            "id": usuario_id,
            "nome": nome
        })

    lista_transmissoes = []

    for usuario_id in transmissoes:

        if usuario_id in usuarios:

            lista_transmissoes.append({
                "usuario_id":
                    usuario_id,

                "nome":
                    usuarios[
                        usuario_id
                    ]
            })

    return {
        "tipo":
            "estado",

        "usuarios":
            lista_usuarios,

        "transmissoes":
            lista_transmissoes
    }


# ======================================================
# ENVIAR ESTADO PARA SOCKET LOCAL
# ======================================================

async def enviar_estado_socket(
    websocket,
    codigo
):

    estado = await obter_estado_sala(
        codigo
    )

    await websocket.send_json(
        estado
    )


# ======================================================
# ENVIAR MENSAGEM PARA OUTRO USUÁRIO
# ======================================================

async def enviar_para_usuario(
    usuario_id,
    mensagem
):

    # Se o usuário estiver na mesma instância,
    # envia diretamente.
    socket = sockets_locais.get(
        usuario_id
    )

    if socket:

        try:

            await socket.send_json(
                mensagem
            )

            return

        except Exception:

            sockets_locais.pop(
                usuario_id,
                None
            )

    # Se estiver em outra instância Vercel,
    # coloca a mensagem na fila Redis.
    await redis.rpush(
        chave_fila(usuario_id),
        json.dumps(mensagem)
    )

    # Evitar fila abandonada permanente.
    await redis.expire(
        chave_fila(usuario_id),
        TEMPO_PRESENCA_USUARIO
    )


# ======================================================
# PROCESSAR FILA REDIS DO USUÁRIO
# ======================================================

async def processar_fila(
    websocket,
    usuario_id
):

    while True:

        try:

            mensagem = await redis.lpop(
                chave_fila(usuario_id)
            )

            if mensagem:

                if isinstance(
                    mensagem,
                    str
                ):

                    dados = json.loads(
                        mensagem
                    )

                else:

                    dados = mensagem

                await websocket.send_json(
                    dados
                )

            else:

                await asyncio.sleep(
                    0.20
                )

        except asyncio.CancelledError:
            break

        except Exception as erro:

            print(
                "Erro processando fila:",
                repr(erro)
            )

            await asyncio.sleep(
                0.5
            )


# ======================================================
# MONITORAR ESTADO GLOBAL
# ======================================================

async def monitorar_estado(
    websocket,
    codigo
):

    ultima_versao = None

    while True:

        try:

            versao = await redis.get(
                chave_versao(codigo)
            )

            if versao != ultima_versao:

                ultima_versao = versao

                await enviar_estado_socket(
                    websocket,
                    codigo
                )

            await asyncio.sleep(
                0.5
            )

        except asyncio.CancelledError:
            break

        except Exception as erro:

            print(
                "Erro monitorando estado:",
                repr(erro)
            )

            await asyncio.sleep(
                1
            )


# ======================================================
# RENOVAR PRESENÇA
# ======================================================

async def renovar_presenca(
    codigo,
    usuario_id
):

    await redis.set(
        chave_presenca(
            codigo,
            usuario_id
        ),
        "1",
        ex=TEMPO_PRESENCA_USUARIO
    )


# ======================================================
# WEBSOCKET
# ======================================================

@app.websocket("/ws/{codigo}")
async def websocket_sala(
    websocket: WebSocket,
    codigo: str
):

    codigo = codigo.upper().strip()

    await websocket.accept()

    # ==================================================
    # SALA PRECISA EXISTIR NO REDIS
    # ==================================================

    if not await sala_existe(
        codigo
    ):

        await websocket.send_json({
            "tipo":
                "erro",

            "mensagem":
                "Sala não encontrada."
        })

        await websocket.close(
            code=1008,
            reason="Sala não encontrada"
        )

        return

    usuario_id = str(
        uuid.uuid4()
    )

    nome = "Usuário"

    tarefa_fila = None
    tarefa_estado = None

    try:

        # ==================================================
        # PRIMEIRA MENSAGEM
        # ==================================================

        primeira_mensagem = (
            await websocket.receive_json()
        )

        nome = (
            primeira_mensagem
            .get(
                "nome",
                ""
            )
            .strip()
        )

        if not nome:

            await websocket.send_json({
                "tipo":
                    "erro",

                "mensagem":
                    "Nome obrigatório."
            })

            await websocket.close()

            return

        # Sala pode ter expirado enquanto
        # a pessoa estava digitando o nome.
        if not await sala_existe(
            codigo
        ):

            await websocket.send_json({
                "tipo":
                    "erro",

                "mensagem":
                    "Sala não encontrada."
            })

            await websocket.close()

            return

        # ==================================================
        # REGISTRAR USUÁRIO GLOBALMENTE
        # ==================================================

        await redis.hset(
            chave_usuarios(codigo),
            values={
                usuario_id: nome
            }
        )

        await renovar_presenca(
            codigo,
            usuario_id
        )

        # Enquanto houver usuário conectado,
        # a sala não expira.
        await redis.persist(
            chave_sala(codigo)
        )

        await redis.persist(
            chave_usuarios(codigo)
        )

        await redis.persist(
            chave_transmissoes(codigo)
        )

        await redis.persist(
            chave_versao(codigo)
        )

        await redis.incr(
            chave_versao(codigo)
        )

        # Socket fica somente nesta instância.
        sockets_locais[
            usuario_id
        ] = websocket

        # ==================================================
        # ID DO USUÁRIO
        # ==================================================

        await websocket.send_json({
            "tipo":
                "meu_id",

            "id":
                usuario_id
        })

        print(
            f"{nome} entrou na sala "
            f"{codigo}"
        )

        # ==================================================
        # TAREFAS DE SINCRONIZAÇÃO
        # ==================================================

        tarefa_fila = asyncio.create_task(
            processar_fila(
                websocket,
                usuario_id
            )
        )

        tarefa_estado = asyncio.create_task(
            monitorar_estado(
                websocket,
                codigo
            )
        )

        await enviar_estado_socket(
            websocket,
            codigo
        )

        # ==================================================
        # LOOP PRINCIPAL
        # ==================================================

        while True:

            mensagem = (
                await websocket
                .receive_json()
            )

            tipo = mensagem.get(
                "tipo"
            )

            print(
                f"{nome} enviou evento: "
                f"{tipo}"
            )

            # ==================================================
            # PING / PONG
            # ==================================================

            if tipo == "ping":

                await renovar_presenca(
                    codigo,
                    usuario_id
                )

                await websocket.send_json({
                    "tipo":
                        "pong"
                })

            # ==================================================
            # INICIAR TRANSMISSÃO
            # ==================================================

            elif tipo == "iniciar_transmissao":

                await renovar_presenca(
                    codigo,
                    usuario_id
                )

                await redis.sadd(
                    chave_transmissoes(
                        codigo
                    ),
                    usuario_id
                )

                await redis.incr(
                    chave_versao(codigo)
                )

                print(
                    f"{nome} iniciou "
                    "transmissão"
                )

            # ==================================================
            # PARAR TRANSMISSÃO
            # ==================================================

            elif tipo == "parar_transmissao":

                await redis.srem(
                    chave_transmissoes(
                        codigo
                    ),
                    usuario_id
                )

                await redis.incr(
                    chave_versao(codigo)
                )

                print(
                    f"{nome} encerrou "
                    "transmissão"
                )

            # ==================================================
            # ASSISTIR
            # ==================================================

            elif tipo == "assistir":

                transmissor_id = (
                    mensagem.get(
                        "transmissor_id"
                    )
                )

                if not transmissor_id:
                    continue

                usuarios = (
                    await redis.hgetall(
                        chave_usuarios(
                            codigo
                        )
                    )
                    or {}
                )

                if transmissor_id not in usuarios:

                    await websocket.send_json({
                        "tipo":
                            "erro",

                        "mensagem":
                            "Transmissor "
                            "não encontrado."
                    })

                    continue

                await enviar_para_usuario(
                    transmissor_id,
                    {
                        "tipo":
                            "novo_espectador",

                        "espectador_id":
                            usuario_id
                    }
                )

            # ==================================================
            # WEBRTC
            # OFFER / ANSWER / ICE
            # ==================================================

            elif tipo in [
                "offer",
                "answer",
                "ice"
            ]:

                destino = mensagem.get(
                    "destino"
                )

                if not destino:
                    continue

                usuarios = (
                    await redis.hgetall(
                        chave_usuarios(
                            codigo
                        )
                    )
                    or {}
                )

                if destino not in usuarios:

                    print(
                        "Destino não encontrado:",
                        destino
                    )

                    continue

                mensagem[
                    "origem"
                ] = usuario_id

                await enviar_para_usuario(
                    destino,
                    mensagem
                )

            else:

                print(
                    "Evento desconhecido:",
                    tipo
                )

    # ======================================================
    # DESCONECTOU
    # ======================================================

    except WebSocketDisconnect:

        print(
            f"{nome} desconectou "
            f"da sala {codigo}"
        )

    # ======================================================
    # ERRO
    # ======================================================

    except Exception as erro:

        print(
            "ERRO NO WEBSOCKET:",
            repr(erro)
        )

    # ======================================================
    # LIMPEZA
    # ======================================================

    finally:

        if tarefa_fila:

            tarefa_fila.cancel()

        if tarefa_estado:

            tarefa_estado.cancel()

        sockets_locais.pop(
            usuario_id,
            None
        )

        try:

            await redis.hdel(
                chave_usuarios(codigo),
                usuario_id
            )

            await redis.srem(
                chave_transmissoes(codigo),
                usuario_id
            )

            await redis.delete(
                chave_presenca(
                    codigo,
                    usuario_id
                )
            )

            await redis.delete(
                chave_fila(
                    usuario_id
                )
            )

            await redis.incr(
                chave_versao(codigo)
            )

            usuarios_restantes = (
                await limpar_usuarios_mortos(
                    codigo
                )
            )

            print(
                f"{nome} removido "
                f"da sala {codigo}"
            )

            print(
                "Usuários restantes:",
                usuarios_restantes
            )

            # ==================================================
            # SALA FICOU VAZIA
            # ==================================================

            if (
                usuarios_restantes == 0
                and
                await sala_existe(codigo)
            ):

                await redis.expire(
                    chave_sala(codigo),
                    TEMPO_EXPIRACAO_SALA
                )

                await redis.expire(
                    chave_usuarios(codigo),
                    TEMPO_EXPIRACAO_SALA
                )

                await redis.expire(
                    chave_transmissoes(codigo),
                    TEMPO_EXPIRACAO_SALA
                )

                await redis.expire(
                    chave_versao(codigo),
                    TEMPO_EXPIRACAO_SALA
                )

                print(
                    f"Sala {codigo} ficou vazia. "
                    "Expira em 10 minutos."
                )

            elif usuarios_restantes > 0:

                await redis.persist(
                    chave_sala(codigo)
                )

        except Exception as erro:

            print(
                "Erro durante limpeza:",
                repr(erro)
            )


# ======================================================
# ARQUIVOS ESTÁTICOS
# ======================================================

app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static"
)