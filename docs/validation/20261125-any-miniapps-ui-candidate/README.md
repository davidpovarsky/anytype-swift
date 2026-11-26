# Real Any MiniApps UI candidate

Adds one independent method to the existing NativeLaunchTests file. Removing the appended extension restores every existing original method and helper byte-for-byte. It requires a newly created disposable simulator, the actual combined app and the actual installed Hanlin MiniApps companion. It uses the ordinary app storage/Keychain configuration, not a test-only data override, so the OS cold callback can reopen the same original native account.

The method creates an actual account/Space/document through the normal UI, invokes Text Studio through the shared picker, enters separate warm/cold text in the real companion and requires the companion callback to foreground Anytype without launch/activate/open assistance. After the cold callback it performs the native app's ordinary saved-account/Space selection; the pending validated request must select its document without manual document navigation. It explicitly does not claim unattended account authentication.

The existing read-only native-versus-editor observer verifies the original paragraph, original IDs, two returned paragraphs, same object/Space, exact content hashes and a separate cold process readback. It performs zero mutation/extra engine calls. The existing prepared-result native controls remain separate from this real cross-app UI scenario. No simulated result, permission grant or ACK is injected.

Status: candidate only. No application build or UI execution is claimed by this source checkpoint. The source App may be reused with an explicitly bound UI-only derivative; the new runner must have actual Apple compilation and exact selector enumeration before execution.
