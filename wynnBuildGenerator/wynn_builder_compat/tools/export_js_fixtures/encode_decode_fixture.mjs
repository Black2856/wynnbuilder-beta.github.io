import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const repoRoot = path.resolve(currentDir, "../../../..");

const utilsSource = fs.readFileSync(path.join(repoRoot, "js", "utils.js"), "utf8");
const cleanData = JSON.parse(fs.readFileSync(path.join(repoRoot, "clean.json"), "utf8")).items;
const encConsts = JSON.parse(
  fs.readFileSync(path.join(repoRoot, "data", "2.2.0.31", "encoding_consts.json"), "utf8"),
);

// WYNN_VERSION_LATEST = 30 (index of "2.2.0.31" in WYNN_VERSION_NAMES)
const WYNN_VERSION_LATEST = 30;
const VECTOR_FLAG = 0xc;

// DOM/browser stubs required by utils.js at module init time.
const stubs = `
const window = {
  location: { href: "", protocol: "https:", host: "localhost", pathname: "/", hash: "" },
  opera: undefined,
};
const navigator = { userAgent: "node", vendor: "" };
const screen = { width: 1920 };
const performance = { now: () => 0 };
const document = {
  addEventListener: () => {},
  removeEventListener: () => {},
  createElement: () => ({
    style: {},
    classList: { add: () => {}, contains: () => false, remove: () => {} },
    textContent: "",
    appendChild: () => {},
    addEventListener: () => {},
  }),
  getElementById: () => null,
  head: { appendChild: () => {} },
  documentElement: { scrollTop: 0 },
  body: { appendChild: () => {}, removeChild: () => {} },
};
const location = window.location;
const ENC = globalThis.__ENC;
`;

const fixtureHelper = `
const itemsByName = new Map(globalThis.__cleanData.map((e) => [e.displayName, e]));
const POWDERABLES = new Set([0, 1, 2, 3, 8]);
const WYNN_VERSION_LATEST = ${WYNN_VERSION_LATEST};
const VECTOR_FLAG = ${VECTOR_FLAG};

function encodeSimpleBuild(equipment8, weaponName, level) {
  const vec = new BitVector(0, 0);

  // Header
  vec.append(VECTOR_FLAG, 6);
  vec.append(WYNN_VERSION_LATEST, 10);

  // 8 armor/accessory + 1 weapon
  const allNames = [...equipment8, weaponName];
  for (let i = 0; i < allNames.length; i++) {
    const name = allNames[i];
    vec.append(ENC.EQUIPMENT_KIND.NORMAL, ENC.EQUIPMENT_KIND.BITLEN);
    if (name === null) {
      vec.append(0, ENC.ITEM_ID_BITLEN);
    } else {
      const item = itemsByName.get(name);
      if (!item) throw new Error("Unknown item: " + name);
      vec.append(item.id + 1, ENC.ITEM_ID_BITLEN);
    }
    if (POWDERABLES.has(i)) {
      vec.append(ENC.EQUIPMENT_POWDERS_FLAG.NO_POWDERS, ENC.EQUIPMENT_POWDERS_FLAG.BITLEN);
    }
  }

  // Tomes: NO_TOMES
  vec.append(ENC.TOMES_FLAG.NO_TOMES, ENC.TOMES_FLAG.BITLEN);

  // Skillpoints: AUTOMATIC
  vec.append(ENC.SP_FLAG.AUTOMATIC, ENC.SP_FLAG.BITLEN);

  // Level
  if (level === ENC.MAX_LEVEL) {
    vec.append(ENC.LEVEL_FLAG.MAX, ENC.LEVEL_FLAG.BITLEN);
  } else {
    vec.append(ENC.LEVEL_FLAG.OTHER, ENC.LEVEL_FLAG.BITLEN);
    vec.append(level, ENC.LEVEL_BITLEN);
  }

  // Aspects: NO_ASPECTS
  vec.append(ENC.ASPECTS_FLAG.NO_ASPECTS, ENC.ASPECTS_FLAG.BITLEN);

  return vec.toB64();
}

function fixtureCase(caseId, level, equipment8, weaponName) {
  const hash = encodeSimpleBuild(equipment8, weaponName, level);
  return {
    caseId,
    input: { level, equipment: equipment8, weapon: weaponName },
    hash,
  };
}

globalThis.__fixture = {
  source: "js/builder/build_encode_decode.js::encodeBuild (simplified)",
  cases: [
    fixtureCase(
      "level-121-max",
      121,
      [
        "Counterfeit Coronet",
        "Coal Fire",
        "Alstroemania",
        "Bleeding Soles",
        "Burning Brand",
        "Cannon Coin",
        "Excision of Trust",
        "Arbiter of Iridescence",
      ],
      "Amalgamation",
    ),
    fixtureCase(
      "level-50-partial-null",
      50,
      [
        "Counterfeit Coronet",
        null,
        null,
        "Bleeding Soles",
        null,
        null,
        null,
        null,
      ],
      "Amalgamation",
    ),
  ],
};
`;

const context = vm.createContext({ __cleanData: cleanData, __ENC: encConsts });
vm.runInContext([stubs, utilsSource, fixtureHelper].join("\n"), context, {
  filename: "encode_decode_fixture",
});

console.log(JSON.stringify(context.__fixture, null, 2));
