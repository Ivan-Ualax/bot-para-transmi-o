// ======================================================
// SALA
// ======================================================

const partes = window.location.pathname
    .split("/")
    .filter(Boolean);

const codigoSala = partes[1];

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

let transmitindo = false;

let transmissaoAtual = null;


// Peer por usuário:
//
// peers["id_usuario"] = RTCPeerConnection

const peers = {};


// ICE recebido antes de remoteDescription:
//
// icePendentes["id_usuario"] = []

const icePendentes = {};


// ======================================================
// WEBRTC
// ======================================================

// ======================================================
// WEBRTC - STUN + TURN METERED
// ======================================================

const configuracaoRTC = {

    iceServers: [

        // STUN
        {
            urls: "stun:stun.relay.metered.ca:80"
        },

        // TURN UDP
        {
            urls: "turn:global.relay.metered.ca:80",
            username: "f3be97deaec9a7ada83c98f8",
            credential: "WE4hYmTeprl6/ae2"
        },

        // TURN TCP
        {
            urls: "turn:global.relay.metered.ca:80?transport=tcp",
            username: "f3be97deaec9a7ada83c98f8",
            credential: "WE4hYmTeprl6/ae2"
        },

        // TURN porta 443
        {
            urls: "turn:global.relay.metered.ca:443",
            username: "f3be97deaec9a7ada83c98f8",
            credential: "WE4hYmTeprl6/ae2"
        },

        // TURN seguro
        {
            urls: "turns:global.relay.metered.ca:443?transport=tcp",
            username: "f3be97deaec9a7ada83c98f8",
            credential: "WE4hYmTeprl6/ae2"
        }

    ],

    iceTransportPolicy: "all",

    bundlePolicy: "max-bundle",

    rtcpMuxPolicy: "require"
};


// ======================================================
// MOSTRAR SALA
// ======================================================

if (codigoSalaTexto) {

    codigoSalaTexto.textContent =
        `Sala: ${codigoSala}`;
}


// ======================================================
// COPIAR LINK
// ======================================================

if (botaoCopiar) {

    botaoCopiar.addEventListener(
        "click",
        copiarConvite
    );
}


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
            "Erro ao copiar convite:",
            erro
        );

        alert(
            "Não foi possível copiar automaticamente."
        );
    }
}


// ======================================================
// ENTRAR
// ======================================================

botaoEntrar.addEventListener(
    "click",
    conectar
);


nomeInput.addEventListener(
    "keydown",
    evento => {

        if (evento.key === "Enter") {
            conectar();
        }
    }
);


function conectar() {

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


    const nome =
        nomeInput.value.trim();


    if (!nome) {

        alert(
            "Digite seu nome."
        );

        return;
    }


    meuNome = nome;


    botaoEntrar.disabled =
        true;


    const protocolo =
        window.location.protocol === "https:"
            ? "wss"
            : "ws";


    const endereco =
        `${protocolo}://${window.location.host}/ws/${codigoSala}`;


    console.log(
        "Conectando:",
        endereco
    );


    socket =
        new WebSocket(
            endereco
        );


    socket.onopen =
        () => {

            console.log(
                "WebSocket conectado"
            );


            socket.send(
                JSON.stringify({
                    nome: meuNome
                })
            );


            entrada.style.display =
                "none";


            painel.style.display =
                "block";


            statusTexto.textContent =
                `Conectado como ${meuNome}`;
        };


    socket.onerror =
        erro => {

            console.error(
                "Erro WebSocket:",
                erro
            );


            botaoEntrar.disabled =
                false;


            statusTexto.textContent =
                "Erro ao entrar na sala.";
        };


    socket.onclose =
        () => {

            console.log(
                "WebSocket desconectado"
            );


            fecharTodosPeers();


            statusTexto.textContent =
                "Desconectado do servidor.";
        };


    socket.onmessage =
        receberMensagem;
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
            "Mensagem inválida:",
            erro
        );

        return;
    }


    console.log(
        "Recebido:",
        mensagem.tipo
    );


    switch (
        mensagem.tipo
    ) {

        // ==========================================
        // MEU ID
        // ==========================================

        case "meu_id":

            meuId =
                mensagem.id;

            console.log(
                "Meu ID:",
                meuId
            );

            break;


        // ==========================================
        // ESTADO
        // ==========================================

        case "estado":

            atualizarUsuarios(
                mensagem.usuarios || []
            );

            atualizarTransmissoes(
                mensagem.transmissoes || []
            );

            break;


        // ==========================================
        // NOVO ESPECTADOR
        // ==========================================

        case "novo_espectador":

            if (!transmitindo) {

                console.log(
                    "Recebi espectador, " +
                    "mas não estou transmitindo."
                );

                return;
            }


            await criarOfertaParaEspectador(
                mensagem.espectador_id
            );

            break;


        // ==========================================
        // OFFER
        // ==========================================

        case "offer":

            await receberOferta(
                mensagem
            );

            break;


        // ==========================================
        // ANSWER
        // ==========================================

        case "answer":

            await receberAnswer(
                mensagem
            );

            break;


        // ==========================================
        // ICE
        // ==========================================

        case "ice":

            await receberIce(
                mensagem
            );

            break;


        // ==========================================
        // ERRO
        // ==========================================

        case "erro":

            alert(
                mensagem.mensagem
            );

            break;
    }
}


// ======================================================
// USUÁRIOS
// ======================================================

function atualizarUsuarios(
    lista
) {

    usuariosOnline.innerHTML =
        "";


    if (
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

    transmissoesDiv.innerHTML =
        "";


    if (
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


            // Não mostrar Assistir
            // na própria transmissão

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

botaoTransmitir.addEventListener(
    "click",
    iniciarTransmissao
);


async function iniciarTransmissao() {

    if (transmitindo) {
        return;
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getDisplayMedia
    ) {

        statusTexto.textContent =
            "Seu navegador não permite " +
            "compartilhamento de tela.";

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


        const tracks =
            streamLocal.getTracks();


        console.log(
            "Tracks capturadas:",
            tracks.map(
                track => ({
                    tipo:
                        track.kind,

                    nome:
                        track.label,

                    ativo:
                        track.enabled
                })
            )
        );


        video.srcObject =
            streamLocal;


        // Evita ouvir o próprio áudio
        video.muted =
            true;


        video.autoplay =
            true;


        transmitindo =
            true;


        enviarSocket({
            tipo:
                "iniciar_transmissao"
        });


        botaoTransmitir.style.display =
            "none";


        botaoParar.style.display =
            "inline-block";


        statusTexto.textContent =
            "Transmitindo tela";


        const trackVideo =
            streamLocal
                .getVideoTracks()[0];


        if (trackVideo) {

            trackVideo.onended =
                () => {

                    pararTransmissao();
                };
        }


    } catch (erro) {

        console.error(
            "Erro getDisplayMedia:",
            erro
        );


        statusTexto.textContent =
            "Erro ao iniciar transmissão.";
    }
}


// ======================================================
// PARAR TRANSMISSÃO
// ======================================================

botaoParar.addEventListener(
    "click",
    pararTransmissao
);


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


    video.srcObject =
        null;


    enviarSocket({
        tipo:
            "parar_transmissao"
    });


    botaoTransmitir.style.display =
        "inline-block";


    botaoParar.style.display =
        "none";


    statusTexto.textContent =
        "Transmissão encerrada";
}


// ======================================================
// ASSISTIR
// ======================================================

function assistirTransmissao(
    transmissorId
) {

    if (
        transmissorId ===
        meuId
    ) {

        return;
    }


    transmissaoAtual =
        transmissorId;


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
// TRANSMISSOR CRIA OFFER
// ======================================================

async function criarOfertaParaEspectador(
    espectadorId
) {

    if (!streamLocal) {

        console.log(
            "Sem stream para transmitir"
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


        enviarSocket({

            tipo:
                "offer",

            destino:
                espectadorId,

            offer:
                peer.localDescription
        });


        console.log(
            "Offer enviada para:",
            espectadorId
        );


    } catch (erro) {

        console.error(
            "Erro criando offer:",
            erro
        );
    }
}


// ======================================================
// ESPECTADOR RECEBE OFFER
// ======================================================

async function receberOferta(
    mensagem
) {

    const transmissorId =
        mensagem.origem;


    console.log(
        "Offer recebida de:",
        transmissorId
    );


    fecharPeer(
        transmissorId
    );


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
            "Offer aplicada"
        );


        await adicionarIcePendentes(
            transmissorId
        );


        const resposta =
            await peer.createAnswer();


        await peer.setLocalDescription(
            resposta
        );


        enviarSocket({

            tipo:
                "answer",

            destino:
                transmissorId,

            answer:
                peer.localDescription
        });


        statusTexto.textContent =
            "Recebendo transmissão...";


        console.log(
            "Answer enviada"
        );


    } catch (erro) {

        console.error(
            "Erro processando offer:",
            erro
        );


        transmissaoAtual =
            null;


        statusTexto.textContent =
            "Erro ao conectar à transmissão.";
    }
}


// ======================================================
// TRANSMISSOR RECEBE ANSWER
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
            "Peer não existe para answer:",
            usuarioId
        );

        return;
    }


    try {

        await peer.setRemoteDescription(
            new RTCSessionDescription(
                mensagem.answer
            )
        );


        console.log(
            "Answer aplicada:",
            usuarioId
        );


        await adicionarIcePendentes(
            usuarioId
        );


    } catch (erro) {

        console.error(
            "Erro aplicando answer:",
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


    if (!candidato) {
        return;
    }


    const peer =
        peers[
            usuarioId
        ];


    // ICE chegou cedo

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
            "ICE armazenado temporariamente:",
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
            "ICE remoto adicionado:",
            usuarioId
        );


    } catch (erro) {

        console.error(
            "Erro adicionando ICE:",
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

    const peer =
        new RTCPeerConnection(
            configuracaoRTC
        );


    peers[
        usuarioId
    ] = peer;


    console.log(
        "Peer criado:",
        usuarioId
    );


    // ==========================================
    // ICE LOCAL
    // ==========================================

    peer.onicecandidate =
        evento => {

            if (
                evento.candidate
            ) {

                console.log(
                    "ICE local:",
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


            } else {

                console.log(
                    "ICE gathering finalizado"
                );
            }
        };


    // ==========================================
    // TRACK
    // ==========================================

    if (receberVideo) {

        peer.ontrack =
            evento => {

                console.log(
                    "Track recebida:",
                    evento.track.kind
                );


                let stream =
                    evento.streams[0];


                if (!stream) {

                    stream =
                        new MediaStream(
                            [evento.track]
                        );
                }


                video.srcObject =
                    stream;


                video.muted =
                    false;


                video.controls =
                    true;


                const tentativa =
                    video.play();


                if (tentativa) {

                    tentativa
                        .then(
                            () => {

                                console.log(
                                    "Vídeo reproduzindo"
                                );

                            }
                        )
                        .catch(
                            erro => {

                                console.log(
                                    "Autoplay bloqueado:",
                                    erro
                                );


                                statusTexto.textContent =
                                    "Transmissão conectada. " +
                                    "Toque no vídeo para reproduzir.";
                            }
                        );
                }


                statusTexto.textContent =
                    "Assistindo transmissão";
            };
    }


    // ==========================================
    // CONNECTION STATE
    // ==========================================

    peer.onconnectionstatechange =
        () => {

            const estado =
                peer.connectionState;


            console.log(
                "WebRTC:",
                usuarioId,
                estado
            );


            if (
                estado === "connected"
            ) {

                if (receberVideo) {

                    statusTexto.textContent =
                        "Assistindo transmissão";

                } else {

                    statusTexto.textContent =
                        "Espectador conectado";
                }
            }


            if (
                estado === "failed"
            ) {

                console.error(
                    "WebRTC FAILED:",
                    usuarioId
                );


                if (receberVideo) {

                    transmissaoAtual =
                        null;


                    statusTexto.textContent =
                        "Falha ao conectar à transmissão.";
                }
            }


            if (
                estado === "closed"
            ) {

                console.log(
                    "Peer fechado:",
                    usuarioId
                );
            }
        };


    // ==========================================
    // ICE CONNECTION
    // ==========================================

    peer.oniceconnectionstatechange =
        () => {

            const estado =
                peer.iceConnectionState;


            console.log(
                "ICE connection:",
                usuarioId,
                estado
            );


            if (
                estado === "failed"
            ) {

                console.error(
                    "ICE FAILED"
                );
            }
        };


    // ==========================================
    // ICE GATHERING
    // ==========================================

    peer.onicegatheringstatechange =
        () => {

            console.log(
                "ICE gathering:",
                usuarioId,
                peer.iceGatheringState
            );
        };


    // ==========================================
    // SIGNALING
    // ==========================================

    peer.onsignalingstatechange =
        () => {

            console.log(
                "Signaling:",
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
                "ICE pendente adicionado"
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
            "WebSocket não está aberto:",
            dados.tipo
        );

        return false;
    }


    socket.send(
        JSON.stringify(
            dados
        )
    );


    return true;
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

            peer.close();

        } catch (erro) {

            console.log(
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
}