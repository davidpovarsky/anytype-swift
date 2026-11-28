def mixed_test_result(log):
    # XCTest grammar is retained from actual Property4; Swift Testing grammar
    # is retained from actual G04/Hierarchy. Each positive framework is required.
    lines = log.splitlines()
    case_re = re.compile(r"^Test Case '(?:[A-Za-z_][A-Za-z_0-9]*\.)*NativeBookmarkPresentationTests\.([^']+)' (started at .+|passed \([0-9.]+ seconds\))$")
    starts = {}; passes = {}; xctest_events = []
    for index, line in enumerate(lines):
        if not line.startswith('Test Case '):
            continue
        match = case_re.fullmatch(line)
        assert match, 'Unknown, failed, skipped or unselected XCTest event: ' + line
        name, outcome = match.groups()
        assert name in XCTEST_METHODS
        target = starts if outcome.startswith('started') else passes
        assert name not in target, 'Duplicate XCTest event'
        target[name] = index
        xctest_events.append(line)
    assert set(starts) == set(passes) == set(XCTEST_METHODS), 'All four selected XCTest cases must pass'
    assert all(starts[name] < passes[name] for name in XCTEST_METHODS)
    suite_start = [(i, line) for i, line in enumerate(lines)
                   if re.fullmatch(r"Test Suite 'NativeBookmarkPresentationTests' started at .+", line)]
    suite_pass = [(i, line) for i, line in enumerate(lines)
                  if re.fullmatch(r"Test Suite 'NativeBookmarkPresentationTests' passed at .+", line)]
    assert len(suite_start) == len(suite_pass) == 1
    assert suite_start[0][0] < min(starts.values()) <= max(passes.values()) < suite_pass[0][0]
    xctest_suites = [line for line in lines if line.startswith('Test Suite ')]
    assert all(re.fullmatch(r"Test Suite '(Selected tests|NativeBookmarkPresentationTests)' (started|passed) at .+", line)
               for line in xctest_suites), 'Unknown, failed or skipped XCTest suite'
    summaries = [line.strip() for line in lines if line.strip().startswith('Executed ')]
    summary_re = re.compile(r'Executed (0|4) tests, with 0 failures(?: \(0 unexpected\))? in [0-9.]+ \([0-9.]+\) seconds')
    counts = []
    for line in summaries:
        match = summary_re.fullmatch(line)
        assert match, 'Unknown XCTest result summary'
        counts.append(int(match.group(1)))
    assert counts.count(4) == 2 and counts.count(0) <= 1

    method_start = re.compile(r'^◇ Test ([A-Za-z_][A-Za-z_0-9]*)\(\) started\.$')
    method_pass = re.compile(r'^✔ Test ([A-Za-z_][A-Za-z_0-9]*)\(\) passed after [0-9.]+ seconds\.$')
    swift_starts = {}; swift_passes = {}; swift_events = []
    for index, line in enumerate(lines):
        start = method_start.fullmatch(line)
        passed = method_pass.fullmatch(line)
        if start or passed:
            name = (start or passed).group(1)
            assert name in SWIFT_TESTING_METHODS, 'Unselected Swift Testing method'
            target = swift_starts if start else swift_passes
            assert name not in target, 'Duplicate Swift Testing event'
            target[name] = index
            swift_events.append(line)
        elif re.match(r'^[◇✔✘↷] Test (?!run )', line):
            raise AssertionError('Unknown, failed, skipped or parameterized Swift Testing event: ' + line)
    assert set(swift_starts) == set(swift_passes) == set(SWIFT_TESTING_METHODS), 'Both selected Swift Testing cases must pass'
    assert all(swift_starts[name] < swift_passes[name] for name in SWIFT_TESTING_METHODS)
    suite_name = 'Native wiki hierarchy preserves the original tree domain'
    swift_suite_start = '◇ Suite "' + suite_name + '" (aka \'AnyHierarchyTests\') started.'
    swift_suite_pass = re.escape('✔ Suite "' + suite_name + '" (aka \'AnyHierarchyTests\')') + r' passed after [0-9.]+ seconds\.'
    suite_lines = [(i, line) for i, line in enumerate(lines) if re.match(r'^[◇✔✘↷] Suite ', line)]
    assert len(suite_lines) == 2 and suite_lines[0][1] == swift_suite_start
    assert re.fullmatch(swift_suite_pass, suite_lines[1][1])
    assert suite_lines[0][0] < min(swift_starts.values()) <= max(swift_passes.values()) < suite_lines[1][0]
    totals = [(i, line) for i, line in enumerate(lines) if 'Test run with ' in line]
    positive = []; empty = []
    for index, line in totals:
        if re.fullmatch(r'✔ Test run with 2 tests in 1 suite passed after [0-9.]+ seconds\.', line):
            positive.append((index, line))
        elif re.fullmatch(r'✔ Test run with 0 tests passed after [0-9.]+ seconds\.', line):
            empty.append((index, line))
        else:
            raise AssertionError('Unknown Swift Testing total: ' + line)
    assert len(positive) == 1 and len(empty) <= 1 and positive[0][0] > suite_lines[1][0]
    assert all(index < suite_lines[0][0] or index > positive[0][0] for index, _ in empty)
    # A toolchain may omit the other product's empty-framework output. A retained
    # empty footer is bounded to that one other product and grants no test credit.
    run_starts = [i for i, line in enumerate(lines) if line == '◇ Test run started.']
    assert len(run_starts) == len(totals)
    assert run_starts and run_starts[0] < totals[0][0]
    return {'actualXCTestMethods': list(XCTEST_METHODS), 'actualXCTestCaseCount': 4,
            'actualSwiftTestingMethods': list(SWIFT_TESTING_METHODS), 'actualSwiftTestingCaseCount': 2,
            'actualMethodCount': 6, 'actualCaseCount': 6,
            'hostLiteralScenarios': 17, 'literalScenariosAreEnumeratedTests': False,
            'oldHostMethodsExecuted': 0, 'oldIntegrationMethodsExecuted': 0,
            'HTTPFixturesInvoked': 0, 'nativeCalls': 0,
            'observedXCTestLines': xctest_events + xctest_suites + summaries,
            'observedSwiftTestingLines': swift_events + [line for _, line in suite_lines] + [line for _, line in totals],
            'emptyFrameworkOutputsObserved': {'XCTestSummaries': counts.count(0), 'SwiftTestingFooters': len(empty)},
            'zeroFrameworkFooterIsNotAcceptance': True,
            'actualEventNamesAreObservedNotPreclaimedCompiledEnumeration': True}
