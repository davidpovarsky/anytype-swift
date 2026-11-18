# Account lifecycle: first native execution and callback correction

The first account run [44233581579](https://github.com/davidpovarsky/anytype-swift/actions/runs/44233581579), at App `9b320715b4835c9f1045c6d1680ca8e71417a66d`, built both exact native binaries successfully. The new-create phase then failed with a nil callback panic. No lifecycle phase passed; new-reopen, legacy-edit and new-recover did not run.

The fixture called `Space.DeriveTreeObject` without `TreeDerivationParams.InitFunc`. The existing cache creation path at `core/block/object/objectcache/cache.go:123` invokes that callback unconditionally, then fills the context, Space and build options. The fix supplies a callback returning an empty `smartblock.InitContext`, allowing the actual private factory to initialize through the normal native path. It does not modify production cache behavior, weaken assertions or replace the factory.

The changed Go source was formatted with the installed gofmt. Python controllers are unchanged. The corrected native runtime remains **NOT_RUN** until a fresh exact-source Linux run. App capability remains **OFF** and this fixture is not acceptance of two application clients.

`verified-failure.json` records artifact, receipt, native log and ELF hashes. The artifact was inspected in memory on the connected host; its digest matched GitHub metadata. Raw artifacts and logs remain in GitHub. No native account data, key, mnemonic or raw log was copied into this repository.
