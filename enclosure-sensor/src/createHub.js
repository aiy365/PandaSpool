import * as THREE from "three";
import { DIM, POSE } from "./dims.js";
import { createBarrelJack, createC3, createExpander, createPMS5003, createRelay4, createSHT31 } from "./parts.js";
import { createShellBase, createShellLid } from "./shell.js";

function makeLabel(text, w = 26, h = 6.4) {
  if (typeof document === "undefined") {
    const g = new THREE.Group();
    g.name = `label:${text}`;
    return g;
  }
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 128;
  const g = c.getContext("2d");
  g.clearRect(0, 0, 512, 128);
  g.fillStyle = "#1a2229";
  g.fillRect(10, 20, 492, 88);
  g.strokeStyle = "#3dd6c6";
  g.lineWidth = 5;
  g.strokeRect(10, 20, 492, 88);
  g.fillStyle = "#eef8f6";
  g.font = "700 48px 'Segoe UI','PingFang SC',sans-serif";
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(text, 256, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true }),
  );
  m.name = `label:${text}`;
  return m;
}

function wrap(id, object, rest, explode) {
  const g = new THREE.Group();
  g.name = id;
  g.add(object);
  g.position.copy(rest);
  g.userData.rest = rest.clone();
  g.userData.explode = explode.clone();
  g.userData.title = object.userData.title || id;
  g.userData.part = object.userData.part || id;
  g.userData.printable = !!object.userData.printable;
  return g;
}

export const reviewViews = {
  hero: { position: [230, 150, 210], target: [0, 16, 0] },
  front: { position: [0, 70, 260], target: [0, 14, 20] },
  top: { position: [0, 320, 4], target: [0, 0, 0] },
  sensors: { position: [-200, 90, 120], target: [-40, 14, 8] },
  power: { position: [200, 100, 80], target: [40, 16, -4] },
  split: { position: [200, 180, 200], target: [0, 30, 0] },
};

const JACKS = [
  { id: "out-light", title: "补光灯" },
  { id: "out-always", title: "仓内长开" },
  { id: "out-boost", title: "仓内打印加强" },
  { id: "out-room", title: "车间有人" },
];

export function createEnclosureAirHubModel() {
  const root = new THREE.Group();
  root.name = "pandaspool-air-hub";
  const parts = [];

  const base = createShellBase();
  parts.push(wrap("shell-base", base, new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, -18, 0)));

  const lid = createShellLid();
  parts.push(wrap("shell-lid", lid, new THREE.Vector3(0, DIM.shell.y - DIM.shell.lid, 0), new THREE.Vector3(0, 42, 0)));

  const expander = createExpander();
  expander.rotation.y = Math.PI;
  parts.push(wrap("expander", expander, new THREE.Vector3(POSE.expander.x, 3.4, POSE.expander.z), new THREE.Vector3(-22, 18, -24)));

  const c3 = createC3();
  c3.rotation.y = Math.PI;
  parts.push(wrap("esp32-c3", c3, new THREE.Vector3(POSE.c3.x, 10.2, POSE.c3.z), new THREE.Vector3(-22, 36, -24)));

  const pms = createPMS5003();
  parts.push(wrap("pms5003", pms, new THREE.Vector3(POSE.pms.x, DIM.pms.y / 2 + 2.2, POSE.pms.z), new THREE.Vector3(-36, 22, 16)));

  const sht = createSHT31();
  sht.rotation.y = Math.PI / 2;
  parts.push(wrap("sht31", sht, new THREE.Vector3(POSE.sht.x, 8, POSE.sht.z), new THREE.Vector3(-40, 20, -6)));

  const relay = createRelay4();
  parts.push(wrap("relay-4ch", relay, new THREE.Vector3(POSE.relay.x, 6.4, POSE.relay.z), new THREE.Vector3(36, 16, 0)));

  const din = createBarrelJack();
  din.rotation.y = -Math.PI / 2;
  din.userData.title = "12V 圆口输入";
  din.userData.part = "dc-in";
  parts.push(wrap("dc-in", din, new THREE.Vector3(POSE.dcIn.x, 11, POSE.dcIn.z), new THREE.Vector3(0, 8, -30)));

  JACKS.forEach((j, i) => {
    const jack = createBarrelJack();
    jack.rotation.y = Math.PI / 2;
    jack.userData.title = `12V 出 · ${j.title}`;
    jack.userData.part = j.id;
    parts.push(wrap(j.id, jack, new THREE.Vector3(POSE.jacks[i], 11, POSE.jackZ), new THREE.Vector3(POSE.jacks[i] * 0.15, 6, 28)));
    const lab = makeLabel(j.title, 24, 6);
    lab.position.set(POSE.jacks[i], 3.4, DIM.shell.z / 2 + 0.4);
    lab.rotation.x = -0.15;
    root.add(lab);
  });

  const inLab = makeLabel("12V IN", 20, 5.4);
  inLab.position.set(POSE.dcIn.x, 18, -DIM.shell.z / 2 - 0.2);
  inLab.rotation.y = Math.PI;
  root.add(inLab);

  for (const p of parts) root.add(p);

  root.userData.sculptRuntime = {
    nodes: Object.fromEntries(parts.map((p) => [p.name, p])),
    parts,
  };
  root.userData.tick = (t, enabled) => {
    if (!enabled) return;
    const blades = root.getObjectByName("pms-blades");
    if (blades) blades.rotation.x = t * 7;
  };
  root.userData.setExplode = (k) => {
    for (const p of parts) {
      const r = p.userData.rest;
      const e = p.userData.explode;
      p.position.set(r.x + e.x * k, r.y + e.y * k, r.z + e.z * k);
    }
  };
  return root;
}

export const PART_ORDER = [
  "shell-base",
  "shell-lid",
  "esp32-c3",
  "expander",
  "pms5003",
  "sht31",
  "relay-4ch",
];
