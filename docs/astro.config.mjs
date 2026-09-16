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
        { label: "Getting started", slug: "getting-started" },
        {
          label: "1 · Sandbox",
          items: [
            {
              label: "A safe environment for experiments",
              slug: "sandbox/no-regret-measures",
            },
            {
              label: "AppSec shell (Docker sbx)",
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
                { label: "Skills", slug: "sandbox/sbx/skills" },
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
        {
          label: "2 · Tools",
          items: [{ label: "Shortlist", slug: "tools/shortlist" }],
        },
        {
          label: "3 · Triage",
          items: [
            { label: "Triage rubric", slug: "triage/triage-rubric" },
            { label: "Observations (run table)", slug: "triage/observations" },
          ],
        },
        {
          label: "4 · Validation",
          items: [
            {
              label: "Validation-loop record",
              slug: "validation/validation-loop-template",
            },
          ],
        },
        {
          label: "5 · Hardening",
          items: [
            {
              label: "Hardening checklist",
              slug: "hardening/hardening-checklist",
            },
          ],
        },
        {
          label: "Exercises",
          items: [
            {
              label: "1 · First discovery pass",
              slug: "exercises/first-discovery-pass",
            },
          ],
        },
      ],
    }),
  ],
});
