export const CONTROL_STEP_TYPES = ["if", "loop", "sequence", "try"]
export const MAX_CONTROL_NESTING = 3

export function isControlStep(step) {
  return Boolean(step && CONTROL_STEP_TYPES.includes(step.type))
}

export function isCustomStep(step) {
  return Boolean(step && step.kind === "custom")
}

export function isExpandableStep(step) {
  return isControlStep(step) || isCustomStep(step)
}

export function createDefaultCondition() {
  return {
    field: "",
    operator: "equals",
    value: ""
  }
}

export function ensureIfConfig(step) {
  if (!step) {
    return
  }
  if (!step.config || typeof step.config !== "object") {
    step.config = {}
  }

  if (!Array.isArray(step.config.then_steps)) {
    step.config.then_steps = []
  }

  if (!Array.isArray(step.config.conditions_input)) {
    if (Array.isArray(step.config.conditions) && step.config.conditions.length > 0) {
      step.config.conditions_input = step.config.conditions.map(normalizeCondition)
    } else if (step.config.left || step.config.operator || step.config.right) {
      step.config.conditions_input = [
        normalizeCondition({
          field: step.config.left || "",
          operator: step.config.operator || "equals",
          value: step.config.right || ""
        })
      ]
    } else {
      step.config.conditions_input = [createDefaultCondition()]
    }
  }

  if (!Array.isArray(step.config.elseif_branches)) {
    if (Array.isArray(step.config.else_ifs)) {
      step.config.elseif_branches = step.config.else_ifs.map((branch) => ({
        conditions_input: Array.isArray(branch.conditions)
          ? branch.conditions.map(normalizeCondition)
          : [
              normalizeCondition({
                field: branch.left || "",
                operator: branch.operator || "equals",
                value: branch.right || ""
              })
            ],
        steps: Array.isArray(branch.steps) ? branch.steps : []
      }))
    } else {
      step.config.elseif_branches = []
    }
  }

  step.config.elseif_branches.forEach((branch) => {
    if (!Array.isArray(branch.conditions_input) || branch.conditions_input.length === 0) {
      branch.conditions_input = [createDefaultCondition()]
    } else {
      branch.conditions_input = branch.conditions_input.map(normalizeCondition)
    }
    if (!Array.isArray(branch.steps)) {
      branch.steps = []
    }
  })
}

export function ensureLoopConfig(step) {
  if (!step) {
    return
  }
  if (!step.config || typeof step.config !== "object") {
    step.config = {}
  }
  if (!Array.isArray(step.config.steps)) {
    step.config.steps = []
  }
}

export function ensureSequenceConfig(step) {
  ensureLoopConfig(step)
}

export function ensureTryConfig(step) {
  if (!step) {
    return
  }
  if (!step.config || typeof step.config !== "object") {
    step.config = {}
  }
  if (!Array.isArray(step.config.try_steps)) {
    step.config.try_steps = []
  }
  if (!Array.isArray(step.config.catch_steps)) {
    step.config.catch_steps = []
  }
  if (!Array.isArray(step.config.finally_steps)) {
    step.config.finally_steps = []
  }
}

export function ensureStepContainers(step) {
  if (!step) {
    return
  }

  if (!step.config || typeof step.config !== "object") {
    step.config = {}
  }

  if (step.type === "if") {
    ensureIfConfig(step)
  } else if (step.type === "loop") {
    ensureLoopConfig(step)
  } else if (step.type === "sequence") {
    ensureSequenceConfig(step)
  } else if (step.type === "try") {
    ensureTryConfig(step)
  } else if (isCustomStep(step) && !Array.isArray(step.steps)) {
    step.steps = []
  }
}

export function getStepBranches(step) {
  ensureStepContainers(step)

  if (!step) {
    return []
  }

  if (step.type === "loop") {
    return [
      {
        key: "steps",
        source: "config",
        label: "循环步骤",
        steps: step.config.steps
      }
    ]
  }

  if (step.type === "sequence") {
    return [
      {
        key: "steps",
        source: "config",
        label: "顺序步骤",
        steps: step.config.steps
      }
    ]
  }

  if (step.type === "try") {
    return [
      {
        key: "try_steps",
        source: "config",
        label: "Try 分支",
        steps: step.config.try_steps
      },
      {
        key: "catch_steps",
        source: "config",
        label: "Catch 分支",
        steps: step.config.catch_steps
      },
      {
        key: "finally_steps",
        source: "config",
        label: "Finally 分支",
        steps: step.config.finally_steps
      }
    ]
  }

  if (step.type === "if") {
    const branches = [
      {
        key: "then_steps",
        source: "config",
        branchType: "then",
        label: "真分支（if）",
        steps: step.config.then_steps,
        conditions: step.config.conditions_input,
        conditionEditable: true
      }
    ]

    ;(step.config.elseif_branches || []).forEach((branch, branchIndex) => {
      branches.push({
        key: "steps",
        source: "elseif",
        branchType: "elseif",
        branchIndex,
        label: `Else If 分支 ${branchIndex + 1}`,
        steps: branch.steps,
        conditions: branch.conditions_input,
        conditionEditable: true,
        removable: true
      })
    })

    branches.push({
      key: "else_steps",
      source: "config",
      branchType: "else",
      label: "假分支（else）",
      steps: Array.isArray(step.config.else_steps) ? step.config.else_steps : [],
      enabled: Array.isArray(step.config.else_steps),
      optional: true
    })

    return branches
  }

  if (isCustomStep(step)) {
    return [
      {
        key: "steps",
        source: "step",
        label: "自定义组件子步骤",
        steps: step.steps
      }
    ]
  }

  return []
}

export function serializeStepPath(path) {
  if (!Array.isArray(path) || path.length === 0) {
    return ""
  }
  return path
    .map((segment) => `${segment.source}:${segment.key}:${segment.branchIndex ?? "x"}:${segment.index}`)
    .join("|")
}

export function resolveCollectionByPath(rootSteps, parentPath, location) {
  if (!location) {
    return Array.isArray(rootSteps) ? rootSteps : null
  }

  if (location.source === "root") {
    return Array.isArray(rootSteps) ? rootSteps : null
  }

  const parentStep = resolveStepByPath(rootSteps, parentPath)
  if (!parentStep) {
    return null
  }

  ensureStepContainers(parentStep)
  return resolveCollectionFromStep(parentStep, location)
}

export function resolveStepByPath(rootSteps, path) {
  if (!Array.isArray(rootSteps) || !Array.isArray(path) || path.length === 0) {
    return null
  }

  let collection = rootSteps
  let step = null

  for (let i = 0; i < path.length; i += 1) {
    const segment = path[i]
    if (!Array.isArray(collection) || segment.index >= collection.length) {
      return null
    }
    step = collection[segment.index]
    if (!step) {
      return null
    }
    ensureStepContainers(step)
    if (i < path.length - 1) {
      collection = resolveCollectionFromStep(step, path[i + 1])
    }
  }

  return step
}

export function resolveParentInfoByPath(rootSteps, path) {
  if (!Array.isArray(path) || path.length === 0) {
    return null
  }

  const parentPath = path.slice(0, -1)
  const currentSegment = path[path.length - 1]
  const collection = currentSegment.source === "root"
    ? rootSteps
    : resolveCollectionByPath(rootSteps, parentPath, currentSegment)

  return {
    parentPath,
    currentSegment,
    collection
  }
}

export function collectStepChain(rootSteps, path) {
  if (!Array.isArray(rootSteps) || !Array.isArray(path) || path.length === 0) {
    return []
  }

  let collection = rootSteps
  const chain = []

  for (let i = 0; i < path.length; i += 1) {
    const segment = path[i]
    if (!Array.isArray(collection) || segment.index >= collection.length) {
      break
    }
    const step = collection[segment.index]
    if (!step) {
      break
    }
    ensureStepContainers(step)
    chain.push(step)
    if (i < path.length - 1) {
      collection = resolveCollectionFromStep(step, path[i + 1])
    }
  }

  return chain
}

export function getControlDepthForPath(rootSteps, path) {
  return collectStepChain(rootSteps, path).filter(isControlStep).length
}

export function getControlMaxDepth(step, baseDepth = 0) {
  if (!step) {
    return baseDepth
  }

  ensureStepContainers(step)
  const currentDepth = baseDepth + (isControlStep(step) ? 1 : 0)
  let maxDepth = currentDepth

  getStepBranches(step).forEach((branch) => {
    ;(branch.steps || []).forEach((childStep) => {
      maxDepth = Math.max(maxDepth, getControlMaxDepth(childStep, currentDepth))
    })
  })

  return maxDepth
}

export function normalizeCondition(condition) {
  const left = condition?.left ?? condition?.field ?? ""
  const right = condition?.right ?? condition?.value ?? ""

  return {
    field: String(left),
    operator: normalizeConditionOperator(condition?.operator),
    value: String(right)
  }
}

export function normalizeIfConfigForSave(step) {
  if (!step || step.type !== "if" || !step.config) {
    return
  }

  ensureIfConfig(step)

  step.config.conditions = (step.config.conditions_input || []).map((condition) => ({
    left: condition.field || "",
    operator: mapConditionOperatorToRunner(condition.operator),
    right: condition.value || ""
  }))

  step.config.else_ifs = (step.config.elseif_branches || []).map((branch) => ({
    conditions: (branch.conditions_input || []).map((condition) => ({
      left: condition.field || "",
      operator: mapConditionOperatorToRunner(condition.operator),
      right: condition.value || ""
    })),
    steps: Array.isArray(branch.steps) ? branch.steps : []
  }))
}

function resolveCollectionFromStep(step, location) {
  if (!step || !location) {
    return null
  }

  if (location.source === "config") {
    return step.config?.[location.key] || null
  }

  if (location.source === "step") {
    return step[location.key] || null
  }

  if (location.source === "elseif") {
    return step.config?.elseif_branches?.[location.branchIndex]?.[location.key] || null
  }

  return null
}

function normalizeConditionOperator(operator) {
  const operatorMap = {
    equals: "equals",
    "==": "equals",
    "!=": "not_equals",
    not_equals: "not_equals",
    contains: "contains",
    not_contains: "not_contains",
    greater_than: "greater_than",
    ">": "greater_than",
    greater_or_equal: "greater_or_equal",
    ">=": "greater_or_equal",
    less_than: "less_than",
    "<": "less_than",
    less_or_equal: "less_or_equal",
    "<=": "less_or_equal",
    truthy: "truthy",
    falsy: "falsy",
    regex: "regex",
    startswith: "startswith",
    endswith: "endswith"
  }

  return operatorMap[operator] || "equals"
}

function mapConditionOperatorToRunner(operator) {
  const operatorMap = {
    equals: "==",
    not_equals: "!=",
    contains: "contains",
    not_contains: "not_contains",
    greater_than: ">",
    greater_or_equal: ">=",
    less_than: "<",
    less_or_equal: "<=",
    truthy: "truthy",
    falsy: "falsy",
    regex: "regex",
    startswith: "startswith",
    endswith: "endswith"
  }

  return operatorMap[operator] || "=="
}
