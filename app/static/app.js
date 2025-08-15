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
            if (msg.kind === "event") {
                addEventToList(msg.data);
            }
        };

        socket.onclose = function () {
            console.warn("Conexão WebSocket fechada. Tentando reconectar em 5s...");
            setTimeout(() => location.reload(), 5000);
        };
    }

    function addEventToList(ev) {
        if (!eventsList) return;
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.className = "text-blue-600 hover:underline";
        link.setAttribute("hx-get", `/monitoramento/event/${ev.id}`);
        link.setAttribute("hx-target", "#event-image");
        link.setAttribute("hx-swap", "innerHTML");
        const ts = new Date(ev.ts).toLocaleString();
        link.textContent = `${ts} - Câmera ${ev.camera_id}`;
        li.appendChild(link);
        eventsList.prepend(li);
        while (eventsList.children.length > 50) {
            eventsList.removeChild(eventsList.lastChild);
        }
    }

    // Botão de exportar relatório
    const exportBtn = document.getElementById("export-report");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            window.location.href = "/relatorios/export";
        });
    }

    // Notificação de câmera offline
    document.querySelectorAll("[data-camera-status]").forEach(el => {
        if (el.dataset.cameraStatus === "offline") {
            el.classList.add("bg-red-200");
            el.title = "Câmera offline";
        }
    });
});
