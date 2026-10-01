// Print the report even when its disclosure is closed, then restore that state.
let panelsToClose: HTMLDetailsElement[] = [];

window.addEventListener("beforeprint", () => {
  for (const panel of document.querySelectorAll<HTMLDetailsElement>(
    ".run-report-panel:not([open])",
  )) {
    panelsToClose.push(panel);
    panel.open = true;
  }
});

window.addEventListener("afterprint", () => {
  for (const panel of panelsToClose) panel.open = false;
  panelsToClose = [];
});
