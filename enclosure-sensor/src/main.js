import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { createEnclosureAirHubModel, reviewViews } from "./createHub.js";

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14181e);
scene.fog = new THREE.Fog(0x14181e, 420, 900);

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.06).texture;

const camera = new THREE.PerspectiveCamera(32, window.innerWidth / window.innerHeight, 0.1, 2000);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.minDistance = 120;
controls.maxDistance = 620;

scene.add(new THREE.HemisphereLight(0xe8eef5, 0x2a3038, 1.15));
const key = new THREE.DirectionalLight(0xfff6ea, 2.4);
key.position.set(-120, 220, 180);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -160;
key.shadow.camera.right = 160;
key.shadow.camera.top = 140;
key.shadow.camera.bottom = -140;
scene.add(key);
scene.add(new THREE.DirectionalLight(0x9ecbff, 0.7).translateX(140).translateY(80).translateZ(-40));

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(240, 48),
  new THREE.MeshStandardMaterial({ color: 0x1b2027, roughness: 0.9 }),
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -4;
ground.receiveShadow = true;
scene.add(ground);

const hub = createEnclosureAirHubModel();
scene.add(hub);

const explode = document.querySelector("#explode");
explode.addEventListener("input", () => hub.userData.setExplode(Number(explode.value)));

function applyView(name) {
  const p = reviewViews[name];
  camera.position.fromArray(p.position);
  controls.target.fromArray(p.target);
  controls.update();
  document.querySelectorAll("[data-view]").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
}
document.querySelectorAll("[data-view]").forEach((b) =>
  b.addEventListener("click", () => {
    applyView(b.dataset.view);
    if (b.dataset.view === "split") {
      explode.value = "0.72";
      hub.userData.setExplode(0.72);
    }
  }),
);
applyView("hero");
const spin = document.querySelector("#spin");
const picked = document.querySelector("#picked");

const ray = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const named = Object.values(hub.userData.sculptRuntime.nodes);
canvas.addEventListener("pointerdown", (ev) => {
  const r = canvas.getBoundingClientRect();
  mouse.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hits = ray.intersectObjects(named, true);
  if (!hits.length) return;
  let obj = hits[0].object;
  while (obj && !named.includes(obj)) obj = obj.parent;
  const title = obj?.children?.[0]?.userData?.title || obj?.name;
  picked.textContent = title || obj?.name || "";
});

function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);

const clock = new THREE.Clock();
function frame() {
  controls.update();
  hub.userData.tick(clock.getElapsedTime(), spin.checked);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
frame();
