function materialMultiplier(materialAmounts, materialTiers) {
  const tierToMult = [0, 1, 1.25, 1.4];
  return (
    tierToMult[materialTiers[0]] * materialAmounts[0]
    + tierToMult[materialTiers[1]] * materialAmounts[1]
  ) / (materialAmounts[0] + materialAmounts[1]);
}

function effectivenessGrid(positionModifiers) {
  let eff = [[100, 100], [100, 100], [100, 100]];
  for (let n in positionModifiers) {
    let posMods = positionModifiers[n];
    let i = Math.floor(n / 2);
    let j = n % 2;
    for (const [key, value] of Object.entries(posMods)) {
      if (value == 0) {
        continue;
      } else {
        if (key === "above") {
          for (let k = i - 1; k > -1; k--) {
            eff[k][j] += value;
          }
        } else if (key === "under") {
          for (let k = i + 1; k < 3; k++) {
            eff[k][j] += value;
          }
        } else if (key === "left") {
          if (j == 1) {
            eff[i][j - 1] += value;
          }
        } else if (key === "right") {
          if (j == 0) {
            eff[i][j + 1] += value;
          }
        } else if (key === "touching") {
          for (let k in eff) {
            for (let l in eff[k]) {
              if (
                (Math.abs(k - i) == 1 && Math.abs(l - j) == 0)
                || (Math.abs(k - i) == 0 && Math.abs(l - j) == 1)
              ) {
                eff[k][l] += value;
              }
            }
          }
        } else if (key === "notTouching") {
          for (let k in eff) {
            for (let l in eff[k]) {
              if (
                (Math.abs(k - i) > 1)
                || (Math.abs(k - i) == 1 && Math.abs(l - j) == 1)
              ) {
                eff[k][l] += value;
              }
            }
          }
        } else {
          throw new Error(`unknown position modifier: ${key}`);
        }
      }
    }
  }
  return eff;
}

function applyItemIds(statValues, durability, itemIdsByIngredient, effectivenessFlat, itemIsPowder = [], isConsumable = false) {
  const values = { ...statValues };
  let durabilityValues = durability.slice();
  for (const n in itemIdsByIngredient) {
    const itemIds = itemIdsByIngredient[n];
    const effMult = (effectivenessFlat[n] / 100).toFixed(2);
    const isPowder = itemIsPowder[n] || false;
    for (const [key, value] of Object.entries(itemIds)) {
      if (key !== "dura" && !isConsumable) {
        if (!isPowder) {
          values[key] = Math.round((values[key] || 0) + value * effMult);
        } else {
          values[key] = Math.round((values[key] || 0) + value);
        }
      } else {
        durabilityValues = durabilityValues.map((x) => x + value);
      }
    }
  }
  return { values, durability: durabilityValues };
}

function applyRolledIds(minRolls, maxRolls, rolledIdsByIngredient, effectivenessFlat) {
  const mins = { ...minRolls };
  const maxes = { ...maxRolls };
  for (const n in rolledIdsByIngredient) {
    const effMult = (effectivenessFlat[n] / 100).toFixed(2);
    for (const [key, roll] of Object.entries(rolledIdsByIngredient[n])) {
      const [minValue, maxValue] = roll;
      if (maxValue && maxValue != 0) {
        const rolls = [minValue, maxValue].map((x) => Math.floor(x * effMult)).sort((a, b) => a - b);
        mins[key] = mins[key] ? mins[key] + rolls[0] : rolls[0];
        maxes[key] = maxes[key] ? maxes[key] + rolls[1] : rolls[1];
      }
    }
  }
  return { minRolls: mins, maxRolls: maxes };
}

const cases = [
  {
    caseId: "empty",
    positionModifiers: [{}, {}, {}, {}, {}, {}],
  },
  {
    caseId: "directional",
    positionModifiers: [
      { right: 20, under: 10 },
      { left: -15 },
      {},
      {},
      {},
      {},
    ],
  },
  {
    caseId: "touching",
    positionModifiers: [
      { touching: 25 },
      {},
      {},
      {},
      {},
      {},
    ],
  },
  {
    caseId: "not-touching",
    positionModifiers: [
      { notTouching: 40 },
      {},
      {},
      {},
      {},
      {},
    ],
  },
  {
    caseId: "negative-booster",
    positionModifiers: [
      { touching: -150 },
      {},
      {},
      {},
      {},
      {},
    ],
  },
  {
    caseId: "mixed",
    positionModifiers: [
      { right: 50, under: -25 },
      { left: 10, notTouching: 30 },
      { above: 15, touching: -20 },
      {},
      { above: 5 },
      { left: -35, touching: 10 },
    ],
  },
];

const fixture = {
  source: "js/craft.js effectiveness/material multiplier blocks",
  materialMultipliers: [
    { amounts: [1, 1], tiers: [1, 1], output: materialMultiplier([1, 1], [1, 1]) },
    { amounts: [2, 1], tiers: [3, 1], output: materialMultiplier([2, 1], [3, 1]) },
    { amounts: [4, 6], tiers: [2, 3], output: materialMultiplier([4, 6], [2, 3]) },
  ],
  effectiveness: cases.map((testCase) => ({
    ...testCase,
    output: effectivenessGrid(testCase.positionModifiers),
    flat: effectivenessGrid(testCase.positionModifiers).flat(),
  })),
  itemIdApplication: [
    {
      caseId: "negative-booster-requirement-flip",
      statValues: {},
      durability: [100, 100],
      effectivenessFlat: [-50, 100, 100, 100, 100, 100],
      itemIdsByIngredient: [
        { strReq: -25 },
        {},
        {},
        {},
        {},
        {},
      ],
      itemIsPowder: [false, false, false, false, false, false],
      isConsumable: false,
    },
    {
      caseId: "durability-not-affected",
      statValues: { dexReq: 10 },
      durability: [80, 120],
      effectivenessFlat: [250, 100, 100, 100, 100, 100],
      itemIdsByIngredient: [
        { dexReq: 4, dura: -30 },
        {},
        {},
        {},
        {},
        {},
      ],
      itemIsPowder: [false, false, false, false, false, false],
      isConsumable: false,
    },
    {
      caseId: "powder-ignores-effectiveness",
      statValues: {},
      durability: [100, 100],
      effectivenessFlat: [250, 100, 100, 100, 100, 100],
      itemIdsByIngredient: [
        { intReq: 4 },
        {},
        {},
        {},
        {},
        {},
      ],
      itemIsPowder: [true, false, false, false, false, false],
      isConsumable: false,
    },
  ].map((testCase) => ({
    ...testCase,
    output: applyItemIds(
      testCase.statValues,
      testCase.durability,
      testCase.itemIdsByIngredient,
      testCase.effectivenessFlat,
      testCase.itemIsPowder,
      testCase.isConsumable,
    ),
  })),
  rolledIdApplication: [
    {
      caseId: "negative-effectiveness-roll-sort",
      minRolls: {},
      maxRolls: {},
      effectivenessFlat: [-150, 100, 100, 100, 100, 100],
      rolledIdsByIngredient: [
        { rawSpellDamage: [-25, -10] },
        {},
        {},
        {},
        {},
        {},
      ],
    },
    {
      caseId: "positive-effectiveness-accumulates",
      minRolls: { rawHealth: 5 },
      maxRolls: { rawHealth: 9 },
      effectivenessFlat: [125, 50, 100, 100, 100, 100],
      rolledIdsByIngredient: [
        { rawHealth: [10, 20] },
        { rawHealth: [-3, 7] },
        {},
        {},
        {},
        {},
      ],
    },
  ].map((testCase) => ({
    ...testCase,
    output: applyRolledIds(
      testCase.minRolls,
      testCase.maxRolls,
      testCase.rolledIdsByIngredient,
      testCase.effectivenessFlat,
    ),
  })),
};

console.log(JSON.stringify(fixture, null, 2));
