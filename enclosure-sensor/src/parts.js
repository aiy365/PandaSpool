import * as THREE from "three";
import { DIM } from "./dims.js";

export function mat(opts) {
  return new THREE.MeshPhysicalMaterial({
    color: 0x888888,
    roughness: 0.48,
    metalness: 0.06,
    ...opts,
  });
}

export function mesh(geo, material, name) {
  const m = new THREE.Mesh(geo, material);
  m.name = name || "";
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

export function box(w, h, d, material, name) {
  return mesh(new THREE.BoxGeometry(w, h, d), material, name);
}

export function cyl(rt, rb, h, material, name, seg = 20) {
  return mesh(new THREE.CylinderGeometry(rt, rb, h, seg), material, name);
}

function header(n, pitch = 2.54) {
  const g = new THREE.Group();
  const plastic = mat({ color: 0x141414, roughness: 0.7 });
  const pin = mat({ color: 0xcbb56a, metalness: 0.82, roughness: 0.26 });
  g.add(box(n * pitch + 1.1, 2.3, 2.3, plastic, "hdr"));
  for (let i = 0; i < n; i++) {
    const p = cyl(0.3, 0.3, 7.2, pin, `p${i}`, 8);
    p.position.set((i - (n - 1) / 2) * pitch, 1.8, 0);
    g.add(p);
  }
  return g;
}

/** ESP32-C3 SuperMini / PRO MINI 22.52 × 18 mm */
export function createC3() {
  const g = new THREE.Group();
  g.name = "esp32-c3";
  g.userData.title = "ESP32-C3 SuperMini 22.52×18";
  g.userData.part = "esp32-c3";
  const { x, z, t } = DIM.c3;
  const pcb = mat({ color: 0x121417, roughness: 0.52 });
  g.add(box(x, t, z, pcb, "c3-pcb"));
  const gold = mat({ color: 0xd7b56a, metalness: 0.75, roughness: 0.28 });
  for (let side of [-1, 1]) {
    for (let i = 0; i < 9; i++) {
      const pad = box(1.5, 0.2, 1.7, gold, "pad");
      pad.position.set(side * (x / 2 - 0.2), t / 2 + 0.05, -z / 2 + 2.4 + i * 2.3);
      g.add(pad);
    }
  }
  const chip = box(5.1, 0.85, 5.1, mat({ color: 0x0a0a0a, roughness: 0.35 }), "qfn");
  chip.position.y = t / 2 + 0.5;
  g.add(chip);
  const usb = box(8.8, 3.1, 7.2, mat({ color: 0xd8dde2, metalness: 0.55, roughness: 0.3 }), "usb-c");
  usb.position.set(0, 1.4, z / 2 + 1.4);
  g.add(usb);
  for (const sx of [-3.2, 3.2]) {
    const btn = box(2.6, 1.4, 2.6, mat({ color: 0xf2f2f2, roughness: 0.45 }), "btn");
    btn.position.set(sx, t / 2 + 0.8, 4.2);
    g.add(btn);
  }
  const xtal = box(2.2, 0.7, 1.6, mat({ color: 0xc9b27a, metalness: 0.4, roughness: 0.4 }), "xtal");
  xtal.position.set(-4.4, t / 2 + 0.4, -1.2);
  g.add(xtal);
  const ant = box(11, 0.35, 2.6, gold, "ant");
  ant.position.set(0, t / 2 + 0.15, -z / 2 + 2.2);
  g.add(ant);
  return g;
}

/** ESP32-C3 扩展板 PH2.0 + 彩排端子 */
export function createExpander() {
  const g = new THREE.Group();
  g.name = "expander";
  g.userData.title = "ESP32-C3 扩展板 PH2.0";
  g.userData.part = "expander";
  const { x, z, t } = DIM.expander;
  g.add(box(x, t, z, mat({ color: 0x101214, roughness: 0.5 }), "exp-pcb"));
  const colors = [0xd92b2b, 0xe0b000, 0x2f9e4f, 0x2563eb];
  for (let col = 0; col < 2; col++) {
    for (let i = 0; i < 9; i++) {
      const c = colors[i < 2 ? 0 : i < 5 ? 1 : i < 7 ? 2 : 3];
      const blk = box(5.2, 6.2, 2.4, mat({ color: c, roughness: 0.45 }), "term");
      blk.position.set((col === 0 ? -1 : 1) * (x / 2 - 3.4), 3.4, -z / 2 + 5 + i * 3.5);
      g.add(blk);
    }
  }
  const ph = box(6.4, 5.2, 8.2, mat({ color: 0xf4f6f8, roughness: 0.4 }), "ph20");
  ph.position.set(-6, 3.2, z / 2 - 8);
  g.add(ph);
  const lipo = box(8, 3.2, 6, mat({ color: 0x1f7a3a, roughness: 0.4 }), "lipo");
  lipo.position.set(8, 2.2, z / 2 - 8);
  g.add(lipo);
  const usb = box(8.6, 3, 7, mat({ color: 0xd8dde2, metalness: 0.5, roughness: 0.3 }), "exp-usb");
  usb.position.set(0, 2.1, z / 2 + 1.2);
  g.add(usb);
  return g;
}

/** PMS5003 50×38×21，风扇在 −X 端面 */
export function createPMS5003() {
  const g = new THREE.Group();
  g.name = "pms5003";
  g.userData.title = "PMS5003 50×38×21";
  g.userData.part = "pms5003";
  const { x, z, y } = DIM.pms;
  const cream = mat({ color: 0xe8e4d8, roughness: 0.48, metalness: 0.12 });
  const dark = mat({ color: 0x2a2c30, roughness: 0.42 });
  g.add(box(x - 6, y, z, cream, "pms-body"));
  const fanEnd = box(6, y, z, dark, "pms-fan-end");
  fanEnd.position.x = -x / 2 + 3;
  g.add(fanEnd);
  const ring = cyl(8.6, 8.6, 1.4, dark, "fan-ring", 24);
  ring.rotation.z = Math.PI / 2;
  ring.position.set(-x / 2 + 0.4, 0, 0);
  g.add(ring);
  const blades = new THREE.Group();
  blades.name = "pms-blades";
  for (let i = 0; i < 7; i++) {
    const b = box(7.6, 1.8, 0.7, mat({ color: 0x3a3d42, roughness: 0.35 }), `bl${i}`);
    b.position.x = -3.6;
    const p = new THREE.Group();
    p.rotation.x = (i / 7) * Math.PI * 2;
    p.add(b);
    blades.add(p);
  }
  blades.rotation.z = Math.PI / 2;
  blades.position.set(-x / 2 + 1.2, 0, 0);
  g.add(blades);
  g.userData.spin = blades;
  const inlet = box(1.2, 10, 22, dark, "inlet");
  inlet.position.set(x / 2 - 0.4, 0, 0);
  g.add(inlet);
  return g;
}

/** GY-SHT31-D 13.2×10.4 */
export function createSHT31() {
  const g = new THREE.Group();
  g.name = "sht31";
  g.userData.title = "GY-SHT31-D 13.2×10.4";
  g.userData.part = "sht31";
  const { x, z, t } = DIM.sht;
  g.add(box(x, t, z, mat({ color: 0x5b2d8a, roughness: 0.46 }), "sht-pcb"));
  const hole = cyl(1.15, 1.15, t + 0.4, mat({ color: 0x2a1540, roughness: 0.6 }), "hole", 12);
  hole.position.set(x / 2 - 2.2, 0, -z / 2 + 2.2);
  g.add(hole);
  const ic = box(2.6, 0.8, 2.6, mat({ color: 0x111111, roughness: 0.32 }), "sht-ic");
  ic.position.set(-1.2, t / 2 + 0.4, 0.4);
  g.add(ic);
  const hdr = header(6, 2.0);
  hdr.scale.set(0.85, 0.85, 0.85);
  hdr.position.set(0, 1.1, z / 2 - 1.2);
  g.add(hdr);
  return g;
}

/** 4 路继电器 75×74×20 */
export function createRelay4() {
  const g = new THREE.Group();
  g.name = "relay-4ch";
  g.userData.title = "4路继电器 75×74×20";
  g.userData.part = "relay-4ch";
  const { x, z, y } = DIM.relay;
  g.add(box(x, 1.6, z, mat({ color: 0x1f8a46, roughness: 0.5 }), "relay-pcb"));
  const blk = mat({ color: 0x161616, roughness: 0.4 });
  for (let i = 0; i < 4; i++) {
    const r = box(15.5, 16.2, 18.6, blk, `relay-${i}`);
    r.position.set(-22 + i * 16.2, 9.2, z / 2 - 16);
    g.add(r);
    const term = box(10.2, 10, 14.5, mat({ color: 0x1f9d55, roughness: 0.42 }), `out-${i}`);
    term.position.set(-22 + i * 16.2, 6.2, z / 2 - 5);
    g.add(term);
  }
  const vin = box(10, 9, 14, mat({ color: 0x1f9d55, roughness: 0.42 }), "vin");
  vin.position.set(-x / 2 + 8, 5.6, -z / 2 + 10);
  g.add(vin);
  const xf = box(10, 10, 10, mat({ color: 0xe0b000, roughness: 0.4 }), "xfmr");
  xf.position.set(-x / 2 + 16, 6.6, -8);
  g.add(xf);
  for (let i = 0; i < 4; i++) {
    const b = cyl(2.1, 2.1, 2.2, mat({ color: 0x222 }), `sw${i}`, 12);
    b.position.set(-8 + i * 7.2, 2.4, -z / 2 + 16);
    g.add(b);
  }
  const usb = box(7.4, 3, 8, mat({ color: 0xcfd6dc, metalness: 0.45, roughness: 0.32 }), "r-usb");
  usb.position.set(-4, 2.2, -z / 2 - 0.4);
  g.add(usb);
  const wifi = box(14.5, 3.4, 24, mat({ color: 0x111, roughness: 0.4 }), "wifi");
  wifi.position.set(x / 2 - 16, 2.6, -6);
  g.add(wifi);
  return g;
}

export function createBarrelJack() {
  const g = new THREE.Group();
  const black = mat({ color: 0x141414, roughness: 0.42, metalness: 0.12 });
  const body = cyl(5.5, 5.5, 14, black, "jack", 18);
  body.rotation.z = Math.PI / 2;
  g.add(body);
  const lip = cyl(6.1, 6.1, 2, black, "lip", 18);
  lip.rotation.z = Math.PI / 2;
  lip.position.x = 6.4;
  g.add(lip);
  const hole = cyl(2.6, 2.6, 7, mat({ color: 0x050505, roughness: 0.9 }), "bore", 14);
  hole.rotation.z = Math.PI / 2;
  hole.position.x = 4;
  g.add(hole);
  return g;
}
