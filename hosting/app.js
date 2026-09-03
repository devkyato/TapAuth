const config = window.TAPAUTH_CLOUD_CONFIG || {};
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
    if (row.event_type === "LOGOUT") {
        tapMessage.textContent = "Check-out recorded";
        tapSubtext.textContent = `Stayed ${row.duration_label || "00:00:00"}.`;
    } else {
        tapMessage.textContent = "Check-in recorded";
        tapSubtext.textContent = "Time entered saved.";
    }
    greetingTimer = setTimeout(() => {
        tapMessage.textContent = "Ready for tap-in or tap-out";
        tapSubtext.textContent = "Recent taps from the Raspberry Pi appear here automatically.";
    }, 3200);
}

function renderLogs(rows) {
    if (!rows.length) {
        logsBody.innerHTML = '<tr><td colspan="5">No activity yet.</td></tr>';
        return;
    }
    const newest = rows[0];
    if (newest.id !== lastSeenId) {
        if (lastSeenId !== null) showGreeting(newest);
        lastSeenId = newest.id;
    }
    const key = rows.map((row) => `${row.id}:${row.status}:${row.duration_label || ""}`).join("|");
    if (key === lastRowsKey) return;
    lastRowsKey = key;
    logsBody.innerHTML = rows.map((row) => `
        <tr>
            <td><span class="status-pill">${escapeHtml(row.event_type || "")}</span></td>
            <td>${escapeHtml(row.date_logged || "")}</td>
            <td>${escapeHtml(row.time_entered || "")}</td>
            <td>${escapeHtml(row.time_left || "")}</td>
            <td>${escapeHtml(row.duration_label || "")}</td>
        </tr>
    `).join("");
}

async function refresh() {
    if (!config.supabaseUrl || !config.supabasePublishableKey) {
        syncState.textContent = "Setup needed";
        logsBody.innerHTML = '<tr><td colspan="5">Run the TapAuth configuration wizard before deploying Firebase Hosting.</td></tr>';
        return;
    }
    const filter = [
        config.bucketId ? `bucket_id=eq.${encodeURIComponent(config.bucketId)}` : "",
        config.deviceId ? `device_id=eq.${encodeURIComponent(config.deviceId)}` : ""
    ].filter(Boolean).map((part) => `&${part}`).join("");
    const response = await fetch(
        `${config.supabaseUrl}/rest/v1/tapauth_public_activity?select=*&order=date_logged.desc&limit=6${filter}`,
        { headers: { apikey: config.supabasePublishableKey } }
    );
    if (!response.ok) throw new Error(`Supabase returned ${response.status}.`);
    renderLogs(await response.json());
    syncState.textContent = "Live";
}

updateClock();
setInterval(updateClock, 1000);
refresh().catch((error) => {
    syncState.textContent = "Offline";
    logsBody.innerHTML = `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
});
setInterval(() => refresh().catch(() => { syncState.textContent = "Offline"; }), 5000);
