// Include theme links as well as links rendered from Markdown.
function markExternalLinks() {
  const siteOrigin = new URL(import.meta.env.SITE).origin;

  for (const link of document.querySelectorAll<HTMLAnchorElement>("a[href]")) {
    let url: URL;
    try {
      url = new URL(link.href);
    } catch {
      continue;
    }

    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.origin === window.location.origin ||
      url.origin === siteOrigin
    ) {
      continue;
    }

    link.target = "_blank";
    link.relList.add("noopener", "noreferrer");
    if (!link.hasAttribute("aria-description")) {
      link.setAttribute("aria-description", "Opens in a new tab");
    }
  }
}

markExternalLinks();
document.addEventListener("astro:page-load", markExternalLinks);
