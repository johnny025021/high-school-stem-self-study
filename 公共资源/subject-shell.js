(() => {
  const cfg = window.SUBJECT_CONFIG;
  if (!cfg) throw new Error("缺少学科配置 SUBJECT_CONFIG");

  const moduleText = {
    chapter_practice: {
      title: "章节练习",
      symbol: "题",
      description: "选择书籍或题库大类，再选择需要学习的章节。题库正式接入后，这里将显示题面、答案、解析和掌握度评价。"
    },
    formula_memory: {
      title: cfg.formulaTitle || "公式记忆",
      symbol: "ƒ",
      description: cfg.formulaDescription || "通过名称、条件和表达式进行双向回忆，并记录掌握程度。"
    },
    secondary_conclusion_memory: {
      title: "二级结论记忆",
      symbol: "∴",
      description: cfg.conclusionDescription || "记忆结论、适用条件、限制范围与常见误用。"
    }
  };

  const storageKey = `stembank:${cfg.id}:active-module`;
  const title = document.querySelector("#moduleTitle");
  const symbol = document.querySelector("#moduleSymbol");
  const description = document.querySelector("#moduleDescription");
  const librarySelect = document.querySelector("#librarySelect");
  const packageInput = document.querySelector("#packageInput");
  const queueNote = document.querySelector("#queueNote");

  (cfg.libraries || []).forEach((library) => {
    const option = document.createElement("option");
    option.value = library.id;
    option.textContent = library.name;
    librarySelect.append(option);
  });

  function setModule(id) {
    const module = moduleText[id] || moduleText.chapter_practice;
    document.querySelectorAll(".module-tab").forEach((button) => {
      const active = button.dataset.module === id;
      button.classList.toggle("on", active);
      button.setAttribute("aria-selected", String(active));
    });
    title.textContent = module.title;
    symbol.textContent = module.symbol;
    description.textContent = module.description;
    document.querySelector("#activeModulePill").textContent = module.title;
    localStorage.setItem(storageKey, id);
  }

  document.querySelectorAll(".module-tab").forEach((button) => {
    button.addEventListener("click", () => setModule(button.dataset.module));
  });

  const padToolsDialog = document.querySelector("#padToolsDialog");
  document.querySelector("#openPadTools")?.addEventListener("click", () => padToolsDialog?.showModal());
  document.querySelector("#closePadTools")?.addEventListener("click", () => padToolsDialog?.close());
  padToolsDialog?.addEventListener("click", (event) => {
    if (event.target === padToolsDialog) padToolsDialog.close();
  });

  packageInput.addEventListener("change", () => {
    const files = [...packageInput.files];
    queueNote.textContent = files.length
      ? `已选择 ${files.length} 个 ZIP；当前为架构版，下一阶段启用结构校验和正式导入。`
      : "尚未选择题库包";
  });

  document.querySelector("#subjectVersion").textContent = `界面 ${cfg.version}`;
  document.querySelector("#subjectStatus").textContent = cfg.status;
  document.querySelector("#recordPath").textContent = `学习记录/${cfg.folder}/`;
  document.querySelector("#dbName").textContent = cfg.dbName;
  document.title = `${cfg.name}自主学习 · STEMBank`;
  setModule(localStorage.getItem(storageKey) || "chapter_practice");
})();
