def swift_testing_result(log):
    # Event grammar comes from retained, actually executed G04 Swift Testing6.4.3
    # stdout. Runtime descriptions of the private enum are retained as observed;
    # their exact spelling is not fabricated as a pre-execution compiled ID.
    lines = log.splitlines()
    assert not re.search(r"^Test Case '[^']+' started", log, re.M), 'Unexpected XCTest execution'
    assert not re.search(r'^.*(?:Test|Suite) .*\b(?:failed|skipped)\b', log, re.M), 'Failed or skipped test event'
    method_start = re.compile(r'^◇ Test ([A-Za-z_][A-Za-z_0-9]*)\(([^()\n]*)\) started\.$')
    method_pass = re.compile(r'^✔ Test ([A-Za-z_][A-Za-z_0-9]*)\(([^()\n]*)\) with 2 test cases passed after [0-9.]+ seconds\.$')
    case_event = re.compile(r'^(◇|✔) Test case passing 1 argument (.+) to ([A-Za-z_][A-Za-z_0-9]*)\(([^()\n]*)\) (started\.|passed after [0-9.]+ seconds\.)$')
    starts = {}; passes = {}; cases = {}; retained = []
    for offset, line in enumerate(lines):
        event = method_start.fullmatch(line)
        if event:
            name, signature = event.groups()
            assert name in METHODS and name not in starts, 'Unselected or duplicate method start'
            starts[name] = (signature, offset)
            retained.append(line)
            continue
        event = method_pass.fullmatch(line)
        if event:
            name, signature = event.groups()
            assert name in METHODS and name not in passes, 'Unselected or duplicate method PASS'
            passes[name] = (signature, offset)
            retained.append(line)
            continue
        event = case_event.fullmatch(line)
        if event:
            marker, argument, name, signature, outcome = event.groups()
            assert name in METHODS and argument.startswith('example → ') and len(argument) <= 2048
            assert (marker == '◇') == (outcome == 'started.'), 'Argument event status mismatch'
            assert name in starts and signature == starts[name][0]
            key = (name, argument)
            state = 'started' if marker == '◇' else 'passed'
            row = cases.setdefault(key, {})
            assert state not in row, 'Duplicate argument event'
            row[state] = offset
            retained.append(line)
            continue
        if re.match(r'^[◇✔✘↷] Test (?!run )', line):
            raise AssertionError('Unknown or unselected Swift Testing event: ' + line)
    assert set(starts) == set(passes) == set(METHODS), 'Require exactly the four selected actual method passes'
    assert len(cases) == 8, 'Require eight distinct actual argument cases, not declared count alone'
    actual = []
    for name in METHODS:
        assert starts[name][0] == passes[name][0]
        observed = [(argument, row) for (method, argument), row in cases.items() if method == name]
        assert len(observed) == 2, 'Each selected method must execute both distinct argument cases'
        for argument, row in observed:
            assert set(row) == {'started', 'passed'}
            assert starts[name][1] < row['started'] < row['passed'] < passes[name][1]
            actual.append({'method': name, 'actualEventSignature': name + '(' + starts[name][0] + ')',
                           'observedArgumentDescription': argument,
                           'startedLogLine': row['started'] + 1, 'passedLogLine': row['passed'] + 1})
    suite_name = 'Hierarchy rename preserves exact requested title bytes'
    suite_start = '◇ Suite "' + suite_name + '" (aka \'' + SUITE + '\') started.'
    suite_pass = re.escape('✔ Suite "' + suite_name + '" (aka \'' + SUITE + '\')') + r' passed after [0-9.]+ seconds\.'
    suite_lines = [(i, line) for i, line in enumerate(lines) if re.match(r'^[◇✔✘↷] Suite ', line)]
    assert len(suite_lines) == 2 and suite_lines[0][1] == suite_start
    assert re.fullmatch(suite_pass, suite_lines[1][1])
    assert suite_lines[0][0] < min(v[1] for v in starts.values())
    assert suite_lines[1][0] > max(v[1] for v in passes.values())
    totals = [(i, line) for i, line in enumerate(lines) if 'Test run with ' in line]
    assert len(totals) == 1 and re.fullmatch(r'✔ Test run with 4 tests in 1 suite passed after [0-9.]+ seconds\.', totals[0][1])
    assert totals[0][0] > suite_lines[1][0]
    return {'actualSwiftTestingMethods': list(METHODS), 'actualMethodCount': 4,
            'actualPassedArgumentCaseCount': 8, 'argumentCases': actual,
            'declaredSourceArgumentValues': ['latin', 'hebrew'],
            'argumentDescriptionSpellingIsObservedNotAnInventedCompiledSelector': True,
            'oldMethodsExecuted': 0, 'XCTestCases': 0, 'HTTPFixturesInvoked': 0,
            'observedTestOutcomeLines': retained + [line for _, line in suite_lines] + [totals[0][1]],
            'zeroXCTestOrSwiftTestingFooterIsNotAcceptance': True}
