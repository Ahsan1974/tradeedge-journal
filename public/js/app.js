/* TradeEdge Journal — shared UI */
(function () {
  "use strict";

  function initIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function initSidebar() {
    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("menuToggle");
    const overlay = document.getElementById("sidebarOverlay");
    if (!sidebar || !toggle) return;

    function open() {
      sidebar.classList.add("open");
      if (overlay) {
        overlay.hidden = false;
        overlay.classList.add("open");
      }
      toggle.setAttribute("aria-expanded", "true");
    }
    function close() {
      sidebar.classList.remove("open");
      if (overlay) {
        overlay.classList.remove("open");
        overlay.hidden = true;
      }
      toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", () => {
      if (sidebar.classList.contains("open")) close();
      else open();
    });
    if (overlay) overlay.addEventListener("click", close);
  }

  function initFlashes() {
    document.querySelectorAll(".flash-close").forEach((btn) => {
      btn.addEventListener("click", () => btn.closest(".flash")?.remove());
    });
    setTimeout(() => {
      document.querySelectorAll(".flash").forEach((el) => el.remove());
    }, 6000);
  }

  function initConfirm() {
    const modal = document.getElementById("confirmModal");
    if (!modal) return;
    const msg = document.getElementById("confirmMessage");
    const ok = document.getElementById("confirmOk");
    const cancel = document.getElementById("confirmCancel");
    let pendingForm = null;

    function openModal(message, form) {
      pendingForm = form;
      if (msg) msg.textContent = message || "Are you sure?";
      modal.hidden = false;
      modal.classList.add("open");
      ok?.focus();
    }
    function closeModal() {
      pendingForm = null;
      modal.classList.remove("open");
      modal.hidden = true;
    }

    document.querySelectorAll("form.js-confirm-delete").forEach((form) => {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        openModal(form.dataset.message || "Delete this item?", form);
      });
    });
    cancel?.addEventListener("click", closeModal);
    ok?.addEventListener("click", () => {
      if (pendingForm) {
        const f = pendingForm;
        pendingForm = null;
        closeModal();
        f.submit();
      }
    });
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("open")) closeModal();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initIcons();
    initSidebar();
    initFlashes();
    initConfirm();
  });
})();
