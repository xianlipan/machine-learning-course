function initializeSyllabusMap(root) {
  if (root.dataset.initialized === "true") return;

  const svg = root.querySelector("svg");
  const motion = root.querySelector("#syllabus-motion");
  const startButton = root.querySelector('[data-map-action="start"]');
  const pauseButton = root.querySelector('[data-map-action="pause"]');
  const resetButton = root.querySelector('[data-map-action="reset"]');
  const routeToggle = root.querySelector('[data-map-action="route"]');

  if (!svg || !motion || typeof motion.beginElement !== "function") {
    startButton.disabled = true;
    pauseButton.disabled = true;
    return;
  }

  let started = false;
  let paused = false;

  // 先把角色放在路径起点，等待用户点击开始。
  motion.beginElement();
  svg.pauseAnimations();

  startButton.addEventListener("click", () => {
    if (!started) {
      svg.unpauseAnimations();
      svg.setCurrentTime(0);
      motion.beginElement();
      started = true;
    } else if (paused) {
      svg.unpauseAnimations();
    }

    paused = false;
    startButton.textContent = "继续探索";
    pauseButton.textContent = "暂停";
    pauseButton.disabled = false;
  });

  pauseButton.addEventListener("click", () => {
    if (!started) return;

    if (paused) {
      svg.unpauseAnimations();
      pauseButton.textContent = "暂停";
    } else {
      svg.pauseAnimations();
      pauseButton.textContent = "继续";
    }
    paused = !paused;
  });

  resetButton.addEventListener("click", () => {
    svg.unpauseAnimations();
    svg.setCurrentTime(0);
    motion.beginElement();
    svg.pauseAnimations();
    started = false;
    paused = false;
    startButton.textContent = "开始探索";
    pauseButton.textContent = "暂停";
    pauseButton.disabled = true;
  });

  routeToggle.addEventListener("change", () => {
    root.classList.toggle("syllabus-map--route-hidden", !routeToggle.checked);
  });

  root.dataset.initialized = "true";
}

function initializeAllSyllabusMaps() {
  document.querySelectorAll("[data-syllabus-map]").forEach(initializeSyllabusMap);
}

if (typeof document$ !== "undefined") {
  document$.subscribe(initializeAllSyllabusMaps);
} else {
  document.addEventListener("DOMContentLoaded", initializeAllSyllabusMaps);
}
