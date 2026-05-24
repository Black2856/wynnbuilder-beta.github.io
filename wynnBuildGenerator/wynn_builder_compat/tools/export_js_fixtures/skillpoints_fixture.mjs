import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const repoRoot = path.resolve(currentDir, "../../../..");
const skillpointsSource = fs.readFileSync(path.join(repoRoot, "js", "skillpoints.js"), "utf8");
const cleanData = JSON.parse(fs.readFileSync(path.join(repoRoot, "clean.json"), "utf8")).items;

const setup = `
const skp_order = ["str", "dex", "int", "def", "agi"];
const skp_reqs = ["strReq", "dexReq", "intReq", "defReq", "agiReq"];
const sets = new Map();
const performance = { now: () => 0 };
const console = { log: () => {} };

class FixtureItem {
  constructor(name, reqs, skillpoints, options = {}) {
    this.name = name;
    this.statMap = new Map([
      ["reqs", reqs],
      ["skillpoints", skillpoints],
      ["crafted", Boolean(options.crafted)],
      ["set", options.set || null],
    ]);
  }

  get(key) {
    return this.statMap.get(key);
  }
}

function item(name, reqs, skillpoints, options = {}) {
  return new FixtureItem(name, reqs, skillpoints, options);
}

const itemDataByName = new Map(globalThis.__cleanData.map((entry) => [entry.displayName, entry]));

function itemFromData(name) {
  const raw = itemDataByName.get(name);
  if (!raw) {
    throw new Error("Missing clean.json item fixture: " + name);
  }
  return item(
    raw.displayName,
    skp_reqs.map((key) => raw[key] || 0),
    skp_order.map((key) => raw[key] || 0),
    { set: raw.set || null },
  );
}

function serializeResult(result) {
  return {
    bestOrder: result[0].map((entry) => entry.name),
    bestSkillpoints: result[1],
    finalSkillpoints: result[2],
    bestTotal: result[3],
    bestActiveSetCounts: Object.fromEntries(result[4]),
    totalItemSkillpoints: result[5],
  };
}

function fixtureCase(caseId, equipment, weapon) {
  return {
    caseId,
    input: {
      equipment: equipment.map((entry) => ({
        name: entry.name,
        reqs: entry.get("reqs"),
        skillpoints: entry.get("skillpoints"),
        crafted: entry.get("crafted"),
        set: entry.get("set"),
      })),
      weapon: {
        name: weapon.name,
        reqs: weapon.get("reqs"),
        skillpoints: weapon.get("skillpoints"),
        crafted: weapon.get("crafted"),
        set: weapon.get("set"),
      },
    },
    result: serializeResult(calculate_skillpoints(equipment, weapon)),
  };
}

const baseEquipment = [
  item("earth-req", [15, 0, 0, 0, 0], [5, 0, 0, 0, 0]),
  item("dex-helper", [0, 0, 0, 0, 0], [0, 12, 0, 0, 0]),
  item("dex-req", [0, 20, 0, 0, 0], [0, 4, 0, 0, 0]),
  item("int-helper", [0, 0, 0, 0, 0], [0, 0, 9, 0, 0]),
  item("int-req", [0, 0, 18, 0, 0], [0, 0, 5, 0, 0]),
  item("def-helper", [0, 0, 0, 0, 0], [0, 0, 0, 7, 0]),
  item("def-req", [0, 0, 0, 16, 0], [0, 0, 0, 3, 0]),
  item("agi-helper", [0, 0, 0, 0, 0], [0, 0, 0, 0, 8]),
  item("agi-req", [0, 0, 0, 0, 14], [0, 0, 0, 0, 2]),
];
const baseWeapon = item("weapon", [22, 10, 10, 10, 10], [3, 0, 0, 0, 0]);

const craftedEquipment = [
  item("crafted-earth", [30, 0, 0, 0, 0], [40, 0, 0, 0, 0], { crafted: true }),
  item("earth-helper", [0, 0, 0, 0, 0], [12, 0, 0, 0, 0]),
  item("earth-req-2", [25, 0, 0, 0, 0], [6, 0, 0, 0, 0]),
  item("dex-helper-2", [0, 0, 0, 0, 0], [0, 8, 0, 0, 0]),
  item("dex-req-2", [0, 16, 0, 0, 0], [0, 5, 0, 0, 0]),
  item("int-zero", [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
  item("def-zero", [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
  item("agi-zero", [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
  item("neutral", [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
];
const craftedWeapon = item("crafted-case-weapon", [35, 10, 0, 0, 0], [2, 0, 0, 0, 0]);

const realEquipment = [
  itemFromData("Counterfeit Coronet"),
  itemFromData("Coal Fire"),
  itemFromData("Alstroemania"),
  itemFromData("Bleeding Soles"),
  itemFromData("Burning Brand"),
  itemFromData("Cannon Coin"),
  itemFromData("Excision of Trust"),
  itemFromData("Arbiter of Iridescence"),
  item("empty-tome-slot", [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
];
const realWeapon = itemFromData("Amalgamation");

globalThis.__fixture = {
  source: "js/skillpoints.js::calculate_skillpoints",
  cases: [
    fixtureCase("base-nine-equipment", baseEquipment, baseWeapon),
    fixtureCase("crafted-skillpoints-deferred", craftedEquipment, craftedWeapon),
    fixtureCase("real-clean-json-equipment", realEquipment, realWeapon),
  ],
};
`;

const context = vm.createContext({ __cleanData: cleanData });
vm.runInContext(`${setup}\n${skillpointsSource}`, context, {
  filename: "skillpoints_fixture",
});

console.log(JSON.stringify(context.__fixture, null, 2));
