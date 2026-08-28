import * as THREE from "three";
import { DIM, POSE } from "./dims.js";
import { box, cyl, mat, mesh } from "./parts.js";

function roundedRect(w, h, r) {
  const s = new THREE.Shape();
  const x = -w / 2;
  const y = -h / 2;
  const rr = Math.min(r, w / 2 - 0.2, h / 2 - 0.2);
  s.moveTo(x + rr, y);
  s.lineTo(x + w - rr, y);
  s.absarc(x + w - rr, y + rr, rr, -Math.PI / 2, 0, false);
  s.lineTo(x + w, y + h - rr);
  s.absarc(x + w - rr, y + h - rr, rr, 0, Math.PI / 2, false);
  s.lineTo(x + rr, y + h);
  s.absarc(x + rr, y + h - rr, rr, Math.PI / 2, Math.PI, false);
  s.lineTo(x, y + rr);
  s.absarc(x + rr, y + rr, rr, Math.PI, Math.PI * 1.5, false);
  return s;
}

function extrudeY(shape, height, material, name) {
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: height,
    bevelEnabled: false,
    curveSegments: 12,
  });
  geo.rotateX(-Math.PI / 2);
  const m = mesh(geo, material, name);
  return m;
}

function wallRing(w, d, r, wall, height, material, name) {
  const outer = roundedRect(w, d, r);
  const inner = roundedRect(w - wall * 2, d - wall * 2, Math.max(1.2, r - wall));
  inner.holes = [];
  outer.holes.push(inner);
  return extrudeY(outer, height, material, name);
}

function addBoss(parent, x, z, h, inner = 3.2) {
  const od = cyl(3.6, 3.6, h, mat({ color: 0xd8dee4, roughness: 0.55 }), "boss-od", 16);
  od.position.set(x, h / 2, z);
  parent.add(od);
  const ring = mesh(
    new THREE.RingGeometry(inner / 2, 3.55, 18),
    mat({ color: 0x6b747c, roughness: 0.5 }),
    "boss-mark",
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.set(x, h + 0.05, z);
  parent.add(ring);
}

function grille(w, h, material) {
  const g = new THREE.Group();
  const plate = box(w, h, 1.6, material, "grille-plate");
  g.add(plate);
  const slotM = mat({ color: 0x1b2228, roughness: 0.55 });
  const n = 9;
  for (let i = 0; i < n; i++) {
    const s = box(w - 4, 1.15, 1.8, slotM, `slot-${i}`);
    s.position.set(0, (i - (n - 1) / 2) * 2.35, 0.2);
    g.add(s);
  }
  return g;
}

export function createShellBase() {
  const g = new THREE.Group();
  g.name = "shell-base";
  g.userData.title = "外壳 · 底壳";
  g.userData.part = "shell-base";
  g.userData.printable = true;
  const S = DIM.shell;
  const body = mat({ color: 0xcfd6dd, roughness: 0.58, metalness: 0.04 });
  const accent = mat({ color: 0x2a333c, roughness: 0.45 });

  const floor = extrudeY(roundedRect(S.x, S.z, S.radius), S.floor, body, "floor");
  g.add(floor);

  const walls = wallRing(S.x, S.z, S.radius, S.wall, S.y - S.lid - 0.4, body, "walls");
  walls.position.y = S.floor;
  g.add(walls);

  // inner lip shelf
  const shelf = wallRing(S.x - 1.2, S.z - 1.2, S.radius - 0.6, 1.15, 3.2, body, "lip-shelf");
  shelf.position.y = S.y - S.lid - 3.4;
  g.add(shelf);

  const inset = 10;
  addBoss(g, -S.x / 2 + inset, -S.z / 2 + inset, 8);
  addBoss(g, S.x / 2 - inset, -S.z / 2 + inset, 8);
  addBoss(g, -S.x / 2 + inset, S.z / 2 - inset, 8);
  addBoss(g, S.x / 2 - inset, S.z / 2 - inset, 8);

  // PMS cradle
  const cradle = mat({ color: 0xb7c0c8, roughness: 0.5 });
  for (const [sx, sz] of [
    [-DIM.pms.holeX / 2, -DIM.pms.holeZ / 2],
    [DIM.pms.holeX / 2, -DIM.pms.holeZ / 2],
    [-DIM.pms.holeX / 2, DIM.pms.holeZ / 2],
    [DIM.pms.holeX / 2, DIM.pms.holeZ / 2],
  ]) {
    addBoss(g, POSE.pms.x + sx, POSE.pms.z + sz, 4.2, 1.7);
  }
  const pmsPad = box(DIM.pms.x + 4, 1.2, DIM.pms.z + 4, cradle, "pms-pad");
  pmsPad.position.set(POSE.pms.x, 0.8, POSE.pms.z);
  g.add(pmsPad);

  // relay pads
  for (const [sx, sz] of [
    [-32, -30],
    [32, -30],
    [-32, 30],
    [32, 30],
  ]) {
    addBoss(g, POSE.relay.x + sx, POSE.relay.z + sz, 5.5, 1.7);
  }

  // expander rails
  const rail = box(DIM.expander.x + 2, 2.2, 3.2, cradle, "rail");
  const r1 = rail.clone();
  r1.position.set(POSE.expander.x, 1.4, POSE.expander.z - DIM.expander.z / 2 + 2);
  g.add(r1);
  const r2 = rail.clone();
  r2.position.set(POSE.expander.x, 1.4, POSE.expander.z + DIM.expander.z / 2 - 2);
  g.add(r2);

  // front fascia recess
  const fascia = box(92, 16, 2.2, accent, "fascia");
  fascia.position.set(0, 11, S.z / 2 - 1.0);
  g.add(fascia);

  // PMS inlet window on front-left
  const inlet = grille(28, 16, accent);
  inlet.rotation.y = 0;
  inlet.position.set(POSE.pms.x, 14, S.z / 2 - 0.6);
  g.add(inlet);

  // fan exhaust on left wall
  const exhaust = grille(22, 18, accent);
  exhaust.rotation.y = Math.PI / 2;
  exhaust.position.set(-S.x / 2 + 0.9, 15, POSE.pms.z);
  g.add(exhaust);

  // SHT chimney
  const chim = box(18, 14, 2, accent, "sht-vent");
  chim.position.set(-S.x / 2 + 1.0, 16, POSE.sht.z);
  chim.rotation.y = Math.PI / 2;
  g.add(chim);

  return g;
}

export function createShellLid() {
  const g = new THREE.Group();
  g.name = "shell-lid";
  g.userData.title = "外壳 · 顶盖";
  g.userData.part = "shell-lid";
  g.userData.printable = true;
  const S = DIM.shell;
  const body = mat({ color: 0xd7dde3, roughness: 0.52, metalness: 0.05 });
  const dark = mat({ color: 0x243038, roughness: 0.42 });

  const top = extrudeY(roundedRect(S.x, S.z, S.radius), S.lid, body, "lid-top");
  g.add(top);

  const lip = wallRing(S.x - 2.6, S.z - 2.6, S.radius - 1.4, 1.3, 4.4, body, "lid-lip");
  lip.position.y = -4.4;
  g.add(lip);

  const inset = 10;
  for (const [x, z] of [
    [-S.x / 2 + inset, -S.z / 2 + inset],
    [S.x / 2 - inset, -S.z / 2 + inset],
    [-S.x / 2 + inset, S.z / 2 - inset],
    [S.x / 2 - inset, S.z / 2 - inset],
  ]) {
    const cap = cyl(4.2, 4.2, 1.4, dark, "lid-cap", 14);
    cap.position.set(x, S.lid + 0.2, z);
    g.add(cap);
    const hole = cyl(1.7, 1.7, 3.2, mat({ color: 0x111 }), "lid-hole", 10);
    hole.position.set(x, S.lid - 0.4, z);
    g.add(hole);
  }

  // status window over relays
  const win = box(58, 0.8, 18, mat({ color: 0x9ad7d0, roughness: 0.15, transmission: 0.4, thickness: 1, transparent: true, opacity: 0.55 }), "window");
  win.position.set(POSE.relay.x, S.lid + 0.3, POSE.relay.z + 18);
  g.add(win);

  const badge = box(36, 0.6, 8, dark, "badge");
  badge.position.set(-40, S.lid + 0.4, -40);
  g.add(badge);

  return g;
}
