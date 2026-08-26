from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

import uuid
import random
import string


app = FastAPI()

salas = {}


def gerar_codigo_sala(tamanho=6):
    caracteres = string.ascii_uppercase + string.digits

    return "".join(
        random.choices(
            caracteres,
            k=tamanho
        )
    )


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.post("/criar-sala")
async def criar_sala():
    codigo = gerar_codigo_sala()

    while codigo in salas:
        codigo = gerar_codigo_sala()

    salas[codigo] = {
        "usuarios": {},
        "transmissoes": {}
    }

    print(f"Sala criada: {codigo}")

    return JSONResponse({
        "codigo": codigo,
        "url": f"/sala/{codigo}"
    })


@app.get("/sala/{codigo}")
async def abrir_sala(codigo: str):
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


async def enviar_estado_sala(codigo):
    sala = salas.get(codigo)

    if not sala:
        return

    estado = {
        "tipo": "estado",

        "usuarios": [
            {
                "id": usuario_id,
                "nome": dados["nome"]
            }
            for usuario_id, dados
            in sala["usuarios"].items()
        ],

        "transmissoes": [
            {
                "usuario_id": usuario_id,
                "nome": sala[
                    "usuarios"
                ][usuario_id]["nome"]
            }
            for usuario_id
            in sala["transmissoes"]

            if usuario_id
            in sala["usuarios"]
        ]
    }

    for dados in list(
        sala["usuarios"].values()
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
                erro
            )


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
            await websocket.receive_json()
        )

        nome = (
            primeira_mensagem
            .get("nome", "")
            .strip()
        )

        if not nome:
            await websocket.send_json({
                "tipo": "erro",
                "mensagem": "Nome obrigatório."
            })

            await websocket.close()

            return

        salas[codigo][
            "usuarios"
        ][usuario_id] = {
            "nome": nome,
            "socket": websocket
        }

        await websocket.send_json({
            "tipo": "meu_id",
            "id": usuario_id
        })

        print(
            f"{nome} entrou na sala {codigo}"
        )

        print(
            "Usuários conectados:",
            len(
                salas[codigo]["usuarios"]
            )
        )

        await enviar_estado_sala(
            codigo
        )

        while True:
            mensagem = (
                await websocket.receive_json()
            )

            tipo = mensagem.get(
                "tipo"
            )

            print(
                f"{nome} enviou evento: {tipo}"
            )

            # ==========================
            # INICIAR TRANSMISSÃO
            # ==========================

            if tipo == "iniciar_transmissao":

                salas[codigo][
                    "transmissoes"
                ][usuario_id] = True

                print(
                    f"{nome} iniciou transmissão"
                )

                await enviar_estado_sala(
                    codigo
                )

            # ==========================
            # PARAR TRANSMISSÃO
            # ==========================

            elif tipo == "parar_transmissao":

                salas[codigo][
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

            # ==========================
            # ASSISTIR TRANSMISSÃO
            # ==========================

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
                    in salas[codigo]["usuarios"]
                ):

                    print(
                        "Transmissor encontrado!"
                    )

                    await salas[codigo][
                        "usuarios"
                    ][transmissor_id][
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
                        "ERRO: transmissor "
                        "não encontrado"
                    )

            # ==========================
            # WEBRTC
            # offer / answer / ice
            # ==========================

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
                    in salas[codigo]["usuarios"]
                ):

                    mensagem[
                        "origem"
                    ] = usuario_id

                    await salas[codigo][
                        "usuarios"
                    ][destino][
                        "socket"
                    ].send_json(
                        mensagem
                    )

                    print(
                        f"{tipo} encaminhado!"
                    )

                else:
                    print(
                        f"Destino não encontrado: "
                        f"{destino}"
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

            salas[codigo][
                "usuarios"
            ].pop(
                usuario_id,
                None
            )

            salas[codigo][
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
                    salas[codigo]["usuarios"]
                )
            )

            await enviar_estado_sala(
                codigo
            )


app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static"
)