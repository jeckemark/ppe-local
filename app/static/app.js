document.addEventListener("DOMContentLoaded", function () {
    console.log("PPE Local iniciado.");

    // Atualiza o feed de eventos em tempo real usando WebSocket
    const eventsList = document.getElementById("events-list");
    if (eventsList) {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/events`;
        const socket = new WebSocket(wsUrl);

        socket.onmessage = function (event) {
            const data = JSON.parse(event.data);
            addEventToList(data);
        };

        socket.onclose = function () {
            console.warn("Conexão WebSocket fechada. Tentando reconectar em 5s...");
            setTimeout(() => location.reload(), 5000);
        };
    }

    function addEventToList(eventData) {
        if (!eventsList) return;
        const item = document.createElement("div");
        item.classList.add("border", "p-2", "mb-2", "bg-white", "shadow-sm", "rounded");
        item.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <p class="text-sm font-semibold">${eventData.event_type}</p>
                    <p class="text-xs text-gray-500">${new Date(eventData.created_at).toLocaleString()}</p>
                </div>
                <img src="/${eventData.thumb_path}" alt="thumb" class="w-16 h-16 object-cover rounded">
            </div>
        `;
        eventsList.prepend(item);
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
