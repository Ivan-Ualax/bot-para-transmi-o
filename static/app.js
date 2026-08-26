// ======================================================
// CONFIGURAÇÃO
// ======================================================

const BASE_URL = "https://bot-para-transmi-o.vercel.app";
const SIGNALING_URL = "wss://bot-para-transmi-o.vercel.app";

const partes = window.location.pathname
    .split("/")
    .filter(Boolean);

const codigoSala = partes[1] || null;

console.log("Sala:", codigoSala);


// ======================================================
// ELEMENTOS
// ======================================================

const nomeInput =
    document.getElementById("nome");

const botaoEntrar =
    document.getElementById("entrar");

const botaoTransmitir =
    document.getElementById("transmitir");

const botaoParar =
    document.getElementById("parar");

const botaoCopiar =
    document.getElementById("copiar-link");

const entrada =
    document.getElementById("entrada");

const painel =
    document.getElementById("painel");

const usuariosOnline =
    document.getElementById("usuarios-online");

const transmissoesDiv =
    document.getElementById("transmissoes");

const statusTexto =
    document.getElementById("status");

const codigoSalaTexto =
    document.getElementById("codigo-sala");

const video =
    document.getElementById("video");


// ======================================================
// ESTADO
// ======================================================

let socket = null;

let meuId = null;
let meuNome = null;

let streamLocal = null;
let streamRemoto = null;

let transmitindo = false;

let transmissaoAtual = null;

let heartbeat = null;

const peers = {};
const icePendentes = {};


// ======================================================
// TURN
// ======================================================
//
// MANTENHA aqui o username e a credential
// que você pegou na Metered.
//
// Eu não vou repetir sua senha aqui.
//

const TURN_USERNAME =
    "COLOQUE_SEU_USERNAME_METERED";

const TURN_CREDENTIAL =
    "COLOQUE_SUA_CREDENTIAL_METERED";


const configuracaoRTC = {

    iceServers: [

        {
            urls:
                "stun:stun.relay.metered.ca:80"
        },

        {
            urls:
                "turn:global.relay.metered.ca:80",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        },

        {
            urls:
                "turn:global.relay.metered.ca:80?transport=tcp",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        },

        {
            urls:
                "turn:global.relay.metered.ca:443",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        },

        {
            urls:
                "turns:global.relay.metered.ca:443?transport=tcp",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        }
    ],

    iceTransportPolicy: "all",
    bundlePolicy: "max-bundle",
    rtcpMuxPolicy: "require"
};


// ======================================================
// INICIALIZAÇÃO
// ======================================================

function iniciarPagina() {

    console.log(
        "APP.JS carregado corretamente"
    );


    if (!codigoSala) {

        console.error(
            "Código da sala não encontrado."
        );

        return;
    }


    if (codigoSalaTexto) {

        codigoSalaTexto.textContent =
            `Sala: ${codigoSala}`;
    }


    if (!botaoEntrar) {

        console.error(
            "Botão #entrar não encontrado."
        );

        return;
    }


    botaoEntrar.addEventListener(
        "click",
        conectar
    );


    if (nomeInput) {

        nomeInput.addEventListener(
            "keydown",
            evento => {

                if (
                    evento.key === "Enter"
                ) {

                    conectar();
                }
            }
        );
    }


    if (botaoTransmitir) {

        botaoTransmitir.addEventListener(
            "click",
            iniciarTransmissao
        );
    }


    if (botaoParar) {

        botaoParar.addEventListener(
            "click",
            pararTransmissao
        );
    }


    if (botaoCopiar) {

        botaoCopiar.addEventListener(
            "click",
            copiarConvite
        );
    }
}


// ======================================================
// COPIAR LINK
// ======================================================

async function copiarConvite() {

    try {

        await navigator.clipboard.writeText(
            window.location.href
        );


        botaoCopiar.textContent =
            "Link copiado!";


        setTimeout(
            () => {

                botaoCopiar.textContent =
                    "Copiar convite";

            },
            2000
        );

    } catch (erro) {

        console.error(
            "Erro ao copiar:",
            erro
        );


        alert(
            window.location.href
        );
    }
}


// ======================================================
// ENTRAR NA SALA
// ======================================================

function conectar() {

    console.log(
        "Botão Entrar clicado"
    );


    if (!codigoSala) {

        statusTexto.textContent =
            "Sala inválida.";

        return;
    }


    if (!nomeInput) {

        console.error(
            "#nome não encontrado"
        );

        return;
    }


    const nome =
        nomeInput.value.trim();


    if (!nome) {

        alert(
            "Digite seu nome."
        );

        return;
    }


    if (
        socket &&
        (
            socket.readyState ===
                WebSocket.OPEN ||

            socket.readyState ===
                WebSocket.CONNECTING
        )
    ) {

        console.log(
            "WebSocket já conectado."
        );

        return;
    }


    meuNome = nome;


    botaoEntrar.disabled =
        true;


    statusTexto.textContent =
        "Conectando à sala...";


    const endereco =
        `${SIGNALING_URL}/ws/${codigoSala}`;


    console.log(
        "Conectando WebSocket:",
        endereco
    );


    try {

        socket =
            new WebSocket(
                endereco
            );

    } catch (erro) {

        console.error(
            "Erro criando WebSocket:",
            erro
        );


        botaoEntrar.disabled =
            false;


        statusTexto.textContent =
            "Erro ao conectar.";

        return;
    }


    socket.onopen =
        () => {

            console.log(
                "WebSocket conectado."
            );


            socket.send(
                JSON.stringify({
                    nome: meuNome
                })
            );


            if (entrada) {

                entrada.style.display =
                    "none";
            }


            if (painel) {

                painel.style.display =
                    "block";
            }


            statusTexto.textContent =
                `Conectado como ${meuNome}`;


            iniciarHeartbeat();
        };


    socket.onerror =
        erro => {

            console.error(
                "ERRO WEBSOCKET:",
                erro
            );


            botaoEntrar.disabled =
                false;


            statusTexto.textContent =
                "Erro ao conectar ao servidor.";
        };


    socket.onclose =
        evento => {

            console.log(
                "WebSocket fechado:",
                evento.code,
                evento.reason
            );


            pararHeartbeat();

            fecharTodosPeers();


            botaoEntrar.disabled =
                false;


            statusTexto.textContent =
                "Desconectado do servidor.";
        };


    socket.onmessage =
        receberMensagem;
}


// ======================================================
// HEARTBEAT
// ======================================================

function iniciarHeartbeat() {

    pararHeartbeat();


    heartbeat =
        setInterval(
            () => {

                if (
                    socket &&
                    socket.readyState ===
                        WebSocket.OPEN
                ) {

                    enviarSocket({
                        tipo: "ping"
                    });
                }

            },
            30000
        );
}


function pararHeartbeat() {

    if (!heartbeat) {

        return;
    }


    clearInterval(
        heartbeat
    );


    heartbeat = null;
}


// ======================================================
// RECEBER WEBSOCKET
// ======================================================

async function receberMensagem(
    evento
) {

    let mensagem;


    try {

        mensagem =
            JSON.parse(
                evento.data
            );

    } catch (erro) {

        console.error(
            "JSON inválido:",
            evento.data,
            erro
        );

        return;
    }


    console.log(
        "RECEBIDO:",
        mensagem.tipo,
        mensagem
    );


    switch (
        mensagem.tipo
    ) {

        // ==================================================
        // MEU ID
        // ==================================================

        case "meu_id":

            meuId =
                mensagem.id;


            console.log(
                "Meu ID:",
                meuId
            );

            break;


        // ==================================================
        // ESTADO DA SALA
        // ==================================================

        case "estado":

            atualizarUsuarios(
                mensagem.usuarios || []
            );


            atualizarTransmissoes(
                mensagem.transmissoes || []
            );

            break;


        // ==================================================
        // NOVO ESPECTADOR
        // ==================================================

        case "novo_espectador":

            console.log(
                "Novo espectador:",
                mensagem.espectador_id
            );


            if (!transmitindo) {

                console.log(
                    "Não estou transmitindo."
                );

                return;
            }


            await criarOfertaParaEspectador(
                mensagem.espectador_id
            );

            break;


        // ==================================================
        // OFFER
        // ==================================================

        case "offer":

            console.log(
                "OFFER recebida:",
                mensagem.origem
            );


            await receberOferta(
                mensagem
            );

            break;


        // ==================================================
        // ANSWER
        // ==================================================

        case "answer":

            console.log(
                "ANSWER recebida:",
                mensagem.origem
            );


            await receberAnswer(
                mensagem
            );

            break;


        // ==================================================
        // ICE
        // ==================================================

        case "ice":

            await receberIce(
                mensagem
            );

            break;


        case "pong":

            console.log(
                "PONG"
            );

            break;


        case "erro":

            console.error(
                "Erro servidor:",
                mensagem.mensagem
            );


            statusTexto.textContent =
                mensagem.mensagem ||
                "Erro no servidor.";

            break;


        default:

            console.log(
                "Evento desconhecido:",
                mensagem
            );
    }
}


// ======================================================
// USUÁRIOS ONLINE
// ======================================================

function atualizarUsuarios(
    lista
) {

    if (!usuariosOnline) {

        return;
    }


    usuariosOnline.innerHTML =
        "";


    if (
        !lista ||
        lista.length === 0
    ) {

        usuariosOnline.textContent =
            "Nenhum usuário online.";

        return;
    }


    lista.forEach(
        usuario => {

            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "usuario-item";


            if (
                usuario.id === meuId
            ) {

                item.textContent =
                    `${usuario.nome} (você)`;

            } else {

                item.textContent =
                    usuario.nome;
            }


            usuariosOnline.appendChild(
                item
            );
        }
    );
}


// ======================================================
// TRANSMISSÕES
// ======================================================

function atualizarTransmissoes(
    lista
) {

    if (!transmissoesDiv) {

        return;
    }


    transmissoesDiv.innerHTML =
        "";


    if (
        !lista ||
        lista.length === 0
    ) {

        transmissoesDiv.textContent =
            "Nenhuma transmissão ativa.";

        return;
    }


    lista.forEach(
        transmissao => {

            const card =
                document.createElement(
                    "div"
                );


            card.className =
                "transmissao-card";


            const nome =
                document.createElement(
                    "span"
                );


            nome.textContent =
                `${transmissao.nome} está transmitindo`;


            card.appendChild(
                nome
            );


            if (
                transmissao.usuario_id !==
                    meuId
            ) {

                const botao =
                    document.createElement(
                        "button"
                    );


                botao.textContent =
                    "Assistir";


                botao.disabled =
                    false;


                botao.addEventListener(
                    "click",
                    () => {

                        assistirTransmissao(
                            transmissao.usuario_id
                        );
                    }
                );


                card.appendChild(
                    botao
                );
            }


            transmissoesDiv.appendChild(
                card
            );
        }
    );
}


// ======================================================
// INICIAR TRANSMISSÃO
// ======================================================

async function iniciarTransmissao() {

    if (transmitindo) {

        return;
    }


    if (
        !socket ||
        socket.readyState !==
            WebSocket.OPEN
    ) {

        statusTexto.textContent =
            "Entre na sala primeiro.";

        return;
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getDisplayMedia
    ) {

        statusTexto.textContent =
            "Seu navegador não permite compartilhar tela.";

        return;
    }


    try {

        streamLocal =
            await navigator.mediaDevices
                .getDisplayMedia({

                    video: {

                        frameRate: {
                            ideal: 30,
                            max: 60
                        }

                    },

                    audio: true
                });


        console.log(
            "STREAM:",
            streamLocal
        );


        console.log(
            "TRACKS:",
            streamLocal
                .getTracks()
                .map(
                    track => ({
                        kind:
                            track.kind,

                        label:
                            track.label,

                        enabled:
                            track.enabled
                    })
                )
        );


        if (video) {

            video.srcObject =
                streamLocal;


            video.muted =
                true;


            video.autoplay =
                true;


            try {

                await video.play();

            } catch (erro) {

                console.log(
                    "Preview bloqueado:",
                    erro
                );
            }
        }


        transmitindo =
            true;


        enviarSocket({
            tipo:
                "iniciar_transmissao"
        });


        if (botaoTransmitir) {

            botaoTransmitir.style.display =
                "none";
        }


        if (botaoParar) {

            botaoParar.style.display =
                "inline-block";
        }


        statusTexto.textContent =
            "Transmitindo tela";


        const videoTrack =
            streamLocal
                .getVideoTracks()[0];


        if (videoTrack) {

            videoTrack.onended =
                pararTransmissao;
        }


    } catch (erro) {

        console.error(
            "Erro ao compartilhar:",
            erro
        );


        statusTexto.textContent =
            "Erro ao iniciar transmissão.";
    }
}


// ======================================================
// PARAR TRANSMISSÃO
// ======================================================

function pararTransmissao() {

    if (!transmitindo) {

        return;
    }


    transmitindo =
        false;


    if (streamLocal) {

        streamLocal
            .getTracks()
            .forEach(
                track => {

                    track.onended =
                        null;

                    track.stop();
                }
            );


        streamLocal =
            null;
    }


    fecharTodosPeers();


    if (video) {

        video.srcObject =
            null;
    }


    enviarSocket({
        tipo:
            "parar_transmissao"
    });


    if (botaoTransmitir) {

        botaoTransmitir.style.display =
            "inline-block";
    }


    if (botaoParar) {

        botaoParar.style.display =
            "none";
    }


    statusTexto.textContent =
        "Transmissão encerrada";
}


// ======================================================
// ASSISTIR
// ======================================================

function assistirTransmissao(
    transmissorId
) {

    console.log(
        "ASSISTIR:",
        transmissorId
    );


    if (
        !transmissorId ||
        transmissorId === meuId
    ) {

        return;
    }


    if (
        !socket ||
        socket.readyState !==
            WebSocket.OPEN
    ) {

        statusTexto.textContent =
            "Servidor desconectado.";

        return;
    }


    if (
        transmissaoAtual &&
        transmissaoAtual !==
            transmissorId
    ) {

        fecharPeer(
            transmissaoAtual
        );
    }


    transmissaoAtual =
        transmissorId;


    streamRemoto =
        new MediaStream();


    if (video) {

        video.srcObject =
            streamRemoto;

        video.muted =
            false;

        video.autoplay =
            true;

        video.controls =
            true;
    }


    statusTexto.textContent =
        "Conectando à transmissão...";


    enviarSocket({

        tipo:
            "assistir",

        transmissor_id:
            transmissorId

    });
}


// ======================================================
// CRIAR OFFER
// ======================================================

async function criarOfertaParaEspectador(
    espectadorId
) {

    console.log(
        "Criando offer para:",
        espectadorId
    );


    if (!streamLocal) {

        console.error(
            "Sem stream local."
        );

        return;
    }


    fecharPeer(
        espectadorId
    );


    const peer =
        criarPeer(
            espectadorId,
            false
        );


    streamLocal
        .getTracks()
        .forEach(
            track => {

                peer.addTrack(
                    track,
                    streamLocal
                );
            }
        );


    try {

        const oferta =
            await peer.createOffer();


        await peer.setLocalDescription(
            oferta
        );


        console.log(
            "OFFER criada."
        );


        enviarSocket({

            tipo:
                "offer",

            destino:
                espectadorId,

            offer:
                peer.localDescription

        });


    } catch (erro) {

        console.error(
            "Erro offer:",
            erro
        );
    }
}


// ======================================================
// RECEBER OFFER
// ======================================================

async function receberOferta(
    mensagem
) {

    const transmissorId =
        mensagem.origem;


    console.log(
        "Processando OFFER:",
        transmissorId
    );


    fecharPeer(
        transmissorId
    );


    streamRemoto =
        new MediaStream();


    if (video) {

        video.srcObject =
            streamRemoto;
    }


    const peer =
        criarPeer(
            transmissorId,
            true
        );


    try {

        await peer.setRemoteDescription(

            new RTCSessionDescription(
                mensagem.offer
            )
        );


        console.log(
            "RemoteDescription OFFER OK"
        );


        await adicionarIcePendentes(
            transmissorId
        );


        const answer =
            await peer.createAnswer();


        await peer.setLocalDescription(
            answer
        );


        enviarSocket({

            tipo:
                "answer",

            destino:
                transmissorId,

            answer:
                peer.localDescription

        });


        console.log(
            "ANSWER enviada."
        );


        statusTexto.textContent =
            "Recebendo transmissão...";


    } catch (erro) {

        console.error(
            "Erro processando OFFER:",
            erro
        );


        transmissaoAtual =
            null;


        statusTexto.textContent =
            "Erro ao conectar à transmissão.";
    }
}


// ======================================================
// RECEBER ANSWER
// ======================================================

async function receberAnswer(
    mensagem
) {

    const usuarioId =
        mensagem.origem;


    const peer =
        peers[
            usuarioId
        ];


    if (!peer) {

        console.error(
            "Peer não encontrado:",
            usuarioId
        );

        return;
    }


    try {

        if (
            peer.signalingState !==
            "have-local-offer"
        ) {

            console.log(
                "Answer ignorada:",
                peer.signalingState
            );

            return;
        }


        await peer.setRemoteDescription(

            new RTCSessionDescription(
                mensagem.answer
            )
        );


        console.log(
            "ANSWER aplicada:",
            usuarioId
        );


        await adicionarIcePendentes(
            usuarioId
        );


    } catch (erro) {

        console.error(
            "Erro ANSWER:",
            erro
        );
    }
}


// ======================================================
// RECEBER ICE
// ======================================================

async function receberIce(
    mensagem
) {

    const usuarioId =
        mensagem.origem;


    const candidato =
        mensagem.candidate;


    if (
        !usuarioId ||
        !candidato
    ) {

        return;
    }


    const peer =
        peers[
            usuarioId
        ];


    if (
        !peer ||
        !peer.remoteDescription ||
        !peer.remoteDescription.type
    ) {

        if (
            !icePendentes[
                usuarioId
            ]
        ) {

            icePendentes[
                usuarioId
            ] = [];
        }


        icePendentes[
            usuarioId
        ].push(
            candidato
        );


        console.log(
            "ICE guardado:",
            usuarioId
        );


        return;
    }


    try {

        await peer.addIceCandidate(

            new RTCIceCandidate(
                candidato
            )
        );


        console.log(
            "ICE remoto OK:",
            usuarioId
        );


    } catch (erro) {

        console.error(
            "Erro ICE:",
            erro
        );
    }
}


// ======================================================
// CRIAR PEER
// ======================================================

function criarPeer(
    usuarioId,
    receberVideo
) {

    console.log(
        "Criando Peer:",
        usuarioId
    );


    const peer =
        new RTCPeerConnection(
            configuracaoRTC
        );


    peers[
        usuarioId
    ] = peer;


    // ==================================================
    // ICE LOCAL
    // ==================================================

    peer.onicecandidate =
        evento => {

            if (!evento.candidate) {

                console.log(
                    "ICE gathering completo."
                );

                return;
            }


            console.log(
                "ICE LOCAL:",
                {
                    tipo:
                        evento.candidate.type,

                    protocolo:
                        evento.candidate.protocol,

                    endereco:
                        evento.candidate.address,

                    porta:
                        evento.candidate.port
                }
            );


            enviarSocket({

                tipo:
                    "ice",

                destino:
                    usuarioId,

                candidate:
                    evento.candidate.toJSON
                        ? evento.candidate.toJSON()
                        : evento.candidate
            });
        };


    // ==================================================
    // RECEBER TRACK
    // ==================================================

    if (receberVideo) {

        peer.ontrack =
            evento => {

                console.log(
                    "TRACK RECEBIDA:",
                    evento.track.kind
                );


                if (!streamRemoto) {

                    streamRemoto =
                        new MediaStream();
                }


                const existe =
                    streamRemoto
                        .getTracks()
                        .some(
                            track =>
                                track.id ===
                                evento.track.id
                        );


                if (!existe) {

                    streamRemoto.addTrack(
                        evento.track
                    );
                }


                if (video) {

                    video.srcObject =
                        streamRemoto;


                    video.muted =
                        false;


                    video.controls =
                        true;


                    video.autoplay =
                        true;


                    video.play()
                        .then(
                            () => {

                                console.log(
                                    "Vídeo reproduzindo."
                                );
                            }
                        )
                        .catch(
                            erro => {

                                console.log(
                                    "Autoplay:",
                                    erro
                                );


                                statusTexto.textContent =
                                    "Conectado. Toque no vídeo.";
                            }
                        );
                }


                statusTexto.textContent =
                    "Assistindo transmissão";
            };
    }


    // ==================================================
    // WEBRTC
    // ==================================================

    peer.onconnectionstatechange =
        () => {

            const estado =
                peer.connectionState;


            console.log(
                "WEBRTC:",
                usuarioId,
                estado
            );


            if (
                estado === "connected"
            ) {

                statusTexto.textContent =
                    receberVideo
                        ? "Assistindo transmissão"
                        : "Espectador conectado";
            }


            if (
                estado === "failed"
            ) {

                console.error(
                    "WEBRTC FAILED:",
                    usuarioId
                );


                if (receberVideo) {

                    transmissaoAtual =
                        null;


                    statusTexto.textContent =
                        "Falha ao conectar à transmissão.";
                }
            }
        };


    // ==================================================
    // ICE STATE
    // ==================================================

    peer.oniceconnectionstatechange =
        () => {

            console.log(
                "ICE STATE:",
                usuarioId,
                peer.iceConnectionState
            );


            if (
                peer.iceConnectionState ===
                "failed"
            ) {

                console.error(
                    "ICE FAILED:",
                    usuarioId
                );
            }
        };


    // ==================================================
    // ICE GATHERING
    // ==================================================

    peer.onicegatheringstatechange =
        () => {

            console.log(
                "ICE GATHERING:",
                usuarioId,
                peer.iceGatheringState
            );
        };


    // ==================================================
    // SIGNALING
    // ==================================================

    peer.onsignalingstatechange =
        () => {

            console.log(
                "SIGNALING:",
                usuarioId,
                peer.signalingState
            );
        };


    return peer;
}


// ======================================================
// ICE PENDENTE
// ======================================================

async function adicionarIcePendentes(
    usuarioId
) {

    const peer =
        peers[
            usuarioId
        ];


    const candidatos =
        icePendentes[
            usuarioId
        ];


    if (
        !peer ||
        !candidatos ||
        candidatos.length === 0
    ) {

        return;
    }


    console.log(
        "Processando ICE pendente:",
        candidatos.length
    );


    for (
        const candidato
        of candidatos
    ) {

        try {

            await peer.addIceCandidate(

                new RTCIceCandidate(
                    candidato
                )
            );


            console.log(
                "ICE pendente OK."
            );


        } catch (erro) {

            console.error(
                "Erro ICE pendente:",
                erro
            );
        }
    }


    delete icePendentes[
        usuarioId
    ];
}


// ======================================================
// ENVIAR SOCKET
// ======================================================

function enviarSocket(
    dados
) {

    if (
        !socket ||
        socket.readyState !==
            WebSocket.OPEN
    ) {

        console.error(
            "WebSocket fechado:",
            dados
        );

        return false;
    }


    try {

        socket.send(
            JSON.stringify(
                dados
            )
        );


        return true;

    } catch (erro) {

        console.error(
            "Erro enviando socket:",
            erro
        );


        return false;
    }
}


// ======================================================
// FECHAR PEER
// ======================================================

function fecharPeer(
    usuarioId
) {

    const peer =
        peers[
            usuarioId
        ];


    if (peer) {

        try {

            peer.onicecandidate =
                null;


            peer.ontrack =
                null;


            peer.onconnectionstatechange =
                null;


            peer.oniceconnectionstatechange =
                null;


            peer.onsignalingstatechange =
                null;


            peer.close();

        } catch (erro) {

            console.error(
                "Erro fechando peer:",
                erro
            );
        }


        delete peers[
            usuarioId
        ];
    }


    delete icePendentes[
        usuarioId
    ];
}


// ======================================================
// FECHAR TODOS
// ======================================================

function fecharTodosPeers() {

    Object.keys(
        peers
    ).forEach(
        usuarioId => {

            fecharPeer(
                usuarioId
            );
        }
    );


    transmissaoAtual =
        null;


    streamRemoto =
        null;
}


// ======================================================
// SAIR DA PÁGINA
// ======================================================

window.addEventListener(
    "beforeunload",
    () => {

        pararHeartbeat();

        fecharTodosPeers();


        if (
            socket &&
            socket.readyState ===
                WebSocket.OPEN
        ) {

            try {

                socket.close(
                    1000,
                    "Página encerrada"
                );

            } catch (erro) {

                console.log(
                    erro
                );
            }
        }
    }
);


// ======================================================
// INICIAR
// ======================================================

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        iniciarPagina
    );

} else {

    iniciarPagina();
}