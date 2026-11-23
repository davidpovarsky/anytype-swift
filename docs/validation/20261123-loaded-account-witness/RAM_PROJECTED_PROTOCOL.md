# Projected RAM source query (NOT_RUN)

This opt-in controller is a separately named continuation of the failed RAM source query. It does not run native builds or tests. The original disk graph (6aac), original RAM profile (3b7b), failed query, failed cleanup, failed recovery V1, and later recovery V2 remain unchanged. One actual Go query has occurred in the original profile; this projected profile has executed zero queries.

## Exact source projection

The new command uses Go's -json= form with precisely the 24 top-level fields consumed by the unchanged dependency_plan function. A static AST comparison binds this set to every literal package access and all sixteen file-array names. Module is retained as a whole nested value, including Replace and GoMod. Deps, Imports, ImportMap, Stale and BuildID were never source-identity inputs to this parser.

The source review pins the actual Go 1.26.5 list.go and work/exec.go implementations. The projected option does not introduce -compiled or -export. Generated test-main handling, module replacement, complete source hashes, private RAM custody, all output limits, and the original parser's refusals remain unchanged. A successful complete graph must still be observed; projection is not a substitute for a result.

## Process ownership and credentials

The fixed entry requires sudo -n python3 -I -B. Isolated mode excludes project/PYTHONPATH import discovery; only standard-library imports precede adoption. Entry real/effective/saved IDs are root with group0, and SUDO_UID/GID must identify1001. System account lookup must match the observed ordinary GID1001 and supplementary groups4,24,27,30,104,1001. Before resolving project paths or doing source/data/Git operations, this process adopts real/effective UID1001 and ordinary groups, retaining saved UID0.

Only stop_owned temporarily restores effective UID0. A private registry binds the actual subprocess.Popen object, PID=PGID and the identical caller-owned record created at one of the two fixed spawn sites. There is no caller-supplied PID channel. The old finite TERM/KILL/absence body is byte-exact after an internal function-name substitution.

SIGTERM/SIGINT are deferred while that finite cleanup body runs. Its finally restores ordinary effective UID before delivering a pending handled signal or performing project/file/Git operations. The receipt retains ordinary-before, privileged, ordinary-after and separate first/restoration/signal errors. Failure to restore exits126 with finite metadata on the existing stderr and leaves custody unresolved; it must not proceed into project I/O or claim cleanup. This process-local saved-UID mechanism changes no account, group, daemon, ACL or persistent permission configuration.

## Separate resources and custody

The new container, tmpfs source/path and evidence directory have fixed distinct names. The earlier stopped container is retained. The RAM budget remains64MiB/8192inodes, query120s, stdout8MiB, stderr1MiB, total evidence16MiB. Source-query disk gates remain1GiB+16MiB start and1GiB active/final, with4GiB/2GiB memory gates. Complete remaining RAM bytes must be preserved and independently read back before exact normal unmount. Any guard failure retains the appropriate original failure and custody.

Native compile gates remain2.95GB start,2.60GB stop and2.50GB final reserve. This source-only profile grants no native/account/semantic/file-completeness or destination-write acceptance. The four new native loaded-account controls remain NOT_RUN.
