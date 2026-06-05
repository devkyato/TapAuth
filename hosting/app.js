import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
    collection,
    getFirestore,
    limit,
    onSnapshot,
    orderBy,
    query
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";

const app = initializeApp(window.AIRHUB_FIREBASE_CONFIG);
const db = getFirestore(app);
const logsBody = document.getElementById("logsBody");
const syncState = document.getElementById("syncState");
const tapMessage = document.getElementById("tapMessage");
const tapSubtext = document.getElementById("tapSubtext");
let lastSeenId = null;
let greetingTimer = null;

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    }[char]));
}

function formatDate(value) {
    if (!value) return "Pending time";
    const date = typeof value.toDate === "function" ? value.toDate() : new Date(value);
    return date.toLocaleString();
}

function updateClock() {
    document.getElementById("clock").textContent = new Date().toLocaleString();
}

function showGreeting(name, status) {
    clearTimeout(greetingTimer);
    tapMessage.classList.remove("tap-flash");
    tapMessage.textContent = status === "GUEST" ? "Please register your name." : `Hi, ${name}!`;
    void tapMessage.offsetWidth;
    tapMessage.classList.add("tap-flash");
    tapSubtext.textContent = status === "GUEST" ? "Guest taps need a registered name before they count as active." : "Time-in saved. Welcome.";
    greetingTimer = setTimeout(() => {
        tapMessage.classList.remove("tap-flash");
        tapMessage.textContent = "Ready for tap-in";
        tapSubtext.textContent = "Recent taps from the Raspberry Pi appear here automatically.";
    }, 3200);
}

function renderLogs(snapshot) {
    if (snapshot.empty) {
        logsBody.innerHTML = '<tr><td colspan="3">No logs yet.</td></tr>';
        return;
    }

    const rows = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
    const newest = rows[0];
    if (newest && newest.id !== lastSeenId) {
        if (lastSeenId !== null) showGreeting(newest.fullname || "Name required", newest.status);
        lastSeenId = newest.id;
    }

    logsBody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(row.fullname || "Name required")}</td>
            <td>${escapeHtml(formatDate(row.date_logged))}</td>
            <td><span class="status-pill">${escapeHtml(row.status || "GUEST")}</span></td>
        </tr>
    `).join("");
}

updateClock();
setInterval(updateClock, 1000);

const logsQuery = query(collection(db, "airhub_logs"), orderBy("date_logged", "desc"), limit(12));
onSnapshot(logsQuery, (snapshot) => {
    syncState.textContent = "Live";
    renderLogs(snapshot);
}, (error) => {
    syncState.textContent = "Offline";
    logsBody.innerHTML = `<tr><td colspan="3">${escapeHtml(error.message || "Unable to load Firestore logs.")}</td></tr>`;
});