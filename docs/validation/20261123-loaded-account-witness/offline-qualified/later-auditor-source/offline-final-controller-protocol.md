# Later final controller audit

This is a new ordinary-UID read-only observation. It does not reconstruct the missing historical current_source_after or loaded-after observation from the failed offline completion. It does not rerun Go, graph parsing, the codec, ordinary dependency hashing, captured native source/tool hashing, a container, a mount, a build or a test.

The original complete_projected_graph.py at clean1b98 remains byte-identical. Its original result is FAILED with only final controller Git status exit128. The completed graph's original before/after equality is retained, not rerun.

The auditor compares exactly28 current controller records with retained current-source-before.json.gz (SHA2a5d9b30...). Git HEAD and selected paths stay1b98; Git object SHA-1, physical SHA-256, mode and every captured decimal metadata string are compared. The old producer __main__ file is only a file-origin binding. The separate external auditor records its own actual-loaded before/after identity and expressly leaves historical loaded-after absent.

Installed /usr/bin/git is4,003,072B/SHA068c11a6747b848c3ed35599f714250864d2bd94b4165d27770ce5c36e83894f, package1:2.43.0-1ubuntu7.4. Installed git-config.1.gz SHA5fd1cd7f480c9890ccac7ff1a201043793dc090345c24c92527550b721828b19 documents the supported packedGitWindowSize and packedGitLimit settings. Only each new Git command receives -c core.packedGitWindowSize=16m -c core.packedGitLimit=64m. No persistent configuration changes. The observed401,958,671B pack tuple and original ENOMEM are preserved; no pack payload was read in diagnosis, and no precise allocation/syscall cause is claimed.

The new reader keeps a512MiB address-space ceiling (never raises inherited limits),120s overall/20s per Git command, finite5s TERM+5s KILL cleanup for its exact owned Popen group,256KiB each stdout/stderr,1GiB+16MiB disk start/1GiB final,16MiB original-query+offline+new evidence, and16MiB explicit fixed-file reads. This last counter excludes Git's own pack I/O, which has finite mapping limits and command deadlines. No older successful scope is replayed.
