let activeConversationId = null;

// Conversation list
async function loadConversations() {
    try {
        const convs = await apiGet("/api/conversations");
        const listEl = document.getElementById("conversationList");
        listEl.innerHTML = "";

        convs.forEach((c) => {
            const item = document.createElement("div");
            item.className = `conv-item${c.id === activeConversationId ? " active" : ""}`;
            item.innerHTML = `
                <span class="title">${escapeHtml(c.title)}</span>
                <button class="delete-btn" data-id="${c.id}">&times;</button>
            `;
            item.querySelector(".title").addEventListener("click", () => selectConversation(c.id));
            item.querySelector(".delete-btn").addEventListener("click", (e) => {
                e.stopPropagation();
                deleteConversation(c.id);
            });
            listEl.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to load conversations:", err);
    }
}

async function createConversation() {
    try {
        const conv = await apiPost("/api/conversations", { title: "New Chat" });
        await loadConversations();
        selectConversation(conv.id);
    } catch (err) {
        console.error("Failed to create conversation:", err);
    }
}

async function deleteConversation(id) {
    if (!confirm("Delete this conversation?")) return;
    try {
        await apiDelete(`/api/conversations/${id}`);
        if (activeConversationId === id) {
            activeConversationId = null;
            showEmptyState();
        }
        await loadConversations();
    } catch (err) {
        console.error("Failed to delete conversation:", err);
    }
}

async function selectConversation(id) {
    activeConversationId = id;
    const messagesEl = document.getElementById("chatMessages");
    messagesEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    document.getElementById("chatHeaderTitle").textContent = "Loading...";

    try {
        const messages = await apiGet(`/api/conversations/${id}/messages`);
        renderMessages(messages);
        document.querySelectorAll(".conv-item").forEach((el) => {
            el.classList.toggle("active", el.querySelector(".delete-btn")?.dataset.id == String(id));
        });
    } catch (err) {
        messagesEl.innerHTML = `<div class="empty-state"><div class="icon">!</div><p>Failed to load messages</p></div>`;
    }

    document.getElementById("chatHeaderTitle").textContent =
        document.querySelector(`.conv-item.active .title`)?.textContent || "Chat";
}

function showEmptyState() {
    document.getElementById("chatMessages").innerHTML = `
        <div class="empty-state">
            <div class="icon">&#x1F4AC;</div>
            <p>Select or create a conversation</p>
        </div>`;
    document.getElementById("chatHeaderTitle").textContent = "Chat";
}

function renderMessages(messages) {
    const container = document.getElementById("chatMessages");
    container.innerHTML = "";

    if (messages.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">&#x1F4AC;</div>
                <p>Start a conversation</p>
            </div>`;
        return;
    }

    messages.forEach((m) => {
        const div = document.createElement("div");
        div.className = `message ${m.role}`;
        div.textContent = m.content;
        container.appendChild(div);
    });

    container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const message = input.value.trim();
    if (!message || !activeConversationId) return;

    input.value = "";
    input.disabled = true;

    const container = document.getElementById("chatMessages");
    // Remove empty state if present
    const emptyState = container.querySelector(".empty-state");
    if (emptyState) emptyState.remove();

    // Add user message
    const userMsg = document.createElement("div");
    userMsg.className = "message user";
    userMsg.textContent = message;
    container.appendChild(userMsg);

    // Add assistant message placeholder
    const assistantMsg = document.createElement("div");
    assistantMsg.className = "message assistant";
    assistantMsg.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    container.appendChild(assistantMsg);
    container.scrollTop = container.scrollHeight;

    const token = getToken();
    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
                conversation_id: activeConversationId,
                message: message,
            }),
        });

        if (res.status === 401) {
            clearToken();
            window.location.href = "/login.html";
            return;
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Chat failed" }));
            throw new Error(err.detail || "Chat failed");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let content = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split("\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            assistantMsg.textContent = `Error: ${data.error}`;
                            return;
                        }
                        if (data.done) {
                            // Update conversation list to reflect new title
                            loadConversations();
                            return;
                        }
                        if (data.content) {
                            content += data.content;
                            assistantMsg.textContent = content;
                            container.scrollTop = container.scrollHeight;
                        }
                    } catch (e) {
                        // ignore parse errors
                    }
                }
            }
        }
    } catch (err) {
        assistantMsg.textContent = `Error: ${err.message}`;
    } finally {
        input.disabled = false;
        input.focus();
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Init
document.addEventListener("DOMContentLoaded", () => {
    requireAuth();
    loadConversations();

    document.getElementById("btnNewChat").addEventListener("click", createConversation);
    document.getElementById("btnLogout").addEventListener("click", () => {
        clearToken();
        window.location.href = "/login.html";
    });

    const input = document.getElementById("chatInput");
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });
    document.getElementById("btnSend").addEventListener("click", sendMessage);
});
