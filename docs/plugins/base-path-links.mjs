// Astro's base setting does not prefix links and images written in Markdown.
export default function basePathLinks(base) {
  const prefix = base.replace(/\/$/, "");
  return {
    name: "base-path-links",
    element: {
      filter: [],
      visit(node, ctx) {
        for (const attribute of ["href", "src"]) {
          const url = node.properties?.[attribute];
          if (
            typeof url === "string" &&
            /^\/(?!\/)/.test(url) &&
            url.split(/[?#]/, 1)[0] !== prefix &&
            !url.startsWith(`${prefix}/`)
          ) {
            ctx.setProperty(node, attribute, prefix + url);
          }
        }
      },
    },
  };
}
