// @ts-check

import starlightAaiTheme from "@aai-institute/starlight-theme";
import { satteri } from "@astrojs/markdown-satteri";
import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import basePathLinks from "./plugins/base-path-links.mjs";

const base = "/agentic-appsec-playbook";

// User-facing documentation site. Content: src/content/docs. Design notes and
// acceptance records stay in the repository (design/, records/) and are linked.
export default defineConfig({
  site: "https://aai-institute.github.io",
  base,
  markdown: {
    processor: satteri({ hastPlugins: [basePathLinks(base)] }),
  },
  integrations: [
    {
      name: "external-links",
      hooks: {
        "astro:config:setup": ({ injectScript }) => {
          injectScript("page", 'import "/src/scripts/external-links.ts";');
          injectScript("page", 'import "/src/scripts/report-template.ts";');
        },
      },
    },
    starlight({
      title: "Agentic AppSec Playbook",
      description:
        "Run open-source, AI-agent-based application security tooling on your own code, safely.",
      plugins: [starlightAaiTheme()],
      customCss: ["./src/styles/custom.css"],
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/aai-institute/agentic-appsec-playbook",
        },
      ],
      editLink: {
        baseUrl:
          "https://github.com/aai-institute/agentic-appsec-playbook/edit/main/docs/",
      },
      sidebar: [
        { label: "Home", slug: "" },
        {
          label: "Getting started",
          items: [
            // Pointer into the next section: the no-regret measures must hold before the first run.
            {
              label: "Before your first run: secure the agent",
              link: "/sandbox/no-regret-measures/#_top",
            },
            { label: "Tool shortlist", slug: "tools/shortlist" },
            { label: "Choosing a model", slug: "tools/choosing-a-model" },
            { label: "Review skills", slug: "discovery/review-skills" },
            { label: "Tutorial: your first security review", slug: "getting-started" },
          ],
        },
        // Tool-neutral guidance on running an agent safely. Routes stay under /sandbox/ so
        // existing links keep working; the hardening checklist joins when it is released.
        {
          label: "Securing the agent",
          items: [
            {
              label: "Containment: the no-regret measures",
              slug: "sandbox/no-regret-measures",
            },
            { label: "The agent's context", slug: "sandbox/agent-context" },
          ],
        },
        {
          label: "Triage",
          items: [
            { label: "Overview", slug: "triage" },
            { label: "Triage rubric", slug: "triage/triage-rubric" },
            { label: "Run observations", slug: "triage/observations" },
          ],
        },
        {
          label: "Validation",
          items: [
            {
              label: "Validation loop record",
              slug: "validation/validation-loop-template",
            },
          ],
        },
        // Future exercises stay unpublished until ready.
        // See design/documentation-notes.md for the release checklist.
        {
          label: "Exercises",
          items: [
            {
              label: "1 · First discovery pass",
              slug: "exercises/first-discovery-pass",
            },
            {
              label: "2 · Validate a finding",
              slug: "exercises/validate-a-finding",
            },
          ],
        },
        {
          label: "Sandbox reference",
          items: [
            {
              label: "appsec-sbx",
              items: [
                { label: "Overview", slug: "sandbox/sbx" },
                {
                  label: "Providers and credentials",
                  slug: "sandbox/sbx/providers",
                },
                {
                  label: "VM lifetime, reset and policy",
                  slug: "sandbox/sbx/lifetime",
                },
                { label: "Skill installation", slug: "sandbox/sbx/skills" },
                {
                  label: "Import, export and host state",
                  slug: "sandbox/sbx/import-export",
                },
                { label: "Command reference", slug: "sandbox/sbx/commands" },
              ],
            },
            {
              label: "Threat model",
              items: [
                { label: "Overview", slug: "sandbox/threat-model" },
                { label: "Threat catalogue", slug: "sandbox/threat-model/catalogue" },
                { label: "Control coverage", slug: "sandbox/threat-model/controls" },
                { label: "Acceptance requirements", slug: "sandbox/threat-model/acceptance" },
              ],
            },
          ],
        },
        { label: "Glossary", slug: "glossary" },
      ],
    }),
  ],
});
