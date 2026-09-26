import os
import uuid
import random
import string
import time
import requests

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


app = FastAPI()


# ======================================================
# CONFIGURAÇÃO DAS SALAS
# ======================================================

salas = {}

# 10 minutos em segundos
TEMPO_EXPIRACAO_SALA = 10 * 60


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

    # ==================================================
    # VALIDAR VARIÁVEIS
    # ==================================================

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

    # ==================================================
    # ENDPOINT CLOUDFLARE
    # ==================================================

    url = (
        "https://rtc.live.cloudflare.com/"
        "v1/turn/keys/"
        f"{turn_key_id}/"
        "credentials/generate-ice-servers"
    )

    # ==================================================
    # HEADERS
    # ==================================================

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

    # ==================================================
    # CORPO
    # ==================================================

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

        # ==================================================
        # ERRO HTTP
        # ==================================================

        if not resposta.ok:

            print(
                "Cloudflare TURN recusou:"
            )

            print(
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

        # ==================================================
        # CONVERTER JSON
        # ==================================================

        try:

            dados = resposta.json()

        except ValueError as erro:

            print(
                "Resposta Cloudflare "
                "não é JSON:",
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

        # ==================================================
        # VALIDAR ICE SERVERS
        # ==================================================

        ice_servers = dados.get(
            "iceServers"
        )

        if (
            not isinstance(
                ice_servers,
                list
            )
            or
            len(ice_servers) == 0
        ):

            print(
                "Cloudflare respondeu "
                "sem iceServers:"
            )

            print(
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

        print(
            "Quantidade de iceServers:",
            len(ice_servers)
        )

        return JSONResponse(
            content=dados
        )

    except requests.Timeout:

        print(
            "Timeout ao acessar "
            "Cloudflare TURN."
        )

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
            "Erro de conexão "
            "Cloudflare TURN:",
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
            "Erro HTTP "
            "Cloudflare TURN:",
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
            "Erro inesperado "
            "Cloudflare TURN:",
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
# GERAR CÓDIGO DA SALA
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
# CONTROLE DE EXPIRAÇÃO
# ======================================================

def sala_expirada(codigo):

    sala = salas.get(codigo)

    if not sala:
        return True

    # Enquanto houver pelo menos uma pessoa,
    # a sala nunca expira.
    if len(sala["usuarios"]) > 0:
        return False

    vazia_desde = sala.get(
        "vazia_desde"
    )

    if vazia_desde is None:
        return False

    tempo_vazia = (
        time.time() - vazia_desde
    )

    return (
        tempo_vazia
        >=
        TEMPO_EXPIRACAO_SALA
    )


def remover_sala_se_expirada(codigo):

    if codigo not in salas:
        return False

    if not sala_expirada(codigo):
        return False

    print(
        f"Sala {codigo} encerrada "
        "por ficar 10 minutos vazia."
    )

    del salas[codigo]

    return True


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

    codigo = gerar_codigo_sala()

    while codigo in salas:
        codigo = gerar_codigo_sala()

    salas[codigo] = {

        "usuarios": {},

        "transmissoes": {},

        # A sala acabou de ser criada.
        # Como ainda está vazia, começa aqui
        # o prazo de 10 minutos.
        "vazia_desde": time.time()

    }

    print(
        f"Sala criada: {codigo}"
    )

    return JSONResponse(
        content={

            "codigo":
                codigo,

            "url":
                f"/sala/{codigo}"

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

    # ==================================================
    # A SALA PRECISA TER SIDO CRIADA
    # ==================================================

    if codigo not in salas:

        print(
            f"Tentativa de abrir "
            f"sala inexistente: {codigo}"
        )

        return FileResponse(
            "static/sala_inexistente.html",
            status_code=404
        )

    # ==================================================
    # VERIFICAR EXPIRAÇÃO
    # ==================================================

    if remover_sala_se_expirada(
        codigo
    ):

        print(
            f"Tentativa de abrir "
            f"sala expirada: {codigo}"
        )

        return FileResponse(
            "static/sala_inexistente.html",
            status_code=404
        )

    # IMPORTANTE:
    #
    # Apenas abrir a página NÃO cancela o contador.
    #
    # O contador só será cancelado quando a pessoa
    # realmente colocar o nome e conectar no WebSocket.

    return FileResponse(
        "static/sala.html"
    )


# ======================================================
# ENVIAR ESTADO DA SALA
# ======================================================

async def enviar_estado_sala(
    codigo
):

    sala = salas.get(
        codigo
    )

    if not sala:
        return

    estado = {

        "tipo":
            "estado",

        "usuarios": [

            {

                "id":
                    usuario_id,

                "nome":
                    dados["nome"]

            }

            for usuario_id, dados
            in sala[
                "usuarios"
            ].items()

        ],

        "transmissoes": [

            {

                "usuario_id":
                    usuario_id,

                "nome":
                    sala[
                        "usuarios"
                    ][
                        usuario_id
                    ][
                        "nome"
                    ]

            }

            for usuario_id
            in sala[
                "transmissoes"
            ]

            if usuario_id
            in sala[
                "usuarios"
            ]

        ]

    }

    usuarios_remover = []

    for usuario_id, dados in list(
        sala[
            "usuarios"
        ].items()
    ):

        try:

            await dados[
                "socket"
            ].send_json(
                estado
            )

        except Exception as erro:

            print(
                "Erro ao enviar estado "
                f"para {usuario_id}:",
                repr(erro)
            )

            usuarios_remover.append(
                usuario_id
            )

    # ==================================================
    # REMOVER SOCKETS MORTOS
    # ==================================================

    for usuario_id in usuarios_remover:

        sala[
            "usuarios"
        ].pop(
            usuario_id,
            None
        )

        sala[
            "transmissoes"
        ].pop(
            usuario_id,
            None
        )

    # Se os sockets mortos eram as últimas pessoas
    # da sala, começa o contador.
    if (
        usuarios_remover
        and
        len(sala["usuarios"]) == 0
        and
        sala.get("vazia_desde") is None
    ):

        sala["vazia_desde"] = time.time()

        print(
            f"Sala {codigo} ficou vazia. "
            "Expira em 10 minutos."
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
    # NÃO CRIAR SALA PELO WEBSOCKET
    # ==================================================

    if codigo not in salas:

        print(
            f"WebSocket recusado: "
            f"sala inexistente {codigo}"
        )

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

    # ==================================================
    # VERIFICAR SE EXPIROU
    # ==================================================

    if remover_sala_se_expirada(
        codigo
    ):

        print(
            f"WebSocket recusado: "
            f"sala expirada {codigo}"
        )

        await websocket.send_json({

            "tipo":
                "erro",

            "mensagem":
                "Essa sala expirou."

        })

        await websocket.close(
            code=1008,
            reason="Sala expirada"
        )

        return

    usuario_id = str(
        uuid.uuid4()
    )

    nome = "Usuário"

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

        # ==================================================
        # VERIFICAR NOVAMENTE A SALA
        # ==================================================

        if codigo not in salas:

            await websocket.send_json({

                "tipo":
                    "erro",

                "mensagem":
                    "Sala não encontrada."

            })

            await websocket.close()

            return

        # ==================================================
        # REGISTRAR USUÁRIO
        # ==================================================

        salas[
            codigo
        ][
            "usuarios"
        ][
            usuario_id
        ] = {

            "nome":
                nome,

            "socket":
                websocket

        }

        # ==================================================
        # CANCELAR CONTADOR DE EXPIRAÇÃO
        # ==================================================
        #
        # Agora existe alguém realmente conectado.
        # A sala pode ficar aberta pelo tempo que quiser.

        salas[
            codigo
        ][
            "vazia_desde"
        ] = None

        # ==================================================
        # ENVIAR ID
        # ==================================================

        await websocket.send_json({

            "tipo":
                "meu_id",

            "id":
                usuario_id

        })

        print(
            f"{nome} entrou "
            f"na sala {codigo}"
        )

        print(
            "Usuários conectados:",
            len(
                salas[
                    codigo
                ][
                    "usuarios"
                ]
            )
        )

        await enviar_estado_sala(
            codigo
        )

        # ==================================================
        # LOOP
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

                await websocket.send_json({

                    "tipo":
                        "pong"

                })

            # ==================================================
            # INICIAR TRANSMISSÃO
            # ==================================================

            elif tipo == "iniciar_transmissao":

                salas[
                    codigo
                ][
                    "transmissoes"
                ][
                    usuario_id
                ] = True

                print(
                    f"{nome} iniciou "
                    "transmissão"
                )

                await enviar_estado_sala(
                    codigo
                )

            # ==================================================
            # PARAR TRANSMISSÃO
            # ==================================================

            elif tipo == "parar_transmissao":

                salas[
                    codigo
                ][
                    "transmissoes"
                ].pop(
                    usuario_id,
                    None
                )

                print(
                    f"{nome} encerrou "
                    "transmissão"
                )

                await enviar_estado_sala(
                    codigo
                )

            # ==================================================
            # ASSISTIR TRANSMISSÃO
            # ==================================================

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

                if (
                    transmissor_id
                    and
                    codigo in salas
                    and
                    transmissor_id
                    in salas[
                        codigo
                    ][
                        "usuarios"
                    ]
                ):

                    print(
                        "Transmissor encontrado."
                    )

                    await salas[
                        codigo
                    ][
                        "usuarios"
                    ][
                        transmissor_id
                    ][
                        "socket"
                    ].send_json({

                        "tipo":
                            "novo_espectador",

                        "espectador_id":
                            usuario_id

                    })

                    print(
                        "Pedido enviado "
                        "ao transmissor."
                    )

                else:

                    print(
                        "Transmissor "
                        "não encontrado:",
                        transmissor_id
                    )

                    await websocket.send_json({

                        "tipo":
                            "erro",

                        "mensagem":
                            "Transmissor "
                            "não encontrado."

                    })

            # ==================================================
            # WEBRTC
            # OFFER / ANSWER / ICE
            # ==================================================

            elif tipo in [

                "offer",

                "answer",

                "ice"

            ]:

                destino = (
                    mensagem.get(
                        "destino"
                    )
                )

                print(
                    f"{nome} enviou "
                    f"{tipo} "
                    f"para {destino}"
                )

                if (
                    destino
                    and
                    codigo in salas
                    and
                    destino
                    in salas[
                        codigo
                    ][
                        "usuarios"
                    ]
                ):

                    mensagem[
                        "origem"
                    ] = usuario_id

                    try:

                        await salas[
                            codigo
                        ][
                            "usuarios"
                        ][
                            destino
                        ][
                            "socket"
                        ].send_json(
                            mensagem
                        )

                        print(
                            f"{tipo} encaminhado."
                        )

                    except Exception as erro:

                        print(
                            "Erro encaminhando "
                            f"{tipo}:",
                            repr(erro)
                        )

                else:

                    print(
                        "Destino "
                        "não encontrado:",
                        destino
                    )

            # ==================================================
            # EVENTO DESCONHECIDO
            # ==================================================

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

        if codigo in salas:

            salas[
                codigo
            ][
                "usuarios"
            ].pop(
                usuario_id,
                None
            )

            salas[
                codigo
            ][
                "transmissoes"
            ].pop(
                usuario_id,
                None
            )

            print(
                f"{nome} removido "
                f"da sala {codigo}"
            )

            usuarios_restantes = len(
                salas[
                    codigo
                ][
                    "usuarios"
                ]
            )

            print(
                "Usuários restantes:",
                usuarios_restantes
            )

            # ==================================================
            # ÚLTIMA PESSOA SAIU
            # ==================================================

            if usuarios_restantes == 0:

                salas[
                    codigo
                ][
                    "vazia_desde"
                ] = time.time()

                print(
                    f"Sala {codigo} ficou vazia. "
                    "Expira em 10 minutos."
                )

            await enviar_estado_sala(
                codigo
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