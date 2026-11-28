export function deriveFinal64(input) {
  const require = (ok, message) => { if (!ok) throw new Error(message); };
  const clone = value => JSON.parse(JSON.stringify(value));
  const sorted = value => Array.isArray(value) ? value.map(sorted) :
    value && typeof value === "object" ?
      Object.fromEntries(Object.keys(value).sort().map(key => [key, sorted(value[key])])) : value;
  const render = value => JSON.stringify(sorted(value), null, 2) + "\n";
  const equal = (a, b) => render(a) === render(b);
  const keys = map => Object.keys(map.files).sort();
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const sdkPrefix = ".runtime-artifacts/sdk-source/";
  const parseMap = (raw, name) => {
    const map = JSON.parse(raw);
    require(equal(Object.keys(map).sort(), ["files", "modes"]), name + " map shape");
    require(equal(keys(map), Object.keys(map.modes).sort()), name + " complete modes");
    for (const path of keys(map)) {
      const row = map.files[path], mode = map.modes[path];
      require(path.length > 0 && !path.startsWith("/") && !path.includes("\\") &&
        !path.split("/").some(part => part === ".." || part === "" || part === "."),
        name + " relative source path");
      require(equal(Object.keys(row).sort(), ["bytes", "sha256"]) &&
        Number.isSafeInteger(row.bytes) && row.bytes >= 0 && /^[0-9a-f]{64}$/.test(row.sha256) &&
        Number.isSafeInteger(mode) && mode >= 0 && mode <= 4095, name + " exact source row");
    }
    require(render(map) === raw, name + " canonical complete bytes");
    return map;
  };
  const rowMatches = (map, path, row) => own(map.files, path) && own(map.modes, path) &&
    equal(map.files[path], {bytes: row.bytes, sha256: row.sha256}) &&
    map.modes[path] === row.nativeMode;
  const apply = (map, actions, includeTests) => {
    const result = clone(map);
    for (const action of actions) {
      if (!includeTests && action.kind === "test") continue;
      const path = action.sourceRelativePath;
      require(["production", "test"].includes(action.kind), "declared action kind");
      require(["replace", "add"].includes(action.action), "declared action");
      if (action.action === "replace") {
        require(action.before !== null && rowMatches(result, path, action.before),
          "exact before-image " + path);
      } else {
        require(action.before === null && !own(result.files, path) && !own(result.modes, path),
          "new source path absent " + path);
      }
      result.files[path] = {bytes: action.after.bytes, sha256: action.after.sha256};
      result.modes[path] = action.after.nativeMode;
    }
    return sorted(result);
  };
  const inverse = (map, actions, includeTests) => {
    const result = clone(map);
    for (const action of [...actions].reverse()) {
      if (!includeTests && action.kind === "test") continue;
      const path = action.sourceRelativePath;
      require(rowMatches(result, path, action.after), "inverse exact after-image " + path);
      if (action.action === "add") {
        delete result.files[path];
        delete result.modes[path];
      } else {
        result.files[path] = {bytes: action.before.bytes, sha256: action.before.sha256};
        result.modes[path] = action.before.nativeMode;
      }
    }
    return sorted(result);
  };
  const projection = map => {
    const files = {}, modes = {};
    for (const path of keys(map)) if (path.startsWith(sdkPrefix)) {
      files[path.slice(sdkPrefix.length)] = clone(map.files[path]);
      modes[path.slice(sdkPrefix.length)] = map.modes[path];
    }
    return sorted({files, modes});
  };
  const changedPaths = (before, after) => [...new Set([...keys(before), ...keys(after)])]
    .filter(path => !equal(before.files[path] ?? null, after.files[path] ?? null) ||
      (before.modes[path] ?? null) !== (after.modes[path] ?? null)).sort();
  const maps = {};
  for (const [name, raw] of Object.entries(input.mapTexts)) maps[name] = parseMap(raw, name);
  require(input.n24Overlay.files.every(row => ["production", "qualification-test"].includes(row.kind)),
    "N24 declared source kinds");
  const nActions = input.n24Overlay.files.map(row => ({
    stage: "n24-bound-http-acl", kind: row.kind === "qualification-test" ? "test" : row.kind,
    sourceDeclaredKind: row.kind, action: row.action,
    sourceRelativePath: row.sourceRelativePath,
    carrierCommit: input.n24Commit, carrierPath: row.carrierPath,
    before: row.preimage === null ? null : {
      bytes: row.preimage.bytes, sha256: row.preimage.sha256, nativeMode: row.preimage.nativeMode
    },
    after: {bytes: row.bytes, sha256: row.sha256, nativeMode: row.nativeMode}
  }));
  const rootActions = clone(input.rootActions).map(row => ({
    ...row, carrierCommit: row.carrierCommit === "THIS_COMMIT" ? input.lifecycleCommit : row.carrierCommit
  }));
  const brokerActions = clone(input.brokerActions);
  const nPaths = new Set(nActions.map(row => row.sourceRelativePath));
  const rootPaths = new Set(rootActions.map(row => row.sourceRelativePath));
  require(rootActions.every(row => !nPaths.has(row.sourceRelativePath)), "N24 and boot/lifecycle source paths disjoint");
  require(brokerActions.every(row => !nPaths.has(row.sourceRelativePath) &&
    !rootPaths.has(row.sourceRelativePath)), "broker source paths disjoint");
  require(brokerActions.length === 2 && brokerActions[0].kind === "production" &&
    brokerActions[0].action === "replace" && brokerActions[1].kind === "test" &&
    brokerActions[1].action === "add", "one broker replacement and one new test");
  require(render(apply(maps.base, nActions, false)) === input.mapTexts.n24Production, "base to exact N24 production");
  require(render(apply(maps.base, nActions, true)) === input.mapTexts.n24Qualification, "base to exact N24 qualification");
  require(render(apply(maps.n24Production, rootActions, false)) === input.mapTexts.rootProduction, "N24 to exact lifecycle production");
  require(render(apply(maps.n24Qualification, rootActions, true)) === input.mapTexts.rootQualification, "N24 to exact lifecycle qualification");
  require(render(projection(maps.rootProduction)) === input.mapTexts.n24SDKProduction, "unchanged pre-broker SDK production projection");
  const production = apply(maps.rootProduction, brokerActions, false);
  const qualification = apply(maps.rootQualification, brokerActions, true);
  require(equal(changedPaths(maps.rootProduction, production), [brokerActions[0].sourceRelativePath]), "one production metadata replacement");
  require(equal(changedPaths(maps.rootQualification, qualification),
    brokerActions.map(row => row.sourceRelativePath).sort()), "two qualification metadata changes");
  const inverseStages = [];
  for (const [kind, finalMap, includeTests, rootName, nName] of [
    ["production", production, false, "rootProduction", "n24Production"],
    ["qualification", qualification, true, "rootQualification", "n24Qualification"]
  ]) {
    let current = inverse(finalMap, brokerActions, includeTests);
    require(render(current) === input.mapTexts[rootName], kind + " broker inverse exact full bytes");
    inverseStages.push({kind, restored: rootName, files: keys(current).length, raw: render(current)});
    current = inverse(current, rootActions, includeTests);
    require(render(current) === input.mapTexts[nName], kind + " lifecycle inverse exact full bytes");
    inverseStages.push({kind, restored: nName, files: keys(current).length, raw: render(current)});
    current = inverse(current, nActions, includeTests);
    require(render(current) === input.mapTexts.base, kind + " N24 inverse exact original full bytes");
    inverseStages.push({kind, restored: "base", files: keys(current).length, raw: render(current)});
  }
  const allActions = [...nActions, ...rootActions, ...brokerActions];
  const finalSources = new Map();
  for (const action of allActions) finalSources.set(action.sourceRelativePath, action);
  for (const [path, action] of finalSources) {
    require(rowMatches(qualification, path, action.after), "final qualification source " + path);
    if (action.kind === "production") require(rowMatches(production, path, action.after), "final production source " + path);
    else require(!own(production.files, path), "new test excluded from production " + path);
  }
  const selectionGroups = [];
  const n = input.n24Selection, boot = input.bootSelection, broker = input.brokerSelection;
  for (const [label, group] of Object.entries(n.groups)) for (const [pkg, parents] of Object.entries(group.packages)) {
    selectionGroups.push({suite: "N24", label, cwd: group.cwd, package: pkg,
      packagePath: group.cwd === "sdk" ? "." : "./internal/server", tags: [],
      parents: [...parents], children: n.expectedChildren.filter(name => parents.includes(name.split("/")[0]))});
  }
  for (const group of boot.packages) selectionGroups.push({
    suite: "boot-lifecycle33", label: group.path, cwd: "any",
    package: "github.com/anyproto/any/" + group.path.slice(2), packagePath: group.path,
    tags: [...group.tags], requiresCGO: group.requiresCGO === true,
    parents: [...group.parents], children: boot.expectedChildren.filter(name => group.parents.includes(name.split("/")[0]))
  });
  selectionGroups.push({suite: "broker7", label: "broker-cancellation", cwd: "sdk",
    package: "github.com/anyproto/any-sync-sdk/internal/files/broker", packagePath: broker.package, tags: [],
    parents: [...broker.parents], children: [...broker.children]});
  const suites = [
    {name: "N24", parents: n.parentMethods, children: n.expectedChildren, parentCount: 9, childCount: 15, total: 24},
    {name: "boot-lifecycle33", parents: boot.exactParentMethods, children: boot.expectedChildren, parentCount: 17, childCount: 16, total: 33},
    {name: "broker7", parents: broker.parents, children: broker.children, parentCount: 5, childCount: 2, total: 7}
  ];
  const events = [];
  for (const suite of suites) {
    const groups = selectionGroups.filter(group => group.suite === suite.name);
    const parents = groups.flatMap(group => group.parents), children = groups.flatMap(group => group.children);
    require(equal([...parents].sort(), [...suite.parents].sort()) &&
      equal([...children].sort(), [...suite.children].sort()), "exact suite selection " + suite.name);
    require(parents.length === suite.parentCount && new Set(parents).size === parents.length &&
      children.length === suite.childCount && new Set(children).size === children.length &&
      parents.length + children.length === suite.total, "suite count and uniqueness " + suite.name);
    for (const group of groups) {
      for (const child of group.children) require(group.parents.includes(child.split("/")[0]), "child belongs to selected parent");
      for (const kind of ["parent", "child"]) for (const name of kind === "parent" ? group.parents : group.children) {
        events.push({suite: group.suite, kind, test: name, cwd: group.cwd,
          package: group.package, tags: [...group.tags]});
      }
    }
  }
  require(new Set(events.map(row => row.test)).size === events.length, "no global test-name overlap");
  require(new Set(events.map(row => row.package + "\0" + row.test)).size === events.length, "no package/event overlap");
  const parents = events.filter(row => row.kind === "parent"), children = events.filter(row => row.kind === "child");
  require(parents.length === 31 && children.length === 33 && events.length === 64, "exact 31/33/64 union");
  require(events.filter(row => row.test === "TestStartAddressStop").length === 1, "legacy StartAddressStop selected once");
  const sdkProduction = projection(production), sdkQualification = projection(qualification);
  const counts = {production: keys(production).length, qualification: keys(qualification).length,
    sdkProduction: keys(sdkProduction).length, sdkQualification: keys(sdkQualification).length,
    orderedSourceActions: allActions.length, finalChangedSourcePaths: finalSources.size,
    selectedParentEvents: parents.length, selectedChildEvents: children.length, selectedEvents: events.length};
  require(counts.production === 1648 && counts.qualification === 1657 &&
    counts.sdkProduction === 755 && counts.sdkQualification === 757, "exact source counts");
  return {
    maps: {production, qualification, sdkProduction, sdkQualification},
    mapTexts: {production: render(production), qualification: render(qualification),
      sdkProduction: render(sdkProduction), sdkQualification: render(sdkQualification)},
    orderedActions: allActions, finalSources: [...finalSources.values()].sort((a,b) =>
      a.sourceRelativePath < b.sourceRelativePath ? -1 : a.sourceRelativePath > b.sourceRelativePath ? 1 : 0),
    inverseStages, counts, selectionGroups, events,
    testsExecuted: 0, nativeExecutions: 0, physicalMaterializations: 0
  };
}
