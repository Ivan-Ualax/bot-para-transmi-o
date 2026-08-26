// ======================================================
// CONFIGURAÇÃO
// ======================================================

const BASE_URL =
    "https://bot-para-transmi-o.vercel.app";

const SIGNALING_URL =
    "wss://bot-para-transmi-o.vercel.app";


const partes = window.location.pathname
    .split("/")
    .filter(Boolean);

const codigoSala =
    partes[1] || null;


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
// TURN - METERED
// ======================================================
//
// COLOQUE AQUI AS SUAS CREDENCIAIS NOVAS DA METERED.
//
// NÃO publique a credencial definitiva no GitHub.
//

const TURN_USERNAME =
    "f3be97deaec9a7ada83c98f8";

const TURN_CREDENTIAL =
    "WE4hYmTeprl6/ae2";


// ======================================================
// CONFIGURAÇÃO WEBRTC
// ======================================================

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
                "turn:global.relay.metered.ca:80?transport=udp",

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
                "turn:global.relay.metered.ca:443?transport=tcp",

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

    // TESTE TURN:
    // somente candidatos relay.
    //
    // Depois que funcionar,
    // podemos voltar para "all".

    iceTransportPolicy:
        "relay",

    bundlePolicy:
        "max-bundle",

    rtcpMuxPolicy:
        "require",

    iceCandidatePoolSize:
        4
};


// ======================================================
// INICIALIZAÇÃO
// ======================================================

function iniciarPagina() {

    console.log(
        "APP.JS carregado"
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


    if (botaoEntrar) {

        botaoEntrar.addEventListener(
            "click",
            conectar
        );
    }


    if (nomeInput) {

        nomeInput.addEventListener(
            "keydown",
            evento => {

                if (
                    evento.key ===
                    "Enter"
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
        "Entrando na sala..."
    );


    if (!codigoSala) {

        atualizarStatus(
            "Sala inválida."
        );

        return;
    }


    const nome =
        nomeInput?.value.trim();


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

        return;
    }


    meuNome =
        nome;


    if (botaoEntrar) {

        botaoEntrar.disabled =
            true;
    }


    atualizarStatus(
        "Conectando à sala..."
    );


    const endereco =
        `${SIGNALING_URL}/ws/${codigoSala}`;


    console.log(
        "WebSocket:",
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


        if (botaoEntrar) {

            botaoEntrar.disabled =
                false;
        }


        atualizarStatus(
            "Erro ao conectar."
        );


        return;
    }


    socket.onopen =
        () => {

            console.log(
                "WebSocket conectado."
            );


            enviarSocket({
                nome:
                    meuNome
            });


            if (entrada) {

                entrada.style.display =
                    "none";
            }


            if (painel) {

                painel.style.display =
                    "block";
            }


            atualizarStatus(
                `Conectado como ${meuNome}`
            );


            iniciarHeartbeat();
        };


    socket.onerror =
        erro => {

            console.error(
                "ERRO WEBSOCKET:",
                erro
            );


            if (botaoEntrar) {

                botaoEntrar.disabled =
                    false;
            }


            atualizarStatus(
                "Erro ao conectar ao servidor."
            );
        };


    socket.onclose =
        evento => {

            console.warn(
                "WebSocket fechado:",
                evento.code,
                evento.reason
            );


            pararHeartbeat();

            fecharTodosPeers();


            if (botaoEntrar) {

                botaoEntrar.disabled =
                    false;
            }


            atualizarStatus(
                "Desconectado do servidor."
            );
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
                        tipo:
                            "ping"
                    });
                }

            },
            25000
        );
}


function pararHeartbeat() {

    if (!heartbeat) {

        return;
    }


    clearInterval(
        heartbeat
    );


    heartbeat =
        null;
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

        case "meu_id":

            meuId =
                mensagem.id;


            console.log(
                "Meu ID:",
                meuId
            );


            break;


        case "estado":

            atualizarUsuarios(
                mensagem.usuarios || []
            );


            atualizarTransmissoes(
                mensagem.transmissoes || []
            );


            break;


        case "novo_espectador":

            console.log(
                "Novo espectador:",
                mensagem.espectador_id
            );


            if (!transmitindo) {

                return;
            }


            await criarOfertaParaEspectador(
                mensagem.espectador_id
            );


            break;


        case "offer":

            console.log(
                "OFFER recebida:",
                mensagem.origem
            );


            await receberOferta(
                mensagem
            );


            break;


        case "answer":

            console.log(
                "ANSWER recebida:",
                mensagem.origem
            );


            await receberAnswer(
                mensagem
            );


            break;


        case "ice":

            await receberIce(
                mensagem
            );


            break;


        case "pong":

            break;


        case "erro":

            console.error(
                "Erro servidor:",
                mensagem.mensagem
            );


            atualizarStatus(
                mensagem.mensagem ||
                "Erro no servidor."
            );


            break;
    }
}


// ======================================================
// STATUS
// ======================================================

function atualizarStatus(
    texto
) {

    console.log(
        "STATUS:",
        texto
    );


    if (statusTexto) {

        statusTexto.textContent =
            texto;
    }
}


// ======================================================
// USUÁRIOS
// ======================================================

function atualizarUsuarios(
    lista
) {

    if (!usuariosOnline) {

        return;
    }


    usuariosOnline.innerHTML =
        "";


    if (!lista.length) {

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


            item.textContent =
                usuario.id === meuId
                    ? `${usuario.nome} (você)`
                    : usuario.nome;


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


    if (!lista.length) {

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
                    transmissaoAtual ===
                    transmissao.usuario_id
                        ? "Conectando..."
                        : "Assistir";


                botao.disabled =
                    transmissaoAtual ===
                    transmissao.usuario_id;


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

        atualizarStatus(
            "Entre na sala primeiro."
        );

        return;
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices
            .getDisplayMedia
    ) {

        atualizarStatus(
            "Seu navegador não permite compartilhar tela."
        );

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

                    audio:
                        true
                });


        console.log(
            "Tracks:",
            streamLocal
                .getTracks()
                .map(
                    track => ({
                        kind:
                            track.kind,

                        label:
                            track.label
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


            await video.play()
                .catch(() => {});
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


        atualizarStatus(
            "Transmitindo tela"
        );


        const videoTrack =
            streamLocal
                .getVideoTracks()[0];


        if (videoTrack) {

            videoTrack.onended =
                pararTransmissao;
        }


    } catch (erro) {

        console.error(
            "Erro getDisplayMedia:",
            erro
        );


        atualizarStatus(
            "Erro ao iniciar transmissão."
        );
    }
}


// ======================================================
// PARAR
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


    atualizarStatus(
        "Transmissão encerrada"
    );
}


// ======================================================
// ASSISTIR
// ======================================================

function assistirTransmissao(
    transmissorId
) {

    if (
        !transmissorId ||
        transmissorId ===
            meuId
    ) {

        return;
    }


    if (
        !socket ||
        socket.readyState !==
            WebSocket.OPEN
    ) {

        atualizarStatus(
            "Servidor desconectado."
        );

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


    atualizarStatus(
        "Conectando à transmissão..."
    );


    enviarSocket({

        tipo:
            "assistir",

        transmissor_id:
            transmissorId
    });
}


// ======================================================
// OFFER
// ======================================================

async function criarOfertaParaEspectador(
    espectadorId
) {

    if (!streamLocal) {

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


        enviarSocket({

            tipo:
                "offer",

            destino:
                espectadorId,

            offer:
                peer.localDescription
        });


        console.log(
            "OFFER enviada:",
            espectadorId
        );


    } catch (erro) {

        console.error(
            "Erro OFFER:",
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
            "OFFER aplicada."
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


        atualizarStatus(
            "Recebendo transmissão..."
        );


    } catch (erro) {

        console.error(
            "Erro OFFER:",
            erro
        );


        transmissaoAtual =
            null;


        atualizarStatus(
            "Erro ao conectar à transmissão."
        );
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

            console.warn(
                "ANSWER ignorada:",
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
            "ICE pendente:",
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
            "Erro ICE remoto:",
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
    // ERRO DO TURN / ICE
    // ==================================================

    peer.onicecandidateerror =
        evento => {

            const erroIce = {

                url:
                    evento.url || null,

                codigo:
                    evento.errorCode || null,

                texto:
                    evento.errorText || null,

                hostCandidate:
                    evento.hostCandidate || null
            };


            // Assim o Chrome NÃO mostra só "Object".

            console.error(
                "ERRO ICE SERVER:",
                JSON.stringify(
                    erroIce,
                    null,
                    2
                )
            );


            if (
                evento.errorCode ===
                    401
            ) {

                console.error(
                    "TURN recusou usuário/senha."
                );
            }


            if (
                evento.errorCode ===
                    438
            ) {

                console.error(
                    "Credencial TURN expirada."
                );
            }


            if (
                evento.errorCode ===
                    701
            ) {

                console.error(
                    "Servidor TURN não pôde ser alcançado."
                );
            }
        };


    // ==================================================
    // ICE LOCAL
    // ==================================================

    peer.onicecandidate =
        evento => {

            if (!evento.candidate) {

                console.log(
                    "ICE gathering finalizado."
                );

                return;
            }


            const candidato =
                evento.candidate;


            console.log(
                "ICE LOCAL:",
                JSON.stringify(
                    {

                        tipo:
                            candidato.type,

                        protocolo:
                            candidato.protocol,

                        endereco:
                            candidato.address,

                        porta:
                            candidato.port

                    },
                    null,
                    2
                )
            );


            if (
                candidato.type ===
                    "relay"
            ) {

                console.log(
                    "✅ TURN RELAY OBTIDO"
                );
            }


            enviarSocket({

                tipo:
                    "ice",

                destino:
                    usuarioId,

                candidate:
                    candidato.toJSON
                        ? candidato.toJSON()
                        : candidato
            });
        };


    // ==================================================
    // TRACK
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
                        .catch(
                            erro => {

                                console.warn(
                                    "Autoplay bloqueado:",
                                    erro
                                );


                                atualizarStatus(
                                    "Conectado. Clique no vídeo."
                                );
                            }
                        );
                }
            };
    }


    // ==================================================
    // WEBRTC STATE
    // ==================================================

    peer.onconnectionstatechange =
        () => {

            console.log(
                "WEBRTC:",
                usuarioId,
                peer.connectionState
            );


            if (
                peer.connectionState ===
                    "connected"
            ) {

                atualizarStatus(
                    receberVideo
                        ? "Assistindo transmissão"
                        : "Espectador conectado"
                );
            }


            if (
                peer.connectionState ===
                    "failed"
            ) {

                console.error(
                    "WEBRTC FAILED:",
                    usuarioId
                );


                if (receberVideo) {

                    transmissaoAtual =
                        null;


                    atualizarStatus(
                        "Falha ao conectar à transmissão."
                    );
                }
            }
        };


    // ==================================================
    // ICE STATE
    // ==================================================

    peer.oniceconnectionstatechange =
        async () => {

            const estado =
                peer.iceConnectionState;


            console.log(
                "ICE STATE:",
                usuarioId,
                estado
            );


            if (
                estado ===
                    "connected" ||
                estado ===
                    "completed"
            ) {

                console.log(
                    "✅ ICE CONECTADO"
                );
            }


            if (
                estado ===
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
            "Erro enviando WebSocket:",
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

            peer.onicecandidateerror =
                null;

            peer.ontrack =
                null;

            peer.onconnectionstatechange =
                null;

            peer.oniceconnectionstatechange =
                null;

            peer.onicegatheringstatechange =
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
// SAIR
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