/** Millimetres. Numbers from seller drawings / official datasheets. */
export const DIM = {
  c3: { x: 18.0, z: 22.52, t: 1.6, h: 5.2 }, // SuperMini / PRO MINI, USB on +Z
  expander: { x: 52, z: 40, t: 1.6, h: 11 }, // PH2.0 扩展板，图纸未标长宽，按端子推
  pms: { x: 50, z: 38, y: 21, holeX: 45, holeZ: 33 },
  sht: { x: 13.2, z: 10.4, t: 1.2, hole: 2.2 },
  relay: { x: 75, z: 74, y: 20 },
  jack: { pitch: 18, bore: 11.2 },
  shell: {
    x: 178,
    z: 124,
    y: 38,
    wall: 2.2,
    floor: 2.6,
    lid: 2.4,
    radius: 11,
    lip: 1.4,
  },
};

export const POSE = {
  // centers on the base top plane (y=0 is inner floor)
  relay: { x: 42, z: -2 },
  pms: { x: -48, z: 22 },
  expander: { x: -48, z: -32 },
  c3: { x: -48, z: -32 }, // sits on expander
  sht: { x: -72, z: -4 },
  jacks: [-27, -9, 9, 27],
  jackZ: 58.5,
  dcIn: { x: 8, z: -58.5 },
};
