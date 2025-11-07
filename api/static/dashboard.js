// api/static/dashboard.js
const API_URL = 'http://localhost:5000/api';

let videoStream = null;
let capturedImageData = null;
let notifications = [];

// =============================================================================
// INICIALIZACIÓN
// =============================================================================

document.addEventListener('DOMContentLoaded', init);

function init() {
    loadStats();
    loadDetecciones();
    loadActivity();
    startLiveSimulation();

    // Auto-refresh cada 30 segundos
    setInterval(() => {
        loadStats();
        loadDetecciones();
        checkNewEvents();
    }, 30000);
}

// =============================================================================
// NOTIFICACIONES EN TIEMPO REAL
// =============================================================================

async function checkNewEvents() {
    try {
        const response = await fetch(`${API_URL}/eventos`);
        const data = await response.json();

        if (data.success) {
            const newEvents = data.data.filter(e => !notifications.includes(e.id));

            if (newEvents.length > 0) {
                newEvents.forEach(event => {
                    showNotification(
                        '🚨 Nuevo Evento',
                        `${event.tipo}: ${event.descripcion}`,
                        'error'
                    );
                    notifications.push(event.id);
                });

                // Actualizar contador
                document.getElementById('notificationCount').textContent = notifications.length;
            }
        }
    } catch (error) {
        console.error('Error verificando eventos:', error);
    }
}

function toggleNotifications() {
    showNotification('Notificaciones', `Tienes ${notifications.length} eventos pendientes`, 'success');
}

function showNotification(title, message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');

    toast.className = `toast ${type} active`;
    toastTitle.textContent = title;
    toastMessage.textContent = message;

    setTimeout(() => {
        toast.classList.remove('active');
    }, 5000);
}

// =============================================================================
// ESTADÍSTICAS
// =============================================================================

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/dashboard/stats`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('statPersonas').textContent = data.data.personas_registradas;
            document.getElementById('statDetecciones').textContent = data.data.detecciones_hoy;
            document.getElementById('statDesconocidos').textContent = data.data.desconocidos_hoy;
            document.getElementById('statEventos').textContent = data.data.eventos_pendientes;

            // Actualizar notificaciones
            document.getElementById('notificationCount').textContent = data.data.eventos_pendientes;
        }
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

// =============================================================================
// DETECCIONES
// =============================================================================

async function loadDetecciones() {
    try {
        const response = await fetch(`${API_URL}/detecciones?limit=20`);
        const data = await response.json();

        const container = document.getElementById('deteccionesList');

        if (data.success && data.data.length > 0) {
            container.innerHTML = data.data.map(det => `
                <div class="detection-item">
                    <div class="detection-avatar">
                        ${det.nombre.charAt(0).toUpperCase()}
                    </div>
                    <div class="detection-info">
                        <div class="detection-name">${det.nombre} ${det.apellido || ''}</div>
                        <div class="detection-time">${formatDate(det.timestamp)}</div>
                    </div>
                    <span class="badge ${det.es_desconocido ? 'badge-danger' : 'badge-success'}">
                        ${det.es_desconocido ? '⚠️ Desconocido' : '✓ Conocido'}
                    </span>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No hay detecciones recientes</p>';
        }
    } catch (error) {
        console.error('Error cargando detecciones:', error);
    }
}

// =============================================================================
// PERSONAS
// =============================================================================

async function loadPersonas() {
    try {
        const response = await fetch(`${API_URL}/personas`);
        const data = await response.json();

        const container = document.getElementById('personasList');

        if (data.success && data.data.length > 0) {
            container.innerHTML = data.data.map(persona => `
                <div class="detection-item">
                    <div class="detection-avatar">
                        ${persona.nombre.charAt(0).toUpperCase()}
                    </div>
                    <div class="detection-info">
                        <div class="detection-name">${persona.nombre_completo}</div>
                        <div class="detection-time">
                            ${persona.tipo} • Registrado: ${formatDate(persona.fecha_registro)}
                        </div>
                    </div>
                    <span class="badge badge-success">✓ Activo</span>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No hay personas registradas</p>';
        }
    } catch (error) {
        console.error('Error cargando personas:', error);
    }
}

function openAddPersonModal() {
    document.getElementById('addPersonModal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
    if (videoStream) {
        stopCamera();
    }
}

async function startCamera() {
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('videoPreview');
        video.srcObject = videoStream;
        video.style.display = 'block';

        document.getElementById('captureBtn').style.display = 'inline-block';

        showNotification('Cámara', 'Cámara activada. Colócate frente a ella y presiona Capturar', 'success');
    } catch (error) {
        console.error('Error accediendo a la cámara:', error);
        showNotification('Error', 'No se pudo acceder a la cámara', 'error');
    }
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
        document.getElementById('videoPreview').style.display = 'none';
    }
}

function capturePhoto() {
    const video = document.getElementById('videoPreview');
    const canvas = document.getElementById('captureCanvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    capturedImageData = canvas.toDataURL('image/jpeg');

    const img = document.getElementById('capturedImage');
    img.src = capturedImageData;
    img.style.display = 'block';

    video.style.display = 'none';
    document.getElementById('captureBtn').style.display = 'none';
    document.getElementById('retakeBtn').style.display = 'inline-block';

    stopCamera();

    showNotification('Foto Capturada', 'Foto capturada correctamente', 'success');
}

function retakePhoto() {
    capturedImageData = null;
    document.getElementById('capturedImage').style.display = 'none';
    document.getElementById('retakeBtn').style.display = 'none';
    startCamera();
}

async function submitNewPerson(event) {
    event.preventDefault();

    if (!capturedImageData) {
        showNotification('Error', 'Debes capturar una foto', 'error');
        return;
    }

    const formData = {
        nombre: document.getElementById('personNombre').value,
        apellido: document.getElementById('personApellido').value,
        tipo: document.getElementById('personTipo').value,
        notas: document.getElementById('personNotas').value,
        imagen: capturedImageData
    };

    try {
        const response = await fetch(`${API_URL}/personas`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Éxito', 'Persona registrada correctamente', 'success');
            closeModal('addPersonModal');
            document.getElementById('addPersonForm').reset();
            capturedImageData = null;
            loadPersonas();
            loadStats();
        } else {
            showNotification('Error', data.error, 'error');
        }
    } catch (error) {
        console.error('Error registrando persona:', error);
        showNotification('Error', 'Error al registrar persona', 'error');
    }
}

async function exportPersonas() {
    showNotification('Exportando', 'Generando archivo Excel...', 'success');

    try {
        const response = await fetch(`${API_URL}/personas`);
        const data = await response.json();

        if (data.success) {
            const csv = generateCSV(data.data);
            downloadFile(csv, 'personas_registradas.csv', 'text/csv');
            showNotification('Éxito', 'Archivo exportado correctamente', 'success');
        }
    } catch (error) {
        console.error('Error exportando:', error);
        showNotification('Error', 'Error al exportar', 'error');
    }
}

// =============================================================================
// EVENTOS
// =============================================================================

async function loadEventos() {
    try {
        const response = await fetch(`${API_URL}/eventos`);
        const data = await response.json();

        const container = document.getElementById('eventosList');

        if (data.success && data.data.length > 0) {
            container.innerHTML = data.data.map(evento => `
                <div style="padding: 15px; border-left: 4px solid ${evento.severidad === 'alta' ? '#c62828' : '#667eea'}; background: ${evento.severidad === 'alta' ? '#ffebee' : '#f8f9ff'}; margin-bottom: 10px; border-radius: 5px;">
                    <div style="font-weight: bold; color: #333; margin-bottom: 5px;">
                        ${evento.severidad === 'alta' ? '🚨' : '⚠️'} ${evento.tipo}
                    </div>
                    <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">
                        ${formatDate(evento.timestamp)}
                    </div>
                    <p style="margin-top: 5px; font-size: 0.9em;">${evento.descripcion}</p>
                    <button class="btn btn-success" style="margin-top: 10px;" onclick="resolverEvento(${evento.id})">
                        ✓ Resolver
                    </button>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No hay eventos pendientes</p>';
        }
    } catch (error) {
        console.error('Error cargando eventos:', error);
    }
}

async function resolverEvento(eventoId) {
    try {
        const response = await fetch(`${API_URL}/eventos/${eventoId}/resolver`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ notas: 'Resuelto desde dashboard' })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Éxito', 'Evento resuelto correctamente', 'success');
            loadEventos();
            loadStats();
        }
    } catch (error) {
        console.error('Error resolviendo evento:', error);
    }
}

// =============================================================================
// CÁMARA EN VIVO (SIMULADA)
// =============================================================================

function startLiveSimulation() {
    const canvas = document.getElementById('liveCanvas');
    const ctx = canvas.getContext('2d');

    function drawFrame() {
        // Fondo degradado
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, '#1a1a2e');
        gradient.addColorStop(1, '#16213e');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Grid de fondo
        ctx.strokeStyle = 'rgba(102, 126, 234, 0.1)';
        ctx.lineWidth = 1;
        for (let i = 0; i < canvas.width; i += 40) {
            ctx.beginPath();
            ctx.moveTo(i, 0);
            ctx.lineTo(i, canvas.height);
            ctx.stroke();
        }
        for (let i = 0; i < canvas.height; i += 40) {
            ctx.beginPath();
            ctx.moveTo(0, i);
            ctx.lineTo(canvas.width, i);
            ctx.stroke();
        }

        // Texto central
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.font = '24px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('🎥 SISTEMA DE DETECCIÓN ACTIVO', canvas.width / 2, canvas.height / 2 - 40);

        ctx.font = '16px Arial';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.fillText('Esperando conexión con cámara...', canvas.width / 2, canvas.height / 2);

        // Timestamp
        ctx.font = '14px monospace';
        ctx.textAlign = 'left';
        ctx.fillStyle = '#667eea';
        ctx.fillText(new Date().toLocaleString('es-MX'), 20, canvas.height - 20);

        // Indicador de FPS
        ctx.textAlign = 'right';
        ctx.fillText('FPS: 30', canvas.width - 20, canvas.height - 20);

        requestAnimationFrame(drawFrame);
    }

    drawFrame();
}

// =============================================================================
// EXPORTAR REPORTES
// =============================================================================

async function exportPDF() {
    showNotification('Generando', 'Creando reporte PDF...', 'success');

    try {
        const response = await fetch(`${API_URL}/detecciones?limit=1000`);
        const data = await response.json();

        if (data.success) {
            const content = generatePDFContent(data.data);
            downloadFile(content, 'reporte_detecciones.txt', 'text/plain');
            showNotification('Éxito', 'Reporte generado (formato simplificado)', 'success');
        }
    } catch (error) {
        showNotification('Error', 'Error al generar reporte', 'error');
    }
}

async function exportExcel() {
    showNotification('Generando', 'Creando archivo Excel...', 'success');

    try {
        const response = await fetch(`${API_URL}/detecciones?limit=1000`);
        const data = await response.json();

        if (data.success) {
            const csv = generateCSV(data.data);
            downloadFile(csv, 'detecciones.csv', 'text/csv');
            showNotification('Éxito', 'Archivo Excel generado', 'success');
        }
    } catch (error) {
        showNotification('Error', 'Error al generar Excel', 'error');
    }
}

async function exportEventosPDF() {
    showNotification('Generando', 'Creando reporte de eventos...', 'success');

    try {
        const response = await fetch(`${API_URL}/eventos`);
        const data = await response.json();

        if (data.success) {
            const content = generateEventosPDFContent(data.data);
            downloadFile(content, 'reporte_eventos.txt', 'text/plain');
            showNotification('Éxito', 'Reporte generado', 'success');
        }
    } catch (error) {
        showNotification('Error', 'Error al generar reporte', 'error');
    }
}

async function exportEventosExcel() {
    showNotification('Generando', 'Creando archivo Excel de eventos...', 'success');

    try {
        const response = await fetch(`${API_URL}/eventos`);
        const data = await response.json();

        if (data.success) {
            const csv = generateEventosCSV(data.data);
            downloadFile(csv, 'eventos.csv', 'text/csv');
            showNotification('Éxito', 'Archivo Excel generado', 'success');
        }
    } catch (error) {
        showNotification('Error', 'Error al generar Excel', 'error');
    }
}

async function exportStatsPDF() {
    showNotification('Generando', 'Creando reporte de estadísticas...', 'success');

    try {
        const response = await fetch(`${API_URL}/dashboard/stats`);
        const data = await response.json();

        if (data.success) {
            const content = generateStatsPDFContent(data.data);
            downloadFile(content, 'reporte_estadisticas.txt', 'text/plain');
            showNotification('Éxito', 'Reporte generado', 'success');
        }
    } catch (error) {
        showNotification('Error', 'Error al generar reporte', 'error');
    }
}

function generateCSV(data) {
    if (!data || data.length === 0) return '';

    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(item => Object.values(item).join(',')).join('\n');

    return `${headers}\n${rows}`;
}

function generateEventosCSV(data) {
    const headers = 'ID,Tipo,Severidad,Descripcion,Timestamp,Camara,Resuelto\n';
    const rows = data.map(e =>
        `${e.id},"${e.tipo}","${e.severidad}","${e.descripcion}","${e.timestamp}","${e.camara_nombre}",${e.resuelto}`
    ).join('\n');

    return headers + rows;
}

function generatePDFContent(data) {
    let content = '=== REPORTE DE DETECCIONES ===\n\n';
    content += `Generado: ${new Date().toLocaleString('es-MX')}\n`;
    content += `Total de detecciones: ${data.length}\n\n`;
    content += '─'.repeat(70) + '\n\n';

    data.forEach((det, idx) => {
        content += `${idx + 1}. ${det.nombre} ${det.apellido || ''}\n`;
        content += `   Fecha: ${det.timestamp}\n`;
        content += `   Estado: ${det.es_desconocido ? 'DESCONOCIDO' : 'CONOCIDO'}\n`;
        content += `   Confianza: ${(det.confianza * 100).toFixed(1)}%\n`;
        content += '\n';
    });

    return content;
}

function generateEventosPDFContent(data) {
    let content = '=== REPORTE DE EVENTOS ===\n\n';
    content += `Generado: ${new Date().toLocaleString('es-MX')}\n`;
    content += `Total de eventos: ${data.length}\n\n`;
    content += '─'.repeat(70) + '\n\n';

    data.forEach((evento, idx) => {
        content += `${idx + 1}. ${evento.tipo}\n`;
        content += `   Severidad: ${evento.severidad.toUpperCase()}\n`;
        content += `   Fecha: ${evento.timestamp}\n`;
        content += `   Descripción: ${evento.descripcion}\n`;
        content += '\n';
    });

    return content;
}

function generateStatsPDFContent(stats) {
    let content = '=== REPORTE DE ESTADÍSTICAS ===\n\n';
    content += `Generado: ${new Date().toLocaleString('es-MX')}\n\n`;
    content += '─'.repeat(70) + '\n\n';
    content += `Personas Registradas: ${stats.personas_registradas}\n`;
    content += `Detecciones Hoy: ${stats.detecciones_hoy}\n`;
    content += `Personas Únicas Hoy: ${stats.personas_unicas_hoy}\n`;
    content += `Desconocidos Hoy: ${stats.desconocidos_hoy}\n`;
    content += `Eventos Pendientes: ${stats.eventos_pendientes}\n`;
    content += `Cámaras Activas: ${stats.camaras_activas}\n`;

    return content;
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// =============================================================================
// CONFIGURACIÓN
// =============================================================================

async function loadConfig() {
    try {
        const response = await fetch(`${API_URL}/configuracion`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('configAlertas').checked = data.data.activar_alertas;
            document.getElementById('configFrames').checked = data.data.guardar_frames;
            document.getElementById('configUmbral').value = data.data.umbral_confianza;
            document.getElementById('configRetencion').value = data.data.dias_retencion_imagenes;

            showNotification('Configuración', 'Configuración cargada correctamente', 'success');
        }
    } catch (error) {
        console.error('Error cargando configuración:', error);
    }
}

async function updateConfig(key, value) {
    try {
        const response = await fetch(`${API_URL}/configuracion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ [key]: value })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Guardado', 'Configuración actualizada', 'success');
        }
    } catch (error) {
        console.error('Error actualizando configuración:', error);
    }
}

async function saveAllConfig() {
    const config = {
        activar_alertas: document.getElementById('configAlertas').checked ? '1' : '0',
        guardar_frames: document.getElementById('configFrames').checked ? '1' : '0',
        umbral_confianza: document.getElementById('configUmbral').value,
        dias_retencion_imagenes: document.getElementById('configRetencion').value
    };

    try {
        const response = await fetch(`${API_URL}/configuracion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Éxito', 'Toda la configuración ha sido guardada', 'success');
        }
    } catch (error) {
        console.error('Error guardando configuración:', error);
        showNotification('Error', 'Error al guardar configuración', 'error');
    }
}

// =============================================================================
// NAVEGACIÓN Y UTILIDADES
// =============================================================================

function showTab(tabName) {
    document.querySelectorAll('[id^="tab-"]').forEach(tab => {
        tab.style.display = 'none';
    });

    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    document.getElementById(`tab-${tabName}`).style.display = 'block';
    event.target.classList.add('active');

    if (tabName === 'personas') {
        loadPersonas();
    } else if (tabName === 'eventos') {
        loadEventos();
    } else if (tabName === 'config') {
        loadConfig();
    }
}

async function loadActivity() {
    const container = document.getElementById('activityList');
    container.innerHTML = `
        <div style="text-align: center; padding: 20px; color: #999;">
            <p style="font-size: 2em;">📊</p>
            <p style="margin-top: 10px;">Actividad del sistema</p>
            <p style="margin-top: 5px; font-size: 0.9em;">Monitoreo en tiempo real</p>
        </div>
    `;
}

function formatDate(dateString) {
    if (!dateString || dateString === 'N/A') return 'N/A';
    try {
        return new Date(dateString).toLocaleString('es-MX');
    } catch {
        return dateString;
    }
}