// @ts-check

import starlightAaiTheme from "@aai-institute/starlight-theme";
import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";

// User-facing documentation site. Content: src/content/docs. Design notes and
// acceptance records stay in the repository (design/, records/) and are linked.
// No `site`/`base` yet: publication is a later step.
export default defineConfig({
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
