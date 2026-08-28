import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import * as THREE from "three";
import { STLExporter } from "three/addons/exporters/STLExporter.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { createEnclosureAirHubModel, PART_ORDER } from "../src/createHub.js";

const require = createRequire(import.meta.url);
const AdmZip = require("adm-zip");

const outDir = path.resolve("exports");
await fs.mkdir(outDir, { recursive: true });

const root = createEnclosureAirHubModel();
root.updateMatrixWorld(true);
const parts = root.userData.sculptRuntime.parts.filter((p) => PART_ORDER.includes(p.name) || p.userData.printable);

function flatten(object) {
  const geos = [];
  object.updateMatrixWorld(true);
  object.traverse((child) => {
    if (!child.isMesh || !child.geometry) return;
    let g = child.geometry.clone();
    if (g.index) g = g.toNonIndexed();
    g.deleteAttribute("uv");
    g.deleteAttribute("uv2");
    g.deleteAttribute("normal");
    g.applyMatrix4(child.matrixWorld);
    g.rotateX(-Math.PI / 2);
    geos.push(g);
  });
  if (!geos.length) return null;
  const merged = mergeGeometries(geos, false);
  if (!merged) throw new Error(`merge failed for ${object.name}`);
  return merged;
}

function geometryToStlBuffer(geometry) {
  const mesh = new THREE.Mesh(geometry);
  const exporter = new STLExporter();
  const data = exporter.parse(mesh, { binary: true });
  return Buffer.from(data.buffer, data.byteOffset, data.byteLength);
}

function xmlEscape(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" }[c]));
}

function geometryToObjectXml(id, name, geometry) {
  const pos = geometry.getAttribute("position");
  let index = geometry.getIndex();
  if (!index) {
    const n = pos.count;
    const arr = new Uint32Array(n);
    for (let i = 0; i < n; i++) arr[i] = i;
    geometry.setIndex(Array.from(arr));
    index = geometry.getIndex();
  }
  const verts = [];
  for (let i = 0; i < pos.count; i++) {
    verts.push(`          <vertex x="${pos.getX(i).toFixed(4)}" y="${pos.getY(i).toFixed(4)}" z="${pos.getZ(i).toFixed(4)}"/>`);
  }
  const tris = [];
  for (let i = 0; i < index.count; i += 3) {
    tris.push(`          <triangle v1="${index.getX(i)}" v2="${index.getX(i + 1)}" v3="${index.getX(i + 2)}"/>`);
  }
  return `      <object id="${id}" name="${xmlEscape(name)}" type="model">
        <mesh>
          <vertices>
${verts.join("\n")}
          </vertices>
          <triangles>
${tris.join("\n")}
          </triangles>
        </mesh>
      </object>`;
}

const exported = [];
for (const p of root.userData.sculptRuntime.parts) {
  if (!PART_ORDER.includes(p.name)) continue;
  const geo = flatten(p);
  if (!geo) continue;
  geo.computeVertexNormals();
  const stlName = `${String(exported.length + 1).padStart(2, "0")}-${p.name}.stl`;
  await fs.writeFile(path.join(outDir, stlName), geometryToStlBuffer(geo));
  exported.push({ name: p.name, title: p.userData.title, geo, stlName });
}

const objectsXml = exported.map((e, i) => geometryToObjectXml(i + 1, e.name, e.geo)).join("\n");
const itemsXml = exported.map((_, i) => `      <item objectid="${i + 1}"/>`).join("\n");
const modelXml = `<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <metadata name="Application">PrintPilot enclosure hub</metadata>
  <metadata name="Title">printpilot-air-hub</metadata>
  <resources>
${objectsXml}
  </resources>
  <build>
${itemsXml}
  </build>
</model>
`;

const zip = new AdmZip();
zip.addFile("[Content_Types].xml", Buffer.from(`<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
`));
zip.addFile("_rels/.rels", Buffer.from(`<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
`));
zip.addFile("3D/3dmodel.model", Buffer.from(modelXml, "utf8"));
const mfPath = path.join(outDir, "printpilot-air-hub.3mf");
zip.writeZip(mfPath);

const bounds = new THREE.Box3();
for (const e of exported) bounds.expandByObject(new THREE.Mesh(e.geo));
console.log(JSON.stringify({
  outDir,
  "3mf": mfPath,
  parts: exported.map((e) => ({ name: e.name, stl: e.stlName, triangles: e.geo.index.count / 3 })),
  size_mm: bounds.getSize(new THREE.Vector3()).toArray().map((n) => Number(n.toFixed(2))),
}, null, 2));
