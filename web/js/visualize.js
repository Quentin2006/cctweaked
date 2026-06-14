import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const BLOCK_COLORS = {
  'minecraft:stone': 0x808080,
  'minecraft:dirt': 0x8b4513,
  'minecraft:grass_block': 0x4caf50,
  'minecraft:cobblestone': 0x606060,
  'minecraft:oak_planks': 0xc4a882,
  'minecraft:bedrock': 0x333333,
  'minecraft:water': 0x2196f3,
  'minecraft:coal_ore': 0x2c2c2c,
  'minecraft:iron_ore': 0xb8b8b8,
  'minecraft:gold_ore': 0xffd700,
  'minecraft:diamond_ore': 0x4fc3f7,
  'minecraft:redstone_ore': 0xe53935,
  'minecraft:netherrack': 0x8b0000,
  'minecraft:sand': 0xe8d4a0,
  'minecraft:gravel': 0x9e9e9e,
  'minecraft:oak_log': 0x6b4226,
  'minecraft:oak_leaves': 0x2e7d32,
  'minecraft:grass': 0x66bb6a,
};

const DEFAULT_BLOCK_COLOR = 0x9c27b0;

const container = document.getElementById('viz-container');
if (!container) throw new Error('viz-container not found');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c111a);

const width = container.clientWidth;
const height = container.clientHeight;

const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
camera.position.set(8, 8, 8);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(width, height);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 0, 0);
controls.enableZoom = true;
controls.zoomSpeed = 1.0;
controls.minDistance = 2;
controls.maxDistance = 80;
controls.maxPolarAngle = Math.PI / 2 - 0.05;
controls.update();

const ambientLight = new THREE.AmbientLight(0x404060);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(5, 10, 5);
scene.add(dirLight);

const gridHelper = new THREE.GridHelper(20, 20, 0x243244, 0x1a2636);
gridHelper.position.y = -0.5;
scene.add(gridHelper);

const blockGroup = new THREE.Group();
scene.add(blockGroup);

// --- Turtle Model ---
const turtleGroup = new THREE.Group();
scene.add(turtleGroup);

const TURTLE_BODY_COLOR = 0x44c767;
const TURTLE_HEAD_COLOR = 0x66e389;
const TURTLE_ACCENT_COLOR = 0x00e5ff;

const bodyGeo = new THREE.BoxGeometry(0.8, 0.5, 0.8);
const bodyMat = new THREE.MeshLambertMaterial({
  color: TURTLE_BODY_COLOR,
  emissive: TURTLE_BODY_COLOR,
  emissiveIntensity: 0.08,
});
const body = new THREE.Mesh(bodyGeo, bodyMat);
body.position.y = 0.25;
turtleGroup.add(body);

const bodyEdges = new THREE.EdgesGeometry(bodyGeo);
const bodyEdgeMat = new THREE.LineBasicMaterial({
  color: TURTLE_ACCENT_COLOR,
  transparent: true,
  opacity: 0.25,
});
const bodyWire = new THREE.LineSegments(bodyEdges, bodyEdgeMat);
bodyWire.position.copy(body.position);
turtleGroup.add(bodyWire);

const headGeo = new THREE.BoxGeometry(0.3, 0.3, 0.3);
const headMat = new THREE.MeshLambertMaterial({ color: TURTLE_HEAD_COLOR });
const head = new THREE.Mesh(headGeo, headMat);
head.position.set(0, 0.25, 0.55);
turtleGroup.add(head);

// Direction indicator — small cone on top showing facing
const coneGeo = new THREE.ConeGeometry(0.12, 0.25, 4);
const coneMat = new THREE.MeshLambertMaterial({
  color: TURTLE_ACCENT_COLOR,
  emissive: TURTLE_ACCENT_COLOR,
  emissiveIntensity: 0.4,
});
const cone = new THREE.Mesh(coneGeo, coneMat);
cone.position.set(0, 0.65, 0.35);
cone.rotation.x = Math.PI / 2;
turtleGroup.add(cone);

const ringGeo = new THREE.RingGeometry(0.3, 0.5, 24);
const ringMat = new THREE.MeshBasicMaterial({
  color: TURTLE_ACCENT_COLOR,
  transparent: true,
  opacity: 0.15,
  side: THREE.DoubleSide,
});
const ring = new THREE.Mesh(ringGeo, ringMat);
ring.rotation.x = -Math.PI / 2;
ring.position.y = 0.02;
turtleGroup.add(ring);

// Facing direction vectors
const FACING_VECTORS = {
  0: { x: 0, z: -1 },   // north
  1: { x: 1, z: 0 },    // east
  2: { x: 0, z: 1 },    // south
  3: { x: -1, z: 0 },   // west
};

function updateTurtle(pos) {
  turtleGroup.position.set(pos.x, pos.y, pos.z);
  // head faces +Z (south = facing 2).  Rotate Y for other directions.
  // facing: 0=north(-Z), 1=east(+X), 2=south(+Z), 3=west(-X)
  const angles = { 0: Math.PI, 1: -Math.PI / 2, 2: 0, 3: Math.PI / 2 };
  turtleGroup.rotation.y = angles[pos.facing] || 0;
}

async function fetchPosition() {
  try {
    const resp = await fetch('/position');
    if (!resp.ok) return;
    updateTurtle(await resp.json());
  } catch (_err) {}
}

function getBlockColor(name) {
  return BLOCK_COLORS[name] !== undefined ? BLOCK_COLORS[name] : DEFAULT_BLOCK_COLOR;
}

function disposeGroup(group) {
  while (group.children.length > 0) {
    const child = group.children[0];
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach((m) => m.dispose());
      } else {
        child.material.dispose();
      }
    }
    group.remove(child);
  }
}

function buildBlocks(data) {
  disposeGroup(blockGroup);

  const list = data && data.blocks ? data.blocks : [];
  for (const b of list) {
    const color = getBlockColor(b.name);
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshLambertMaterial({ color });
    const cube = new THREE.Mesh(geometry, material);
    cube.position.set(b.x, b.y, b.z);

    const edges = new THREE.EdgesGeometry(geometry);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x1a2636 });
    const wireframe = new THREE.LineSegments(edges, edgeMat);
    wireframe.position.copy(cube.position);

    blockGroup.add(cube);
    blockGroup.add(wireframe);
  }
}

async function fetchBlocks() {
  try {
    const resp = await fetch('/blocks');
    if (!resp.ok) return;
    const data = await resp.json();
    buildBlocks(data);
  } catch (_err) {
    // server not available — keep previous blocks
  }
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

animate();
fetchBlocks();
fetchPosition();
setInterval(fetchBlocks, 1000);
setInterval(fetchPosition, 500);

const resizeObserver = new ResizeObserver(function () {
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w === 0 || h === 0) return;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
});
resizeObserver.observe(container);
