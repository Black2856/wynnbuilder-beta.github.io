import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const repoRoot = path.resolve(currentDir, "../../../..");
const buildUtilsSource = fs.readFileSync(path.join(repoRoot, "js", "build_utils.js"), "utf8");
const craftSource = fs.readFileSync(path.join(repoRoot, "js", "craft.js"), "utf8");
const recipesData = JSON.parse(fs.readFileSync(path.join(repoRoot, "recipes_clean.json"), "utf8")).recipes;
const ingredientsData = JSON.parse(fs.readFileSync(path.join(repoRoot, "ingreds_clean.json"), "utf8"));

const setup = `
const powderStats = [];
const powderNames = new Map();
class EncodingBitVector {}
`;

const probe = `
function asMap(object) {
  const map = new Map();
  for (const [key, value] of Object.entries(object)) {
    map.set(key, value);
  }
  return map;
}

function ingredient(input) {
  return new Map([
    ["name", input.name || "Ingredient"],
    ["posMods", asMap(input.posMods || {})],
    ["itemIDs", asMap(input.itemIDs || {})],
    ["consumableIDs", asMap(input.consumableIDs || {})],
    ["ids", new Map([
      ["minRolls", asMap(input.minRolls || {})],
      ["maxRolls", asMap(input.maxRolls || {})],
    ])],
    ["isPowder", Boolean(input.isPowder)],
    ["pid", input.pid || 0],
  ]);
}

function serialize(value) {
  if (value instanceof Map) {
    const object = {};
    for (const [key, entry] of value.entries()) {
      object[key] = serialize(entry);
    }
    return object;
  }
  if (Array.isArray(value)) {
    return value.map(serialize);
  }
  return value;
}

const armorRecipeInput = {
  type: "CHESTPLATE",
  duration: [0, 0],
  durability: [100, 130],
  lvl: [103, 105],
  healthOrDamage: [300, 500],
  materials: [new Map([["amount", 2]]), new Map([["amount", 1]])],
};
const armorIngredientsInput = [
  {
    name: "Negative Booster",
    posMods: { touching: -150 },
    itemIDs: { strReq: -25 },
    minRolls: { rawSpellDamage: -25 },
    maxRolls: { rawSpellDamage: -10 },
  },
  {
    name: "Health",
    posMods: {},
    itemIDs: { dura: -30 },
    minRolls: { rawHealth: 100 },
    maxRolls: { rawHealth: 200 },
  },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
];

const weaponRecipeInput = {
  type: "WAND",
  duration: [0, 0],
  durability: [80, 90],
  lvl: [103, 105],
  healthOrDamage: [120, 240],
  materials: [new Map([["amount", 1]]), new Map([["amount", 3]])],
};
const weaponIngredientsInput = [
  {
    name: "Damage",
    posMods: { right: 25 },
    itemIDs: { intReq: 12 },
    minRolls: { rawSpellDamage: 20 },
    maxRolls: { rawSpellDamage: 40 },
  },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
  { name: "No Ingredient", posMods: {}, itemIDs: {}, minRolls: {}, maxRolls: {} },
];

function fixtureCase(caseId, recipeInput, materialTiers, ingredientsInput, attackSpeed, hash) {
  const recipe = new Map(Object.entries(recipeInput));
  const craft = new Craft(recipe, materialTiers, ingredientsInput.map(ingredient), attackSpeed, hash);
  return {
    caseId,
    input: {
      recipe: {
        ...recipeInput,
        materials: recipeInput.materials.map((entry) => ({ amount: entry.get("amount") })),
      },
      materialTiers,
      ingredients: ingredientsInput.map((entry) => ({
        posMods: entry.posMods || {},
        itemIDs: entry.itemIDs || {},
        consumableIDs: entry.consumableIDs || {},
        rolledIDs: Object.fromEntries(
          Object.keys({ ...(entry.minRolls || {}), ...(entry.maxRolls || {}) }).map((key) => [
            key,
            [(entry.minRolls || {})[key] || 0, (entry.maxRolls || {})[key] || 0],
          ]),
        ),
        isPowder: Boolean(entry.isPowder),
      })),
      attackSpeed,
      hash,
      rolledIDs,
    },
    statMap: serialize(craft.statMap),
  };
}

function plainExpandedIngredient(expanded) {
  const ids = expanded.get("ids");
  const minRolls = serialize(ids.get("minRolls"));
  const maxRolls = serialize(ids.get("maxRolls"));
  return {
    posMods: serialize(expanded.get("posMods")),
    itemIDs: serialize(expanded.get("itemIDs")),
    consumableIDs: serialize(expanded.get("consumableIDs")),
    rolledIDs: Object.fromEntries(
      Object.keys({ ...minRolls, ...maxRolls }).map((key) => [
        key,
        [minRolls[key] || 0, maxRolls[key] || 0],
      ]),
    ),
    isPowder: Boolean(expanded.get("isPowder")),
  };
}

function plainExpandedRecipe(expanded) {
  return {
    type: expanded.get("type"),
    duration: expanded.get("duration"),
    durability: expanded.get("durability"),
    lvl: expanded.get("lvl"),
    healthOrDamage: expanded.get("healthOrDamage"),
    materials: expanded.get("materials").map((entry) => ({ amount: entry.get("amount"), item: entry.get("item") })),
    name: expanded.get("name"),
    skill: expanded.get("skill"),
    id: expanded.get("id"),
  };
}

function fixtureCaseFromExpanded(caseId, recipeExpanded, materialTiers, ingredientsExpanded, attackSpeed, hash) {
  const craft = new Craft(recipeExpanded, materialTiers, ingredientsExpanded, attackSpeed, hash);
  return {
    caseId,
    input: {
      recipe: plainExpandedRecipe(recipeExpanded),
      materialTiers,
      ingredients: ingredientsExpanded.map(plainExpandedIngredient),
      attackSpeed,
      hash,
      rolledIDs,
    },
    statMap: serialize(craft.statMap),
  };
}

const recipesData = globalThis.__recipesData;
const ingredientsData = globalThis.__ingredientsData;
const recipeByName = new Map(recipesData.map((recipe) => [recipe.name, recipe]));
const ingredientByName = new Map(ingredientsData.map((ingredient) => [ingredient.displayName, ingredient]));
const noIngredient = {
  name: "No Ingredient",
  displayName: "No Ingredient",
  tier: 0,
  lvl: 0,
  skills: ["ARMOURING", "TAILORING", "WEAPONSMITHING", "WOODWORKING", "JEWELING", "COOKING", "ALCHEMISM", "SCRIBING"],
  ids: {},
  itemIDs: { dura: 0, strReq: 0, dexReq: 0, intReq: 0, defReq: 0, agiReq: 0 },
  consumableIDs: { dura: 0, charges: 0 },
  posMods: { left: 0, right: 0, above: 0, under: 0, touching: 0, notTouching: 0 },
  id: 4000,
};
ingredientByName.set("No Ingredient", noIngredient);

const armorIngredients = [
  "Voidtossed Memory",
  "Voidtossed Memory",
  "Voidtossed Memory",
  "Elephelk Trunk",
  "Negative Rafflesia",
  "Decaying Heart",
].map((name) => expandIngredient(ingredientByName.get(name)));
const weaponIngredients = [
  "Voidtossed Memory",
  "Voidtossed Memory",
  "Elephelk Trunk",
  "Negative Rafflesia",
  "Decaying Heart",
  "No Ingredient",
].map((name) => expandIngredient(ingredientByName.get(name)));
const accessoryIngredients = [
  "Voidtossed Memory",
  "Doom Stone",
  "Ancient Currency",
  "Negative Rafflesia",
  "Bottled Fairy",
  "No Ingredient",
].map((name) => expandIngredient(ingredientByName.get(name)));

const realEquipmentCases = [
  ["real-helmet-103-105-boosters", "Helmet-103-105", armorIngredients, "NORMAL", "real-helmet"],
  ["real-chestplate-103-105-boosters", "Chestplate-103-105", armorIngredients, "NORMAL", "real-chest"],
  ["real-leggings-103-105-boosters", "Leggings-103-105", armorIngredients, "NORMAL", "real-leggings"],
  ["real-boots-103-105-boosters", "Boots-103-105", armorIngredients, "NORMAL", "real-boots"],
  ["real-wand-103-105-boosters", "Wand-103-105", weaponIngredients, "FAST", "real-wand"],
  ["real-spear-103-105-boosters", "Spear-103-105", weaponIngredients, "SLOW", "real-spear"],
  ["real-bow-103-105-boosters", "Bow-103-105", weaponIngredients, "NORMAL", "real-bow"],
  ["real-dagger-103-105-boosters", "Dagger-103-105", weaponIngredients, "SUPER_FAST", "real-dagger"],
  ["real-relik-103-105-boosters", "Relik-103-105", weaponIngredients, "SUPER_SLOW", "real-relik"],
  ["real-ring-103-105-boosters", "Ring-103-105", accessoryIngredients, "NORMAL", "real-ring"],
  ["real-bracelet-103-105-boosters", "Bracelet-103-105", accessoryIngredients, "NORMAL", "real-bracelet"],
  ["real-necklace-103-105-boosters", "Necklace-103-105", accessoryIngredients, "NORMAL", "real-necklace"],
].map(([caseId, recipeName, ingredients, attackSpeed, hash]) =>
  fixtureCaseFromExpanded(caseId, expandRecipe(recipeByName.get(recipeName)), [3, 3], ingredients, attackSpeed, hash),
);

globalThis.__fixture = {
  source: "js/craft.js::Craft mock cases",
  cases: [
    fixtureCase("mock-chestplate", armorRecipeInput, [3, 1], armorIngredientsInput, "NORMAL", "mock"),
    fixtureCase("mock-wand-fast", weaponRecipeInput, [1, 3], weaponIngredientsInput, "FAST", "mock-weapon"),
    ...realEquipmentCases,
  ],
};
`;

const context = vm.createContext({ console, __recipesData: recipesData, __ingredientsData: ingredientsData });
vm.runInContext(`${setup}\n${buildUtilsSource}\n${craftSource}\n${probe}`, context, {
  filename: "craft_preview_fixture",
});

console.log(JSON.stringify(context.__fixture, null, 2));
