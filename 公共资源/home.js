(() => {
  const lastSubject = localStorage.getItem("stembank:last-subject");
  if (!lastSubject) return;
  const card = document.querySelector(`[data-subject="${lastSubject}"]`);
  if (card) card.setAttribute("aria-description", "上次学习的学科");

  document.querySelectorAll("[data-subject]").forEach((link) => {
    link.addEventListener("click", () => localStorage.setItem("stembank:last-subject", link.dataset.subject));
  });
})();
