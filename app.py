import os
import json
import uuid
import random
import string
import urllib.request
import urllib.error

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

salas = {}


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
            "Cloudflare TURN não configurado."
        )

        return JSONResponse(
            status_code=500,
            content={
                "erro":
                    "Credenciais Cloudflare TURN não configuradas."
            }
        )

    url = (
        "https://rtc.live.cloudflare.com/"
        "v1/turn/keys/"
        f"{turn_key_id}/"
        "credentials/generate-ice-servers"
    )

    corpo = json.dumps({
        "ttl": 86400
    }).encode(
        "utf-8"
    )

    requisicao = urllib.request.Request(
        url,
        data=corpo,
        method="POST",
        headers={
            "Authorization":
                f"Bearer {turn_api_token}",

            "Content-Type":
                "application/json",

            "Accept":
                "application/json"
        }
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=10
        ) as resposta:

            corpo_resposta = (
                resposta
                .read()
                .decode(
                    "utf-8"
                )
            )

            dados = json.loads(
                corpo_resposta
            )

            print(
                "Credenciais Cloudflare TURN geradas."
            )

            return JSONResponse(
                content=dados
            )

    except urllib.error.HTTPError as erro:

        try:

            detalhe = (
                erro
                .read()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
            )

        except Exception:

            detalhe = ""

        print(
            "Cloudflare HTTP ERROR:",
            erro.code,
            detalhe
        )

        return JSONResponse(
            status_code=502,
            content={
                "erro":
                    "Cloudflare recusou a geração TURN.",

                "status":
                    erro.code,

                "detalhe":
                    detalhe
            }
        )

    except urllib.error.URLError as erro:

        print(
            "Cloudflare URL ERROR:",
            repr(erro)
        )

        return JSONResponse(
            status_code=502,
            content={
                "erro":
                    "Não foi possível acessar o Cloudflare TURN."
            }
        )

    except Exception as erro:

        print(
            "Erro Cloudflare TURN:",
            repr(erro)
        )

        return JSONResponse(
            status_code=502,
            content={
                "erro":
                    "Não foi possível gerar credenciais TURN."
            }
        )


# ======================================================
# GERAR CÓDIGO DA SALA
# ======================================================

def gerar_codigo_sala(
    tamanho=6
):

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

        "transmissoes": {}

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

    codigo = codigo.upper()

    if codigo not in salas:

        salas[codigo] = {

            "usuarios": {},

            "transmissoes": {}

        }

        print(
            f"Sala criada ao abrir link: {codigo}"
        )

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
            in sala["usuarios"].items()

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
            in sala["transmissoes"]

            if usuario_id
            in sala["usuarios"]

        ]

    }

    for dados in list(
        sala[
            "usuarios"
        ].values()
    ):

        try:

            await dados[
                "socket"
            ].send_json(
                estado
            )

        except Exception as erro:

            print(
                "Erro ao enviar estado:",
                repr(erro)
            )


# ======================================================
# WEBSOCKET
# ======================================================

@app.websocket("/ws/{codigo}")
async def websocket_sala(

    websocket: WebSocket,

    codigo: str

):

    codigo = codigo.upper()

    await websocket.accept()

    if codigo not in salas:

        salas[codigo] = {

            "usuarios": {},

            "transmissoes": {}

        }

    usuario_id = str(
        uuid.uuid4()
    )

    nome = "Usuário"

    try:

        primeira_mensagem = (
            await websocket
            .receive_json()
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

        await websocket.send_json({

            "tipo":
                "meu_id",

            "id":
                usuario_id

        })

        print(
            f"{nome} entrou na sala {codigo}"
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

        while True:

            mensagem = (
                await websocket
                .receive_json()
            )

            tipo = mensagem.get(
                "tipo"
            )

            print(
                f"{nome} enviou evento: {tipo}"
            )


            # ==================================================
            # HEARTBEAT
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
                    f"{nome} iniciou transmissão"
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
                    f"{nome} encerrou transmissão"
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
                    in salas[
                        codigo
                    ][
                        "usuarios"
                    ]
                ):

                    print(
                        "Transmissor encontrado!"
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
                        "Pedido enviado ao transmissor!"
                    )

                else:

                    print(
                        "ERRO: transmissor não encontrado"
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

                destino = (
                    mensagem.get(
                        "destino"
                    )
                )

                print(
                    f"{nome} enviou "
                    f"{tipo} para {destino}"
                )

                if (
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
                        f"{tipo} encaminhado!"
                    )

                else:

                    print(
                        f"Destino não encontrado: {destino}"
                    )

            else:

                print(
                    f"Evento desconhecido: {tipo}"
                )


    except WebSocketDisconnect:

        print(
            f"{nome} desconectou "
            f"da sala {codigo}"
        )


    except Exception as erro:

        print(
            "ERRO NO WEBSOCKET:",
            repr(erro)
        )


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
                f"{nome} removido da sala {codigo}"
            )

            print(
                "Usuários restantes:",
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