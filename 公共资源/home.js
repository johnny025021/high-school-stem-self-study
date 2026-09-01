(() => {
  const lastSubject = localStorage.getItem("stembank:last-subject");
  if (lastSubject) {
    const card = document.querySelector(`[data-subject="${lastSubject}"]`);
    if (card) card.setAttribute("aria-description", "上次学习的学科");
  }

  document.querySelectorAll("[data-subject]").forEach((link) => {
    link.addEventListener("click", () => localStorage.setItem("stembank:last-subject", link.dataset.subject));
  });

  const SUBJECTS = [
    { id: "math", name: "数学", db: "general_learning_question_bank_stem_math_v1", html: "3.3.0" },
    { id: "physics", name: "物理", db: "general_learning_question_bank_stem_physics_v1", html: "3.3.0" },
    { id: "chemistry", name: "化学", db: "general_learning_question_bank_stem_chemistry_v1", html: "3.5.0" }
  ];
  const notice = (text, ms = 4200) => {
    const box = document.getElementById("homeNotice");
    if (!box) return;
    box.textContent = text;
    box.classList.remove("hidden");
    clearTimeout(notice.timer);
    notice.timer = setTimeout(() => box.classList.add("hidden"), ms);
  };
  const allFromStore = (db, name) => new Promise((resolve, reject) => {
    if (!db.objectStoreNames.contains(name)) return resolve([]);
    const req = db.transaction(name, "readonly").objectStore(name).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
  const databaseExists = async (name) => {
    if (!indexedDB.databases) return true;
    const list = await indexedDB.databases();
    return list.some(item => item.name === name);
  };
  const openExistingDb = async (name) => {
    if (!(await databaseExists(name))) return null;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(name);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  };
  const latestState = (events) => {
    const state = {};
    [...events].sort((a, b) => String(a.occurred_at || "").localeCompare(String(b.occurred_at || ""))).forEach(event => {
      if (event.question_id) state[event.question_id] = event.result || "unknown";
    });
    return state;
  };
  const requiredPackages = (events, subjectId) => {
    const map = new Map();
    events.forEach(event => {
      if (!event.package_id) return;
      const row = map.get(event.package_id) || { package_id: event.package_id, package_version: event.package_version || "", subject_id: subjectId, book_name: event.book_name || "", chapter_name: event.chapter_name || "", question_count_in_record: 0, suggested_file_name: event.package_file_name || "" };
      row.question_count_in_record++;
      map.set(event.package_id, row);
    });
    return [...map.values()];
  };
  const readSubjectRecord = async (subject) => {
    const db = await openExistingDb(subject.db);
    if (!db) return { app_id: "general_learning_question_bank", subject_id: subject.id, subject_name: subject.name, source_html_version: subject.html, minimum_compatible_html_version: "2.0.0", record_schema_version: "2.0", question_schema_version: "1.1", profile_id: "STUDENT_001", profile_name: "学生", device_id: "", device_name: "", exported_at: new Date().toISOString(), required_packages: [], events: [], feedback: [], question_state: {}, local_database_status: "not_created" };
    try {
      const [settings, allEvents, allFeedback] = await Promise.all([allFromStore(db, "settings"), allFromStore(db, "events"), allFromStore(db, "feedback")]);
      const setting = Object.fromEntries(settings.map(row => [row.key, row.value]));
      const profile = setting.profile || { profile_id: "STUDENT_001", profile_name: "学生" };
      const device = setting.device || { device_id: "", device_name: "" };
      const events = allEvents.filter(event => !event.profile_id || event.profile_id === profile.profile_id);
      const feedback = allFeedback.filter(item => !item.profile_id || item.profile_id === profile.profile_id);
      return { app_id: "general_learning_question_bank", subject_id: subject.id, subject_name: subject.name, profile_id: profile.profile_id, profile_name: profile.profile_name, source_html_version: subject.html, minimum_compatible_html_version: "2.0.0", record_schema_version: "2.0", question_schema_version: "1.1", device_id: device.device_id || "", device_name: device.device_name || "", exported_at: new Date().toISOString(), required_packages: requiredPackages(events, subject.id), events: events.sort((a, b) => String(a.occurred_at || "").localeCompare(String(b.occurred_at || ""))), feedback, question_state: latestState(events), local_database_status: "loaded" };
    } finally { db.close(); }
  };
  const stamp = () => new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z").replace("T", "_");
  const exportAll = async () => {
    const button = document.getElementById("exportAllRecords");
    button.disabled = true;
    button.textContent = "正在汇总三科记录…";
    try {
      const records = await Promise.all(SUBJECTS.map(readSubjectRecord));
      const documentData = { backup_type: "stembank_combined_subject_records", combined_schema_version: "1.0", app_id: "general_learning_question_bank", exported_at: new Date().toISOString(), subject_count: 3, total_events: records.reduce((sum, item) => sum + item.events.length, 0), total_feedback: records.reduce((sum, item) => sum + item.feedback.length, 0), subjects: Object.fromEntries(records.map(item => [item.subject_id, item])) };
      const fileName = `数理化学习记录_${stamp()}.json`;
      const file = new File([JSON.stringify(documentData, null, 2)], fileName, { type: "application/json" });
      let shared = false;
      if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({ title: "数理化最新学习记录", text: "STEMBank 数学、物理、化学三科学习记录合并备份", files: [file] });
          shared = true;
          notice(`已调用系统分享：三科共 ${documentData.total_events} 条学习事件`);
        } catch (shareError) {
          if (shareError?.name === "AbortError") return;
        }
      }
      if (!shared) {
        const url = URL.createObjectURL(file), link = document.createElement("a");
        link.href = url; link.download = fileName; document.body.appendChild(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1500);
        notice(`已下载三科合并记录：共 ${documentData.total_events} 条学习事件`);
      }
    } catch (error) {
      if (error?.name !== "AbortError") notice(`导出失败：${error.message}`, 6000);
    } finally {
      button.disabled = false;
      button.textContent = "导出数理化学习记录";
    }
  };
  document.getElementById("exportAllRecords")?.addEventListener("click", exportAll);
})();
