import os
import uuid
import random
import string
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


        # Não imprimir username/credential.
        # Essas credenciais são temporárias,
        # mas não precisam aparecer nos logs.

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
            f"Sala criada ao abrir link: "
            f"{codigo}"
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