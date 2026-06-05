import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
    getDatabase,
    limitToLast,
    onValue,
    orderByChild,
    query,
    ref
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-database.js";

const app = initializeApp(window.AIRHUB_FIREBASE_CONFIG);
const db = getDatabase(app, "https://airhub-login-default-rtdb.asia-southeast1.firebasedatabase.app/");
const logsBody = document.getElementById("logsBody");
const syncState = document.getElementById("syncState");
const tapMessage = document.getElementById("tapMessage");
const tapSubtext = document.getElementById("tapSubtext");
let lastSeenId = null;
let greetingTimer = null;

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[char]));
}

function formatDate(value) {
    if (!value) return "Pending time";
    return new Date(value).toLocaleString();
}

function updateClock() {
    document.getElementById("clock").textContent = new Date().toLocaleString();
}

function showGreeting(name, status) {
    clearTimeout(greetingTimer);
    tapMessage.classList.remove("tap-flash");
    tapMessage.textContent = status === "GUEST_PENDING" ? "Guest accepted. Type your name on the kiosk." : `Hi, ${name}!`;
    void tapMessage.offsetWidth;
    tapMessage.classList.add("tap-flash");
    tapSubtext.textContent = status === "GUEST_PENDING" ? "The tap is saved locally and will sync when online." : "Time-in saved. Welcome.";
    greetingTimer = setTimeout(() => {
        tapMessage.classList.remove("tap-flash");
        tapMessage.textContent = "Ready for tap-in";
        tapSubtext.textContent = "Recent taps from the Raspberry Pi appear here automatically.";
    }, 3200);
}

function renderLogs(snapshot) {
    const value = snapshot.val() || {};
    const rows = Object.entries(value).map(([id, row]) => ({ id, ...row }))
        .sort((a, b) => new Date(b.date_logged || 0) - new Date(a.date_logged || 0));

    if (rows.length === 0) {
        logsBody.innerHTML = '<tr><td colspan="3">No logs yet.</td></tr>';
        return;
    }

    const newest = rows[0];
    if (newest && newest.id !== lastSeenId) {
        if (lastSeenId !== null) showGreeting(newest.fullname || "Guest", newest.status);
        lastSeenId = newest.id;
    }

    logsBody.innerHTML = rows.slice(0, 12).map((row) => `
        <tr>
            <td>${escapeHtml(row.fullname || "Guest")}</td>
            <td>${escapeHtml(formatDate(row.date_logged))}</td>
            <td><span class="status-pill">${escapeHtml(row.status || "GUEST")}</span></td>
        </tr>
    `).join("");
}

updateClock();
setInterval(updateClock, 1000);

const logsQuery = query(ref(db, "airhub/logs"), orderByChild("date_logged"), limitToLast(12));
onValue(logsQuery, (snapshot) => {
    syncState.textContent = "Live";
    renderLogs(snapshot);
}, (error) => {
    syncState.textContent = "Offline";
    logsBody.innerHTML = `<tr><td colspan="3">${escapeHtml(error.message || "Unable to load Realtime Database logs.")}</td></tr>`;
});