/**
 * Smart Day Planner — Frontend Application
 * Alpine.js reactive store + UI logic
 */

document.addEventListener("alpine:init", () => {
  Alpine.store("app", {
    // ── State ────────────────────────────────────────────
    currentDate: new Date().toISOString().split("T")[0],
    blocks: [],
    preferences: {
      wake_time: "07:00",
      sleep_time: "23:00",
      work_start: "09:00",
      work_end: "17:00",
      breakfast_duration: 30,
      lunch_duration: 60,
      dinner_duration: 45,
      exercise_enabled: true,
      exercise_duration: 60,
      study_enabled: true,
      study_duration: 90,
    },
    loading: false,
    showPrefs: false,
    editingBlock: null,
    showAddModal: false,
    newBlock: { start_time: "08:00", end_time: "09:00", title: "", category: "personal", description: "" },
    toast: { show: false, message: "", type: "success" },
    savedDates: [],

    // ── AI Agent State ────────────────────────────────────
    chatOpen: false,
    chatInput: "",
    agentLoading: false,
    isListening: false,
    isRecordingAudio: false,
    recordingSeconds: 0,
    recordingTimer: null,
    mediaRecorder: null,
    audioChunks: [],
    speechSupported: false,
    voiceResponseEnabled: true,
    recognition: null,
    messages: [
      {
        id: 1,
        sender: "agent",
        text: "¡Hola! 👋 Soy tu asistente personal de horario.\n\nPuedes escribirme o usar el **micrófono 🎙️** para decirme:\n• *agrega reunión de 10 a 11am*\n• *genera mi horario*\n• *elimina el ejercicio*\n• *mueve el estudio a las 18:00*\n• *¿qué tengo a las 14:00?*\n• *descarga el pdf*",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ],

    // ── Computed ──────────────────────────────────────────
    get hasBlocks() {
      return this.blocks.length > 0;
    },

    // ── Init ─────────────────────────────────────────────
    async init() {
      await this.loadPreferences();
      await this.loadSchedule();
      await this.loadDates();
      this.initSpeech();
    },

    // ── API helpers ──────────────────────────────────────
    async _fetch(url, options = {}) {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error" }));
        throw new Error(err.detail || "Request failed");
      }
      return res.json();
    },

    // ── Preferences ──────────────────────────────────────
    async loadPreferences() {
      try {
        const data = await this._fetch("/api/preferences");
        Object.assign(this.preferences, data);
      } catch (e) {
        console.error("Error loading preferences:", e);
      }
    },

    async savePreferences() {
      try {
        await this._fetch("/api/preferences", {
          method: "PUT",
          body: JSON.stringify(this.preferences),
        });
        this.showToast("Preferencias guardadas", "success");
      } catch (e) {
        this.showToast("Error al guardar preferencias", "error");
      }
    },

    // ── Schedule ─────────────────────────────────────────
    async loadSchedule() {
      this.loading = true;
      try {
        const data = await this._fetch(`/api/schedule/${this.currentDate}`);
        this.blocks = data.blocks || [];
      } catch (e) {
        console.error("Error loading schedule:", e);
        this.blocks = [];
      } finally {
        this.loading = false;
      }
    },

    async generateSchedule() {
      this.loading = true;
      try {
        await this.savePreferences();
        const data = await this._fetch(
          `/api/schedule/generate?target_date=${this.currentDate}`,
          { method: "POST", body: JSON.stringify(this.preferences) }
        );
        this.blocks = data.blocks || [];
        await this.loadDates();
        this.showToast("Horario generado exitosamente ✨", "success");
      } catch (e) {
        this.showToast("Error al generar horario", "error");
      } finally {
        this.loading = false;
      }
    },

    async loadDates() {
      try {
        const data = await this._fetch("/api/dates");
        this.savedDates = data.dates || [];
      } catch (e) {
        console.error("Error loading dates:", e);
      }
    },

    // ── Block CRUD ───────────────────────────────────────
    startEdit(block) {
      this.editingBlock = { ...block };
    },

    cancelEdit() {
      this.editingBlock = null;
    },

    async saveEdit() {
      if (!this.editingBlock) return;
      try {
        const { id, ...updates } = this.editingBlock;
        await this._fetch(`/api/schedule/block/${id}`, {
          method: "PUT",
          body: JSON.stringify(updates),
        });
        this.editingBlock = null;
        await this.loadSchedule();
        this.showToast("Bloque actualizado", "success");
      } catch (e) {
        this.showToast("Error al actualizar", "error");
      }
    },

    async deleteBlock(blockId) {
      try {
        await this._fetch(`/api/schedule/block/${blockId}`, {
          method: "DELETE",
        });
        await this.loadSchedule();
        this.showToast("Bloque eliminado", "success");
      } catch (e) {
        this.showToast("Error al eliminar", "error");
      }
    },

    openAddModal() {
      this.newBlock = {
        start_time: "08:00",
        end_time: "09:00",
        title: "",
        category: "personal",
        description: "",
      };
      this.showAddModal = true;
    },

    async addBlock() {
      try {
        await this._fetch("/api/schedule/block", {
          method: "POST",
          body: JSON.stringify({
            ...this.newBlock,
            schedule_date: this.currentDate,
          }),
        });
        this.showAddModal = false;
        await this.loadSchedule();
        this.showToast("Bloque agregado", "success");
      } catch (e) {
        this.showToast("Error al agregar bloque", "error");
      }
    },

    // ── Navigation ───────────────────────────────────────
    async changeDate(newDate) {
      this.currentDate = newDate;
      await this.loadSchedule();
    },

    async prevDay() {
      const d = new Date(this.currentDate + "T12:00:00");
      d.setDate(d.getDate() - 1);
      await this.changeDate(d.toISOString().split("T")[0]);
    },

    async nextDay() {
      const d = new Date(this.currentDate + "T12:00:00");
      d.setDate(d.getDate() + 1);
      await this.changeDate(d.toISOString().split("T")[0]);
    },

    // ── PDF ──────────────────────────────────────────────
    downloadPDF() {
      window.open(`/api/schedule/${this.currentDate}/pdf`, "_blank");
    },

    // ── Toast ────────────────────────────────────────────
    showToast(message, type = "success") {
      this.toast = { show: true, message, type };
      setTimeout(() => {
        this.toast.show = false;
      }, 3000);
    },

    // ── AI Agent Chat ─────────────────────────────────────
    toggleChat() {
      this.chatOpen = !this.chatOpen;
      if (this.chatOpen) {
        this.scrollChatBottom();
        setTimeout(() => {
          const input = document.getElementById("agent-chat-input");
          if (input) input.focus();
        }, 150);
      }
    },

    clearChat() {
      this.messages = [
        {
          id: Date.now(),
          sender: "agent",
          text: "Historial limpiado. ¿En qué te ayudo hoy con tu horario?",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ];
    },

    quickSend(text) {
      this.chatInput = text;
      this.sendMessage();
    },

    // ── Speech / Voice Capabilities ──────────────────────
    initSpeech() {
      // Check if MediaRecorder is available (100% browser standard)
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        this.speechSupported = true;
      } else {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.speechSupported = !!SpeechRecognition;
      }
    },

    async toggleVoiceInput() {
      // If currently recording, stop and process
      if (this.isRecordingAudio) {
        this.stopAudioRecording();
        return;
      }

      // 1. Primary method: MediaRecorder (works offline in browser, NO network error!)
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          await this.startAudioRecording();
          return;
        } catch (err) {
          console.warn("MediaRecorder access error:", err);
          if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
            this.showToast("Permiso de micrófono denegado. Permite el acceso al micro en tu navegador.", "error");
            return;
          }
        }
      }

      // 2. Fallback to browser SpeechRecognition if MediaRecorder is not available
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.startBrowserRecognition();
      } else {
        this.showToast("Tu navegador no soporta captura de audio.", "error");
      }
    },

    async startAudioRecording() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioChunks = [];

        let options = {};
        if (typeof MediaRecorder.isTypeSupported === "function") {
          if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            options = { mimeType: "audio/webm;codecs=opus" };
          } else if (MediaRecorder.isTypeSupported("audio/webm")) {
            options = { mimeType: "audio/webm" };
          } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
            options = { mimeType: "audio/ogg" };
          }
        }

        this.mediaRecorder = new MediaRecorder(stream, options);

        this.mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            this.audioChunks.push(e.data);
          }
        };

        this.mediaRecorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());
          clearInterval(this.recordingTimer);
          this.isRecordingAudio = false;
          this.isListening = false;

          const mimeType = this.mediaRecorder.mimeType || "audio/webm";
          const audioBlob = new Blob(this.audioChunks, { type: mimeType });

          if (audioBlob.size < 500) {
            this.showToast("Audio muy breve. Mantén presionado o habla más tiempo.", "error");
            return;
          }

          await this.sendAudioToServer(audioBlob);
        };

        this.mediaRecorder.start(250);
        this.isRecordingAudio = true;
        this.isListening = true;
        this.recordingSeconds = 0;

        // Auto-stop after 10 seconds of speech
        this.recordingTimer = setInterval(() => {
          this.recordingSeconds++;
          if (this.recordingSeconds >= 10) {
            this.stopAudioRecording();
          }
        }, 1000);
      } catch (err) {
        console.error("Error accessing microphone:", err);
        this.isRecordingAudio = false;
        this.isListening = false;
        if (err.name === "NotAllowedError") {
          this.showToast("Acceso al micrófono denegado. Habilita el permiso en tu navegador.", "error");
        } else {
          this.showToast("No se pudo iniciar el micrófono: " + err.message, "error");
        }
      }
    },

    stopAudioRecording() {
      if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
        try {
          this.mediaRecorder.stop();
        } catch (e) {
          console.warn("Error stopping recorder:", e);
        }
      }
      this.isRecordingAudio = false;
      this.isListening = false;
      clearInterval(this.recordingTimer);
    },

    async sendAudioToServer(audioBlob) {
      this.agentLoading = true;
      this.scrollChatBottom();

      const formData = new FormData();
      formData.append("audio_file", audioBlob, "recording.webm");
      formData.append("target_date", this.currentDate);

      try {
        const res = await fetch("/api/agent/voice", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Error en el servidor");
        }

        const data = await res.json();
        const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        if (data.transcription) {
          this.messages.push({
            id: Date.now(),
            sender: "user",
            text: data.transcription,
            time: now,
            fromVoice: true,
          });
        }

        this.messages.push({
          id: Date.now() + 1,
          sender: "agent",
          text: data.response || "Comando procesado.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          action: data.action,
        });

        if (this.voiceResponseEnabled) {
          this.speak(data.response || "");
        }

        if (data.blocks) {
          this.blocks = data.blocks;
        }
        if (data.dates) {
          this.savedDates = data.dates;
        }
        if (data.preferences) {
          Object.assign(this.preferences, data.preferences);
        }
        if (data.action === "download_pdf") {
          this.downloadPDF();
        }

        if (data.action && data.action !== "none") {
          this.showToast("Horario actualizado por voz ✨", "success");
        }
      } catch (err) {
        this.messages.push({
          id: Date.now() + 1,
          sender: "agent",
          text: "⚠️ " + err.message,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          error: true,
        });
      } finally {
        this.agentLoading = false;
        this.scrollChatBottom();
      }
    },

    startBrowserRecognition() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) return;

      const recognition = new SpeechRecognition();
      recognition.lang = "es-ES";
      recognition.interimResults = true;
      recognition.continuous = false;

      recognition.onstart = () => {
        this.isListening = true;
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        this.chatInput = transcript;
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        this.isListening = false;
        if (event.error === "network") {
          this.showToast("El navegador bloqueó Google Cloud Speech. Usando grabación de audio directa...", "info");
          this.startAudioRecording();
        } else if (event.error === "not-allowed") {
          this.showToast("Permiso de micrófono denegado en el navegador", "error");
        } else if (event.error !== "no-speech") {
          this.showToast("Error de voz: " + event.error, "error");
        }
      };

      recognition.onend = () => {
        this.isListening = false;
        if (this.chatInput && this.chatInput.trim()) {
          this.sendMessage(true);
        }
      };

      try {
        this.chatInput = "";
        recognition.start();
      } catch (e) {
        this.startAudioRecording();
      }
    },

    toggleVoiceResponse() {
      this.voiceResponseEnabled = !this.voiceResponseEnabled;
      if (!this.voiceResponseEnabled && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      this.showToast(
        this.voiceResponseEnabled ? "Voz del asistente activada 🔊" : "Voz del asistente silenciada 🔇",
        "success"
      );
    },

    speak(text) {
      if (!this.voiceResponseEnabled || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();

      let cleanText = text
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/\*(.*?)\*/g, "$1")
        .replace(/`([^`]+)`/g, "$1")
        .replace(/•/g, "")
        .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, "")
        .trim();

      if (!cleanText) return;

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = "es-ES";
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    },

    async sendMessage(fromVoice = false) {
      const text = this.chatInput ? this.chatInput.trim() : "";
      if (!text || this.agentLoading) return;

      const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

      // Add user message
      this.messages.push({
        id: Date.now(),
        sender: "user",
        text: text,
        time: now,
        fromVoice: fromVoice,
      });

      this.chatInput = "";
      this.agentLoading = true;
      this.scrollChatBottom();

      try {
        const data = await this._fetch("/api/agent/chat", {
          method: "POST",
          body: JSON.stringify({
            message: text,
            target_date: this.currentDate,
          }),
        });

        // Add agent response
        this.messages.push({
          id: Date.now() + 1,
          sender: "agent",
          text: data.response || "Comando procesado.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          action: data.action,
        });

        // Speak response if voice response is enabled or user spoke
        if (fromVoice || this.voiceResponseEnabled) {
          this.speak(data.response || "");
        }

        // Update schedule if returned
        if (data.blocks) {
          this.blocks = data.blocks;
        }

        // Update saved dates
        if (data.dates) {
          this.savedDates = data.dates;
        }

        // Update preferences if changed
        if (data.preferences) {
          Object.assign(this.preferences, data.preferences);
        }

        // Auto trigger PDF download if requested
        if (data.action === "download_pdf") {
          this.downloadPDF();
        }

        if (data.action && data.action !== "none") {
          this.showToast("Horario actualizado por el Asistente ✨", "success");
        }
      } catch (err) {
        const errMsg = "⚠️ Ocurrió un error al procesar tu solicitud: " + (err.message || "Error desconocido");
        this.messages.push({
          id: Date.now() + 1,
          sender: "agent",
          text: errMsg,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          error: true,
        });
        if (fromVoice || this.voiceResponseEnabled) {
          this.speak("Ocurrió un error al procesar tu solicitud.");
        }
      } finally {
        this.agentLoading = false;
        this.scrollChatBottom();
      }
    },

    scrollChatBottom() {
      setTimeout(() => {
        const container = document.getElementById("chat-messages-container");
        if (container) {
          container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
        }
      }, 50);
    },

    formatMessage(text) {
      if (!text) return "";
      let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

      html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
      html = html.replace(/\n/g, "<br>");
      return html;
    },

    // ── Helpers ──────────────────────────────────────────
    formatDate(dateStr) {
      const d = new Date(dateStr + "T12:00:00");
      return d.toLocaleDateString("es-ES", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    },

    categoryColor(cat) {
      const colors = {
        sleep: "bg-indigo-100 text-indigo-800 border-indigo-300",
        work: "bg-blue-100 text-blue-800 border-blue-300",
        meal: "bg-amber-100 text-amber-800 border-amber-300",
        exercise: "bg-emerald-100 text-emerald-800 border-emerald-300",
        study: "bg-violet-100 text-violet-800 border-violet-300",
        personal: "bg-cyan-100 text-cyan-800 border-cyan-300",
        free: "bg-indigo-50 text-indigo-700 border-indigo-200",
        routine: "bg-gray-100 text-gray-700 border-gray-300",
      };
      return colors[cat] || "bg-gray-100 text-gray-700 border-gray-300";
    },

    categoryDot(cat) {
      const colors = {
        sleep: "bg-indigo-500",
        work: "bg-blue-500",
        meal: "bg-amber-500",
        exercise: "bg-emerald-500",
        study: "bg-violet-500",
        personal: "bg-cyan-500",
        free: "bg-indigo-300",
        routine: "bg-gray-400",
      };
      return colors[cat] || "bg-gray-400";
    },

    categoryLabel(cat) {
      const labels = {
        sleep: "Dormir",
        work: "Trabajo",
        meal: "Comida",
        exercise: "Ejercicio",
        study: "Estudio",
        personal: "Personal",
        free: "Libre",
        routine: "Rutina",
      };
      return labels[cat] || cat;
    },

    blockDuration(block) {
      const [sh, sm] = block.start_time.split(":").map(Number);
      const [eh, em] = block.end_time.split(":").map(Number);
      let diff = (eh * 60 + em) - (sh * 60 + sm);
      if (diff <= 0) diff += 1440;
      const h = Math.floor(diff / 60);
      const m = diff % 60;
      if (h && m) return `${h}h ${m}m`;
      if (h) return `${h}h`;
      return `${m}m`;
    },

    isToday() {
      return this.currentDate === new Date().toISOString().split("T")[0];
    },
  });
});
