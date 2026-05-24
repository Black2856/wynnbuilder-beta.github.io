import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const repoRoot = path.resolve(currentDir, "../../../..");
const sourcePath = path.join(repoRoot, "js", "build_utils.js");
const source = fs.readFileSync(sourcePath, "utf8");

const probe = `
globalThis.__fixture = {
  source: "js/build_utils.js",
  levelToSkillPoints: [0, 1, 2, 100, 101, 121].map((level) => ({
    input: level,
    output: levelToSkillPoints(level),
  })),
  levelToHPBase: [1, 106, 121, 122].map((level) => ({
    input: level,
    output: levelToHPBase(level),
  })),
  skillPointsToPercentage: [-1, 0, 1, 50, 100, 150, 151].map((skp) => ({
    input: skp,
    output: skillPointsToPercentage(skp),
  })),
  constants: {
    skpOrder: skp_order,
    skpElements: skp_elements,
    attackSpeeds: attackSpeeds,
    baseDamageMultiplier: baseDamageMultiplier,
    skillpointFinalMult: skillpoint_final_mult,
    skillpointDamageMult: skillpoint_damage_mult,
  },
};
`;

const context = vm.createContext({ console });
vm.runInContext(`${source}\n${probe}`, context, {
  filename: sourcePath,
});

console.log(JSON.stringify(context.__fixture, null, 2));

