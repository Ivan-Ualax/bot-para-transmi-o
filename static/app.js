// ======================================================
// CONFIGURAÇÃO GERAL
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

console.log(
    "Sala:",
    codigoSala
);


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
// COLOQUE AQUI SUA CREDENCIAL ATUAL DA METERED.
//
// Depois que tudo funcionar,
// gere outra credencial antes de publicar.
//
// Não compartilhe a nova credencial publicamente.
//

// ======================================================
// TURN - METERED
// ======================================================

const TURN_USERNAME =
    "713568c33df25731fe8641aa";

const TURN_CREDENTIAL =
    "bgZWM4k7aXiBuZ3i";


// ======================================================
// CONFIGURAÇÃO WEBRTC
// ======================================================

const configuracaoRTC = {

    iceServers: [

        // STUN
        {
            urls:
                "stun:stun.relay.metered.ca:80"
        },

        // TURN UDP
        {
            urls:
                "turn:br.relay.metered.ca:80",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        },

        // TURN TCP
        {
            urls:
                "turn:br.relay.metered.ca:80?transport=tcp",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        },

        // TURN 443
        {
            urls:
                "turn:br.relay.metered.ca:443",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        },

        // TURN TLS
        {
            urls:
                "turns:br.relay.metered.ca:443?transport=tcp",

            username:
                TURN_USERNAME,

            credential:
                TURN_CREDENTIAL
        }

    ],

    // Força o uso do TURN durante o teste
    iceTransportPolicy:
        "relay",

    bundlePolicy:
        "max-bundle",

    rtcpMuxPolicy:
        "require"
};


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
// COPIAR CONVITE
// ======================================================

async function copiarConvite() {

    try {

        await navigator.clipboard.writeText(
            window.location.href
        );


        if (botaoCopiar) {

            botaoCopiar.textContent =
                "Link copiado!";


            setTimeout(
                () => {

                    botaoCopiar.textContent =
                        "Copiar convite";

                },
                2000
            );
        }


    } catch (erro) {

        console.error(
            "Erro ao copiar convite:",
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


    if (!nomeInput) {

        console.error(
            "Campo nome não encontrado."
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


        if (botaoEntrar) {

            botaoEntrar.disabled =
                false;
        }


        atualizarStatus(
            "Erro ao conectar."
        );


        return;
    }


    // ==================================================
    // SOCKET CONECTADO
    // ==================================================

    socket.onopen =
        () => {

            console.log(
                "WebSocket conectado."
            );


            socket.send(
                JSON.stringify({
                    nome:
                        meuNome
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


            atualizarStatus(
                `Conectado como ${meuNome}`
            );


            iniciarHeartbeat();
        };


    // ==================================================
    // ERRO
    // ==================================================

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


    // ==================================================
    // FECHOU
    // ==================================================

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
                mensagem.usuarios ||
                []
            );


            atualizarTransmissoes(
                mensagem.transmissoes ||
                []
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


        // ==================================================
        // PONG
        // ==================================================

        case "pong":

            console.log(
                "PONG"
            );


            break;


        // ==================================================
        // ERRO
        // ==================================================

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
                usuario.id ===
                    meuId
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


                if (
                    transmissaoAtual ===
                        transmissao.usuario_id
                ) {

                    botao.textContent =
                        "Conectando...";

                    botao.disabled =
                        true;

                } else {

                    botao.textContent =
                        "Assistir";

                    botao.disabled =
                        false;
                }


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

                            ideal:
                                30,

                            max:
                                60
                        }
                    },

                    audio:
                        true
                });


        console.log(
            "TRACKS:",
            streamLocal
                .getTracks()
                .map(
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

                console.warn(
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


        atualizarStatus(
            "Transmitindo tela"
        );


        const trackVideo =
            streamLocal
                .getVideoTracks()[0];


        if (trackVideo) {

            trackVideo.onended =
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

    console.log(
        "ASSISTIR:",
        transmissorId
    );


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
// CRIAR OFFER
// ======================================================

async function criarOfertaParaEspectador(
    espectadorId
) {

    console.log(
        "Criando OFFER para:",
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
            "Erro processando OFFER:",
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
    // ERRO TURN / STUN
    // ==================================================

    peer.onicecandidateerror =
        evento => {

            const detalhes = {

                url:
                    evento.url ||
                    "não informado",

                codigo:
                    evento.errorCode ||
                    0,

                texto:
                    evento.errorText ||
                    "não informado",

                hostCandidate:
                    evento.hostCandidate ||
                    "não informado"
            };


            console.error(
                "ERRO ICE SERVER:\n" +
                JSON.stringify(
                    detalhes,
                    null,
                    2
                )
            );


            switch (
                evento.errorCode
            ) {

                case 400:

                    console.error(
                        "TURN 400: servidor respondeu, mas recusou/fracassou na alocação."
                    );

                    break;


                case 401:

                    console.error(
                        "TURN 401: usuário ou credential inválidos."
                    );

                    break;


                case 438:

                    console.error(
                        "TURN 438: credencial ou nonce expirado."
                    );

                    break;


                case 701:

                    console.error(
                        "TURN/STUN 701: endereço não resolvido ou servidor inacessível."
                    );

                    break;


                default:

                    console.error(
                        "Erro ICE:",
                        evento.errorCode,
                        evento.errorText
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
                    "ICE gathering completo."
                );


                return;
            }


            const candidato =
                evento.candidate;


            console.log(
                "ICE LOCAL:\n" +
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
    // TRACK REMOTA
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


                const trackExiste =
                    streamRemoto
                        .getTracks()
                        .some(
                            track =>
                                track.id ===
                                evento.track.id
                        );


                if (!trackExiste) {

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
    // CONNECTION STATE
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
                estado ===
                    "connected"
            ) {

                atualizarStatus(
                    receberVideo
                        ? "Assistindo transmissão"
                        : "Espectador conectado"
                );
            }


            if (
                estado ===
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


            if (
                estado ===
                    "disconnected"
            ) {

                console.warn(
                    "WEBRTC desconectado:",
                    usuarioId
                );
            }


            if (
                estado ===
                    "closed"
            ) {

                console.log(
                    "WEBRTC fechado:",
                    usuarioId
                );
            }
        };


    // ==================================================
    // ICE CONNECTION STATE
    // ==================================================

    peer.oniceconnectionstatechange =
        () => {

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
// ADICIONAR ICE PENDENTE
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
// ENVIAR WEBSOCKET
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
// SAÍDA DA PÁGINA
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
// START
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