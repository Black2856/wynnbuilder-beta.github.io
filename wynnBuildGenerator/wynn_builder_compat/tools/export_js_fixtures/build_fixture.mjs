import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const repoRoot = path.resolve(currentDir, "../../../..");
const buildUtilsSource = fs.readFileSync(path.join(repoRoot, "js", "build_utils.js"), "utf8");
const skillpointsSource = fs.readFileSync(path.join(repoRoot, "js", "skillpoints.js"), "utf8");
const cleanJson = JSON.parse(fs.readFileSync(path.join(repoRoot, "clean.json"), "utf8"));
const cleanData = cleanJson.items;
const setsData = cleanJson.sets;

// Stubs for globals required by build_utils.js and skillpoints.js.
// build_utils.js reads window.location at the top level and uses navigator.userAgent.
// skillpoints.js uses performance.now() and the global `sets` Map, and emits console.log
// timing/stat lines that would corrupt JSON output — silence them here.
const stubs = `
const window = { location: { href: "", protocol: "https:", host: "localhost", pathname: "/" } };
const navigator = { userAgent: "" };
const performance = { now: () => 0 };
const sets = new Map(Object.entries(globalThis.__setsData));
const console = { log: () => {} };
`;

// initBuildStats logic inlined from js/builder/build.js::Build.initBuildStats.
// Kept in sync with that source; does not depend on DOM.
const buildStatHelper = `
const BUILD_STATIC_IDS = [
  "hp", "eDef", "tDef", "wDef", "fDef", "aDef",
  "str", "dex", "int", "def", "agi",
  "damMobs", "defMobs",
];
const BUILD_MUST_IDS = [
  "eMdPct","eMdRaw","eSdPct","eSdRaw","eDamPct","eDamRaw","eDamAddMin","eDamAddMax",
  "tMdPct","tMdRaw","tSdPct","tSdRaw","tDamPct","tDamRaw","tDamAddMin","tDamAddMax",
  "wMdPct","wMdRaw","wSdPct","wSdRaw","wDamPct","wDamRaw","wDamAddMin","wDamAddMax",
  "fMdPct","fMdRaw","fSdPct","fSdRaw","fDamPct","fDamRaw","fDamAddMin","fDamAddMax",
  "aMdPct","aMdRaw","aSdPct","aSdRaw","aDamPct","aDamRaw","aDamAddMin","aDamAddMax",
  "nMdPct","nMdRaw","nSdPct","nSdRaw","nDamPct","nDamRaw","nDamAddMin","nDamAddMax",
  "mdPct","mdRaw","sdPct","sdRaw","damPct","damRaw","damAddMin","damAddMax",
  "rMdPct","rMdRaw","rSdPct","rSdRaw","rDamPct","rDamRaw","rDamAddMin","rDamAddMax",
  "healPct","critDamPct",
];

// Ported directly from Build.initBuildStats.
// allExpandedStatMaps: array of Maps from expandItem() — equipment + weapon (no tomes).
// activeSetCounts: Map<string, number> from calculate_skillpoints result.
function computeInitBuildStats(level, allExpandedStatMaps, activeSetCounts) {
  const statMap = new Map();
  for (const id of BUILD_STATIC_IDS) statMap.set(id, 0);
  for (const id of BUILD_MUST_IDS) statMap.set(id, 0);
  statMap.set("hp", levelToHPBase(level));
  statMap.set("agiDef", 90);

  const major_ids = new Set();
  for (const item_stats of allExpandedStatMaps) {
    for (const [id, value] of item_stats.get("maxRolls")) {
      if (BUILD_STATIC_IDS.includes(id)) continue;
      statMap.set(id, (statMap.get(id) || 0) + value);
    }
    for (const staticID of BUILD_STATIC_IDS) {
      if (item_stats.get(staticID)) {
        statMap.set(staticID, statMap.get(staticID) + item_stats.get(staticID));
      }
    }
    const itemMajorIds = item_stats.get("majorIds");
    if (itemMajorIds) {
      for (const mid of itemMajorIds) major_ids.add(mid);
    }
  }

  statMap.set("damMult", new Map([["tome", statMap.get("damMobs")]]));
  statMap.set("defMult", new Map([["tome", statMap.get("defMobs")]]));
  statMap.set("activeMajorIDs", major_ids);
  for (const [setName, count] of activeSetCounts) {
    const setDef = sets.get(setName);
    if (!setDef || !setDef.bonuses[count - 1]) continue;
    const bonus = setDef.bonuses[count - 1];
    for (const id in bonus) {
      if (skp_order.includes(id)) continue;
      statMap.set(id, (statMap.get(id) || 0) + bonus[id]);
    }
  }
  statMap.set("poisonPct", 0);
  statMap.set("healMult", new Map([["item", statMap.get("healPct")]]));
  return statMap;
}
`;

// Helper code to prepare clean.json items and produce fixture cases.
const fixtureHelper = `
const itemDataByName = new Map(globalThis.__cleanData.map((e) => [e.displayName, e]));

// Mirror load_item.js: assign item.set from sets data (items lack set field in JSON).
for (const [setName, setDef] of sets) {
  for (const itemName of setDef.items) {
    const item = itemDataByName.get(itemName);
    if (item) item.set = setName;
  }
}


// Replicates clean_item() + expandItem() for a named item from clean.json.
function prepareItem(name) {
  const raw = itemDataByName.get(name);
  if (!raw) throw new Error("Missing item: " + name);
  const item = Object.assign({}, raw);
  if (!item.displayName) item.displayName = item.name;
  item.skillpoints = [item.str || 0, item.dex || 0, item.int || 0, item.def || 0, item.agi || 0];
  item.reqs = [item.strReq || 0, item.dexReq || 0, item.intReq || 0, item.defReq || 0, item.agiReq || 0];
  if (!item.majorIds) item.majorIds = [];
  for (const key of item_fields) {
    if (item[key] === undefined) {
      const STRING_ITEM_FIELDS = [
        "name","displayName","lore","color","tier","set","type","material",
        "drop","quest","restrict","category","atkSpd",
      ];
      if (STRING_ITEM_FIELDS.includes(key)) {
        item[key] = "";
      } else if (key === "majorIds") {
        item[key] = [];
      } else {
        item[key] = 0;
      }
    }
  }
  return expandItem(item);
}

// js/skillpoints.js hardcodes remains_in_order as [0..8] (9 slots).
// The 9th slot represents an empty tome/equipment slot — all zeros, no stats.
const EMPTY_SLOT = (() => {
  const raw = {};
  for (const key of item_fields) raw[key] = 0;
  raw.name = "empty-slot";
  raw.displayName = "empty-slot";
  raw.tier = "";
  raw.type = "";
  raw.set = null;
  raw.majorIds = [];
  raw.skillpoints = [0, 0, 0, 0, 0];
  raw.reqs = [0, 0, 0, 0, 0];
  return expandItem(raw);
})();

// Stat IDs exported to the fixture. Must be stable numeric scalars.
const STAT_EXPORT_IDS = [
  "hp","eDef","tDef","wDef","fDef","aDef",
  "str","dex","int","def","agi",
  "sdPct","sdRaw","mdPct","mdRaw",
  "hpBonus","hprRaw","hprPct","mr",
  "spPct1","spRaw1","spPct2","spRaw2","spPct3","spRaw3","spPct4","spRaw4",
  "atkTier","poison","ls","ms","spd","xpb","lb","ref","eSteal","spRegen","sprintReg","sprint",
  "eDamPct","eDamRaw","tDamPct","tDamRaw","wDamPct","wDamRaw","fDamPct","fDamRaw","aDamPct","aDamRaw",
  "eDefPct","tDefPct","wDefPct","fDefPct","aDefPct",
  "eSdPct","tSdPct","wSdPct","fSdPct","aSdPct","eSdRaw","tSdRaw","wSdRaw","fSdRaw","aSdRaw",
  "eMdPct","tMdPct","wMdPct","fMdPct","aMdPct","eMdRaw","tMdRaw","wMdRaw","fMdRaw","aMdRaw",
  "nMdPct","nMdRaw","nSdPct","nSdRaw","nDamPct","nDamRaw",
  "damPct","damRaw","rSdPct","rSdRaw","rMdPct","rMdRaw",
  "healPct","critDamPct","damMobs","defMobs",
];

function fixtureCase(caseId, level, equipmentNames, weaponName) {
  const equipment = equipmentNames.map(prepareItem);
  const weapon = prepareItem(weaponName);

  // skillpoints.js hardcodes [0..8] so we must pass exactly 9 equipment items.
  // The 9th is an empty slot; it contributes no stats to computeInitBuildStats.
  const equipmentForSkp = [...equipment, EMPTY_SLOT];
  const skpResult = calculate_skillpoints(equipmentForSkp, weapon);

  // computeInitBuildStats receives only real items (no empty slot) + weapon.
  const allStats = [...equipment, weapon];
  const statMap = computeInitBuildStats(level, allStats, skpResult[4]);

  const statResult = {};
  for (const id of STAT_EXPORT_IDS) {
    statResult[id] = statMap.has(id) ? statMap.get(id) : 0;
  }
  // atkSpd is a string from nonRolledIDs, exported separately.
  statResult["atkSpd"] = weapon.get("atkSpd") || "";

  return {
    caseId,
    input: { level, equipment: equipmentNames, weapon: weaponName },
    result: {
      statMap: statResult,
    },
  };
}

globalThis.__fixture = {
  source: "js/builder/build.js::Build.initBuildStats",
  cases: [
    fixtureCase(
      "real-no-powder-no-tome",
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
    // Two Boundless set equipment items (Nonexistence=helmet, Aleph Null=leggings),
    // weapon is non-Boundless. Triggers 2-piece bonus: {eSteal:10, ms:15, ls:250, spd:25}.
    fixtureCase(
      "boundless-2piece",
      105,
      [
        "Nonexistence",
        "Coal Fire",
        "Aleph Null",
        "Bleeding Soles",
        "Burning Brand",
        "Cannon Coin",
        "Excision of Trust",
        "Arbiter of Iridescence",
      ],
      "Amalgamation",
    ),
  ],
};
`;

const context = vm.createContext({ __cleanData: cleanData, __setsData: setsData });
vm.runInContext(
  [stubs, buildUtilsSource, skillpointsSource, buildStatHelper, fixtureHelper].join("\n"),
  context,
  { filename: "build_fixture" },
);

console.log(JSON.stringify(context.__fixture, null, 2));
