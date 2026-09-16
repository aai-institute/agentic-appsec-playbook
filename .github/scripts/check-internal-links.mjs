// Verifies that every site-internal link in the built output resolves to a
// page that was actually generated. Catches links left behind by a rename and
// links to pages that never existed. Run after `astro build`, against dist/.
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const dist = resolve(process.argv[2] ?? "docs/dist");
if (!existsSync(dist)) {
	console.error(`No build output at ${dist}. Run the build first.`);
	process.exit(2);
}

function htmlFiles(dir) {
	return readdirSync(dir).flatMap((entry) => {
		const full = join(dir, entry);
		if (statSync(full).isDirectory()) return htmlFiles(full);
		return full.endsWith(".html") ? [full] : [];
	});
}

// Site-internal hrefs only: a leading slash, but not "//" (protocol-relative).
const HREF = /href="(\/(?!\/)[^"#?]*)/g;

const failures = [];
for (const file of htmlFiles(dist)) {
	const html = readFileSync(file, "utf8");
	for (const [, href] of html.matchAll(HREF)) {
		const target = join(dist, href);
		const ok =
			existsSync(target) &&
			(statSync(target).isFile() || existsSync(join(target, "index.html")));
		if (!ok) failures.push({ page: file.slice(dist.length + 1), href });
	}
}

if (failures.length > 0) {
	console.error(`${failures.length} internal link(s) do not resolve:\n`);
	for (const { page, href } of failures) console.error(`  ${page}  ->  ${href}`);
	process.exit(1);
}
console.log("All internal links resolve.");
