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
let lastRowsKey = "";
let greetingTimer = null;

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[char]));
}

function updateClock() {
    document.getElementById("clock").textContent = new Date().toLocaleString();
}

function showGreeting(row) {
    clearTimeout(greetingTimer);
    tapMessage.classList.remove("tap-flash");
    if (row.status === "GUEST_PENDING") {
        tapMessage.textContent = "Guest tap recorded.";
        tapSubtext.textContent = "Register this card to show a name.";
    } else if (row.event_type === "LOGOUT") {
        tapMessage.textContent = `Log out: ${row.fullname || "Guest"}`;
        tapSubtext.textContent = `Stayed ${row.duration_label || "00:00:00"}.`;
    } else {
        tapMessage.textContent = `Login: ${row.fullname || "Guest"}`;
        tapSubtext.textContent = "Time entered saved.";
    }
    void tapMessage.offsetWidth;
    tapMessage.classList.add("tap-flash");
    greetingTimer = setTimeout(() => {
        tapMessage.classList.remove("tap-flash");
        tapMessage.textContent = "Ready for tap-in or tap-out";
        tapSubtext.textContent = "Recent taps from the Raspberry Pi appear here automatically.";
    }, 3200);
}

function renderLogs(snapshot) {
    const value = snapshot.val() || {};
    const rows = Object.entries(value).map(([id, row]) => ({ id, ...row }))
        .sort((a, b) => new Date(b.date_logged || 0) - new Date(a.date_logged || 0));

    if (rows.length === 0) {
        if (lastRowsKey !== "empty") {
            logsBody.innerHTML = '<tr><td colspan="7">No logs yet.</td></tr>';
            lastRowsKey = "empty";
        }
        return;
    }

    const newest = rows[0];
    if (newest && newest.id !== lastSeenId) {
        if (lastSeenId !== null) showGreeting(newest);
        lastSeenId = newest.id;
    }

    const visibleRows = rows.slice(0, 6);
    const nextRowsKey = visibleRows.map((row) => `${row.id}:${row.status}:${row.duration_label || ""}`).join("|");
    if (nextRowsKey === lastRowsKey) return;
    lastRowsKey = nextRowsKey;

    logsBody.innerHTML = visibleRows.map((row) => `
        <tr>
            <td><span class="status-pill">${escapeHtml(row.event_type || "")}</span></td>
            <td>${escapeHtml(row.lastname || "")}</td>
            <td>${escapeHtml(row.firstname || "")}</td>
            <td>${escapeHtml(row.student_no || "")}</td>
            <td>${escapeHtml(row.time_entered || "")}</td>
            <td>${escapeHtml(row.time_left || "")}</td>
            <td>${escapeHtml(row.duration_label || "")}</td>
        </tr>
    `).join("");
}

updateClock();
setInterval(updateClock, 1000);

const logsQuery = query(ref(db, "airhub/logs"), orderByChild("date_logged"), limitToLast(6));
onValue(logsQuery, (snapshot) => {
    syncState.textContent = "Live";
    renderLogs(snapshot);
}, (error) => {
    syncState.textContent = "Offline";
    logsBody.innerHTML = `<tr><td colspan="7">${escapeHtml(error.message || "Unable to load Realtime Database logs.")}</td></tr>`;
});
