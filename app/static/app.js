document.addEventListener("DOMContentLoaded", function () {
    console.log("PPE Local iniciado.");

    // Atualiza o feed de eventos em tempo real usando WebSocket
    const eventsList = document.getElementById("events-list");
    if (eventsList) {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/events`;
        const socket = new WebSocket(wsUrl);

        socket.onmessage = function (event) {
            const msg = JSON.parse(event.data);
            if (msg && msg.kind === "event" && msg.data) {
                addEventToList(msg.data);
            }
        };

        socket.onclose = function () {
            console.warn("Conexão WebSocket fechada. Tentando reconectar em 5s...");
            setTimeout(() => location.reload(), 5000);
        };
    }

    function addEventToList(ev) {
        if (!eventsList || !ev) return;

        // Cria item simples compatível com HTMX para abrir detalhe do evento (sem stream)
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.className = "text-blue-600 hover:underline";
        link.setAttribute("hx-get", `/monitoramento/event/${ev.id}`);
        link.setAttribute("hx-target", "#event-image");
        link.setAttribute("hx-swap", "innerHTML");

        const tsStr = ev.ts ? new Date(ev.ts).toLocaleString() : "";
        link.textContent = `${tsStr} - Câmera ${ev.camera_id}`;
        li.appendChild(link);

        eventsList.prepend(li);

        // Mantém apenas os 50 mais recentes
        while (eventsList.children.length > 50) {
            eventsList.removeChild(eventsList.lastChild);
        }
    }

    // Botão de exportar relatório (se existir)
    const exportBtn = document.getElementById("export-report");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            window.location.href = "/relatorios/export";
        });
    }

    // Destaque para câmeras offline (se houver marcadores na UI)
    document.querySelectorAll("[data-camera-status]").forEach(el => {
        if (el.dataset.cameraStatus === "offline") {
            el.classList.add("bg-red-200");
            el.title = "Câmera offline";
        }
    });
});
