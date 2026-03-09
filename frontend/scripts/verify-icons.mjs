#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { access } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import path from "node:path";
import process from "node:process";

const projectRoot = process.cwd();
const publicDir = path.join(projectRoot, "public");
const layoutPath = path.join(projectRoot, "app", "layout.tsx");
const manifestPath = path.join(publicDir, "site.webmanifest");

const requiredPublicAssets = [
  "favicon.ico",
  "favicon.svg",
  "favicon-96x96.png",
  "apple-touch-icon.png",
  "site.webmanifest",
];

const requiredLayoutReferences = [
  'manifest: "/site.webmanifest"',
  'url: "/favicon.ico"',
  'url: "/favicon.svg"',
  'url: "/favicon-96x96.png"',
  'apple: "/apple-touch-icon.png"',
];

function toPublicPath(value) {
  if (!value || typeof value !== "string") {
    return null;
  }

  if (value.startsWith("/")) {
    return value.slice(1);
  }

  return value;
}

async function assertReadable(relativePath) {
  const absolutePath = path.join(publicDir, relativePath);
  await access(absolutePath, fsConstants.R_OK);
}

async function verifyFilesystemAssets() {
  for (const asset of requiredPublicAssets) {
    await assertReadable(asset);
  }
}

async function verifyLayoutReferences() {
  const layoutContent = await readFile(layoutPath, "utf8");

  for (const snippet of requiredLayoutReferences) {
    if (!layoutContent.includes(snippet)) {
      throw new Error(
        `Missing metadata icon reference in app/layout.tsx: ${snippet}`
      );
    }
  }
}

async function verifyManifestIcons() {
  const manifestContent = await readFile(manifestPath, "utf8");
  const manifest = JSON.parse(manifestContent);

  if (!Array.isArray(manifest.icons) || manifest.icons.length === 0) {
    throw new Error("site.webmanifest has no icons array entries.");
  }

  for (const icon of manifest.icons) {
    const src = toPublicPath(icon?.src);
    if (!src) {
      throw new Error("site.webmanifest contains an icon with invalid src.");
    }
    await assertReadable(src);
  }
}

async function verifyHttpAssets(baseUrl) {
  const manifestContent = await readFile(manifestPath, "utf8");
  const manifest = JSON.parse(manifestContent);
  const manifestIconPaths = manifest.icons
    .map((icon) => icon?.src)
    .filter((value) => typeof value === "string");

  const paths = [
    "/favicon.ico",
    "/favicon.svg",
    "/favicon-96x96.png",
    "/apple-touch-icon.png",
    "/site.webmanifest",
    ...manifestIconPaths,
  ];

  const uniquePaths = [...new Set(paths)];

  for (const assetPath of uniquePaths) {
    const response = await fetch(`${baseUrl}${assetPath}`, {
      redirect: "follow",
    });

    if (response.status !== 200) {
      throw new Error(
        `HTTP check failed for ${assetPath}: expected 200, got ${response.status}`
      );
    }
  }
}

async function main() {
  const baseUrlArg = process.argv.find((arg) => arg.startsWith("--base-url="));
  const baseUrl = baseUrlArg?.split("=")[1]?.replace(/\/+$/, "");

  await verifyFilesystemAssets();
  await verifyLayoutReferences();
  await verifyManifestIcons();

  if (baseUrl) {
    await verifyHttpAssets(baseUrl);
    console.log(`Icon checks passed (filesystem + metadata + HTTP at ${baseUrl}).`);
    return;
  }

  console.log("Icon checks passed (filesystem + metadata references + manifest icons).");
}

main().catch((error) => {
  console.error(`Icon checks failed: ${error.message}`);
  process.exit(1);
});
