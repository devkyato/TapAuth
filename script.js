(() => {
  "use strict";

  const STORAGE_KEY = "soe-reservations-preview-v5";
  const ALLOWED_FILES = ["stl", "obj", "3mf"];
  const MAX_FILE_SIZE = 100 * 1024 * 1024;
  const RESERVATION_TIMEOUT_SECONDS = 60;
  const MAX_RECENT_LOGS = 25;
  const TAP_BANNER_RESET_MS = 3200;
  const isRaspberryPiRuntime = document.body.dataset.runtime === "pi";
  const GREETINGS = [
    "Hey {name}!", "Hi {name}!", "Hello {name}!", "Welcome, {name}!",
    "Welcome back, {name}!", "Good to see you, {name}!", "Nice to see you, {name}!", "Great to see you, {name}!",
    "Glad you're here, {name}!", "Great to have you here, {name}!", "Good day, {name}!", "How's it going, {name}?",
    "Ready to get started, {name}?", "Ready for AIRHub, {name}?", "You're all set, {name}!", "Look who's here, {name}!",
    "There you are, {name}!", "Awesome to see you, {name}!", "Happy to see you, {name}!", "A warm welcome, {name}!",
    "Hello there, {name}!", "Hey there, {name}!", "Hi there, {name}!", "Welcome in, {name}!",
    "Come on in, {name}!", "Good to have you back, {name}!", "Nice having you here, {name}!", "Glad to have you back, {name}!",
    "It's great to see you, {name}!", "Hope you're doing well, {name}!", "Hope you're having a great day, {name}!", "Another great day at AIRHub, {name}!",
    "AIRHub welcomes you, {name}!", "You're right on time, {name}!", "Ready when you are, {name}!", "Let's get started, {name}!",
    "Let's make something great, {name}!", "Good vibes today, {name}!", "Have a great visit, {name}!", "Welcome to AIRHub, {name}!"
  ];

  const tapButton = document.querySelector("#preview-tap");
  const tapStage = document.querySelector(".tap-stage");
  const tapTitle = document.querySelector("#tap-title");
  const nfcMessage = document.querySelector("#tap-message");
  const formSection = document.querySelector("#form-panel");
  const reservationCountdown = document.querySelector("#reservation-countdown");
  const cancelReservationButton = document.querySelector("#cancel-reservation");
  const forms = [...document.querySelectorAll(".reservation-form")];
  const successMessage = document.querySelector("#success-message");
  const successCopy = document.querySelector("#success-copy");
  const newRequestButton = document.querySelector("#new-request");
  const reservationList = document.querySelector("#reservation-list");
  const reservationFormMessage = document.querySelector("#reservation-form-message");
  const logsList = document.querySelector("#logs-list");
  const logsPanel = document.querySelector(".logs-panel");
  const logsTableWrap = logsPanel?.querySelector(".table-wrap");
  const toggleLogsButton = document.querySelector("#toggle-logs");
  const logsCount = document.querySelector("#logs-count");
  const clock = document.querySelector("#clock");

  const dialogBackdrop = document.querySelector("#tap-dialog-backdrop");
  const tapDialog = document.querySelector(".tap-dialog");
  const closeDialogButton = document.querySelector("#close-dialog");
  const tapChoice = document.querySelector("#tap-choice");
  const appointmentChoice = document.querySelector("#appointment-choice");
  const registrationCodeStep = document.querySelector("#registration-code-step");
  const tapResult = document.querySelector("#tap-result");
  const dialogTitle = document.querySelector("#dialog-title");
  const dialogQuestion = document.querySelector("#dialog-question");
  const dialogIdentity = document.querySelector("#dialog-identity");
  const registeredActions = document.querySelector("#registered-actions");
  const unregisteredActions = document.querySelector("#unregistered-actions");
  const attendanceChoiceButton = document.querySelector(".attendance-choice");
  const attendanceActionTitle = document.querySelector("#attendance-action-title");
  const attendanceActionDescription = document.querySelector("#attendance-action-description");
  const autoCheckInCountdown = document.querySelector("#auto-checkin-countdown");
  const countdownActionLabel = document.querySelector("#countdown-action-label");
  const countdownSeconds = document.querySelector("#countdown-seconds");
  const openRegistrationButton = document.querySelector("#open-registration");
  const registrationCodeForm = document.querySelector("#registration-code-form");
  const registrationCodeMessage = document.querySelector("#registration-code-message");
  const backFromRegistrationButton = document.querySelector("#back-from-registration");
  const backToTapButton = document.querySelector("#back-to-tap");
  const finishTapButton = document.querySelector("#finish-tap");
  const resultTitle = document.querySelector("#tap-result-title");
  const resultCopy = document.querySelector("#tap-result-copy");
  const tapActionButtons = [...document.querySelectorAll("[data-tap-action]")];
  const serviceChoiceButtons = [...document.querySelectorAll(".tap-dialog [data-service]")];
  const printingForm = document.querySelector("#printing-form");
  const printingSteps = [...document.querySelectorAll("#printing-form .form-step")];
  const printingStepBars = [...document.querySelectorAll("#printing-form [data-step-bar]")];
  const printingPrevButton = document.querySelector("#printing-form [data-step-prev]");
  const printingNextButton = document.querySelector("#printing-form [data-step-next]");
  const printingSubmitButton = document.querySelector("#printing-form [data-step-submit]");

  let nfcSession = null;
  let currentTap = null;
  let tapCounter = 0;
  let dismissTimer = null;
  let fadeTimer = null;
  let tapBannerTimer = null;
  let autoCheckInTimer = null;
  let reservationTimer = null;
  let reservationCancelBusy = false;
  let tapActionBusy = false;
  let appointmentBusy = false;
  let previewCheckedIn = false;
  let printingStep = 1;
  let recentLogs = [];
  let logsExpanded = false;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;"
    })[character]);
  }

  function setMinimumDates() {
    const now = new Date();
    const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    document.querySelectorAll('input[type="date"]').forEach((input) => { input.min = localDate; });
  }

  function showDialogStep(step) {
    tapChoice.hidden = step !== "tap";
    appointmentChoice.hidden = step !== "appointment";
    registrationCodeStep.hidden = step !== "registration";
    tapResult.hidden = step !== "result";
  }

  function resetTapBanner() {
    clearTimeout(tapBannerTimer);
    tapBannerTimer = null;
    tapStage.classList.remove("verified", "warning");
    tapTitle.textContent = "Ready for tap-in or tap-out";
    nfcMessage.textContent = "Tap your ID to check in or make an appointment.";
  }

  function setTapBanner(title, message, options = {}) {
    clearTimeout(tapBannerTimer);
    tapStage.classList.toggle("verified", options.kind === "success");
    tapStage.classList.toggle("warning", options.kind === "warning");
    tapTitle.textContent = title;
    nfcMessage.textContent = message;

    if (options.autoReset !== false) {
      tapBannerTimer = setTimeout(resetTapBanner, options.timeout || TAP_BANNER_RESET_MS);
    }
  }

  function clearAutoCheckIn() {
    clearInterval(autoCheckInTimer);
    autoCheckInTimer = null;
    autoCheckInCountdown.hidden = true;
  }

  function startAutoCheckInCountdown() {
    clearInterval(autoCheckInTimer);
    if (!currentTap?.registered || tapChoice.hidden || dialogBackdrop.hidden) {
      autoCheckInCountdown.hidden = true;
      return;
    }

    let secondsRemaining = 10;
    autoCheckInCountdown.hidden = false;
    countdownSeconds.textContent = String(secondsRemaining);
    autoCheckInTimer = setInterval(() => {
      secondsRemaining -= 1;
      countdownSeconds.textContent = String(Math.max(secondsRemaining, 0));
      if (secondsRemaining <= 0) {
        clearAutoCheckIn();
        handleAttendanceAction();
      }
    }, 1000);
  }

  function clearReservationTimer() {
    clearInterval(reservationTimer);
    reservationTimer = null;
  }

  function startReservationTimer() {
    clearReservationTimer();
    if (formSection.hidden || successMessage.hidden === false) return;
    let secondsRemaining = RESERVATION_TIMEOUT_SECONDS;
    reservationCountdown.textContent = String(secondsRemaining);
    reservationTimer = setInterval(() => {
      secondsRemaining -= 1;
      reservationCountdown.textContent = String(Math.max(secondsRemaining, 0));
      if (secondsRemaining <= 0) {
        clearReservationTimer();
        cancelReservation("timeout");
      }
    }, 1000);
  }

  function fieldsForStep(step) {
    const stepElement = printingSteps.find((element) => Number(element.dataset.step) === step);
    return stepElement ? [...stepElement.querySelectorAll("input, select, textarea")] : [];
  }

  function updatePrintingReview() {
    if (!printingForm) return;
    const date = printingForm.elements.date?.value;
    const durationSelect = printingForm.elements.duration;
    const projectName = printingForm.elements.projectName?.value.trim();
    const file = printingForm.elements.modelFile?.files[0];
    const dateLabel = date ? new Date(`${date}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "-";
    printingForm.querySelector('[data-review="date"]').textContent = dateLabel;
    printingForm.querySelector('[data-review="duration"]').textContent = durationSelect?.selectedOptions[0]?.textContent || "-";
    printingForm.querySelector('[data-review="projectName"]').textContent = projectName || "-";
    printingForm.querySelector('[data-review="modelFile"]').textContent = file?.name || "-";
  }

  function showPrintingStep(step) {
    printingStep = Math.min(Math.max(step, 1), printingSteps.length || 1);
    printingSteps.forEach((element) => { element.hidden = Number(element.dataset.step) !== printingStep; });
    printingStepBars.forEach((element) => {
      const index = Number(element.dataset.stepBar);
      element.classList.toggle("active", index === printingStep);
      element.classList.toggle("done", index < printingStep);
    });
    if (printingPrevButton) printingPrevButton.hidden = printingStep === 1;
    if (printingNextButton) printingNextButton.hidden = printingStep === printingSteps.length;
    if (printingSubmitButton) printingSubmitButton.hidden = printingStep !== printingSteps.length;
    if (printingStep === printingSteps.length) updatePrintingReview();
    fieldsForStep(printingStep).find((field) => field.type !== "hidden")?.focus({ preventScroll: true });
  }

  function validatePrintingStep(step) {
    if (step === 2 && !validateFile(printingForm)) {
      printingForm.elements.modelFile.reportValidity();
      return false;
    }
    const invalidField = fieldsForStep(step).find((field) => !field.checkValidity());
    if (invalidField) {
      invalidField.reportValidity();
      invalidField.focus({ preventScroll: true });
      return false;
    }
    return true;
  }

  function greetingFor(firstName) {
    const template = GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
    return template.replace("{name}", firstName);
  }

  function openTapDialog(tap) {
    clearTimeout(dismissTimer);
    clearTimeout(fadeTimer);
    clearTimeout(tapBannerTimer);
    clearAutoCheckIn();
    tapActionBusy = false;
    appointmentBusy = false;
    setDialogBusy(false);
    if (!formSection.hidden) return;
    tapStage.classList.remove("verified", "warning");
    currentTap = tap;
    const user = tap.user || {};
    const registered = Boolean(user.fullname && user.student_no);
    const lookupUnavailable = Boolean(tap.lookupUnavailable);
    const checkedIn = Boolean(user.checked_in ?? tap.checkedIn ?? false);
    const firstName = user.firstname || String(user.fullname || "").trim().split(/\s+/)[0] || "there";
    tap.registered = registered;
    tap.attendanceAction = checkedIn ? "check_out" : "check_in";
    attendanceActionTitle.textContent = checkedIn ? "Check out" : "Check in";
    attendanceChoiceButton.classList.toggle("is-checkout", checkedIn);
    attendanceActionDescription.textContent = checkedIn
      ? "Record your departure from AIRHub now."
      : "Record your attendance and enter AIRHub now.";
    countdownActionLabel.textContent = checkedIn ? "check-out" : "check-in";
    dialogTitle.textContent = lookupUnavailable
      ? "Unable to verify this ID"
      : (registered ? greetingFor(firstName) : "Hey there!");
    dialogQuestion.textContent = lookupUnavailable
      ? "The database is offline. You can still register this card on this device."
      : "What would you like to do?";
    dialogIdentity.textContent = lookupUnavailable
      ? (tap.lookupMessage || "The student database is temporarily unavailable.")
      : registered
      ? `${user.fullname} - ${user.student_no} - ${user.course || "Program not provided"}`
      : "This school ID is not registered yet.";
    registeredActions.hidden = !registered;
    unregisteredActions.hidden = registered;
    registrationCodeForm.reset();
    registrationCodeMessage.textContent = "";
    showDialogStep("tap");
    dialogBackdrop.classList.remove("is-closing");
    dialogBackdrop.hidden = false;
    document.body.classList.add("modal-open");
    if (registered) {
      tapActionButtons[0].focus();
      startAutoCheckInCountdown();
    } else {
      openRegistrationButton.focus();
    }
  }

  function closeTapDialog() {
    clearTimeout(dismissTimer);
    clearTimeout(fadeTimer);
    clearAutoCheckIn();
    dialogBackdrop.hidden = true;
    dialogBackdrop.classList.remove("is-closing");
    document.body.classList.remove("modal-open");
    currentTap = null;
    setDialogBusy(false);
    tapButton.focus({ preventScroll: true });
  }

  function setDialogBusy(isBusy) {
    [...tapActionButtons, ...serviceChoiceButtons].forEach((button) => { button.disabled = isBusy; });
    openRegistrationButton.disabled = isBusy;
    const registrationSubmit = registrationCodeForm.querySelector('button[type="submit"]');
    if (registrationSubmit) registrationSubmit.disabled = isBusy;
  }

  function showResult(title, copy, autoDismiss = false) {
    clearAutoCheckIn();
    resultTitle.textContent = title;
    resultCopy.textContent = copy;
    showDialogStep("result");
    finishTapButton.focus();
    if (autoDismiss) {
      dismissTimer = setTimeout(() => {
        dialogBackdrop.classList.add("is-closing");
        fadeTimer = setTimeout(closeTapDialog, 240);
      }, 1800);
    }
  }

  function logRow(record = {}) {
    const row = document.createElement("tr");
    const eventName = record.event_type || "LOGIN";
    const className = eventName.toLowerCase() === "logout" ? "logout" : "login";
    const name = record.fullname || "Alex D. Santos";
    const studentNumber = record.student_no || "2025-10482";
    const timeValue = record.time_left || record.time_entered;
    const time = timeValue
      ? new Date(timeValue.replace(" ", "T")).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
      : new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    row.innerHTML = `<td><span class="event-pill ${className}">${escapeHtml(eventName)}</span></td><td>${escapeHtml(name)}</td><td>${escapeHtml(studentNumber)}</td><td>${escapeHtml(time)}</td>`;
    return row;
  }

  function fittedLogLimit() {
    if (!logsPanel || !logsTableWrap) return 5;
    const panelStyle = getComputedStyle(logsPanel);
    const heading = logsPanel.querySelector(".panel-head");
    const headingStyle = heading ? getComputedStyle(heading) : null;
    const shell = document.querySelector(".airhub-shell");
    const shellStyle = shell ? getComputedStyle(shell) : null;
    const panelPadding = parseFloat(panelStyle.paddingTop) + parseFloat(panelStyle.paddingBottom);
    const headingHeight = heading?.offsetHeight || 58;
    const headingMargin = parseFloat(headingStyle?.marginBottom || "14");
    const headerHeight = logsPanel.querySelector("thead")?.offsetHeight || 36;
    const shellBottomPadding = parseFloat(shellStyle?.paddingBottom || "10");
    const rowHeight = logsList.querySelector("tr:not(.empty-row)")?.getBoundingClientRect().height || 46;
    const availableHeight = window.innerHeight
      - logsPanel.getBoundingClientRect().top
      - shellBottomPadding
      - panelPadding
      - headingHeight
      - headingMargin
      - headerHeight
      - 42;
    return Math.max(5, Math.min(MAX_RECENT_LOGS, Math.floor(availableHeight / rowHeight)));
  }

  function renderRecentLogs() {
    if (recentLogs.length === 0) {
      logsList.innerHTML = '<tr class="empty-row"><td colspan="4">No logs yet.</td></tr>';
      toggleLogsButton.hidden = true;
      logsPanel.classList.remove("is-expanded");
      return;
    }

    const collapsedLimit = fittedLogLimit();
    const visibleLogs = logsExpanded ? recentLogs : recentLogs.slice(0, collapsedLimit);
    logsList.replaceChildren(...visibleLogs.map(logRow));
    const hasMore = recentLogs.length > collapsedLimit;
    toggleLogsButton.hidden = !hasMore;
    logsPanel.classList.toggle("is-expanded", logsExpanded && hasMore);
    toggleLogsButton.querySelector("span").textContent = logsExpanded ? "See less" : "See more";
    logsCount.textContent = logsExpanded ? "" : `${recentLogs.length} recent`;
  }

  function addTapToLog(record = {}) {
    recentLogs = [
      record,
      ...recentLogs.filter((item) => !record.id || item.id !== record.id)
    ].slice(0, MAX_RECENT_LOGS);
    renderRecentLogs();
  }

  async function processTapAction(tap, action) {
    if (!tap || tap.isPreview) {
      const user = tap?.user || {};
      if (action === "check_out") {
        previewCheckedIn = false;
        return {
          message: "Check out recorded.",
          log: {
            event_type: "LOGOUT",
            status: "TAP_OUT",
            fullname: user.fullname || "Alex D. Santos",
            student_no: user.student_no || "2025-10482"
          }
        };
      }
      if (action === "check_in") {
        previewCheckedIn = true;
        return {
          message: "Check in recorded.",
          log: {
            event_type: "LOGIN",
            status: "TAP_IN",
            fullname: user.fullname || "Alex D. Santos",
            student_no: user.student_no || "2025-10482"
          }
        };
      }
      return { message: "Choose an appointment service." };
    }

    const response = await fetch("/tap_action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        uid: tap.uid,
        tap_counter: tap.tapCounter
      })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Unable to process this tap.");
    return data;
  }

  function confirmTapAction(action) {
    return processTapAction(currentTap, action);
  }

  async function handleAttendanceAction() {
    if (tapActionBusy || !currentTap) return;
    tapActionBusy = true;
    clearAutoCheckIn();
    setDialogBusy(true);
    try {
      const action = currentTap?.attendanceAction || "check_in";
      const response = await confirmTapAction(action);
      if (response.log) addTapToLog(response.log);
      setTapBanner(
        response.message || (action === "check_out" ? "Check out recorded" : "Check in recorded"),
        "Attendance saved successfully.",
        { kind: "success" }
      );
      showResult(
        action === "check_out" ? "Check out recorded" : "Check in recorded",
        response.message || "Your attendance has been saved.",
        true
      );
    } catch (error) {
      setTapBanner("Unable to update attendance", error.message, { kind: "warning", timeout: 5000 });
      showResult("Unable to update attendance", error.message);
    } finally {
      setDialogBusy(false);
      tapActionBusy = false;
    }
  }

  async function handleAppointment() {
    if (appointmentBusy || !currentTap) return;
    appointmentBusy = true;
    clearAutoCheckIn();
    setDialogBusy(true);
    try {
      await confirmTapAction("appointment");
      showDialogStep("appointment");
      serviceChoiceButtons[0].focus();
    } catch (error) {
      setTapBanner("Unable to continue", error.message, { kind: "warning", timeout: 5000 });
      showResult("Unable to continue", error.message);
    } finally {
      setDialogBusy(false);
      appointmentBusy = false;
    }
  }

  function showRegistrationStep() {
    clearAutoCheckIn();
    registrationCodeMessage.textContent = "";
    showDialogStep("registration");
    registrationCodeForm.elements.firstname.focus();
  }

  async function handleRegistrationCode(event) {
    event.preventDefault();
    registrationCodeMessage.textContent = "";
    if (!registrationCodeForm.reportValidity()) return;
    setDialogBusy(true);
    try {
      const fields = new FormData(registrationCodeForm);
      const profile = Object.fromEntries(fields.entries());
      if (currentTap?.isPreview) {
        currentTap.user = {
          firstname: profile.firstname,
          fullname: `${profile.firstname} ${profile.lastname}`,
          student_no: profile.student_no,
          course: profile.course,
          checked_in: false
        };
        currentTap.registered = true;
        openTapDialog(currentTap);
        return;
      }

      const response = await fetch("/register_from_tap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...profile,
          uid: currentTap?.uid,
          tap_counter: currentTap?.tapCounter
        })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Unable to register this card.");
      currentTap.user = data.user;
      currentTap.registered = true;
      openTapDialog(currentTap);
      setTapBanner("Registration complete", "Your school ID is now linked to your student profile.", {
        kind: "success",
        timeout: 5000
      });
    } catch (error) {
      registrationCodeMessage.textContent = error.message;
    } finally {
      setDialogBusy(false);
    }
  }

  function showService(service) {
    clearAutoCheckIn();
    clearTimeout(dismissTimer);
    clearTimeout(fadeTimer);
    nfcSession = currentTap || { uid: "preview-card", tapCounter: `preview-${Date.now()}` };
    const user = nfcSession.user || {};
    const identity = user.fullname && user.student_no
      ? `${user.fullname} - ${user.student_no} - ${user.course || "Program not provided"}`
      : "Registered AIRHub user";
    document.querySelectorAll(".form-identity").forEach((element) => { element.textContent = identity; });
    closeTapDialog();
    forms.forEach((form) => form.reset());
    forms.forEach((form) => { form.hidden = form.dataset.service !== service; });
    if (service === "printing") showPrintingStep(1);
    successMessage.hidden = true;
    reservationFormMessage.textContent = "";
    formSection.hidden = false;
    document.body.classList.add("form-modal-open");
    startReservationTimer();
    forms.find((form) => !form.hidden)?.querySelector("input:not([readonly]), select, textarea")?.focus();
  }

  async function cancelReservation(reason = "cancelled") {
    if (reservationCancelBusy || formSection.hidden) return;
    reservationCancelBusy = true;
    clearReservationTimer();
    const tap = nfcSession;
    nfcSession = null;
    forms.forEach((form) => {
      form.reset();
      form.hidden = true;
    });
    successMessage.hidden = true;
    formSection.hidden = true;
    document.body.classList.remove("form-modal-open");

    try {
      if (!tap) return;
      const response = await processTapAction(tap, "check_out");
      if (response.log) addTapToLog(response.log);
      const message = reason === "timeout"
        ? "The reservation form timed out and your checkout was processed."
        : "The reservation was cancelled and your checkout was processed.";
      setTapBanner(response.message || "Check out recorded", message, { kind: "success" });
      dialogBackdrop.classList.remove("is-closing");
      dialogBackdrop.hidden = false;
      document.body.classList.add("modal-open");
      showResult(
        response.log?.status === "TAP_OUT" ? "Check out recorded" : "Attendance updated",
        message,
        true
      );
    } catch (error) {
      setTapBanner("Reservation closed", error.message, { kind: "warning", timeout: 5000 });
      dialogBackdrop.classList.remove("is-closing");
      dialogBackdrop.hidden = false;
      document.body.classList.add("modal-open");
      showResult("Reservation closed", error.message);
    } finally {
      reservationCancelBusy = false;
    }
  }

  function validateFile(form) {
    if (form.dataset.service !== "printing") return true;
    const input = form.elements.modelFile;
    const file = input.files[0];
    input.setCustomValidity("");
    if (!file) return true;
    const extension = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_FILES.includes(extension)) input.setCustomValidity("Upload an STL, OBJ, or 3MF file.");
    if (file.size > MAX_FILE_SIZE) input.setCustomValidity("The file must be 100 MB or smaller.");
    return input.checkValidity();
  }

  async function saveReservation(form) {
    if (!nfcSession) throw new Error("Tap a school ID before making a reservation.");
    const data = new FormData(form);
    if (isRaspberryPiRuntime && !nfcSession.isPreview) {
      data.append("service", form.dataset.service);
      data.append("uid", nfcSession.uid);
      data.append("tap_counter", nfcSession.tapCounter);
      const response = await fetch("/reservations", { method: "POST", body: data });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to save the reservation.");
      nfcSession = null;
      return result.reservation;
    }
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    const item = {
      service: form.dataset.service,
      date: data.get("date"),
      time: form.dataset.service === "teacher" ? data.get("time") : null,
      queuePosition: form.dataset.service === "printing"
        ? saved.filter((reservation) => reservation.service === "printing" && reservation.date === data.get("date")).length + 1
        : null,
      status: "Pending",
      createdAt: new Date().toISOString()
    };
    saved.push(item);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    nfcSession = null;
    return item;
  }

  function addReservationToList(item) {
    reservationList.querySelector(".empty-row")?.remove();
    const row = document.createElement("tr");
    const service = item.service === "printing" ? "3D Printer" : "Teacher's Reservation";
    const dateValue = new Date(`${item.date}T00:00:00`);
    const date = dateValue.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
    const schedule = item.service === "printing"
      ? `Queue #${item.queuePosition || 1}`
      : new Date(`${item.date}T${item.time}`).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    const status = String(item.status || "PENDING").toLowerCase();
    row.innerHTML = `<td>${escapeHtml(service)}</td><td>${escapeHtml(date)}</td><td>${escapeHtml(schedule)}</td><td><span class="status-pill ${escapeHtml(status)}">${escapeHtml(status.charAt(0).toUpperCase() + status.slice(1))}</span></td>`;
    reservationList.prepend(row);
  }

  function resetPage() {
    resetTapBanner();
    clearReservationTimer();
    forms.forEach((form) => form.reset());
    showPrintingStep(1);
    forms.forEach((form) => { form.hidden = true; });
    formSection.hidden = true;
    successMessage.hidden = true;
    nfcSession = null;
    document.body.classList.remove("form-modal-open");
  }

  async function fetchLogs() {
    if (!isRaspberryPiRuntime) return;
    try {
      const response = await fetch("/user_logs_info");
      if (!response.ok) return;
      const rows = await response.json();
      if (!Array.isArray(rows) || rows.length === 0) {
        recentLogs = [];
        renderRecentLogs();
        return;
      }
      recentLogs = rows.slice(0, MAX_RECENT_LOGS);
      renderRecentLogs();
    } catch (_) {
      // The reader keeps running if the local database is temporarily unavailable.
    }
  }

  async function fetchReservations() {
    if (!isRaspberryPiRuntime) return;
    try {
      const response = await fetch("/reservations/current", { cache: "no-store" });
      if (!response.ok) return;
      const rows = await response.json();
      reservationList.innerHTML = "";
      if (!Array.isArray(rows) || rows.length === 0) {
        reservationList.innerHTML = '<tr class="empty-row"><td colspan="4">No current reservations.</td></tr>';
        return;
      }
      rows.slice(0, 8).reverse().forEach(addReservationToList);
    } catch (_) {
      // Local reservation submissions continue even if this refresh fails.
    }
  }

  async function pollLatestTap() {
    try {
      const response = await fetch(`/latest_tap?since=${tapCounter}`, { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      if (data.changed) handleLiveTap(data);
    } catch (_) {
      // Polling automatically resumes when the Raspberry Pi service is reachable.
    }
  }

  function handleLiveTap(data) {
    if (!data || Number(data.tap_counter) <= Number(tapCounter)) return;
    tapCounter = data.tap_counter;
    openTapDialog({
      uid: data.uid,
      tapCounter: data.tap_counter,
      message: data.message || "School ID detected",
      user: data.user || null,
      lookupUnavailable: Boolean(data.lookup_unavailable),
      lookupMessage: data.lookup_message || ""
    });
  }

  function connectTapStream() {
    if (!isRaspberryPiRuntime || !window.EventSource) return false;
    const stream = new EventSource(`/events/taps?since=${encodeURIComponent(tapCounter)}`);
    let fallbackTimer = null;
    stream.onmessage = (event) => {
      try { handleLiveTap(JSON.parse(event.data)); } catch (_) { /* ignore malformed events */ }
    };
    stream.onerror = () => {
      stream.close();
      if (!fallbackTimer) fallbackTimer = setInterval(pollLatestTap, 1500);
    };
    return true;
  }

  tapButton.addEventListener("click", () => openTapDialog({
    uid: "preview-card",
    tapCounter: `preview-${Date.now()}`,
    user: {
      firstname: "Alex",
      fullname: "Alex D. Santos",
      student_no: "2025-10482",
      course: "BS Computer Engineering",
      checked_in: previewCheckedIn
    },
    isPreview: true
  }));
  document.querySelector('[data-tap-action="check_in"]').addEventListener("click", handleAttendanceAction);
  document.querySelector('[data-tap-action="appointment"]').addEventListener("click", handleAppointment);
  serviceChoiceButtons.forEach((button) => button.addEventListener("click", () => showService(button.dataset.service)));
  backToTapButton.addEventListener("click", () => {
    showDialogStep("tap");
    startAutoCheckInCountdown();
  });
  openRegistrationButton.addEventListener("click", showRegistrationStep);
  registrationCodeForm.addEventListener("submit", handleRegistrationCode);
  backFromRegistrationButton.addEventListener("click", () => showDialogStep("tap"));
  closeDialogButton.addEventListener("click", closeTapDialog);
  finishTapButton.addEventListener("click", closeTapDialog);
  cancelReservationButton.addEventListener("click", () => cancelReservation("cancelled"));
  toggleLogsButton.addEventListener("click", () => {
    logsExpanded = !logsExpanded;
    renderRecentLogs();
    if (!logsExpanded) logsPanel.scrollIntoView({ block: "nearest" });
  });
  printingPrevButton?.addEventListener("click", () => showPrintingStep(printingStep - 1));
  printingNextButton?.addEventListener("click", () => {
    if (!validatePrintingStep(printingStep)) return;
    showPrintingStep(printingStep + 1);
  });
  formSection.addEventListener("pointerdown", () => {
    if (!formSection.hidden && successMessage.hidden) startReservationTimer();
  });
  formSection.addEventListener("input", () => {
    if (!formSection.hidden && successMessage.hidden) startReservationTimer();
  });
  dialogBackdrop.addEventListener("click", (event) => {
    if (event.target === dialogBackdrop) closeTapDialog();
  });
  tapDialog.addEventListener("pointerdown", () => {
    if (currentTap?.registered && !tapChoice.hidden) startAutoCheckInCountdown();
  });
  tapDialog.addEventListener("keydown", () => {
    if (currentTap?.registered && !tapChoice.hidden) startAutoCheckInCountdown();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!formSection.hidden) {
      cancelReservation("cancelled");
      return;
    }
    if (!dialogBackdrop.hidden) closeTapDialog();
  });

  forms.forEach((form) => form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!validateFile(form) || !form.checkValidity()) {
      form.reportValidity();
      return;
    }
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    reservationFormMessage.textContent = "";
    try {
      const reservation = await saveReservation(form);
      clearReservationTimer();
      reservationCountdown.textContent = "-";
      addReservationToList(reservation);
      form.hidden = true;
      successMessage.hidden = false;
      successCopy.textContent = reservation.service === "printing"
        ? "Your 3D printing reservation request has been submitted for review."
        : "Your teacher appointment request has been submitted for review.";
    } catch (error) {
      reservationFormMessage.textContent = error.message;
      startReservationTimer();
    } finally {
      submitButton.disabled = false;
    }
  }));
  newRequestButton.addEventListener("click", resetPage);

  function updateClock() {
    clock.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  setMinimumDates();
  updateClock();
  fetchLogs();
  fetchReservations();
  setInterval(updateClock, 15000);
  if (isRaspberryPiRuntime && !connectTapStream()) setInterval(pollLatestTap, 1500);
  window.addEventListener("resize", () => {
    if (!logsExpanded && recentLogs.length) renderRecentLogs();
  });

  window.airhub = Object.freeze({
    openTapDialog: (tap) => openTapDialog(tap)
  });
})();
